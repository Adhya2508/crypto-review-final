"""
Run this FIRST before uploading:
    python debug_video.py converted.mp4
It will tell you exactly what OpenCV sees.
"""
import sys
import cv2
import shutil

path = sys.argv[1] if len(sys.argv) > 1 else "converted.mp4"

print(f"\n--- Testing: {path} ---")
cap = cv2.VideoCapture(path)
print(f"isOpened : {cap.isOpened()}")
print(f"FPS      : {cap.get(cv2.CAP_PROP_FPS)}")
print(f"Width    : {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
print(f"Height   : {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
print(f"Frame cnt: {cap.get(cv2.CAP_PROP_FRAME_COUNT)}")
ret, frame = cap.read()
print(f"Can read : {ret}")
cap.release()

# Also test via /tmp copy
print(f"\n--- Testing via /tmp copy ---")
shutil.copy2(path, "/tmp/test_input.mp4")
cap2 = cv2.VideoCapture("/tmp/test_input.mp4")
print(f"isOpened : {cap2.isOpened()}")
ret2, frame2 = cap2.read()
print(f"Can read : {ret2}")
cap2.release()

if not ret and not ret2:
    print("\nFIX: Run this to re-encode your video:")
    print("  ffmpeg -i converted.mp4 -vcodec libx264 -pix_fmt yuv420p -acodec aac fixed.mp4")
    print("Then upload fixed.mp4 instead.")
elif ret2 and not ret:
    print("\nOK: /tmp copy works. Pipeline should work now.")
else:
    print("\nOK: Both paths work fine.")
