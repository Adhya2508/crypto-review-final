"""
entropy_graph.py
────────────────
Stand-alone script: given a video name (already processed),
regenerates the entropy graph from its summary.json.

Usage:
    python -m app.entropy_graph <video_name>
"""

import sys
import os
import json


def regenerate(video_name: str):
    from app.experiment_utils import plot_entropy

    root = f"app/workspace/{video_name}"
    summary_path = f"{root}/summary.json"

    if not os.path.exists(summary_path):
        print(f"No summary.json found for '{video_name}'.")
        sys.exit(1)

    with open(summary_path) as f:
        summary = json.load(f)

    entropy_map = summary.get("entropy", {})
    if not entropy_map:
        print("No entropy data in summary.")
        sys.exit(1)

    out = plot_entropy(entropy_map, f"{root}/out")
    print(f"Entropy graph saved → {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.entropy_graph <video_name>")
        sys.exit(1)
    regenerate(sys.argv[1])
