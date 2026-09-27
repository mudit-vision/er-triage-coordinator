import os
import glob
import imageio
from PIL import Image
import numpy as np

frames_dir = os.path.join(os.getcwd(), 'frames')
output_video_path = '/config/.gemini/antigravity/brain/cf9fcc99-9253-4213-8f7c-405f10cb6df3/demo_silent.mp4'

frame_files = sorted(glob.glob(os.path.join(frames_dir, 'frame_*.png')))
print(f"Found {len(frame_files)} frame files in {frames_dir}")

if not frame_files:
    print("Error: No frame files found!")
    exit(1)

writer = imageio.get_writer(output_video_path, fps=8, codec='libx264', quality=8)

for idx, fname in enumerate(frame_files):
    if idx % 50 == 0:
        print(f"Processing frame {idx}/{len(frame_files)}...")
    img = np.array(Image.open(fname).convert('RGB'))
    writer.append_data(img)

writer.close()
print(f"Successfully compiled silent demo video to {output_video_path}!")
print("Video file size:", os.path.getsize(output_video_path), "bytes")
