import os
import re
import math
from io import BytesIO
from pathlib import Path

import requests
import imageio.v2 as imageio
import numpy as np

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
    ImageOps,
)


VIDEO_DIR = Path(
    os.getenv("VIDEO_DIR", "generated_videos")
)

VIDEO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

W = 540
H = 960
FPS = 12


def get_font(size, bold=True):
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


FONT_SMALL = get_font(22, False)
FONT_LABEL = get_font(26, True)
FONT_BODY = get_font(31, False)
FONT_TITLE = get_font(45, True)
FONT_BIG = get_font(62, True)


def clean_text(value):
    value = str(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def wrap_text(draw, text, font, max_width):
    words = clean_text(text).split()

    if not words:
        return []

    lines = []
    current = words[0]

    for word in words[1:]:
        candidate = current + " " + word

        box = draw.textbbox(
            (0, 0),
            candidate,
            font=font,
        )

        if box[2] - box[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)

    return lines


def load_remote_image(url):
    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; MONEY-AI/1.0)"
                )
            },
        )

        response.raise_for_status()

        image = Image.open(
            BytesIO(response.content)
        ).convert("RGB")

        if image.width < 100 or image.height < 100:
            return None

        image.thumbnail(
            (1200, 1200),
            Image.Resampling.LANCZOS,
        )

        return image

    except Exception as exc:
        print(
            f"[MONEY AI] Could not load source image: {exc}",
            flush=True,
        )

        return None


def crop_cover(image, width, height):
    ratio = max(
        width / image.width,
        height / image.height,
    )

    new_size = (
        int(image.width * ratio),
        int(image.height * ratio),
    )

    image = image.resize(
        new_size,
        Image.Resampling.LANCZOS,
    )

    left = (image.width - width) // 2
    top = (image.height - height) // 2

    return image.crop(
        (
            left,
            top,
            left + width,
            top + height,
        )
    )


def make_gradient():
    img = Image.new(
        "RGB",
        (W, H),
    )

    pixels = img.load()

    for y in range(H):
        p = y / max(1, H - 1)

        r = int(7 + 9 * p)
        g = int(9 + 12 * p)
        b = int(16 + 22 * p)

        for x in range(W):
            pixels[x, y] = (
                r,
                g,
                b,
            )

    return img


def add_dark_overlay(image, strength=130):
    overlay = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, strength),
    )

    return Image.alpha_composite(
        image.convert("RGBA"),
        overlay,
    )


def add_bottom_gradient(image):
    overlay = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(
        overlay
    )

    for y in range(
        int(H * 0.42),
        H,
    ):
        progress = (
            y - H * 0.42
        ) / (H * 0.58)

        alpha = int(
            min(
                225,
                25 + progress * 200,
            )
        )

        draw.line(
            (0, y, W, y),
            fill=(0, 0, 0, alpha),
        )

    return Image.alpha_composite(
        image,
        overlay,
    )


def add_glow(image, x, y, radius=190):
    glow = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(glow)

    draw.ellipse(
        (
            x - radius,
            y - radius,
            x + radius,
            y + radius,
        ),
        fill=(70, 110, 255, 45),
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(
            radius // 2
        )
    )

    image.alpha_composite(glow)


def draw_brand(draw):
    draw.text(
        (28, 26),
        "MONEY AI",
        font=FONT_LABEL,
        fill=(255, 255, 255),
    )

    draw.text(
        (28, 61),
        "NEWS • MONEY • AI",
        font=FONT_SMALL,
        fill=(185, 190, 205),
    )


def draw_progress(
    draw,
    progress,
):
    x1 = 28
    x2 = W - 28
    y = H - 19

    draw.rounded_rectangle(
        (
            x1,
            y,
            x2,
            y + 5,
        ),
        radius=3,
        fill=(80, 84, 98),
    )

    current = x1 + (
        x2 - x1
    ) * max(
        0,
        min(1, progress),
    )

    draw.rounded_rectangle(
        (
            x1,
            y,
            current,
            y + 5,
        ),
        radius=3,
        fill=(255, 255, 255),
    )


def draw_shadow_text(
    draw,
    position,
    text,
    font,
    fill=(255, 255, 255),
):
    x, y = position

    draw.text(
        (
            x + 3,
            y + 4,
        ),
        text,
        font=font,
        fill=(0, 0, 0),
    )

    draw.text(
        position,
        text,
        font=font,
        fill=fill,
    )


def draw_center_text(
    draw,
    text,
    y,
    font,
    max_width,
):
    lines = wrap_text(
        draw,
        text,
        font,
        max_width,
    )

    if not lines:
        return y

    line_gap = 9
    current_y = y

    for line in lines:
        box = draw.textbbox(
            (0, 0),
            line,
            font=font,
        )

        width = (
            box[2] - box[0]
        )

        x = (
            W - width
        ) / 2

        draw_shadow_text(
            draw,
            (x, current_y),
            line,
            font,
        )

        current_y += (
            box[3]
            - box[1]
            + line_gap
        )

    return current_y


