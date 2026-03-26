import os
import json
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse

from app.pipeline import (
    process_video,
    decrypt_video_authorized,
    simulate_unauthorized_access,
    clear_all,
    BASE,
)
from app.experiment_utils import run_all_experiments
from app.visualize_encryption import encrypt_frame_visual

app = FastAPI(
    title="Secure Video Slice Encryption System",
    description=(
        "Research-grade video encryption using AES-256-CTR slice encryption "
        "combined with confusion-graph obfuscation.\n\n"
        "Security is grounded in NP-Hard reduction to the **Hamiltonian Path problem**.\n\n"
        "---\n"
        "### Workflow\n"
        "`Upload` -> `Slice` -> `Graph Confusion` -> `Per-slice AES-CTR` -> "
        "`Metadata` -> `Authorised Reconstruction`\n\n"
        "### Key features\n"
        "- Unique key per slice: `K = Kp XOR H(Vind + Sv)`\n"
        "- Type-1 & Type-2 confusion nodes hide true slice order\n"
        "- Parallel encryption (multi-threaded)\n"
        "- Auto-generated research graphs (entropy, timing, dashboard)\n"
        "- Authorized vs Unauthorized access simulation\n"
    ),
    version="2.0.0",
)

STATUS: dict = {}

VALID_IMAGES = {
    "entropy.png",
    "timing.png",
    "graph_distribution.png",
    "security_dashboard.png",
    "encryption_visual.png",
}


def _json_safe(obj):
    """Recursively make all keys strings and values JSON-serialisable."""
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(i) for i in obj]
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


@app.get("/", response_class=HTMLResponse, tags=["System"])
def root():
    return """
    <html><head><title>Secure Video System</title></head>
    <body style="font-family:monospace;background:#0d1117;color:#e6edf3;padding:40px">
      <h1>Secure Video Slice Encryption System</h1>
      <p>Visit <a href="/docs" style="color:#58a6ff">/docs</a> for the interactive API.</p>
      <ul>
        <li>POST /upload-video - process a new video</li>
        <li>GET  /access/authorized/{name}   - authorised decryption demo</li>
        <li>GET  /access/unauthorized/{name} - attacker simulation</li>
        <li>GET  /download/graph/{name}/{img} - download research graphs</li>
      </ul>
    </body></html>
    """


