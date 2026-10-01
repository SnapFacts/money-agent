import os
import secrets
from urllib.parse import urlencode

import requests


class TikTokConnector:
    """
    TikTok OAuth + Content Posting API connector.

    Secrets are read only from environment variables.
    """

    AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
    VIDEO_INIT_URL = (
        "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
    )

    def __init__(self):
        self.client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
        self.client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("TIKTOK_REDIRECT_URI", "")

    def configuration_status(self):
        return {
            "client_key_configured": bool(self.client_key),
            "client_secret_configured": bool(self.client_secret),
            "redirect_uri_configured": bool(self.redirect_uri),
            "ready": all(
                [
                    self.client_key,
                    self.client_secret,
                    self.redirect_uri,
                ]
            ),
        }

    def create_authorization_url(self, state=None):
        if not self.client_key:
            raise RuntimeError("TIKTOK_CLIENT_KEY is not configured.")

        if not self.redirect_uri:
            raise RuntimeError("TIKTOK_REDIRECT_URI is not configured.")

        state = state or secrets.token_urlsafe(32)

        params = {
            "client_key": self.client_key,
            "scope": (
                "user.info.basic,"
                "user.info.stats,"
                "user.info.profile,"
                "video.list,"
                "video.upload"
            ),
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        return {
            "authorization_url": (
                f"{self.AUTH_URL}?{urlencode(params)}"
            ),
            "state": state,
        }

    def exchange_code_for_token(self, code):
        if not self.client_key:
            raise RuntimeError("TIKTOK_CLIENT_KEY is not configured.")

        if not self.client_secret:
            raise RuntimeError("TIKTOK_CLIENT_SECRET is not configured.")

        if not self.redirect_uri:
            raise RuntimeError("TIKTOK_REDIRECT_URI is not configured.")

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
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            params={
                "fields": (
                    "open_id,union_id,avatar_url,"
                    "display_name,profile_deep_link,"
                    "bio_description,is_verified,"
                    "follower_count,following_count,"
                    "likes_count,video_count"
                )
            },
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    def initialize_video_upload(
        self,
        access_token,
        title,
        video_size,
        chunk_size,
        total_chunk_count,
    ):
        response = requests.post(
            self.VIDEO_INIT_URL,
            headers={
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video_size,
                    "chunk_size": chunk_size,
                    "total_chunk_count": total_chunk_count,
                }
            },
            timeout=30,
        )

        response.raise_for_status()
        return response.json()