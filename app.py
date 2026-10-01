import os
import secrets

from flask import Flask, redirect, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from engine.tiktok_connector import TikTokConnector


app = Flask(__name__)

app.secret_key = os.environ["MONEY_AI_SECRET_KEY"]

state_serializer = URLSafeTimedSerializer(app.secret_key)

tiktok = TikTokConnector()


@app.get("/")
def home():
    return """
    <h1>MONEY AI</h1>
    <p>Backend is running.</p>
    <p><a href="/health">Health check</a></p>
    <p><a href="/tiktok/login">Connect TikTok</a></p>
    """


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "money-ai",
        "tiktok": tiktok.configuration_status(),
    }


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
            "message": "OAuth state expired. Please try again.",
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

        user_data = None

        if access_token:
            user_data = tiktok.get_user_info(access_token)

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
    port = int(os.getenv("PORT", "5000"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )