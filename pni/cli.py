from __future__ import annotations

import argparse
import os
import sys

from pni.importer import run_import


def env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="proxmox-netbox-import",
        description="Import Proxmox VMs into NetBox",
    )

    p.add_argument("--dry-run", action="store_true", default=env_bool("DRY_RUN", False))
    p.add_argument(
        "--update-existing",
        action=argparse.BooleanOptionalAction,
        default=env_bool("UPDATE_EXISTING", True),
        help="Update existing NetBox VMs if they already exist (default: true)",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        summary = run_import(dry_run=args.dry_run, update_existing=args.update_existing)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(summary.to_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
