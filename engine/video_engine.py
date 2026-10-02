import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio
import numpy as np


VIDEO_DIR = Path(os.getenv("VIDEO_DIR", "generated_videos"))
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

W, H = 360, 640
FPS = 10


def font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def wrap(draw, text, fnt, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        trial = (current + " " + word).strip()

        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


def make_frame(label, text):
    img = Image.new(
        "RGB",
        (W, H),
        (18, 18, 22),
    )

    draw = ImageDraw.Draw(img)

    f_label = font(18)
    f_title = font(30)

    draw.text(
        (20, 25),
        label,
        font=f_label,
        fill=(220, 220, 220),
    )

    lines = wrap(
        draw,
        text,
        f_title,
        W - 40,
    )

    total_height = len(lines) * 42
    y = max(100, (H - total_height) // 2)

    for line in lines:
        bbox = draw.textbbox(
            (0, 0),
            line,
            font=f_title,
        )

        text_width = bbox[2] - bbox[0]

        draw.text(
            ((W - text_width) / 2, y),
            line,
            font=f_title,
            fill=(255, 255, 255),
        )

        y += 42

    return np.asarray(img)


def render_video(hook, script, caption, hashtags, job_id):
    path = VIDEO_DIR / f"money_ai_{job_id}.mp4"

    print(
        f"[MONEY AI] Starting video render for job {job_id}",
        flush=True,
    )

    scenes = [
        ("HOOK", hook, 2),
        ("STORY", script, 3),
        ("TAKEAWAY", caption, 3),
        ("TAGS", " ".join(hashtags), 2),
    ]

    writer = imageio.get_writer(
        str(path),
        fps=FPS,
        codec="libx264",
        quality=3,
        macro_block_size=None,
    )

    try:
        for label, text, seconds in scenes:
            print(
                f"[MONEY AI] Rendering scene: {label}",
                flush=True,
            )

            frame = make_frame(label, text)
            frame_count = FPS * seconds

            for _ in range(frame_count):
                writer.append_data(frame)

    finally:
        writer.close()

    print(
        f"[MONEY AI] Video ready: {path}",
        flush=True,
    )

    return str(path)
