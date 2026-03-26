"""
experiment_utils.py
───────────────────
Generates research-grade performance and security graphs automatically
after each video upload. All plots are saved to the video's out/ folder.
"""

import os
import json
import math
import matplotlib
matplotlib.use("Agg")           # headless – no display needed
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

PLOT_STYLE = {
    "figure.facecolor": "#0d1117",
    "axes.facecolor":   "#161b22",
    "axes.edgecolor":   "#30363d",
    "axes.labelcolor":  "#e6edf3",
    "xtick.color":      "#8b949e",
    "ytick.color":      "#8b949e",
    "text.color":       "#e6edf3",
    "grid.color":       "#21262d",
    "grid.linestyle":   "--",
    "grid.linewidth":   0.6,
}
ACCENT  = "#58a6ff"
ACCENT2 = "#3fb950"
ACCENT3 = "#f78166"


def _apply_style():
    plt.rcParams.update(PLOT_STYLE)


# ─────────────────────────────────────────────
#  1. Entropy Bar Chart
# ─────────────────────────────────────────────
def plot_entropy(entropy_map: dict, out_dir: str) -> str:
    _apply_style()
    sids   = [str(k) for k in sorted(int(k) for k in entropy_map.keys())]
    values = [entropy_map[s] for s in sids]

    fig, ax = plt.subplots(figsize=(max(6, len(sids) * 0.8 + 2), 4))
    bars = ax.bar(sids, values, color=ACCENT, edgecolor="#0d1117", linewidth=0.5)

    # Ideal entropy reference line
    ax.axhline(8.0, color=ACCENT2, linestyle="--", linewidth=1, label="Ideal (8.0 bpb)")
    ax.set_ylim(0, 8.5)
    ax.set_xlabel("Slice ID")
    ax.set_ylabel("Shannon Entropy (bits/byte)")
    ax.set_title("Per-Slice Ciphertext Entropy", fontsize=13, fontweight="bold", pad=10)
    ax.legend(fontsize=8)
    ax.grid(axis="y")

    # Annotate each bar
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{val:.2f}", ha="center", va="bottom", fontsize=7, color="#8b949e")

    fig.tight_layout()
    path = f"{out_dir}/entropy.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ─────────────────────────────────────────────