def make_visual_background(
    source_image,
    progress,
):
    if source_image is None:
        return make_gradient().convert(
            "RGBA"
        )

    base_width = W
    base_height = H

    zoom = (
        1.0
        + 0.10 * progress
    )

    crop_w = int(
        source_image.width
        / zoom
    )

    crop_h = int(
        source_image.height
        / zoom
    )

    max_x = max(
        0,
        source_image.width
        - crop_w,
    )

    max_y = max(
        0,
        source_image.height
        - crop_h,
    )

    x = int(
        max_x
        * (
            0.35
            + 0.30
            * math.sin(
                progress * math.pi
            )
        )
    )

    y = int(
        max_y
        * (
            0.35
            + 0.20
            * progress
        )
    )

    cropped = source_image.crop(
        (
            x,
            y,
            x + crop_w,
            y + crop_h,
        )
    )

    cropped = cropped.resize(
        (
            base_width,
            base_height,
        ),
        Image.Resampling.LANCZOS,
    )

    return cropped.convert(
        "RGBA"
    )


def split_script(script):
    script = clean_text(script)

    if not script:
        return []

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
        current = []

        for word in words:
            current.append(word)

            if len(current) >= 13:
                chunks.append(
                    " ".join(current)
                )
                current = []

        if current:
            chunks.append(
                " ".join(current)
            )

        return chunks[:5]

    return sentences[:5]


def scene_frame(
    scene,
    source_image,
    progress,
    global_progress,
):
    scene_type = scene["type"]
    headline = clean_text(
        scene.get("headline")
    )
    body = clean_text(
        scene.get("body")
    )

    background = make_visual_background(
        source_image,
        progress,
    )

    background = add_bottom_gradient(
        background
    )

    add_glow(
        background,
        int(W * 0.82),
        int(H * 0.20),
        170,
    )

    draw = ImageDraw.Draw(
        background
    )

    draw_brand(draw)

    if scene_type == "HOOK":
        draw.rounded_rectangle(
            (
                28,
                145,
                205,
                190,
            ),
            radius=22,
            fill=(255, 255, 255),
        )

        draw.text(
            (48, 154),
            "WATCH THIS",
            font=FONT_SMALL,
            fill=(10, 12, 18),
        )

        draw_center_text(
            draw,
            headline,
            250,
            FONT_BIG,
            W - 70,
        )

        draw_center_text(
            draw,
            "Here is what actually matters.",
            640,
            FONT_BODY,
            W - 90,
        )

    elif scene_type == "STORY":
        draw.text(
            (28, 150),
            "THE STORY",
            font=FONT_SMALL,
            fill=(185, 190, 205),
        )

        draw_center_text(
            draw,
            headline,
            205,
            FONT_TITLE,
            W - 70,
        )

        if body:
            box_y = 510

            draw.rounded_rectangle(
                (
                    30,
                    box_y,
                    W - 30,
                    730,
                ),
                radius=24,
                fill=(10, 12, 18, 225),
                outline=(100, 110, 135),
                width=2,
            )

            lines = wrap_text(
                draw,
                body,
                FONT_BODY,
                W - 90,
            )

            y = box_y + 35

            for line in lines[:5]:
                draw.text(
                    (50, y),
                    line,
                    font=FONT_BODY,
                    fill=(245, 246, 250),
                )

                y += 43

    elif scene_type == "WHY":
        draw.text(
            (28, 150),
            "WHY IT MATTERS",
            font=FONT_SMALL,
            fill=(185, 190, 205),
        )

        draw_center_text(
            draw,
            headline,
            215,
            FONT_TITLE,
            W - 70,
        )

        if body:
            draw.rounded_rectangle(
                (
                    30,
                    555,
                    W - 30,
                    760,
                ),
                radius=24,
                fill=(15, 18, 27, 230),
                outline=(100, 110, 135),
                width=2,
            )

            draw.text(
                (52, 585),
                "KEY POINT",
                font=FONT_SMALL,
                fill=(165, 180, 255),
            )

            lines = wrap_text(
                draw,
                body,
                FONT_BODY,
                W - 100,
            )

            y = 630

            for line in lines[:4]:
                draw.text(
                    (52, y),
                    line,
                    font=FONT_BODY,
                    fill=(255, 255, 255),
                )

                y += 42

    elif scene_type == "TAKEAWAY":
        draw.text(
            (28, 150),
            "THE TAKEAWAY",
            font=FONT_SMALL,
            fill=(185, 190, 205),
        )

        draw_center_text(
            draw,
            headline,
            245,
            FONT_BIG,
            W - 70,
        )

        if body:
            draw.rounded_rectangle(
                (
                    30,
                    585,
                    W - 30,
                    790,
                ),
                radius=24,
                fill=(255, 255, 255),
            )

            lines = wrap_text(
                draw,
                body,
                FONT_BODY,
                W - 95,
            )

            y = 625

            for line in lines[:4]:
                draw.text(
                    (52, y),
                    line,
                    font=FONT_BODY,
                    fill=(12, 14, 20),
                )

                y += 43

    elif scene_type == "SOURCE":
        draw.text(
            (28, 150),
            "SOURCE",
            font=FONT_SMALL,
            fill=(185, 190, 205),
        )

        draw_center_text(
            draw,
            headline,
            230,
            FONT_TITLE,
            W - 70,
        )

        draw.rounded_rectangle(
            (
                32,
                510,
                W - 32,
                720,
            ),
            radius=26,
            fill=(12, 15, 22, 235),
            outline=(90, 100, 125),
            width=2,
        )

        draw.text(
            (58, 545),
            "ORIGINAL STORY",
            font=FONT_SMALL,
            fill=(165, 180, 255),
        )

        lines = wrap_text(
            draw,
            body,
            FONT_BODY,
            W - 115,
        )

        y = 600

        for line in lines[:4]:
            draw.text(
                (58, y),
                line,
                font=FONT_BODY,
                fill=(245, 246, 250),
            )

            y += 42

        draw.text(
            (32, 805),
            "MONEY AI",
            font=FONT_LABEL,
            fill=(255, 255, 255),
        )

        draw.text(
            (32, 842),
            "Facts first. Hype second.",
            font=FONT_SMALL,
            fill=(185, 190, 205),
        )

    draw_progress(
        draw,
        global_progress,
    )

    return np.asarray(
        background.convert("RGB")
    )


