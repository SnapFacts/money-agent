import os
import re
import math
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
import imageio.v2 as imageio
import numpy as np

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# MONEY AI — FINAL VIDEO ENGINE
# ============================================================

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


# ============================================================
# FONTS
# ============================================================

def get_font(size, bold=True):
    if bold:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


FONT_XS = get_font(20, False)
FONT_SMALL = get_font(24, True)
FONT_BODY = get_font(30, False)
FONT_BODY_BOLD = get_font(31, True)
FONT_TITLE = get_font(44, True)
FONT_BIG = get_font(60, True)


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    value = str(value)
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


def draw_shadow_text(
    draw,
    xy,
    text,
    font,
    fill=(255, 255, 255),
    shadow=(0, 0, 0),
):
    x, y = xy

    draw.text(
        (x + 3, y + 4),
        text,
        font=font,
        fill=shadow,
    )

    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
    )


def draw_centered(
    draw,
    text,
    y,
    font,
    max_width,
    fill=(255, 255, 255),
):
    lines = wrap_text(
        draw,
        text,
        font,
        max_width,
    )

    if not lines:
        return y

    line_height = int(
        font.size * 1.18
    )

    current_y = y

    for line in lines:
        box = draw.textbbox(
            (0, 0),
            line,
            font=font,
        )

        width = box[2] - box[0]

        x = (W - width) / 2

        draw_shadow_text(
            draw,
            (x, current_y),
            line,
            font,
            fill=fill,
        )

        current_y += line_height

    return current_y


# ============================================================
# SOURCE IMAGE
# ============================================================

def download_source_image(url):
    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=15,
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

        if image.width < 200 or image.height < 200:
            return None

        image.thumbnail(
            (1200, 1200),
            Image.Resampling.LANCZOS,
        )

        print(
            "[MONEY AI] Source image loaded",
            flush=True,
        )

        return image

    except Exception as exc:
        print(
            f"[MONEY AI] Source image unavailable: {exc}",
            flush=True,
        )

        return None


def make_background():
    image = Image.new(
        "RGB",
        (W, H),
    )

    draw = ImageDraw.Draw(image)

    for y in range(H):
        p = y / max(1, H - 1)

        r = int(7 + p * 10)
        g = int(9 + p * 13)
        b = int(16 + p * 23)

        draw.line(
            (0, y, W, y),
            fill=(r, g, b),
        )

    return image


def source_background(source_image, progress):
    if source_image is None:
        return make_background().convert("RGBA")

    zoom = 1.0 + (
        0.08 * progress
    )

    crop_width = int(
        source_image.width / zoom
    )

    crop_height = int(
        source_image.height / zoom
    )

    max_x = max(
        0,
        source_image.width - crop_width,
    )

    max_y = max(
        0,
        source_image.height - crop_height,
    )

    # Slow cinematic movement.
    x = int(
        max_x
        * (
            0.20
            + 0.60
            * progress
        )
    )

    y = int(
        max_y
        * (
            0.35
            + 0.15
            * math.sin(
                progress * math.pi
            )
        )
    )

    crop = source_image.crop(
        (
            x,
            y,
            x + crop_width,
            y + crop_height,
        )
    )

    crop = crop.resize(
        (W, H),
        Image.Resampling.LANCZOS,
    )

    return crop.convert("RGBA")


