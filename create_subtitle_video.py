#!/usr/bin/env python3
"""
Create a subtitle video from source audio.
Extracts audio, transcribes with Whisper, generates SRT subtitles,
and renders a black background video with white subtitles and original audio.
"""

import os
import subprocess
import whisper

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_VIDEO = os.path.join(SCRIPT_DIR, "SnapTikZ.App_7522766063323385095.mp4")
EXTRACTED_AUDIO = os.path.join(SCRIPT_DIR, "audio.aac")
SUBTITLES_SRT = os.path.join(SCRIPT_DIR, "subtitles.srt")
OUTPUT_VIDEO = os.path.join(SCRIPT_DIR, "output_with_subtitles.mp4")

# Video settings
WIDTH = 576
HEIGHT = 1024
FPS = 30


def extract_audio():
    """Extract audio from source video without re-encoding (copy codec)."""
    print("Step 1: Extracting audio from source video...")
    cmd = [
        "ffmpeg", "-y",
        "-i", SOURCE_VIDEO,
        "-vn",
        "-acodec", "copy",
        EXTRACTED_AUDIO
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  Audio extracted to: {EXTRACTED_AUDIO}")


def transcribe_audio():
    """Transcribe audio using Whisper and return segments."""
    print("Step 2: Transcribing audio with Whisper (base model, English)...")
    model = whisper.load_model("base")
    result = model.transcribe(EXTRACTED_AUDIO, language="en")
    segments = result["segments"]
    print(f"  Transcription complete: {len(segments)} segments found")
    return segments


def format_srt_time(seconds):
    """Convert seconds to SRT time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments):
    """Generate SRT subtitle file from Whisper segments."""
    print("Step 3: Generating SRT subtitle file...")
    with open(SUBTITLES_SRT, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = format_srt_time(seg["start"])
            end = format_srt_time(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")
    print(f"  SRT file saved to: {SUBTITLES_SRT}")


def create_output_video():
    """Create final video with black background, burned-in subtitles, and original audio."""
    print("Step 4: Creating output video with black background and subtitles...")

    # Get the duration of the audio
    probe_cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        EXTRACTED_AUDIO
    ]
    result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True)
    duration = float(result.stdout.strip())
    print(f"  Audio duration: {duration:.2f}s")

    # Escape the SRT path for ffmpeg subtitles filter
    # Need to escape colons, backslashes, and brackets in the path for the subtitles filter
    srt_path_escaped = SUBTITLES_SRT.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

    # Use force_style for subtitle styling to avoid font path bracket issues
    subtitle_filter = (
        f"subtitles='{srt_path_escaped}'"
        f":force_style='FontName=Noto Sans,Bold=1,FontSize=26,"
        f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        f"Outline=2,Shadow=1,Alignment=2,MarginV=60'"
    )

    # Build the ffmpeg command
    # - Generate black video background
    # - Burn in subtitles
    # - Mux original audio (copy, no re-encoding)
    cmd = [
        "ffmpeg", "-y",
        # Generate black background video
        "-f", "lavfi",
        "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration}",
        # Input the original audio
        "-i", EXTRACTED_AUDIO,
        # Apply subtitles filter to video
        "-filter_complex", f"[0:v]{subtitle_filter}[v]",
        "-map", "[v]",
        "-map", "1:a",
        # Video encoding
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        # Audio: copy without re-encoding
        "-c:a", "copy",
        # Shortest stream determines duration
        "-shortest",
        OUTPUT_VIDEO
    ]

    print(f"  Running ffmpeg...")
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  Output video saved to: {OUTPUT_VIDEO}")


def verify_output():
    """Verify the output video has both audio and video streams."""
    print("Step 5: Verifying output video...")
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        OUTPUT_VIDEO
    ]
    import json
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    streams = data["streams"]

    has_video = any(s["codec_type"] == "video" for s in streams)
    has_audio = any(s["codec_type"] == "audio" for s in streams)

    print(f"  Video stream: {'YES' if has_video else 'NO'}")
    print(f"  Audio stream: {'YES' if has_audio else 'NO'}")

    if has_video and has_audio:
        # Get file size
        size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
        print(f"  File size: {size_mb:.1f} MB")
        print("  Verification PASSED!")
    else:
        raise RuntimeError("Output video is missing audio or video stream!")


if __name__ == "__main__":
    print("=" * 60)
    print("Subtitle Video Creator")
    print("=" * 60)

    extract_audio()
    segments = transcribe_audio()
    generate_srt(segments)
    create_output_video()
    verify_output()

    print("=" * 60)
    print("DONE! Output: output_with_subtitles.mp4")
    print("=" * 60)