def render_video(
    hook,
    script,
    caption,
    hashtags,
    job_id,
    source=None,
):
    path = (
        VIDEO_DIR
        / f"money_ai_{job_id}.mp4"
    )

    source = source or {}

    image_url = (
        source.get("image_url")
        or ""
    )

    source_name = clean_text(
        source.get("site_name")
        or source.get("name")
        or "Original source"
    )

    source_title = clean_text(
        source.get("title")
        or ""
    )

    print(
        f"[MONEY AI] Loading source visual: {image_url}",
        flush=True,
    )

    source_image = load_remote_image(
        image_url
    )

    if source_image:
        print(
            "[MONEY AI] Source visual loaded",
            flush=True,
        )
    else:
        print(
            "[MONEY AI] No usable source visual; "
            "using generated background",
            flush=True,
        )

    parts = split_script(
        script
    )

    scenes = [
        {
            "type": "HOOK",
            "headline": clean_text(hook),
            "body": "",
            "seconds": 3,
        }
    ]

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
            "headline": (
                "What should you remember?"
            ),
            "body": clean_text(
                caption
            ),
            "seconds": 4,
        }
    )

    scenes.append(
        {
            "type": "SOURCE",
            "headline": (
                source_name
                or "Original source"
            ),
            "body": (
                source_title
                or "Follow the original story "
                "for the full context."
            ),
            "seconds": 3,
        }
    )

    total_seconds = sum(
        scene["seconds"]
        for scene in scenes
    )

    total_frames = max(
        1,
        int(
            total_seconds * FPS
        ),
    )

    print(
        f"[MONEY AI] Rendering "
        f"{total_seconds}s video "
        f"at {W}x{H}/{FPS}fps",
        flush=True,
    )

    writer = imageio.get_writer(
        str(path),
        fps=FPS,
        codec="libx264",
        quality=5,
        macro_block_size=None,
    )

    frame_index = 0

    try:
        for scene_index, scene in enumerate(
            scenes
        ):
            print(
                f"[MONEY AI] Scene "
                f"{scene_index + 1}/"
                f"{len(scenes)}: "
                f"{scene['type']}",
                flush=True,
            )

            frame_count = int(
                scene["seconds"]
                * FPS
            )

            for local_frame in range(
                frame_count
            ):
                local_progress = (
                    local_frame
                    / max(
                        1,
                        frame_count - 1,
                    )
                )

                global_progress = (
                    frame_index
                    / max(
                        1,
                        total_frames - 1,
                    )
                )

                frame = scene_frame(
                    scene=scene,
                    source_image=source_image,
                    progress=local_progress,
                    global_progress=global_progress,
                )

                writer.append_data(
                    frame
                )

                frame_index += 1

    finally:
        writer.close()

    print(
        f"[MONEY AI] Video ready: {path}",
        flush=True,
    )

    return str(path)