def add_dark_gradient(image):
    overlay = Image.new(
        "RGBA",
        (W, H),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(
        overlay
    )

    # Top protection for branding.
    draw.rectangle(
        (0, 0, W, 130),
        fill=(0, 0, 0, 100),
    )

    # Heavy lower gradient for captions.
    for y in range(
        int(H * 0.35),
        H,
        4,
    ):
        p = (
            y - H * 0.35
        ) / (H * 0.65)

        alpha = int(
            30 + 205 * p
        )

        draw.rectangle(
            (0, y, W, y + 4),
            fill=(0, 0, 0, alpha),
        )

    return Image.alpha_composite(
        image,
        overlay,
    )


# ============================================================
# BRANDING / UI
# ============================================================

def draw_brand(draw):
    draw.text(
        (28, 24),
        "MONEY AI",
        font=FONT_SMALL,
        fill=(255, 255, 255),
    )

    draw.text(
        (28, 57),
        "NEWS • MONEY • AI",
        font=FONT_XS,
        fill=(190, 195, 210),
    )


def draw_progress(draw, progress):
    left = 28
    right = W - 28
    top = H - 18

    draw.rounded_rectangle(
        (
            left,
            top,
            right,
            top + 5,
        ),
        radius=3,
        fill=(75, 80, 95),
    )

    current = left + (
        right - left
    ) * max(
        0,
        min(1, progress),
    )

    draw.rounded_rectangle(
        (
            left,
            top,
            current,
            top + 5,
        ),
        radius=3,
        fill=(255, 255, 255),
    )


def draw_label(
    draw,
    text,
    y=145,
):
    text = clean_text(text).upper()

    draw.rounded_rectangle(
        (
            28,
            y,
            28 + 180,
            y + 42,
        ),
        radius=21,
        fill=(255, 255, 255),
    )

    draw.text(
        (48, y + 9),
        text[:18],
        font=FONT_XS,
        fill=(10, 12, 18),
    )


def draw_card(
    draw,
    x1,
    y1,
    x2,
    y2,
):
    draw.rounded_rectangle(
        (
            x1,
            y1,
            x2,
            y2,
        ),
        radius=24,
        fill=(9, 12, 20),
        outline=(85, 95, 120),
        width=2,
    )


# ============================================================
# SCENES
# ============================================================

def render_scene(
    scene,
    source_image,
    local_progress,
    global_progress,
):
    scene_type = scene["type"]

    headline = clean_text(
        scene.get("headline")
    )

    body = clean_text(
        scene.get("body")
    )

    image = source_background(
        source_image,
        local_progress,
    )

    image = add_dark_gradient(
        image
    )

    # Subtle moving light.
    glow = Image.new(
        "RGBA",
        (W, H),
        (0, 0, 0, 0),
    )

    glow_draw = ImageDraw.Draw(
        glow
    )

    gx = int(
        W * (
            0.20
            + 0.60
            * local_progress
        )
    )

    gy = int(
        H * 0.18
    )

    glow_draw.ellipse(
        (
            gx - 150,
            gy - 150,
            gx + 150,
            gy + 150,
        ),
        fill=(75, 105, 255, 28),
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(80)
    )

    image = Image.alpha_composite(
        image,
        glow,
    )

    draw = ImageDraw.Draw(
        image
    )

    draw_brand(draw)

    if scene_type == "HOOK":
        draw_label(
            draw,
            "WATCH THIS",
            150,
        )

        draw_centered(
            draw,
            headline,
            245,
            FONT_BIG,
            W - 60,
        )

        draw_centered(
            draw,
            "Άκου μέχρι το τέλος.",
            650,
            FONT_BODY_BOLD,
            W - 80,
            fill=(220, 225, 255),
        )

    elif scene_type == "STORY":
        draw_label(
            draw,
            "THE STORY",
            150,
        )

        draw_centered(
            draw,
            headline,
            220,
            FONT_TITLE,
            W - 60,
        )

        if body:
            draw_card(
                draw,
                28,
                500,
                W - 28,
                750,
            )

            draw.text(
                (52, 530),
                "WHAT HAPPENED",
                font=FONT_XS,
                fill=(165, 180, 255),
            )

            lines = wrap_text(
                draw,
                body,
                FONT_BODY,
                W - 100,
            )

            y = 575

            for line in lines[:5]:
                draw.text(
                    (52, y),
                    line,
                    font=FONT_BODY,
                    fill=(245, 246, 250),
                )

                y += 43

    elif scene_type == "WHY":
        draw_label(
            draw,
            "WHY IT MATTERS",
            150,
        )

        draw_centered(
            draw,
            headline,
            220,
            FONT_TITLE,
            W - 60,
        )

        if body:
            draw_card(
                draw,
                28,
                540,
                W - 28,
                780,
            )

            draw.text(
                (52, 570),
                "KEY POINT",
                font=FONT_XS,
                fill=(165, 180, 255),
            )

            lines = wrap_text(
                draw,
                body,
                FONT_BODY,
                W - 100,
            )

            y = 615

            for line in lines[:4]:
                draw.text(
                    (52, y),
                    line,
                    font=FONT_BODY,
                    fill=(255, 255, 255),
                )

                y += 43

    elif scene_type == "TAKEAWAY":
        draw_label(
            draw,
            "TAKEAWAY",
            150,
        )

        draw_centered(
            draw,
            headline,
            240,
            FONT_BIG,
            W - 60,
        )

        if body:
            draw.rounded_rectangle(
                (
                    28,
                    590,
                    W - 28,
                    795,
                ),
                radius=24,
                fill=(255, 255, 255),
            )

            lines = wrap_text(
                draw,
                body,
                FONT_BODY_BOLD,
                W - 100,
            )

            y = 630

            for line in lines[:4]:
                draw.text(
                    (52, y),
                    line,
                    font=FONT_BODY_BOLD,
                    fill=(10, 12, 18),
                )

                y += 43

    elif scene_type == "SOURCE":
        draw_label(
            draw,
            "SOURCE",
            150,
        )

        draw_centered(
            draw,
            headline,
            245,
            FONT_TITLE,
            W - 60,
        )

        draw_card(
            draw,
            28,
            525,
            W - 28,
            735,
        )

        draw.text(
            (52, 555),
            "ORIGINAL STORY",
            font=FONT_XS,
            fill=(165, 180, 255),
        )

        lines = wrap_text(
            draw,
            body,
            FONT_BODY,
            W - 100,
        )

        y = 605

        for line in lines[:4]:
            draw.text(
                (52, y),
                line,
                font=FONT_BODY,
                fill=(245, 246, 250),
            )

            y += 43

        draw.text(
            (28, 805),
            "MONEY AI",
            font=FONT_SMALL,
            fill=(255, 255, 255),
        )

        draw.text(
            (28, 840),
            "Facts first. Hype second.",
            font=FONT_XS,
            fill=(190, 195, 210),
        )

    draw_progress(
        draw,
        global_progress,
    )

    return np.asarray(
        image.convert("RGB")
    )


# ============================================================
# SCRIPT PROCESSING
# ============================================================

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

    if len(sentences) >= 3:
        return sentences[:5]

    words = script.split()

    chunks = []
    current = []

    for word in words:
        current.append(word)

        if len(current) >= 12:
            chunks.append(
                " ".join(current)
            )
            current = []

    if current:
        chunks.append(
            " ".join(current)
        )

    return chunks[:5]


# ============================================================
# OPTIONAL VOICEOVER
# ============================================================

def find_ffmpeg():
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()

    except Exception:
        return None


def create_voiceover(script, output_path):
    """
    Creates Greek TTS using the currently available
    network TTS endpoint.

    If unavailable, the video still renders normally.
    """

    script = clean_text(script)

    if not script:
        return False

    # Split into manageable chunks.
    sentences = re.split(
        r"(?<=[.!?])\s+",
        script,
    )

    sentences = [
        clean_text(x)
        for x in sentences
        if clean_text(x)
    ]

    chunks = []

    current = ""

    for sentence in sentences:
        if (
            len(current)
            + len(sentence)
            + 1
            <= 180
        ):
            current = (
                current + " " + sentence
            ).strip()
        else:
            if current:
                chunks.append(current)

            current = sentence

    if current:
        chunks.append(current)

    if not chunks:
        return False

    temp_files = []

    try:
        for index, chunk in enumerate(
            chunks
        ):
            url = (
                "https://translate.google.com/"
                "translate_tts"
                "?ie=UTF-8"
                "&client=tw-ob"
                "&tl=el"
                f"&q={quote(chunk, safe='')}"
            )

            response = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent":
                        "Mozilla/5.0"
                },
            )

            response.raise_for_status()

            if len(response.content) < 1000:
                continue

            temp_path = (
                Path(output_path).parent
                / (
                    Path(output_path).stem
                    + f"_part_{index}.mp3"
                )
            )

            with open(
                temp_path,
                "wb",
            ) as file:
                file.write(
                    response.content
                )

            temp_files.append(
                str(temp_path)
            )

        if not temp_files:
            return False

        ffmpeg = find_ffmpeg()

        if not ffmpeg:
            # Use first chunk if ffmpeg is unavailable.
            os.replace(
                temp_files[0],
                output_path,
            )

            for file in temp_files[1:]:
                try:
                    os.remove(file)
                except Exception:
                    pass

            return True

        concat_file = (
            Path(output_path).parent
            / (
                Path(output_path).stem
                + "_concat.txt"
            )
        )

        with open(
            concat_file,
            "w",
            encoding="utf-8",
        ) as file:
            for item in temp_files:
                file.write(
                    "file '"
                    + item.replace(
                        "'",
                        "'\\''",
                    )
                    + "'\n"
                )

        command = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:a",
            "mp3",
            "-b:a",
            "128k",
            str(output_path),
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )

        if result.returncode != 0:
            return False

        return os.path.exists(
            output_path
        )

    except Exception as exc:
        print(
            f"[MONEY AI] Voice-over unavailable: {exc}",
            flush=True,
        )

        return False

    finally:
        for file in temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception:
                pass

        try:
            if os.path.exists(
                concat_file
            ):
                os.remove(
                    concat_file
                )
        except Exception:
            pass


