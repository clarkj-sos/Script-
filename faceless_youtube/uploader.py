"""
faceless_youtube/uploader.py

YouTube video uploader using the YouTube Data API v3 with resumable uploads,
retry logic, and progress reporting.
"""

from __future__ import annotations

import http.client
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]

MAX_RETRIES = 5
RETRIABLE_STATUS_CODES = {500, 502, 503, 504}
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, http.client.NotConnected,
                         http.client.IncompleteRead, http.client.ImproperConnectionState,
                         http.client.CannotSendRequest, http.client.CannotSendHeader,
                         http.client.ResponseNotReady, http.client.BadStatusLine,
                         ConnectionResetError, ConnectionAbortedError, BrokenPipeError)

CHUNK_SIZE = 1024 * 1024 * 5  # 5 MB chunks for resumable upload


def _utc_iso(dt: datetime) -> str:
    """Return an RFC-3339 string in UTC, e.g. '2025-01-15T18:00:00Z'."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class YouTubeUploader:
    """Upload and manage YouTube videos via the YouTube Data API v3."""

    def __init__(self, config: Any) -> None:
        self.client_secrets_file: str = getattr(
            config, "youtube_client_secrets_file", "client_secrets.json"
        )
        self.token_file: str = getattr(config, "youtube_token_file", "token.json")
        self.credentials_json: str | None = getattr(
            config, "youtube_credentials_json", None
        )
        self.service: Any | None = None

    def authenticate(self) -> Any:
        creds: Credentials | None = None

        if self.credentials_json:
            try:
                info = json.loads(self.credentials_json)
                creds = Credentials.from_authorized_user_info(info, SCOPES)
            except Exception as exc:
                logger.warning("Could not load credentials from JSON string: %s", exc)

        if creds is None and os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as exc:
                logger.warning("Could not load token file '%s': %s", self.token_file, exc)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_token(creds)
            except Exception as exc:
                logger.error("Token refresh failed: %s", exc)
                creds = None

        if creds is None or not creds.valid:
            if not os.path.exists(self.client_secrets_file):
                raise FileNotFoundError(
                    f"Client secrets file not found: {self.client_secrets_file}. "
                    "Download it from the Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
            self._save_token(creds)

        self.service = build("youtube", "v3", credentials=creds)
        logger.info("YouTube API service authenticated successfully.")
        return self.service

    def _save_token(self, creds: Credentials) -> None:
        try:
            with open(self.token_file, "w") as fh:
                fh.write(creds.to_json())
        except OSError as exc:
            logger.warning("Could not save token file: %s", exc)

    def _ensure_service(self) -> Any:
        if self.service is None:
            self.authenticate()
        return self.service

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str],
        category_id: str = "22",
        privacy: str = "private",
        thumbnail_path: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, str]:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        service = self._ensure_service()

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:500],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            file_path,
            chunksize=CHUNK_SIZE,
            resumable=True,
            mimetype="video/*",
        )

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        video_id = self._execute_resumable(request, file_path, progress_callback)
        url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info("Video uploaded successfully: %s", url)

        if thumbnail_path:
            self.set_thumbnail(video_id, thumbnail_path)

        return {"video_id": video_id, "url": url}

    def _execute_resumable(
        self,
        request: Any,
        file_path: str,
        progress_callback: Callable[[int, int], None] | None,
    ) -> str:
        total_size = os.path.getsize(file_path)
        response = None
        error: Exception | None = None
        retry = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    uploaded = int(status.resumable_progress)
                    if progress_callback:
                        progress_callback(uploaded, total_size)
                    pct = uploaded / total_size * 100 if total_size else 0
                    logger.debug("Upload progress: %.1f%%", pct)
                if response is not None:
                    if "id" not in response:
                        raise RuntimeError(
                            f"Unexpected API response during upload: {response}"
                        )
                    return response["id"]
            except HttpError as exc:
                if exc.resp.status in RETRIABLE_STATUS_CODES:
                    error = exc
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as exc:
                error = exc

            if error is not None:
                retry += 1
                if retry > MAX_RETRIES:
                    raise RuntimeError(
                        f"Upload failed after {MAX_RETRIES} retries. Last error: {error}"
                    )
                sleep_time = min(2 ** retry + (time.monotonic() % 1), 64)
                logger.warning(
                    "Retriable error (%s). Retry %d/%d in %.1fs.",
                    error, retry, MAX_RETRIES, sleep_time,
                )
                time.sleep(sleep_time)
                error = None

        raise RuntimeError("Upload loop exited without a response.")

    def set_thumbnail(self, video_id: str, image_path: str) -> bool:
        if not os.path.isfile(image_path):
            logger.warning("Thumbnail file not found: %s", image_path)
            return False

        service = self._ensure_service()
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".png": "image/png", ".gif": "image/gif"}
        mimetype = mime_map.get(ext, "image/jpeg")

        try:
            media = MediaFileUpload(image_path, mimetype=mimetype)
            service.thumbnails().set(videoId=video_id, media_body=media).execute()
            logger.info("Thumbnail set for video %s.", video_id)
            return True
        except HttpError as exc:
            logger.error("Failed to set thumbnail: %s", exc)
            return False

    def update_metadata(
        self,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        service = self._ensure_service()

        current = service.videos().list(part="snippet", id=video_id).execute()
        items = current.get("items", [])
        if not items:
            raise ValueError(f"Video not found: {video_id}")

        snippet = items[0]["snippet"]
        if title is not None:
            snippet["title"] = title[:100]
        if description is not None:
            snippet["description"] = description[:5000]
        if tags is not None:
            snippet["tags"] = tags[:500]

        body = {"id": video_id, "snippet": snippet}
        response = service.videos().update(part="snippet", body=body).execute()
        logger.info("Metadata updated for video %s.", video_id)
        return response.get("snippet", {})

    def schedule_publish(self, video_id: str, publish_at: datetime) -> dict[str, Any]:
        service = self._ensure_service()

        body = {
            "id": video_id,
            "status": {
                "privacyStatus": "private",
                "publishAt": _utc_iso(publish_at),
            },
        }
        response = service.videos().update(part="status", body=body).execute()
        scheduled_time = response.get("status", {}).get("publishAt", "unknown")
        logger.info("Video %s scheduled for publish at %s.", video_id, scheduled_time)
        return {"video_id": video_id, "scheduled_at": scheduled_time}

    def get_upload_status(self, video_id: str) -> dict[str, Any]:
        service = self._ensure_service()
        try:
            response = service.videos().list(
                part="status,processingDetails", id=video_id
            ).execute()
            items = response.get("items", [])
            if not items:
                return {"error": f"Video not found: {video_id}"}
            item = items[0]
            return {
                "video_id": video_id,
                "privacy_status": item.get("status", {}).get("privacyStatus"),
                "upload_status": item.get("status", {}).get("uploadStatus"),
                "processing_status": item.get("processingDetails", {}).get("processingStatus"),
                "processing_progress": item.get("processingDetails", {}).get("processingProgress", {}),
            }
        except HttpError as exc:
            logger.error("get_upload_status failed for %s: %s", video_id, exc)
            return {"error": str(exc)}

    def wait_for_processing(
        self,
        video_id: str,
        poll_interval: int = 30,
        timeout: int = 1800,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = self.get_upload_status(video_id)
            proc = status.get("processing_status")
            logger.debug("Processing status for %s: %s", video_id, proc)
            if proc in ("succeeded", "failed", "terminated"):
                return status
            time.sleep(poll_interval)
        logger.warning("Timed out waiting for processing of video %s.", video_id)
        return self.get_upload_status(video_id)
