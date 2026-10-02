import os
import secrets
import threading
from pathlib import Path

from flask import (
    Flask,
    redirect,
    request,
    session,
    send_from_directory,
    render_template,
    jsonify,
)

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from engine.tiktok_connector import TikTokConnector
from engine.db import (
    init_db,
    create_content_job,
    list_jobs,
    get_job,
    update_job_status,
)
from engine.content_engine import generate_content
from engine.video_engine import render_video
from engine.trend_engine import get_trend_candidates


app = Flask(__name__)
app.secret_key = os.environ["MONEY_AI_SECRET_KEY"]

state_serializer = URLSafeTimedSerializer(app.secret_key)
tiktok = TikTokConnector()

init_db()


@app.get("/tiktokcM12XuTiIWdyAz7FnURIteP29vho3X9t.txt")
def tiktok_verification_file():
    return send_from_directory(
        os.path.dirname(os.path.abspath(__file__)),
        "tiktokcM12XuTiIWdyAz7FnURIteP29vho3X9t.txt",
        mimetype="text/plain",
    )


@app.get("/")
def home():
    return render_template("dashboard.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "money-ai",
        "tiktok": tiktok.configuration_status(),
        "ai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/api/trends")
def api_trends():
    return jsonify(get_trend_candidates())


@app.get("/api/jobs")
def api_jobs():
    return jsonify(list_jobs())


def render_job_background(job_id, content):
    try:
        update_job_status(job_id, "rendering")

        source = content.get("source") or {}

        output = render_video(
            hook=content.get("hook", ""),
            script=content.get("script", ""),
            caption=content.get("caption", ""),
            hashtags=content.get("hashtags", []),
            job_id=job_id,
            source=source,
        )

        update_job_status(job_id, "video_ready")

        print(
            f"[MONEY AI] Video ready for job {job_id}: {output}",
            flush=True,
        )

    except Exception as exc:
        print(
            f"[MONEY AI] Video rendering failed for job {job_id}: {exc}",
            flush=True,
        )

        try:
            update_job_status(job_id, "error")
        except Exception:
            pass


@app.post("/api/generate")
def api_generate():
    payload = request.get_json(silent=True) or {}

    topic = (payload.get("topic") or "").strip()
    source_url = (payload.get("source_url") or "").strip() or None
    source_name = (payload.get("source_name") or "").strip() or None
    published_at = (payload.get("published_at") or "").strip() or None

    if not topic:
        return {"error": "topic is required"}, 400

    try:
        content = generate_content(
            topic=topic,
            source_url=source_url,
            source_name=source_name,
            published_at=published_at,
        )

        job_id = create_content_job(
            topic,
            content,
        )

        thread = threading.Thread(
            target=render_job_background,
            args=(job_id, content),
            daemon=True,
        )

        thread.start()

        return jsonify(
            {
                "job_id": job_id,
                "topic": topic,
                "source_url": source_url,
                "source_name": source_name,
                "content": content,
                "status": "rendering",
            }
        )

    except Exception as exc:
        print(
            f"[MONEY AI] Content generation failed: {exc}",
            flush=True,
        )

        return {
            "error": "Content generation failed.",
            "details": str(exc),
        }, 500


@app.post("/api/render/<int:job_id>")
def api_render(job_id):
    job = get_job(job_id)

    if not job:
        return {"error": "job not found"}, 404

    thread = threading.Thread(
        target=render_job_background,
        args=(job_id, job["content"]),
        daemon=True,
    )

    thread.start()

    return jsonify(
        {
            "job_id": job_id,
            "status": "rendering",
        }
    )


@app.get("/videos/<path:filename>")
def serve_video(filename):
    video_dir = Path(
        os.getenv("VIDEO_DIR", "generated_videos")
    )

    return send_from_directory(
        video_dir,
        filename,
        mimetype="video/mp4",
    )


@app.get("/tiktok/login")
def tiktok_login():
    raw_state = secrets.token_urlsafe(32)
    state = state_serializer.dumps(raw_state)
    session["tiktok_oauth_state"] = state

    result = tiktok.create_authorization_url(
        state=state
    )

    return redirect(
        result["authorization_url"]
    )


@app.get("/tiktok/callback")
def tiktok_callback():
    error = request.args.get("error")

    if error:
        return {
            "status": "error",
            "error": error,
            "description": request.args.get(
                "error_description"
            ),
        }, 400

    state = request.args.get("state")

    if not state:
        return {
            "status": "error",
            "message": "No OAuth state was returned.",
        }, 400

    try:
        state_serializer.loads(
            state,
            max_age=600,
        )

    except SignatureExpired:
        return {
            "status": "error",
            "message": "OAuth state expired.",
        }, 400

    except BadSignature:
        return {
            "status": "error",
            "message": "Invalid OAuth state.",
        }, 400

    code = request.args.get("code")

    if not code:
        return {
            "status": "error",
            "message": "No authorization code was returned.",
        }, 400

    try:
        token_data = (
            tiktok.exchange_code_for_token(
                code
            )
        )

        session.pop(
            "tiktok_oauth_state",
            None,
        )

        access_token = token_data.get(
            "access_token"
        )

        user_data = (
            tiktok.get_user_info(
                access_token
            )
            if access_token
            else None
        )

        return {
            "status": "connected",
            "message": "TikTok authorization completed.",
            "user": user_data,
            "token_received": bool(
                access_token
            ),
            "scope": token_data.get("scope"),
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": "TikTok authorization failed.",
            "error": str(exc),
        }, 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "5000")
        ),
        debug=False,
    )
