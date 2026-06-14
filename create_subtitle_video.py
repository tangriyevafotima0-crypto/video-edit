#!/usr/bin/env python3
"""
Subtitle Video Pipeline
------------------------
Downloads a real ambition-themed background image from the internet,
resizes it to 576x1024 (portrait), darkens it for readability,
then uses ffmpeg to compose the final video with:
- The real photo as a static video background
- Clean, small subtitles at the bottom (FontSize=20)
- Fade-in/fade-out transitions
- Original audio (codec-copied, untouched)

Prerequisites:
- subtitles.srt (already exists)
- audio.aac (already extracted)
- Pillow installed
- ffmpeg available
- Internet access (for downloading background image)
"""

import os
import subprocess
from PIL import Image, ImageEnhance

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WIDTH = 576
HEIGHT = 1024
BACKGROUND_PATH = os.path.join(SCRIPT_DIR, "background.png")
BACKGROUND_RAW_PATH = os.path.join(SCRIPT_DIR, "background_raw.jpg")
SUBTITLES_PATH = os.path.join(SCRIPT_DIR, "subtitles.srt")
AUDIO_PATH = os.path.join(SCRIPT_DIR, "audio.aac")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "output_with_subtitles.mp4")
DURATION = 60.7
FPS = 30
FADE_DURATION = 1.5

# Unsplash image: snowy mountain peak at night - evokes ambition and determination
BACKGROUND_URL = "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1080&q=80"


def download_background():
    """Download a real ambition-themed image and resize to 576x1024."""
    print("Downloading ambition-themed background image...")

    # Download image using wget
    cmd = ["wget", "-O", BACKGROUND_RAW_PATH, BACKGROUND_URL]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to download background image: {result.stderr}")

    print(f"Downloaded raw image to {BACKGROUND_RAW_PATH}")

    # Open and resize to portrait 576x1024
    img = Image.open(BACKGROUND_RAW_PATH)
    print(f"  Raw image size: {img.size}")

    target_w, target_h = WIDTH, HEIGHT
    target_ratio = target_w / target_h

    w, h = img.size
    current_ratio = w / h

    # Crop to target aspect ratio
    if current_ratio > target_ratio:
        # Image is wider - crop width
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        # Image is taller - crop height
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    # Resize to exact target dimensions
    img = img.resize((target_w, target_h), Image.LANCZOS)

    # Darken the image for better subtitle readability
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.55)

    # Save as PNG
    img.save(BACKGROUND_PATH, "PNG")
    print(f"Background saved: {BACKGROUND_PATH} ({WIDTH}x{HEIGHT})")

    # Clean up raw download
    if os.path.exists(BACKGROUND_RAW_PATH):
        os.remove(BACKGROUND_RAW_PATH)

    return BACKGROUND_PATH


def create_video():
    """Use ffmpeg to create the final video with background, subtitles, fades, and audio."""
    print("Creating video with ffmpeg...")

    # Calculate fade-out start time
    fade_out_start = DURATION - FADE_DURATION

    # Subtitle styling - clean, small, bottom-positioned
    # FontSize=20 for readable but not overwhelming text
    # White primary color with black outline for clean look on any background
    # Alignment=2 (bottom-center), MarginV=40 for comfortable bottom padding
    subtitle_style = (
        "FontName=Noto Sans,"
        "Bold=1,"
        "FontSize=20,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H80000000,"
        "Outline=2,"
        "Shadow=1,"
        "MarginV=40,"
        "Alignment=2"
    )

    # Escape the subtitles path for ffmpeg filter
    srt_escaped = SUBTITLES_PATH.replace("\\", "/").replace(":", "\\:")

    # Build the video filter chain
    video_filter = (
        f"loop=loop=-1:size=1:start=0,setpts=PTS-STARTPTS,"
        f"format=yuv420p,"
        f"subtitles='{srt_escaped}':force_style='{subtitle_style}',"
        f"fade=t=in:st=0:d={FADE_DURATION},"
        f"fade=t=out:st={fade_out_start}:d={FADE_DURATION}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", BACKGROUND_PATH,
        "-i", AUDIO_PATH,
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "copy",
        "-shortest",
        "-t", str(DURATION),
        "-r", str(FPS),
        "-s", f"{WIDTH}x{HEIGHT}",
        OUTPUT_PATH
    ]

    print("Running ffmpeg command...")
    print(f"  Output: {OUTPUT_PATH}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg STDERR:\n{result.stderr}")
        raise RuntimeError(f"ffmpeg failed with return code {result.returncode}")

    print(f"Video created successfully: {OUTPUT_PATH}")


def verify_output():
    """Verify the output video with ffprobe."""
    print("\nVerifying output video...")
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        OUTPUT_PATH
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    import json
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video_streams = [s for s in streams if s["codec_type"] == "video"]
    audio_streams = [s for s in streams if s["codec_type"] == "audio"]

    if not video_streams:
        raise RuntimeError("No video stream found!")
    if not audio_streams:
        raise RuntimeError("No audio stream found!")

    v = video_streams[0]
    a = audio_streams[0]

    print(f"  Video: {v['width']}x{v['height']}, codec={v['codec_name']}")
    print(f"  Audio: codec={a['codec_name']}, sample_rate={a.get('sample_rate', 'N/A')}")
    print(f"  Duration: {fmt.get('duration', 'N/A')}s")

    assert int(v['width']) == WIDTH, f"Width mismatch: {v['width']}"
    assert int(v['height']) == HEIGHT, f"Height mismatch: {v['height']}"
    assert a['codec_name'] == 'aac', f"Audio codec mismatch: {a['codec_name']}"

    print("\nAll checks passed!")


if __name__ == "__main__":
    # Step 1: Download and prepare the ambition-themed background
    download_background()

    # Step 2: Create the video with subtitles, fades, and audio
    create_video()

    # Step 3: Verify the output
    verify_output()

    print("\nDone! Output video: output_with_subtitles.mp4")
