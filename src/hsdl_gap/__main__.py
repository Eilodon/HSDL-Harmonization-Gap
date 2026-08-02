from __future__ import annotations

import argparse
import json

from .report import build_legacy_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", default="policies/legacy_v11.json")
    args = parser.parse_args()
    print(json.dumps(build_legacy_report(args.policies), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
