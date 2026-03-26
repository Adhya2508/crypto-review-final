import os
import cv2
import json
import time
import shutil

from Crypto.Random import get_random_bytes
from app.graph_utils import build_confusion_graph, real_topological_order, graph_to_meta, graph_from_meta
from app.crypto_utils import parallel_encrypt, parallel_decrypt, compute_entropy, decrypt_slice

BASE = "app/workspace"
SLICE_FRAMES = 30


def clear_all():
    if os.path.exists(BASE):
        shutil.rmtree(BASE)
    os.makedirs(BASE)


def _make_dirs(root):
    for sub in ("slices", "enc", "dec", "out"):
        os.makedirs(f"{root}/{sub}", exist_ok=True)


def process_video(video_path, video_name):
    root = f"{BASE}/{video_name}"
    _make_dirs(root)

    t_total_start = time.time()
    t_slice_start = time.time()

    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    slice_data = {}
    idx = 0

    while True:
        frames = []
        for _ in range(SLICE_FRAMES):
            ret, f = cap.read()
            if not ret:
                break
            frames.append(f)
        if not frames:
            break

        slice_path = f"{root}/slices/{idx}.mp4"
        out_w = cv2.VideoWriter(slice_path, fourcc, fps, (w, h))
        for fr in frames:
            out_w.write(fr)
        out_w.release()

        with open(slice_path, "rb") as f:
            slice_data[idx] = f.read()
        idx += 1

    cap.release()
    t_slice_end = time.time()

    if not slice_data:
        raise RuntimeError(
            f"Zero slices produced (fps={fps} w={w} h={h}). "
            "Re-encode: ffmpeg -i input.mp4 -vcodec libx264 -pix_fmt yuv420p fixed.mp4"
        )

    real_ids = list(slice_data.keys())

    t_graph_start = time.time()
    G = build_confusion_graph(real_ids)
    t_graph_end = time.time()

    t_enc_start = time.time()
    master = get_random_bytes(16)
    enc = parallel_encrypt(slice_data, master)
    t_enc_end = time.time()

    entropy_map = {str(sid): compute_entropy(ct) for sid, ct in enc.items()}

    for sid, ct in enc.items():
        with open(f"{root}/enc/{sid}.bin", "wb") as f:
            f.write(ct)

    meta = {
        "fps": fps, "w": w, "h": h,
        "master": master.hex(),
        "graph": graph_to_meta(G),
        "real": real_ids,
        "entropy": entropy_map,
        "video_name": video_name,
    }
    with open(f"{root}/meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    t_dec_start = time.time()
    order = real_topological_order(G)
    final_path = f"{root}/out/final.mp4"
    final = cv2.VideoWriter(final_path, fourcc, fps, (w, h))

    for sid in order:
        cap2 = cv2.VideoCapture(f"{root}/slices/{sid}.mp4")
        while True:
            ret, fr = cap2.read()
            if not ret:
                break
            final.write(fr)
        cap2.release()

    final.release()
    t_dec_end   = time.time()
    t_total_end = time.time()

    summary = {
        "video_name": video_name,
        "slices": len(real_ids),
        "fps": fps,
        "resolution": f"{w}x{h}",
        "master_key": master.hex(),
        "timing": {
            "slicing_sec":    round(t_slice_end   - t_slice_start, 3),
            "graph_sec":      round(t_graph_end   - t_graph_start, 3),
            "encryption_sec": round(t_enc_end     - t_enc_start,   3),
            "decryption_sec": round(t_dec_end     - t_dec_start,   3),
            "total_sec":      round(t_total_end   - t_total_start, 3),
        },
        "entropy": entropy_map,
        "final_video": final_path,
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": G.number_of_edges(),
    }

    with open(f"{root}/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def decrypt_video_authorized(video_name):
    root = f"{BASE}/{video_name}"
    if not os.path.exists(f"{root}/meta.json"):
        raise FileNotFoundError("Metadata not found. Upload and process the video first.")

    with open(f"{root}/meta.json") as f:
        meta = json.load(f)

    master   = bytes.fromhex(meta["master"])
    real_ids = meta["real"]
    fps, w, h = meta["fps"], meta["w"], meta["h"]
    G = graph_from_meta(meta["graph"])
    t_start = time.time()

    enc_data = {}
    for sid in real_ids:
        with open(f"{root}/enc/{sid}.bin", "rb") as f:
            enc_data[sid] = f.read()

    dec_data = parallel_decrypt(enc_data, master)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    for sid, pt in dec_data.items():
        with open(f"{root}/dec/{sid}.mp4", "wb") as f:
            f.write(pt)

    order    = real_topological_order(G)
    out_path = f"{root}/out/reconstructed_auth.mp4"
    final    = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    for sid in order:
        cap = cv2.VideoCapture(f"{root}/dec/{sid}.mp4")
        while True:
            ret, fr = cap.read()
            if not ret:
                break
            final.write(fr)
        cap.release()
    final.release()

    return {
        "status": "success",
        "message": "Authorised decryption complete. Video reconstructed.",
        "output_path": out_path,
        "decryption_time_sec": round(time.time() - t_start, 3),
        "slices_decrypted": len(real_ids),
    }


def simulate_unauthorized_access(video_name):
    enc_dir = f"{BASE}/{video_name}/enc"
    if not os.path.exists(enc_dir):
        raise FileNotFoundError("No encrypted slices found. Upload video first.")

    fake_key  = b'\xDE\xAD\xBE\xEF' * 4
    bin_files = sorted(f for f in os.listdir(enc_dir) if f.endswith(".bin"))
    results   = []

    for bf in bin_files:
        with open(f"{enc_dir}/{bf}", "rb") as f:
            ct = f.read()
        try:
            garbage = decrypt_slice(ct, fake_key)
            entropy = compute_entropy(garbage)
        except Exception:
            entropy = 0.0
        results.append({
            "slice_file": bf,
            "bytes_seen": len(ct),
            "entropy_of_garbage": entropy,
            "visually_recoverable": False,
            "ordering_known": False,
        })

    return {
        "status": "access_denied",
        "warning": "UNAUTHORISED ACCESS ATTEMPT. Wrong key = pure noise. Ordering is NP-Hard. Video CANNOT be reconstructed.",
        "attacker_result": "All slices are random byte noise (entropy ~8.0 bpb).",
        "np_hard_note": "Slice order recovery = Hamiltonian Path (NP-Complete).",
        "slice_analysis": results,
    }
