from __future__ import annotations

import argparse
import json
from scorer.scorer import Scorer


def _cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("traj", help="path to trajectory JSONL")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    s = Scorer()
    artifact = s.score_run(args.traj, manifest_path=args.manifest)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
    else:
        print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    _cli()