def attach_audio(
    video_path,
    audio_path,
):
    if not os.path.exists(
        audio_path
    ):
        return video_path

    ffmpeg = find_ffmpeg()

    if not ffmpeg:
        print(
            "[MONEY AI] FFmpeg unavailable; "
            "keeping video without audio.",
            flush=True,
        )

        return video_path

    temp_output = (
        str(video_path)
        + ".muxed.mp4"
    )

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        temp_output,
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )

        if result.returncode != 0:
            print(
                "[MONEY AI] Audio mux failed",
                flush=True,
            )

            return video_path

        os.replace(
            temp_output,
            video_path,
        )

        return video_path

    except Exception as exc:
        print(
            f"[MONEY AI] Audio mux error: {exc}",
            flush=True,
        )

        return video_path


# ============================================================
# MAIN RENDER
# ============================================================

def render_video(
    hook,
    script,
    caption,
    hashtags,
    job_id,
    source=None,
):
    source = source or {}

    output_path = (
        VIDEO_DIR
        / f"money_ai_{job_id}.mp4"
    )

    audio_path = (
        VIDEO_DIR
        / f"money_ai_{job_id}.mp3"
    )

    source_image = download_source_image(
        source.get("image_url")
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
            "headline": "Κράτα αυτό.",
            "body": clean_text(
                caption
            ),
            "seconds": 4,
        }
    )

    scenes.append(
        {
            "type": "SOURCE",
            "headline": source_name,
            "body": (
                source_title
                or "Δες την αρχική πηγή "
                "για ολόκληρο το context."
            ),
            "seconds": 3,
        }
    )

    total_frames = sum(
        int(
            scene["seconds"]
            * FPS
        )
        for scene in scenes
    )

    print(
        f"[MONEY AI] Rendering final video "
        f"{W}x{H} @ {FPS}fps",
        flush=True,
    )

    writer = imageio.get_writer(
        str(output_path),
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
            frame_count = int(
                scene["seconds"]
                * FPS
            )

            print(
                f"[MONEY AI] Scene "
                f"{scene_index + 1}/"
                f"{len(scenes)}: "
                f"{scene['type']}",
                flush=True,
            )

            for frame_number in range(
                frame_count
            ):
                local_progress = (
                    frame_number
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

                frame = render_scene(
                    scene,
                    source_image,
                    local_progress,
                    global_progress,
                )

                writer.append_data(
                    frame
                )

                frame_index += 1

    finally:
        writer.close()

    print(
        f"[MONEY AI] Visual video ready: "
        f"{output_path}",
        flush=True,
    )

    # Voice-over is optional.
    # A failure here must NEVER destroy the video.
    if create_voiceover(
        script,
        audio_path,
    ):
        attach_audio(
            output_path,
            audio_path,
        )

        try:
            os.remove(
                audio_path
            )
        except Exception:
            pass

    print(
        f"[MONEY AI] FINAL VIDEO: "
        f"{output_path}",
        flush=True,
    )

    return str(output_path)
