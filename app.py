import os
import secrets

from flask import Flask, redirect, request, session, send_from_directory, render_template, jsonify
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from engine.tiktok_connector import TikTokConnector
from engine.db import init_db, create_content_job, list_jobs, get_job, update_job_status
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


@app.post("/api/generate")
def api_generate():
    payload = request.get_json(silent=True) or {}
    topic = (payload.get("topic") or "").strip()

    if not topic:
        return {"error": "topic is required"}, 400

    try:
        content = generate_content(topic)

        job_id = create_content_job(topic, content)

        output = render_video(
            content["hook"],
            content["script"],
            content["caption"],
            content["hashtags"],
            job_id,
        )

        update_job_status(job_id, "video_ready")

        return jsonify({
            "job_id": job_id,
            "topic": topic,
            "content": content,
            "status": "video_ready",
            "video": output,
        })

    except Exception as exc:
        try:
            if "job_id" in locals():
                update_job_status(job_id, "error")
        except Exception:
            pass

        return {
            "error": "Video generation failed.",
            "details": str(exc),
        }, 500


@app.post("/api/render/<int:job_id>")
def api_render(job_id):
    job = get_job(job_id)

    if not job:
        return {"error": "job not found"}, 404

    try:
        output = render_video(
            job["content"]["hook"],
            job["content"]["script"],
            job["content"]["caption"],
            job["content"]["hashtags"],
            job_id,
        )

        update_job_status(job_id, "video_ready")

        return jsonify({
            "job_id": job_id,
            "video": output,
            "status": "video_ready",
        })

    except Exception as exc:
        update_job_status(job_id, "error")

        return {
            "error": "Video rendering failed.",
            "details": str(exc),
        }, 500


@app.get("/tiktok/login")
def tiktok_login():
    raw_state = secrets.token_urlsafe(32)
    state = state_serializer.dumps(raw_state)
    session["tiktok_oauth_state"] = state

    result = tiktok.create_authorization_url(state=state)

    return redirect(result["authorization_url"])


@app.get("/tiktok/callback")
def tiktok_callback():
    error = request.args.get("error")

    if error:
        return {
            "status": "error",
            "error": error,
            "description": request.args.get("error_description"),
        }, 400

    state = request.args.get("state")

    if not state:
        return {
            "status": "error",
            "message": "No OAuth state was returned.",
        }, 400

    try:
        state_serializer.loads(state, max_age=600)
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
        token_data = tiktok.exchange_code_for_token(code)

        session.pop("tiktok_oauth_state", None)

        access_token = token_data.get("access_token")

        user_data = (
            tiktok.get_user_info(access_token)
            if access_token
            else None
        )

        return {
            "status": "connected",
            "message": "TikTok authorization completed.",
            "user": user_data,
            "token_received": bool(access_token),
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
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
