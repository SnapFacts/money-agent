import os
import secrets
from urllib.parse import urlencode
import requests


class TikTokConnector:
    AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
    CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
    VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

    def __init__(self):
        self.client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
        self.client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("TIKTOK_REDIRECT_URI", "")
        self.scope = os.getenv("TIKTOK_SCOPE", "user.info.basic")

    def configuration_status(self):
        return {
            "client_key_configured": bool(self.client_key),
            "client_secret_configured": bool(self.client_secret),
            "redirect_uri_configured": bool(self.redirect_uri),
            "scope": self.scope,
            "ready": bool(self.client_key and self.client_secret and self.redirect_uri),
        }

    def create_authorization_url(self, state=None):
        if not self.client_key or not self.redirect_uri:
            raise RuntimeError("TikTok OAuth is not configured.")
        state = state or secrets.token_urlsafe(32)
        params = {
            "client_key": self.client_key,
            "scope": self.scope,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return {"authorization_url": f"{self.AUTH_URL}?{urlencode(params)}", "state": state}

    def exchange_code_for_token(self, code):
        response = requests.post(
            self.TOKEN_URL,
            data={
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_user_info(self, access_token):
        response = requests.get(
            self.USER_INFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "open_id,union_id,avatar_url,display_name,profile_deep_link"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def creator_info(self, access_token):
        response = requests.post(
            self.CREATOR_INFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def initialize_direct_post(self, access_token, title, video_size, chunk_size, total_chunk_count, privacy_level, is_aigc=True):
        response = requests.post(
            self.VIDEO_INIT_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "post_info": {
                    "title": title,
                    "privacy_level": privacy_level,
                    "is_aigc": is_aigc,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video_size,
                    "chunk_size": chunk_size,
                    "total_chunk_count": total_chunk_count,
                },
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def upload_file(self, upload_url, file_path, chunk_size=10_000_000):
        size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            offset = 0
            while offset < size:
                data = f.read(min(chunk_size, size - offset))
                end = offset + len(data) - 1
                r = requests.put(
                    upload_url,
                    headers={
                        "Content-Range": f"bytes {offset}-{end}/{size}",
                        "Content-Type": "video/mp4",
                    },
                    data=data,
                    timeout=120,
                )
                r.raise_for_status()
                offset += len(data)

    def status(self, access_token, publish_id):
        response = requests.post(
            self.STATUS_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
