#!/usr/bin/env python3
"""
Upgraded Subtitle Video Pipeline
---------------------------------
Generates an ambition-themed dark background image (576x1024) using Pillow,
then uses ffmpeg to compose the final video with:
- The generated background as a static video loop
- Styled subtitles (golden/amber, bold, outlined, shadowed)
- Fade-in/fade-out transitions
- Original audio (codec-copied, untouched)

Prerequisites:
- subtitles.srt (already exists)
- audio.aac (already extracted)
- Pillow, numpy installed
- ffmpeg available
"""

import os
import subprocess
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WIDTH = 576
HEIGHT = 1024
BACKGROUND_PATH = os.path.join(SCRIPT_DIR, "background.png")
SUBTITLES_PATH = os.path.join(SCRIPT_DIR, "subtitles.srt")
AUDIO_PATH = os.path.join(SCRIPT_DIR, "audio.aac")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "output_with_subtitles.mp4")
DURATION = 60.7
FPS = 30
FADE_DURATION = 1.5


def generate_background():
    """Generate a dark ambition-themed background image with gradients and geometric patterns."""
    print("Generating ambition-themed background image...")

    # Create base image with dark gradient (dark navy/purple to black)
    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float64)

    # Radial gradient from center - dark purple/navy emanating outward to black
    center_y, center_x = HEIGHT * 0.35, WIDTH * 0.5
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # Distance from the light source point (upper center area)
            dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            max_dist = math.sqrt(center_x ** 2 + center_y ** 2) * 1.2

            # Normalized distance (0 at center, 1 at edges)
            norm_dist = min(dist / max_dist, 1.0)

            # Exponential falloff for a dramatic light effect
            intensity = math.exp(-3.0 * norm_dist)

            # Dark navy/purple base with radial glow
            # R: slight warm tone near center
            img[y, x, 0] = 15 + 40 * intensity
            # G: minimal
            img[y, x, 1] = 5 + 15 * intensity
            # B: deep blue/purple dominant
            img[y, x, 2] = 25 + 60 * intensity

    # Convert to uint8
    img = np.clip(img, 0, 255).astype(np.uint8)
    pil_img = Image.fromarray(img, 'RGB')

    # Add geometric patterns - angular lines evoking power/ambition
    draw = ImageDraw.Draw(pil_img)

    # Draw subtle angular/geometric shapes (low opacity simulation with dark colors)
    # Diagonal lines converging toward upper center
    line_color_subtle = (25, 15, 45)  # Very dark purple
    line_color_accent = (35, 20, 55)  # Slightly brighter purple accent

    # Converging lines from bottom corners toward the light source
    for i in range(12):
        offset = i * 50
        # Lines from bottom-left area
        draw.line(
            [(0, HEIGHT - offset), (int(center_x), int(center_y))],
            fill=line_color_subtle, width=1
        )
        # Lines from bottom-right area
        draw.line(
            [(WIDTH, HEIGHT - offset), (int(center_x), int(center_y))],
            fill=line_color_subtle, width=1
        )

    # Add subtle diamond/rhombus shapes scattered around
    for i in range(6):
        cx = WIDTH * (0.2 + 0.6 * (i / 5.0))
        cy = HEIGHT * (0.5 + 0.08 * math.sin(i * 1.5))
        size = 30 + i * 10
        points = [
            (cx, cy - size),
            (cx + size * 0.6, cy),
            (cx, cy + size),
            (cx - size * 0.6, cy)
        ]
        draw.polygon(points, outline=line_color_accent)

    # Add faint grid lines (very subtle)
    grid_color = (18, 12, 30)
    for y in range(0, HEIGHT, 80):
        draw.line([(0, y), (WIDTH, y)], fill=grid_color, width=1)
    for x in range(0, WIDTH, 80):
        draw.line([(x, 0), (x, HEIGHT)], fill=grid_color, width=1)

    # Add a subtle radial glow/energy burst overlay
    glow_layer = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    # Concentric circles (faint) around the light source
    for r in range(50, 400, 40):
        brightness = max(5, int(25 * math.exp(-r / 200.0)))
        glow_draw.ellipse(
            [int(center_x - r), int(center_y - r),
             int(center_x + r), int(center_y + r)],
            outline=(brightness, brightness // 2, brightness + 10)
        )

    # Blur the glow layer for soft effect
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=3))

    # Blend glow with main image
    from PIL import ImageChops
    pil_img = ImageChops.add(pil_img, glow_layer)

    # Add a slight vignette (darken edges)
    vignette = Image.new('L', (WIDTH, HEIGHT), 0)
    vignette_draw = ImageDraw.Draw(vignette)
    for i in range(30):
        alpha = int(255 * (1.0 - i / 30.0) * 0.4)
        vignette_draw.rectangle(
            [i * 3, i * 3, WIDTH - i * 3, HEIGHT - i * 3],
            outline=alpha
        )
    # Apply vignette as darkening mask
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=20))
    vignette_array = np.array(vignette, dtype=np.float64) / 255.0
    img_array = np.array(pil_img, dtype=np.float64)

    # Vignette: darker at edges (invert mask so 0=edge, 1=center)
    vignette_mask = 0.6 + 0.4 * vignette_array  # Range from 0.6 (edges) to 1.0 (center)
    for c in range(3):
        img_array[:, :, c] *= vignette_mask
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)
    pil_img = Image.fromarray(img_array, 'RGB')

    pil_img.save(BACKGROUND_PATH, 'PNG')
    print(f"Background saved: {BACKGROUND_PATH} ({WIDTH}x{HEIGHT})")
    return BACKGROUND_PATH


def create_video():
    """Use ffmpeg to create the final video with background, subtitles, fades, and audio."""
    print("Creating video with ffmpeg...")

    # Calculate fade-out start time
    fade_out_start = DURATION - FADE_DURATION

    # Subtitle styling using force_style (ASS style format)
    # Golden/amber color: &H0080DDFF (BGR format in ASS: FF DD 80 00 -> gold/amber)
    # Strong black outline, drop shadow
    subtitle_style = (
        "FontName=Noto Sans,"
        "Bold=1,"
        "FontSize=34,"
        "PrimaryColour=&H0080DDFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H80000000,"
        "Outline=3,"
        "Shadow=2,"
        "MarginV=60,"
        "Alignment=2"
    )

    # Escape the subtitles path for ffmpeg filter (replace backslash, colon, brackets)
    srt_escaped = SUBTITLES_PATH.replace("\\", "/").replace(":", "\\:")

    # Build the complex filter
    # 1. Loop background image for duration
    # 2. Apply subtitles with force_style
    # 3. Apply fade-in and fade-out
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

    print(f"Running ffmpeg command...")
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
    # Step 1: Generate the ambition-themed background
    generate_background()

    # Step 2: Create the video with subtitles, fades, and audio
    create_video()

    # Step 3: Verify the output
    verify_output()

    print("\nDone! Output video: output_with_subtitles.mp4")
