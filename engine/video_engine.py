import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio

VIDEO_DIR = Path(os.getenv("VIDEO_DIR", "generated_videos"))
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

W, H = 540, 960
FPS = 15


def font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]

    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)

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


def render_video(hook, script, caption, hashtags, job_id):
    path = VIDEO_DIR / f"money_ai_{job_id}.mp4"

    f_hook = font(42)
    f_body = font(28)
    f_small = font(22)

    scenes = [
        ("HOOK", hook),
        ("STORY", script),
        ("TAKEAWAY", caption),
        ("TAGS", " ".join(hashtags)),
    ]

    writer = imageio.get_writer(
        str(path),
        fps=FPS,
        codec="libx264",
        quality=5,
        macro_block_size=None,
    )

    try:
        for label, text in scenes:
            frame_count = FPS * (3 if label == "HOOK" else 5)

            for _ in range(frame_count):
                img = Image.new(
                    "RGB",
                    (W, H),
                    (18, 18, 22),
                )

                draw = ImageDraw.Draw(img)

                draw.text(
                    (35, 50),
                    label,
                    font=f_small,
                    fill=(220, 220, 220),
                )

                fnt = f_hook if label == "HOOK" else f_body

                lines = wrap(
                    draw,
                    text,
                    fnt,
                    W - 70,
                )

                y = 250

                for line in lines:
                    bbox = draw.textbbox(
                        (0, 0),
                        line,
                        font=fnt,
                    )

                    tw = bbox[2] - bbox[0]

                    draw.text(
                        ((W - tw) / 2, y),
                        line,
                        font=fnt,
                        fill=(255, 255, 255),
                    )

                    y += fnt.size + 15

                writer.append_data(
                    __import__("numpy").array(img)
                )

    finally:
        writer.close()

    return str(path)
