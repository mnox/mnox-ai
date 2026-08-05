#!/usr/bin/env python3
"""render_skill.py — compile a skill TREE (every *.tmpl) under a profile.

The customization spine for mnox-ai skills. A skill's source of truth is its
tree of `*.tmpl` files (generic bodies with `{{placeholder}}` tokens) plus a
`profile.schema.json` (the customization contract). A *profile* TOML supplies
values; rendering is pure substitution.

    profiles/public.toml      → the marketplace render (generic, tracked)
    profiles/matt-local.toml  → the personal render (local/org binding, gitignored)

One source, many renders, zero hand-sync. Validation is the point: a token with
no value, a token the contract doesn't declare, or a contract-required key a
profile omits are all hard errors — drift can't slip through silently.

Operations (pick one; default is --check):
    --check                 validate templates + profile; write nothing
    --verify-against DIR    render in memory, diff each file against DIR/<rel>
    --dest DIR              render the tree into DIR (templates rendered, other
                            files copied; *.tmpl sources and profile.schema.json
                            are never shipped)

Examples:
    render_skill.py --skill schema-review --profile public  --verify-against \\
        plugins/schema-review/skills/schema-review
    render_skill.py --skill schema-review --profile matt-local --dest \\
        ~/.claude/skills/schema-review
    render_skill.py --all --profile public --check
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import sys
from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
NOSHIP = {"profile.schema.json"}  # authoring metadata, never installed


class RenderError(Exception):
    """A validation or resolution failure that should abort the render."""


def find_skill_dir(skill: str) -> Path:
    hits = sorted(REPO_ROOT.glob(f"plugins/*/skills/{skill}"))
    hits = [h for h in hits if (h / "SKILL.md.tmpl").exists() or (h / "SKILL.md").exists()]
    if not hits:
        raise RenderError(f"no skill dir found for {skill!r}")
    if len(hits) > 1:
        raise RenderError(f"ambiguous skill {skill!r}: {hits}")
    return hits[0]


def all_skill_dirs() -> list[Path]:
    return sorted({p.parent for p in REPO_ROOT.glob("plugins/*/skills/*/SKILL.md.tmpl")})


def load_profile(profile: str, skill: str) -> dict[str, str]:
    """Merge global [vars] with skill-local [<skill>.vars] (skill wins)."""
    path = REPO_ROOT / "profiles" / f"{profile}.toml"
    if not path.exists():
        raise RenderError(f"profile not found: {path}")
    data = tomllib.loads(path.read_text())
    merged: dict[str, str] = dict(data.get("vars", {}))
    merged.update(data.get(skill, {}).get("vars", {}))
    return merged


def contract_required(skill_dir: Path) -> set[str] | None:
    schema = skill_dir / "profile.schema.json"
    if not schema.exists():
        return None
    return set(json.loads(schema.read_text()).get("required", []))


def template_files(skill_dir: Path) -> list[Path]:
    return sorted(skill_dir.rglob("*.tmpl"))


def render_text(text: str, values: dict[str, str], label: str) -> str:
    if missing := ({m.group(1) for m in TOKEN_RE.finditer(text)} - set(values)):
        raise RenderError(f"{label}: no profile value for tokens: {sorted(missing)}")
    return TOKEN_RE.sub(lambda m: values[m.group(1)], text)


def validate(skill_dir: Path, values: dict[str, str]) -> None:
    """Cross-check the whole tree's tokens against the contract before rendering."""
    used: set[str] = set()
    for tf in template_files(skill_dir):
        used |= {m.group(1) for m in TOKEN_RE.finditer(tf.read_text())}
    required = contract_required(skill_dir)
    if required is not None:
        if undeclared := (used - required):
            raise RenderError(
                f"{skill_dir.name}: tokens used but not in profile.schema.json "
                f"required: {sorted(undeclared)}"
            )
        if unmet := (required - set(values)):
            raise RenderError(
                f"{skill_dir.name}: profile missing contract-required keys: {sorted(unmet)}"
            )


def verify_against(skill_dir: Path, values: dict[str, str], ref: Path) -> bool:
    ok = True
    for tf in template_files(skill_dir):
        rel = tf.relative_to(skill_dir).with_suffix("")  # drop .tmpl
        rendered = render_text(tf.read_text(), values, str(tf))
        target = ref / rel
        if not target.exists():
            print(f"  ✗ missing in reference: {rel}")
            ok = False
            continue
        if rendered == target.read_text():
            print(f"  ✓ {rel}")
        else:
            ok = False
            print(f"  ✗ {rel} DIFFERS:")
            sys.stdout.writelines(
                difflib.unified_diff(
                    target.read_text().splitlines(keepends=True),
                    rendered.splitlines(keepends=True),
                    fromfile=f"{rel} (expected)",
                    tofile="rendered",
                )
            )
    return ok


def install(skill_dir: Path, values: dict[str, str], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for src in sorted(skill_dir.rglob("*")):
        rel = src.relative_to(skill_dir)
        if src.is_dir():
            continue
        if src.name in NOSHIP:
            continue
        if src.suffix == ".tmpl":
            out = dest / rel.with_suffix("")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_text(src.read_text(), values, str(src)))
        else:
            out = dest / rel
            if out.resolve() == src.resolve():
                continue  # in-place render: plain files are already in place
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
    print(f"  installed → {dest}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--skill")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--dest", type=Path, help="install rendered tree here")
    ap.add_argument(
        "--verify-against", type=Path, dest="verify", help="diff render vs this skill dir"
    )
    ap.add_argument("--check", action="store_true", help="validate only")
    args = ap.parse_args()

    if not args.all and not args.skill:
        ap.error("pass --skill <name> or --all")
    if args.all and (args.dest or args.verify):
        ap.error("--all is for --check only")

    skill_dirs = all_skill_dirs() if args.all else [find_skill_dir(args.skill)]
    rc = 0
    for sd in skill_dirs:
        skill = sd.name
        try:
            values = load_profile(args.profile, skill)
            validate(sd, values)
            if args.verify:
                if not verify_against(sd, values, args.verify.expanduser()):
                    rc = 1
            elif args.dest:
                install(sd, values, args.dest.expanduser())
            else:
                print(f"  ✓ {skill} [{args.profile}] valid ({len(values)} vars)")
        except RenderError as e:
            print(f"ERROR {e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
