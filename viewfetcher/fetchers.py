# -*- coding: utf-8 -*-
# fetchers.py
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

try:  # pragma: no cover - import guard for deployment environments
    from yt_dlp import YoutubeDL  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    YoutubeDL = None  # type: ignore
    _YTDLP_IMPORT_ERROR = exc
else:
    _YTDLP_IMPORT_ERROR = None


def _get_ytdlp() -> Any:
    """Return YoutubeDL class or raise a descriptive error if missing."""
    if YoutubeDL is None:  # pragma: no cover - depends on deployment install
        raise RuntimeError(
            "当前环境缺少 yt-dlp 依赖。请确认 requirements.txt 或部署平台的依赖配置中包含"
            " `yt-dlp`（安装时使用连字符，导入时使用下划线 `yt_dlp`）。"
        ) from _YTDLP_IMPORT_ERROR
    return YoutubeDL

# ---------- YouTube: 提取 videoId ----------
YOUTUBE_VIDEO_ID_RE = re.compile(
    r"(?:v=|/videos/|embed/|youtu\.be/|/shorts/)([A-Za-z0-9_-]{6,})"
)

def extract_youtube_id(url: str) -> Optional[str]:
    m = YOUTUBE_VIDEO_ID_RE.search(url or "")
    return m.group(1) if m else None

# ---------- IG/TikTok: 仍使用 yt-dlp ----------
INSTAGRAM_SESSIONID = os.getenv("INSTAGRAM_SESSIONID")

YDL_OPTS: Dict[str, Any] = {
    "quiet": True,
    "nocheckcertificate": True,
    "skip_download": True,
    "noplaylist": True,
    "simulate": True,
    "forcejson": True,
    "extract_flat": False,
    "socket_timeout": 10,
    "retries": 2,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

if INSTAGRAM_SESSIONID:
    YDL_OPTS.setdefault("http_headers", {})["Cookie"] = f"sessionid={INSTAGRAM_SESSIONID};"

def _iso_from_upload_date(upload_date: Optional[str]) -> Optional[str]:
    if not upload_date:
        return None
    try:
        if isinstance(upload_date, int):
            upload_date = str(upload_date)
        if len(upload_date) == 8 and upload_date.isdigit():
            dt = datetime.strptime(upload_date, "%Y%m%d")
            return dt.replace(tzinfo=timezone.utc).isoformat()
    except Exception:
        return None
    return None


def fetch_by_ytdlp(url: str) -> Dict[str, Any]:
    ydl_cls = _get_ytdlp()
    opts = dict(YDL_OPTS)
    if INSTAGRAM_SESSIONID:
        headers = dict(opts.get("http_headers", {}))
        headers["Cookie"] = f"sessionid={INSTAGRAM_SESSIONID};"
        opts["http_headers"] = headers
    with ydl_cls(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        views = int(info.get("view_count") or info.get("views") or 0)
        likes = int(info.get("like_count") or info.get("likes") or 0)
        comments = int(info.get("comment_count") or info.get("comments") or 0)
        creator = info.get("uploader") or info.get("channel")
        posted_at = None
        if info.get("timestamp"):
            try:
                posted_at = datetime.fromtimestamp(int(info["timestamp"]), tz=timezone.utc).isoformat()
            except Exception:
                posted_at = None
        if not posted_at:
            posted_at = _iso_from_upload_date(info.get("upload_date"))
        return {
            "views": views,
            "likes": likes,
            "comments": comments,
            "creator": creator,
            "posted_at": posted_at,
        }

# ---------- YouTube: 批量 API ----------
def fetch_youtube_batch_stats(video_ids: List[str], api_key: str) -> Dict[str, Dict]:
    endpoint = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "statistics,snippet",          # ← 同时拿统计和 snippet
        "id": ",".join(video_ids),
        "key": api_key
    }
    r = requests.get(endpoint, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    out = {}
    for item in data.get("items", []):
        vid = item.get("id")
        stats = item.get("statistics", {})
        snip = item.get("snippet", {}) or {}
        out[vid] = {
            "views": int(stats.get("viewCount", 0) or 0),
            "likes": int(stats.get("likeCount", 0) or 0),
            "comments": int(stats.get("commentCount", 0) or 0),
            "creator": snip.get("channelTitle", ""),       # ← 发布者
            "posted_at": snip.get("publishedAt", ""),      # ← ISO8601 字符串
        }
    return out

def fetch_metrics(platform: str, url: str, youtube_api_key: Optional[str] = None) -> Dict[str, int]:
    """
    单条调用（兼容旧接口，供 IG/TikTok fallback 用）
    """
    p = (platform or "").strip().lower()
    if p in ("instagram", "tiktok"):
        return fetch_by_ytdlp(url)
    if p == "youtube":
        # 这里不再抓网页，强制要求走批量 API（单条时也可退回，但我们会在 app.py 里批量处理）
        if not youtube_api_key:
            raise RuntimeError("YouTube 需要 API Key，请在页面输入框提供")
        vid = extract_youtube_id(url)
        if not vid:
            return {"views": 0, "likes": 0, "comments": 0}
        d = fetch_youtube_batch_stats([vid], youtube_api_key)
        return d.get(vid, {"views": 0, "likes": 0, "comments": 0})
    # 未知平台，尝试 ytdlp
    return fetch_by_ytdlp(url)