#  2. Timing Breakdown Pie / Bar
# ─────────────────────────────────────────────
def plot_timing(timing: dict, out_dir: str) -> str:
    _apply_style()
    labels = ["Slicing", "Graph\nConfusion", "Encryption", "Decryption"]
    keys   = ["slicing_sec", "graph_sec", "encryption_sec", "decryption_sec"]
    values = [timing.get(k, 0) for k in keys]
    colors = [ACCENT, ACCENT2, ACCENT3, "#d2a8ff"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    # Pie
    wedges, texts, autotexts = ax1.pie(
        values, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=140, pctdistance=0.75,
        wedgeprops={"edgecolor": "#0d1117", "linewidth": 1.2}
    )
    for t in texts:      t.set_fontsize(9)
    for t in autotexts:  t.set_fontsize(8); t.set_color("#0d1117")
    ax1.set_title("Time Distribution", fontsize=12, fontweight="bold", pad=12)

    # Bar
    ax2.barh(labels, values, color=colors, edgecolor="#0d1117", linewidth=0.5)
    ax2.set_xlabel("Seconds")
    ax2.set_title("Processing Time per Stage", fontsize=12, fontweight="bold", pad=12)
    ax2.grid(axis="x")
    for i, v in enumerate(values):
        ax2.text(v + 0.003, i, f"{v:.3f}s", va="center", fontsize=8, color="#8b949e")

    fig.suptitle("Performance Metrics — Video Slice Encryption", fontsize=13,
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    path = f"{out_dir}/timing.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ─────────────────────────────────────────────
#  3. Graph Node Distribution
# ─────────────────────────────────────────────
def plot_graph_distribution(graph_meta: dict, real_ids: list, out_dir: str) -> str:
    _apply_style()
    nodes = graph_meta.get("nodes", [])
    type_counts = {}
    for n in nodes:
        t = n.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    labels = list(type_counts.keys())
    counts = list(type_counts.values())
    colors = [ACCENT, ACCENT2, ACCENT3, "#d2a8ff"][:len(labels)]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(labels, counts, color=colors, edgecolor="#0d1117", linewidth=0.5)
    ax.set_ylabel("Node Count")
    ax.set_title("Confusion Graph Node Distribution", fontsize=12, fontweight="bold")
    ax.grid(axis="y")
    for bar, cnt in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                str(cnt), ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    path = f"{out_dir}/graph_distribution.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ─────────────────────────────────────────────
#  4. Security Dashboard (composite)
# ─────────────────────────────────────────────
def plot_security_dashboard(summary: dict, out_dir: str) -> str:
    _apply_style()
    fig = plt.figure(figsize=(14, 8))
    gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.5, wspace=0.4)

    entropy_map = summary.get("entropy", {})
    timing      = summary.get("timing", {})
    slices      = summary.get("slices", 1)
    graph_nodes = summary.get("graph_nodes", 0)
    graph_edges = summary.get("graph_edges", 0)

    # ─ Panel A: Entropy bars
    ax_e = fig.add_subplot(gs[0, :2])
    sids   = [str(k) for k in sorted(int(k) for k in entropy_map.keys())]
    values = [entropy_map[s] for s in sids]
    ax_e.bar(sids, values, color=ACCENT, edgecolor="#0d1117", linewidth=0.5)
    ax_e.axhline(8.0, color=ACCENT2, linestyle="--", linewidth=1, label="Ideal 8.0 bpb")
    ax_e.set_ylim(0, 8.6)
    ax_e.set_xlabel("Slice ID", fontsize=9)
    ax_e.set_ylabel("Entropy (bpb)", fontsize=9)
    ax_e.set_title("A. Ciphertext Entropy per Slice", fontsize=10, fontweight="bold")
    ax_e.legend(fontsize=8); ax_e.grid(axis="y")

    # ─ Panel B: Timing pie
    ax_p = fig.add_subplot(gs[0, 2])
    t_keys   = ["slicing_sec", "graph_sec", "encryption_sec", "decryption_sec"]
    t_labels = ["Slicing", "Graph", "Encrypt", "Decrypt"]
    t_vals   = [timing.get(k, 0) for k in t_keys]
    ax_p.pie(t_vals, labels=t_labels, autopct="%1.0f%%",
             colors=[ACCENT, ACCENT2, ACCENT3, "#d2a8ff"],
             wedgeprops={"edgecolor": "#0d1117"}, startangle=90,
             textprops={"fontsize": 7})
    ax_p.set_title("B. Time Distribution", fontsize=10, fontweight="bold")

    # ─ Panel C: Scalability simulation (synthetic)
    ax_s = fig.add_subplot(gs[1, :2])
    slice_counts  = list(range(1, slices * 3 + 1, max(1, slices // 4)))
    enc_times_sim = [s * timing.get("encryption_sec", 0.1) / slices for s in slice_counts]
    full_enc_sim  = [s * timing.get("encryption_sec", 0.1) / slices * 1.8 for s in slice_counts]
    ax_s.plot(slice_counts, enc_times_sim, marker="o", color=ACCENT,  label="Slice Encryption")
    ax_s.plot(slice_counts, full_enc_sim,  marker="s", color=ACCENT3, label="Full Encryption (sim)")
    ax_s.set_xlabel("Number of Slices", fontsize=9)
    ax_s.set_ylabel("Estimated Time (sec)", fontsize=9)
    ax_s.set_title("C. Scalability — Slice vs Full Encryption", fontsize=10, fontweight="bold")
    ax_s.legend(fontsize=8); ax_s.grid()

    # ─ Panel D: Stats text box
    ax_t = fig.add_subplot(gs[1, 2])
    ax_t.axis("off")
    stats_text = (
        f"📊  Summary Statistics\n"
        f"{'─'*28}\n"
        f"  Slices (real)    : {slices}\n"
        f"  Graph nodes      : {graph_nodes}\n"
        f"  Graph edges      : {graph_edges}\n"
        f"  Avg entropy      : {sum(values)/max(len(values),1):.4f} bpb\n"
        f"  Total time       : {timing.get('total_sec',0):.3f} s\n"
        f"  Encryption mode  : AES-256-CTR\n"
        f"  Key derivation   : Kp ⊕ H(Vind+Sv)\n"
        f"  Security proof   : NP-Hard (Ham. Path)"
    )
    ax_t.text(0.05, 0.95, stats_text, transform=ax_t.transAxes,
              fontsize=8.5, verticalalignment="top",
              fontfamily="monospace", color="#e6edf3",
              bbox=dict(boxstyle="round,pad=0.5", facecolor="#161b22",
                        edgecolor="#30363d", linewidth=1))

    fig.suptitle("🔐 Video Slice Encryption — Security & Performance Dashboard",
                 fontsize=13, fontweight="bold", y=1.01)

    path = f"{out_dir}/security_dashboard.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ─────────────────────────────────────────────
#  Master runner — called after process_video
# ─────────────────────────────────────────────
def run_all_experiments(summary: dict, root: str) -> dict:
    """
    Generate all experiment graphs.  Returns dict of {graph_name: path}.
    """
    out_dir = f"{root}/out"
    os.makedirs(out_dir, exist_ok=True)

    results = {}

    if summary.get("entropy"):
        results["entropy"]              = plot_entropy(summary["entropy"], out_dir)
    if summary.get("timing"):
        results["timing"]               = plot_timing(summary["timing"], out_dir)
    if summary.get("entropy") and summary.get("timing"):
        results["security_dashboard"]   = plot_security_dashboard(summary, out_dir)

    # Graph distribution needs graph meta from meta.json
    meta_path = f"{root}/meta.json"
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        results["graph_distribution"] = plot_graph_distribution(
            meta.get("graph", {}), meta.get("real", []), out_dir
        )

    return results
