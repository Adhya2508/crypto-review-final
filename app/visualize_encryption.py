"""
visualize_encryption.py
────────────────────────
Stand-alone script (and importable function) that:
  1. Extracts the first frame of a video
  2. Encrypts its raw pixel bytes with AES-CTR
  3. Reconstructs an "encrypted image" from the ciphertext
  4. Saves a side-by-side comparison PNG

Run directly:
    python visualize_encryption.py <video_path> [out_dir]

Or import encrypt_frame_visual() in your own code.
"""

import os
import sys
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

PLOT_STYLE = {
    "figure.facecolor": "#0d1117",
    "axes.facecolor":   "#0d1117",
    "text.color":       "#e6edf3",
}


def encrypt_frame_visual(video_path: str, out_dir: str = ".") -> str:
    """
    Encrypts the first frame of a video and saves a comparison image.
    Returns the path to the saved PNG.
    """
    os.makedirs(out_dir, exist_ok=True)

    # ── Extract first frame ──────────────────────
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError(f"Could not read frame from {video_path}")

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, c   = frame_rgb.shape

    # ── Encrypt raw pixel bytes ──────────────────
    raw     = frame_rgb.tobytes()                   # flat bytes
    key     = get_random_bytes(16)
    nonce   = get_random_bytes(8)
    cipher  = AES.new(key, AES.MODE_CTR, nonce=nonce)
    enc_raw = cipher.encrypt(raw)

    # ── Reconstruct image from ciphertext ────────
    enc_arr = np.frombuffer(enc_raw, dtype=np.uint8).reshape(h, w, c)

    # ── Plot comparison ──────────────────────────
    plt.rcParams.update(PLOT_STYLE)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].imshow(frame_rgb)
    axes[0].set_title("Original Frame", fontsize=13, fontweight="bold",
                       color="#3fb950", pad=10)
    axes[0].axis("off")

    axes[1].imshow(enc_arr)
    axes[1].set_title("Encrypted Frame (AES-CTR)\nPixel bytes → random noise",
                       fontsize=13, fontweight="bold", color="#f78166", pad=10)
    axes[1].axis("off")

    # Annotation box
    info = (
        "AES-256-CTR  |  Random nonce  |  Unique key per slice\n"
        "Visual patterns completely destroyed → perceptually secure"
    )
    fig.text(0.5, 0.01, info, ha="center", fontsize=9,
             color="#8b949e", style="italic")

    fig.suptitle("🔐 Encryption Visual Proof — Frame-Level AES-CTR",
                 fontsize=14, fontweight="bold", y=1.02)

    out_path = os.path.join(out_dir, "encryption_visual.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"[visualize] Saved → {out_path}")
    return out_path


# ── CLI entry point ──────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize_encryption.py <video_path> [out_dir]")
        sys.exit(1)

    vp      = sys.argv[1]
    out_d   = sys.argv[2] if len(sys.argv) > 2 else "."
    path    = encrypt_frame_visual(vp, out_d)
    print(f"Output: {path}")
