#!/usr/bin/env python3
"""Summarize bash_gate.log.jsonl.

Usage:
  bash_gate_stats.py --since 24h
  bash_gate_stats.py --cleanup [--retain-days 30]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Mirror bash_gate.py: the JSONL log lives in the user-writable home, not inside
# the (read-only, update-replaced) plugin tree. Override with BASH_GATE_HOME.
USER_DIR = Path(os.environ.get("BASH_GATE_HOME") or os.path.expanduser("~/.config/bash-gate"))
LOG_PATH = Path(os.environ.get("BASH_GATE_TEST_LOG") or (USER_DIR / "bash_gate.log.jsonl"))


def _parse_since(s: str) -> timedelta:
    m = re.fullmatch(r"(\d+)([hdm])", s.strip())
    if not m:
        raise ValueError(f"bad --since value: {s!r} (use e.g. 24h, 7d, 30m)")
    n = int(m.group(1))
    unit = m.group(2)
    return {"h": timedelta(hours=n), "d": timedelta(days=n), "m": timedelta(minutes=n)}[unit]


def _iter_entries(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def _parse_ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def cmd_summary(since: str) -> int:
    delta = _parse_since(since)
    cutoff = datetime.now(timezone.utc).astimezone() - delta

    by_decision_class: Counter = Counter()
    deferred_reasons: Counter = Counter()
    total = 0

    # Phase 2g arbiter telemetry.
    arb_verdicts: Counter = Counter()
    arb_escalations: Counter = Counter()
    arb_latencies: list[int] = []
    arb_auto_approved: Counter = Counter()
    arb_declined: Counter = Counter()
    arb_total = 0

    for e in _iter_entries(LOG_PATH):
        ts = _parse_ts(e.get("ts", ""))
        if ts is None or ts < cutoff:
            continue
        total += 1
        decision = e.get("decision", "")
        cls = e.get("class", "") or "-"
        by_decision_class[(decision, cls)] += 1
        if decision == "defer":
            deferred_reasons[e.get("reason", "")] += 1

        arb = e.get("arbiter")
        if isinstance(arb, dict) and arb.get("fired"):
            arb_total += 1
            arb_verdicts[arb.get("verdict", "?")] += 1
            arb_escalations[arb.get("escalation", "?")] += 1
            lat = arb.get("latency_ms")
            if isinstance(lat, int):
                arb_latencies.append(lat)
            cmd_short = (e.get("cmd", "") or "").strip().replace("\n", " ")[:60]
            if arb.get("escalation") == "auto-approved":
                arb_auto_approved[cmd_short] += 1
            elif arb.get("escalation") == "user-confirm":
                arb_declined[cmd_short] += 1

    print(f"bash_gate stats — last {since}")
    print(f"log: {LOG_PATH}")
    print(f"total entries: {total}")
    print()
    if not total:
        print("(no entries in window)")
        return 0

    print(f"{'decision':<10} {'class':<16} {'count':>8}")
    print("-" * 36)
    for (decision, cls), n in sorted(by_decision_class.items(), key=lambda kv: -kv[1]):
        print(f"{decision:<10} {cls:<16} {n:>8}")

    print()
    print("top deferred reasons:")
    print(f"{'reason':<40} {'count':>8}")
    print("-" * 50)
    for reason, n in deferred_reasons.most_common(10):
        print(f"{reason:<40} {n:>8}")

    if arb_total:
        print()
        print("=" * 50)
        print(f"arbiter consultations: {arb_total}")
        auto = arb_escalations.get("auto-approved", 0)
        confirm = arb_escalations.get("user-confirm", 0)
        errs = arb_escalations.get("error-fallback", 0)
        decided = auto + confirm
        rate = (100.0 * auto / decided) if decided else 0.0
        print(f"  auto-approved: {auto}  | user-confirm: {confirm}  | error-fallback: {errs}")
        print(f"  auto-approval rate (of decided): {rate:.0f}%  ({auto}/{decided})")
        print(f"  verdicts: " + ", ".join(f"{v}={n}" for v, n in arb_verdicts.most_common()))
        if arb_latencies:
            s = sorted(arb_latencies)
            p50 = s[len(s) // 2]
            p95 = s[min(len(s) - 1, int(len(s) * 0.95))]
            print(f"  latency ms: p50={p50}  p95={p95}  max={s[-1]}")
        if arb_auto_approved:
            print("  top auto-approved commands:")
            for c, n in arb_auto_approved.most_common(5):
                print(f"    {n:>4}  {c}")
        if arb_declined:
            print("  top declined (escalated to user) commands:")
            for c, n in arb_declined.most_common(5):
                print(f"    {n:>4}  {c}")
    return 0


def cmd_cleanup(retain_days: int) -> int:
    if not LOG_PATH.exists():
        print(f"no log at {LOG_PATH}; nothing to do")
        return 0
    cutoff = datetime.now(timezone.utc).astimezone() - timedelta(days=retain_days)
    kept: list[str] = []
    dropped = 0
    with LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                e = json.loads(s)
                ts = _parse_ts(e.get("ts", ""))
            except Exception:
                kept.append(line)
                continue
            if ts is None or ts >= cutoff:
                kept.append(line)
            else:
                dropped += 1
    tmp = LOG_PATH.with_suffix(LOG_PATH.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.writelines(kept)
    tmp.replace(LOG_PATH)
    print(f"retained {len(kept)} entries, dropped {dropped} older than {retain_days}d")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--since", help="window, e.g. 24h, 7d, 30m", default=None)
    p.add_argument("--cleanup", action="store_true", help="drop entries older than --retain-days")
    p.add_argument("--retain-days", type=int, default=30)
    args = p.parse_args()

    if args.cleanup:
        return cmd_cleanup(args.retain_days)
    return cmd_summary(args.since or "24h")


if __name__ == "__main__":
    sys.exit(main())
