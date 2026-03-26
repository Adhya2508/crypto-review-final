"""
run.py  —  Start the Secure Video Encryption API server
Usage:
    python run.py
Then open:  http://127.0.0.1:8000/docs
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
