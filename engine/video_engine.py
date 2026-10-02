import os
import re
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio.v2 as imageio
import numpy as np


VIDEO_DIR = Path(os.getenv("VIDEO_DIR", "generated_videos"))
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

W = 540
H = 960
FPS = 12


def font(size, bold=True):
    candidates = []

    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


FONT_SMALL = font(24, False)
FONT_MEDIUM = font(30, True)
FONT_TITLE = font(48, True)
FONT_HUGE = font(66, True)
FONT_BODY = font(34, False)


def clean_text(text):
    text = str(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def wrap_text(draw, text, fnt, max_width):
    words = clean_text(text).split()

    if not words:
        return []

    lines = []
    current = words[0]

    for word in words[1:]:
        candidate = current + " " + word

        bbox = draw.textbbox(
            (0, 0),
            candidate,
            font=fnt,
        )

        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)

    return lines


def rounded_rectangle(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def gradient_background(t):
    img = Image.new("RGB", (W, H))

    px = img.load()

    for y in range(H):
        progress = y / max(1, H - 1)

        r = int(9 + 12 * progress)
        g = int(11 + 15 * progress)
        b = int(20 + 28 * progress)

        for x in range(W):
            wave = int(
                8
                * math.sin(
                    (x / W) * math.pi * 2
                    + t * 1.7
                )
            )

            px[x, y] = (
                max(0, min(255, r + wave)),
                max(0, min(255, g + wave)),
                max(0, min(255, b + wave)),
            )

    return img


def add_glow(img, center, radius=220):
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)

    cx, cy = center

    draw.ellipse(
        (
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
        ),
        fill=(70, 110, 255, 55),
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(radius // 2)
    )

    img.alpha_composite(glow)


def draw_top_brand(draw):
    draw.text(
        (32, 28),
        "MONEY AI",
        font=FONT_MEDIUM,
        fill=(255, 255, 255),
    )

    draw.text(
        (32, 66),
        "NEWS • MONEY • AI",
        font=FONT_SMALL,
        fill=(150, 160, 180),
    )


def draw_progress(draw, progress):
    x1 = 32
    x2 = W - 32
    y = H - 24

    draw.rounded_rectangle(
        (x1, y, x2, y + 5),
        radius=3,
        fill=(55, 60, 75),
    )

    current = x1 + (x2 - x1) * max(
        0,
        min(1, progress),
    )

    draw.rounded_rectangle(
        (x1, y, current, y + 5),
        radius=3,
        fill=(255, 255, 255),
    )


def draw_scene_number(draw, number):
    text = f"{number:02d}"

    draw.text(
        (W - 90, 34),
        text,
        font=FONT_MEDIUM,
        fill=(125, 135, 155),
    )


def draw_text_block(
    draw,
    text,
    y,
    fnt,
    max_width,
    fill=(255, 255, 255),
    line_gap=12,
):
    lines = wrap_text(
        draw,
        text,
        fnt,
        max_width,
    )

    current_y = y

    for line in lines:
        bbox = draw.textbbox(
            (0, 0),
            line,
            font=fnt,
        )

        width = bbox[2] - bbox[0]

        x = (W - width) / 2

        draw.text(
            (x + 2, current_y + 3),
            line,
            font=fnt,
            fill=(0, 0, 0),
        )

        draw.text(
            (x, current_y),
            line,
            font=fnt,
            fill=fill,
        )

        height = bbox[3] - bbox[1]

        current_y += height + line_gap

    return current_y


def draw_highlight_card(
    draw,
    text,
    y,
    accent=True,
):
    lines = wrap_text(
        draw,
        text,
        FONT_MEDIUM,
        W - 100,
    )

    if not lines:
        return y

    line_height = 42
    padding = 24

    height = (
        len(lines) * line_height
        + padding * 2
    )

    x1 = 42
    x2 = W - 42

    rounded_rectangle(
        draw,
        (x1, y, x2, y + height),
        24,
        fill=(24, 28, 40),
        outline=(60, 68, 88),
        width=2,
    )

    if accent:
        draw.rounded_rectangle(
            (x1, y, x1 + 8, y + height),
            radius=4,
            fill=(105, 130, 255),
        )

    current_y = y + padding

    for line in lines:
        draw.text(
            (x1 + 28, current_y),
            line,
            font=FONT_MEDIUM,
            fill=(245, 247, 255),
        )

        current_y += line_height

    return y + height


def make_frame(
    scene_type,
    headline,
    body,
    scene_number,
    progress,
    t,
):
    img = gradient_background(t).convert("RGBA")

    add_glow(
        img,
        (
            int(W * 0.75 + math.sin(t * 1.4) * 80),
            int(H * 0.28),
        ),
    )

    add_glow(
        img,
        (
            int(W * 0.2),
            int(H * 0.72 + math.cos(t * 1.1) * 60),
        ),
        radius=180,
    )

    draw = ImageDraw.Draw(img)

    draw_top_brand(draw)
    draw_scene_number(draw, scene_number)

    if scene_type == "HOOK":
        draw.text(
            (42, 170),
            "BREAKING DOWN",
            font=FONT_SMALL,
            fill=(145, 160, 190),
        )

        draw_text_block(
            draw,
            headline,
            235,
            FONT_HUGE,
            W - 80,
        )

        draw_highlight_card(
            draw,
            "Here's what actually matters.",
            590,
        )

    elif scene_type == "STORY":
        draw.text(
            (42, 170),
            "THE STORY",
            font=FONT_SMALL,
            fill=(145, 160, 190),
        )

        draw_text_block(
            draw,
            headline,
            225,
            FONT_TITLE,
            W - 80,
        )

        draw_highlight_card(
            draw,
            body,
            480,
        )

    elif scene_type == "WHY":
        draw.text(
            (42, 170),
            "WHY IT MATTERS",
            font=FONT_SMALL,
            fill=(145, 160, 190),
        )

        draw_text_block(
            draw,
            headline,
            230,
            FONT_TITLE,
            W - 80,
        )

        draw_highlight_card(
            draw,
            body,
            500,
        )

    elif scene_type == "TAKEAWAY":
        draw.text(
            (42, 170),
            "THE TAKEAWAY",
            font=FONT_SMALL,
            fill=(145, 160, 190),
        )

        draw_text_block(
            draw,
            headline,
            245,
            FONT_HUGE,
            W - 80,
        )

        draw_highlight_card(
            draw,
            body,
            560,
        )

    elif scene_type == "SOURCE":
        draw.text(
            (42, 170),
            "SOURCE",
            font=FONT_SMALL,
            fill=(145, 160, 190),
        )

        draw.text(
            (42, 225),
            "Read the original",
            font=FONT_TITLE,
            fill=(255, 255, 255),
        )

        draw_highlight_card(
            draw,
            body,
            330,
        )

        draw.text(
            (42, 720),
            "MONEY AI",
            font=FONT_MEDIUM,
            fill=(255, 255, 255),
        )

        draw.text(
            (42, 765),
            "Facts first. Hype second.",
            font=FONT_SMALL,
            fill=(145, 160, 190),
        )

    draw_progress(draw, progress)

    return np.asarray(img.convert("RGB"))


def split_script(script):
    script = clean_text(script)

    if not script:
        return [
            "Watch this story closely.",
            "Here is what matters.",
        ]

    sentences = re.split(
        r"(?<=[.!?])\s+",
        script,
    )

    sentences = [
        clean_text(x)
        for x in sentences
        if clean_text(x)
    ]

    if len(sentences) <= 2:
        words = script.split()

        chunks = []

        chunk = []

        for word in words:
            chunk.append(word)

            if len(chunk) >= 14:
                chunks.append(" ".join(chunk))
                chunk = []

        if chunk:
            chunks.append(" ".join(chunk))

        return chunks[:5]

    return sentences[:5]


def render_video(
    hook,
    script,
    caption,
    hashtags,
    job_id,
):
    path = VIDEO_DIR / f"money_ai_{job_id}.mp4"

    print(
        f"[MONEY AI] Starting professional render for job {job_id}",
        flush=True,
    )

    parts = split_script(script)

    scenes = []

    scenes.append(
        {
            "type": "HOOK",
            "headline": clean_text(hook),
            "body": "",
            "seconds": 3,
        }
    )

    if parts:
        scenes.append(
            {
                "type": "STORY",
                "headline": parts[0],
                "body": (
                    parts[1]
                    if len(parts) > 1
                    else ""
                ),
                "seconds": 4,
            }
        )

    if len(parts) > 2:
        scenes.append(
            {
                "type": "WHY",
                "headline": parts[2],
                "body": (
                    parts[3]
                    if len(parts) > 3
                    else ""
                ),
                "seconds": 4,
            }
        )

    scenes.append(
        {
            "type": "TAKEAWAY",
            "headline": "What should you remember?",
            "body": clean_text(caption),
            "seconds": 4,
        }
    )

    scenes.append(
        {
            "type": "SOURCE",
            "headline": "Follow the source.",
            "body": (
                "MONEY AI turns important stories "
                "into short, understandable videos."
            ),
            "seconds": 3,
        }
    )

    total_seconds = sum(
        scene["seconds"]
        for scene in scenes
    )

    writer = imageio.get_writer(
        str(path),
        fps=FPS,
        codec="libx264",
        quality=5,
        macro_block_size=None,
    )

    frame_index = 0
    total_frames = max(
        1,
        int(total_seconds * FPS),
    )

    try:
        for index, scene in enumerate(scenes):
            print(
                f"[MONEY AI] Rendering scene "
                f"{index + 1}/{len(scenes)}: "
                f"{scene['type']}",
                flush=True,
            )

            frame_count = int(
                scene["seconds"] * FPS
            )

            for local_frame in range(frame_count):
                local_progress = (
                    local_frame
                    / max(1, frame_count - 1)
                )

                global_progress = (
                    frame_index
                    / max(1, total_frames - 1)
                )

                frame = make_frame(
                    scene_type=scene["type"],
                    headline=scene["headline"],
                    body=scene["body"],
                    scene_number=index + 1,
                    progress=global_progress,
                    t=local_progress,
                )

                writer.append_data(frame)

                frame_index += 1

    finally:
        writer.close()

    print(
        f"[MONEY AI] Video ready: {path}",
        flush=True,
    )

    return str(path)