@app.post(
    "/upload-video",
    tags=["Pipeline"],
    summary="Upload and encrypt a video",
    response_description="Processing summary with timing, entropy and graph paths",
)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file (mp4 / avi / mov).

    The system will automatically:
    1. Slice the video into independent chunks
    2. Build a confusion graph (Type-1 + Type-2 nodes)
    3. Derive a unique AES-256 key per slice
    4. Encrypt all slices in parallel (AES-CTR)
    5. Store encrypted bins + secured metadata
    6. Reconstruct preview video (authorised path)
    7. Generate all research experiment graphs
    """
    video_name = os.path.splitext(file.filename)[0].replace(" ", "_")
    temp_path = f"/tmp/upload_{video_name}.mp4"

    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    STATUS[video_name] = "processing"

    try:
        summary = process_video(temp_path, video_name)
        STATUS[video_name] = "done"

        root = f"{BASE}/{video_name}"
        graphs = run_all_experiments(summary, root)
        summary["experiment_graphs"] = {str(k): str(v) for k, v in graphs.items()}

        try:
            vis_path = encrypt_frame_visual(temp_path, f"{root}/out")
            summary["encryption_visual"] = str(vis_path)
        except Exception as vis_err:
            summary["encryption_visual"] = f"skipped: {vis_err}"

        try:
            os.remove(temp_path)
        except Exception:
            pass

        safe = _json_safe(summary)
        return JSONResponse(content=safe)

    except Exception as e:
        STATUS[video_name] = "error"
        try:
            os.remove(temp_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{name}", tags=["Pipeline"], summary="Check processing status")
def get_status(name: str):
    return {"video_name": name, "status": STATUS.get(name, "not-found")}


@app.get("/list-videos", tags=["Pipeline"], summary="List all processed videos")
def list_videos():
    if not os.path.exists(BASE):
        return {"videos": [], "count": 0}
    names = [d for d in os.listdir(BASE) if os.path.isdir(f"{BASE}/{d}")]
    return {"videos": names, "count": len(names)}


@app.get("/summary/{name}", tags=["Pipeline"], summary="Full processing summary")
def get_summary(name: str):
    path = f"{BASE}/{name}/summary.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Summary not found. Upload video first.")
    with open(path) as f:
        return _json_safe(json.load(f))


@app.get("/download/final/{name}", tags=["Downloads"], summary="Download reconstructed preview video")
def download_final(name: str):
    path = f"{BASE}/{name}/out/final.mp4"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Video not found.")
    return FileResponse(path, media_type="video/mp4", filename=f"{name}_final.mp4")


@app.get("/download/graph/{name}/{image}", tags=["Downloads"], summary="Download an experiment graph")
def download_graph(name: str, image: str):
    """
    Download one of the auto-generated research graphs.

    Valid image names:
    - entropy.png
    - timing.png
    - graph_distribution.png
    - security_dashboard.png
    - encryption_visual.png
    """
    if image not in VALID_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image. Choose from: {sorted(VALID_IMAGES)}"
        )
    path = f"{BASE}/{name}/out/{image}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{image} not found for '{name}'.")
    return FileResponse(path, media_type="image/png", filename=image)


@app.get(
    "/access/authorized/{name}",
    tags=["Access Control"],
    summary="Authorised user - decrypt and reconstruct video",
)
def authorized_access(name: str):
    """
    **Authorised user flow**

    Simulates a legitimate user who possesses the master key and metadata.

    Steps:
    1. Load metadata (fps, dimensions, master key, graph)
    2. Load encrypted .bin slices
    3. Derive per-slice keys: K = Kp XOR H(Vind + Sv)
    4. Decrypt all slices with AES-256-CTR
    5. Strip confusion nodes, topological sort
    6. Merge decrypted slices into reconstructed video
    """
    try:
        result = decrypt_video_authorized(name)
        return JSONResponse(content=_json_safe(result))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/download/reconstructed/{name}",
    tags=["Downloads"],
    summary="Download the authorised-decryption reconstructed video",
)
def download_reconstructed(name: str):
    path = f"{BASE}/{name}/out/reconstructed_auth.mp4"
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="Call /access/authorized/{name} first to generate the reconstructed video."
        )
    return FileResponse(path, media_type="video/mp4", filename=f"{name}_reconstructed.mp4")


@app.get(
    "/access/unauthorized/{name}",
    tags=["Access Control"],
    summary="Unauthorised user - simulate attacker with no keys or metadata",
)
def unauthorized_access(name: str):
    """
    **Unauthorised attacker simulation**

    Attacker has only the encrypted .bin files - no master key, no metadata.

    Result:
    - Wrong key decryption yields pure noise (entropy ~8.0 bpb)
    - Slice ordering unknown - NP-Hard to recover (Hamiltonian Path)
    - No visual information recoverable whatsoever
    """
    try:
        result = simulate_unauthorized_access(name)
        return JSONResponse(content=_json_safe(result))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/visualize/{name}", tags=["Research"], summary="Generate frame-level encryption visual proof")
def visualize(name: str):
    """
    Takes the first slice of the video and produces a side-by-side comparison:
    - Left: original frame (readable)
    - Right: AES-CTR encrypted frame (pure visual noise)

    Download the result via /download/graph/{name}/encryption_visual.png
    """
    slice_0 = f"{BASE}/{name}/slices/0.mp4"
    if not os.path.exists(slice_0):
        raise HTTPException(status_code=404, detail="Slices not found. Upload video first.")

    out_dir = f"{BASE}/{name}/out"
    try:
        path = encrypt_frame_visual(slice_0, out_dir)
        return {
            "status": "ok",
            "message": "Visual proof generated.",
            "download_at": f"/download/graph/{name}/encryption_visual.png",
            "path": str(path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete/{name}", tags=["System"], summary="Delete one video workspace")
def delete_video(name: str):
    path = f"{BASE}/{name}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Video workspace not found.")
    shutil.rmtree(path)
    STATUS.pop(name, None)
    return {"deleted": name, "status": "workspace removed"}


@app.post("/clear-workspace", tags=["System"], summary="Clear entire workspace")
def clear_workspace():
    clear_all()
    STATUS.clear()
    return {"message": "Entire workspace cleared."}
