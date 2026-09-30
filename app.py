import os

from flask import Flask, redirect, request, session

from engine.tiktok_connector import TikTokConnector


app = Flask(__name__)

app.secret_key = os.environ["MONEY_AI_SECRET_KEY"]

tiktok = TikTokConnector()


@app.get("/")
def home():
    return """
    <h1>MONEY AI</h1>
    <p>Backend is running.</p>
    <p><a href="/health">Health check</a></p>
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
    result = tiktok.create_authorization_url()

    session["tiktok_oauth_state"] = result["state"]

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
    saved_state = session.get("tiktok_oauth_state")

    if not state or state != saved_state:
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
