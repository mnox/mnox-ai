#!/usr/bin/env python3
"""Parse a PostgreSQL `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` plan and flag bottlenecks.

Walks every node and surfaces the tell-tale signals of a slow query: cardinality
misestimation (estimated vs actual rows), the highest self-time node, sequential
scans discarding most rows, nested loops over large inner sets, sort/hash spills to
disk, heavy disk reads vs cache hits, and index-only-scan heap fetches.

Input: the JSON array emitted by `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) <query>`.
Pass a file path, or pipe the JSON in on stdin (no argument).

Stdlib only — runs on the system python3, no third-party dependencies.

Usage:
    python3 analyze_plan.py plan.json
    python3 analyze_plan.py plan.json --pretty
    psql -XqAt -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT ..." | python3 analyze_plan.py
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# Tuning thresholds for what counts as "worth flagging".
MISESTIMATE_RATIO = 10.0  # estimated vs actual rows off by this factor
SEQSCAN_FILTER_DISCARD = 0.9  # fraction of scanned rows thrown away by filter
SEQSCAN_MIN_ROWS = 10_000  # ignore tiny seq scans (they're fine)
NESTLOOP_MIN_LOOPS = 1_000  # nested-loop inner executed this many times
READ_HEAVY_BLOCKS = 10_000  # shared-read blocks worth calling out
READ_HEAVY_RATIO = 0.5  # reads / (reads + hits) above this = cache-cold / I/O bound


def _num(node: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    """Return the first present numeric key, else default."""
    for key in keys:
        if key in node and node[key] is not None:
            try:
                return float(node[key])
            except (TypeError, ValueError):
                return default
    return default


def _inclusive_time(node: dict[str, Any]) -> float:
    """Total wall time attributable to this node and its subtree (ms).

    `Actual Total Time` is per-loop; multiply by loops for the real contribution.
    """
    return _num(node, "Actual Total Time") * _num(node, "Actual Loops", default=1.0)


def _label(node: dict[str, Any]) -> str:
    parts = [node.get("Node Type", "?")]
    for key in ("Relation Name", "Index Name", "CTE Name", "Alias"):
        if node.get(key):
            parts.append(f"on {node[key]}")
            break
    return " ".join(parts)


def _walk(node: dict[str, Any], findings: list[dict], depth: int = 0) -> None:
    children = node.get("Plans", []) or []

    est_rows = _num(node, "Plan Rows")
    act_rows = _num(node, "Actual Rows")
    label = _label(node)

    # Self-time: inclusive minus the children's inclusive contribution.
    self_time = _inclusive_time(node) - sum(_inclusive_time(c) for c in children)

    # 1. Cardinality misestimation — the #1 root signal.
    if act_rows > 0 and est_rows >= 0:
        hi, lo = max(est_rows, act_rows), max(min(est_rows, act_rows), 1.0)
        ratio = hi / lo
        if ratio >= MISESTIMATE_RATIO and max(est_rows, act_rows) >= 100:
            direction = "under" if est_rows < act_rows else "over"
            findings.append({
                "signal": "row_misestimate",
                "node": label,
                "severity": "high",
                "estimated_rows": est_rows,
                "actual_rows": act_rows,
                "ratio": round(ratio, 1),
                "detail": (
                    f"Planner {direction}estimated rows by {round(ratio, 1)}x "
                    f"(est {est_rows:.0f} vs actual {act_rows:.0f}). "
                    "Usual cause: stale/insufficient statistics or correlated columns. "
                    "Fix: ANALYZE the table; raise column STATISTICS target or "
                    "add CREATE STATISTICS."
                ),
            })

    # 2. Sequential scan discarding most of what it reads -> missing index.
    if node.get("Node Type") == "Seq Scan":
        removed = _num(node, "Rows Removed by Filter")
        scanned = removed + act_rows
        if scanned >= SEQSCAN_MIN_ROWS and removed / max(scanned, 1) >= SEQSCAN_FILTER_DISCARD:
            findings.append({
                "signal": "seqscan_high_discard",
                "node": label,
                "severity": "high",
                "rows_removed_by_filter": removed,
                "rows_kept": act_rows,
                "detail": (
                    f"Seq Scan read ~{scanned:.0f} rows and discarded {removed:.0f} by filter. "
                    "A selective index on the filtered column(s) would avoid the scan. "
                    "Fix: CREATE INDEX CONCURRENTLY; confirm the re-plan uses it."
                ),
            })

    # 3. Nested loop driving a large number of inner executions.
    if node.get("Node Type") == "Nested Loop":
        inner_loops = max((_num(c, "Actual Loops", default=1.0) for c in children), default=1.0)
        if inner_loops >= NESTLOOP_MIN_LOOPS:
            findings.append({
                "signal": "nestloop_high_loops",
                "node": label,
                "severity": "medium",
                "inner_loops": inner_loops,
                "detail": (
                    f"Nested Loop executes its inner side ~{inner_loops:.0f} times. "
                    "Often the fallout of a row underestimate — the planner thought the outer "
                    "side was tiny. Fix the estimate (ANALYZE) so a Hash/Merge Join is chosen, "
                    "or index the inner relation. Test with SET enable_nestloop=off."
                ),
            })

    # 4. Sort spilling to disk -> work_mem too low.
    if node.get("Sort Method") and "disk" in str(node["Sort Method"]).lower():
        findings.append({
            "signal": "sort_spill_disk",
            "node": label,
            "severity": "medium",
            "sort_method": node["Sort Method"],
            "sort_space_kb": _num(node, "Sort Space Used"),
            "detail": (
                f"Sort spilled to disk ({node['Sort Method']}, "
                f"{_num(node, 'Sort Space Used'):.0f} kB). "
                "Fix: raise work_mem for the session/role (not globally), or reduce sorted volume."
            ),
        })

    # 5. Hash join spilling into multiple batches -> work_mem too low.
    batches = _num(node, "Hash Batches", "Original Hash Batches")
    if batches > 1:
        findings.append({
            "signal": "hash_spill_batches",
            "node": label,
            "severity": "medium",
            "hash_batches": batches,
            "detail": (
                f"Hash node used {batches:.0f} batches (>1 means it spilled to disk). "
                "Fix: raise work_mem, or shrink the hashed input."
            ),
        })

    # 6. I/O-bound node: many disk reads vs cache hits.
    reads = _num(node, "Shared Read Blocks")
    hits = _num(node, "Shared Hit Blocks")
    if reads >= READ_HEAVY_BLOCKS and reads / max(reads + hits, 1) >= READ_HEAVY_RATIO:
        findings.append({
            "signal": "io_heavy",
            "node": label,
            "severity": "medium",
            "shared_read_blocks": reads,
            "shared_hit_blocks": hits,
            "detail": (
                f"Node read {reads:.0f} blocks from disk vs {hits:.0f} cache hits. "
                "Working set doesn't fit cache, or a missing index forces a large scan. "
                "Address the scan (index) before assuming a memory problem."
            ),
        })

    # 7. Index-only scan still hitting the heap -> visibility map stale (VACUUM).
    heap_fetches = _num(node, "Heap Fetches")
    if node.get("Node Type") == "Index Only Scan" and heap_fetches > 0:
        findings.append({
            "signal": "ios_heap_fetches",
            "node": label,
            "severity": "low",
            "heap_fetches": heap_fetches,
            "detail": (
                f"Index-Only Scan did {heap_fetches:.0f} heap fetches (visibility checks). "
                "Fix: VACUUM the table to refresh the visibility map."
            ),
        })

    node["_self_time_ms"] = round(self_time, 3)
    node["_label"] = label

    for child in children:
        _walk(child, findings, depth + 1)


def _collect_nodes(node: dict[str, Any], out: list[dict]) -> None:
    out.append(node)
    for child in node.get("Plans", []) or []:
        _collect_nodes(child, out)


def _verdict(findings: list[dict]) -> str:
    if not findings:
        return (
            "No structural red flags detected. The plan's estimates track reality and "
            "nothing spilled or scanned wastefully. If it's still slow, the cost is likely "
            "raw data volume (check the top self-time node) or the query simply runs too often "
            "(check pg_stat_statements total time)."
        )
    highs = [f for f in findings if f["severity"] == "high"]
    if highs:
        return (
            f"{len(highs)} high-severity signal(s) found — start with "
            f"'{highs[0]['signal']}' on {highs[0]['node']}."
        )
    return f"{len(findings)} signal(s) found; highest is '{findings[0]['signal']}'."


def analyze(raw: str) -> dict[str, Any]:
    """Analyze raw EXPLAIN JSON text and return a structured result dict."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "error": (
                f"Input is not valid JSON ({exc}). "
                "Re-run EXPLAIN with the FORMAT JSON option: "
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) <query>"
            ),
        }

    # EXPLAIN JSON is an array with a single object holding "Plan".
    root_obj = data[0] if isinstance(data, list) and data else data
    if not isinstance(root_obj, dict) or "Plan" not in root_obj:
        return {
            "success": False,
            "error": (
                "No 'Plan' key found. This script expects EXPLAIN (ANALYZE, BUFFERS, "
                "FORMAT JSON) output. Plain-text EXPLAIN is not supported."
            ),
        }

    plan = root_obj["Plan"]
    if "Actual Rows" not in plan and "Actual Total Time" not in plan:
        return {
            "success": False,
            "error": (
                "Plan has no actual-execution numbers. Run EXPLAIN with ANALYZE "
                "(not just EXPLAIN) so estimated-vs-actual can be compared. "
                "Warning: ANALYZE executes the query — wrap writes in BEGIN; ... ROLLBACK;."
            ),
        }

    findings: list[dict] = []
    _walk(plan, findings)

    all_nodes: list[dict] = []
    _collect_nodes(plan, all_nodes)
    hotspots = sorted(all_nodes, key=lambda n: n.get("_self_time_ms", 0.0), reverse=True)[:5]

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: severity_rank.get(f["severity"], 9))

    return {
        "success": True,
        "planning_time_ms": _num(root_obj, "Planning Time"),
        "execution_time_ms": _num(root_obj, "Execution Time"),
        "node_count": len(all_nodes),
        "top_self_time_nodes": [
            {"node": n.get("_label", "?"), "self_time_ms": n.get("_self_time_ms", 0.0)}
            for n in hotspots
        ],
        "findings": findings,
        "verdict": _verdict(findings),
    }


def _print_pretty(result: dict[str, Any]) -> None:
    print(f"Execution time: {result['execution_time_ms']:.1f} ms "
          f"(planning {result['planning_time_ms']:.1f} ms, {result['node_count']} nodes)")
    print(f"\nVerdict: {result['verdict']}\n")
    if result["findings"]:
        print("Findings (highest severity first):")
        for f in result["findings"]:
            print(f"  [{f['severity'].upper()}] {f['signal']} @ {f['node']}")
            print(f"      {f['detail']}")
    print("\nTop self-time nodes:")
    for n in result["top_self_time_nodes"]:
        print(f"  {n['self_time_ms']:>10.3f} ms  {n['node']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze an EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) plan and flag bottlenecks.",
    )
    parser.add_argument(
        "plan_file",
        nargs="?",
        default="-",
        help="Path to the EXPLAIN JSON file. Omit (and pipe in) to read from stdin.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print a human-readable summary instead of raw JSON.",
    )
    args = parser.parse_args(argv)

    if args.plan_file == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(args.plan_file) as fh:
                raw = fh.read()
        except FileNotFoundError:
            print(json.dumps({"success": False, "error": f"File not found: {args.plan_file}"}))
            return 1

    result = analyze(raw)

    if not args.pretty:
        print(json.dumps(result, indent=2))
        return 0 if result.get("success") else 1

    if not result.get("success"):
        print(f"ERROR: {result['error']}")
        return 1
    _print_pretty(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
