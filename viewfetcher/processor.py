"""Data ingestion helpers shared by the API layer."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .fetchers import extract_youtube_id, fetch_metrics, fetch_youtube_batch_stats

REQUIRED_COLUMNS = {"platform", "url"}
OPTIONAL_COLUMNS = {"creator", "campaign_id", "posted_at", "notes"}


def _load_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes))
    if filename.lower().endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(file_bytes))
    raise ValueError("仅支持 .csv 或 .xlsx 文件")


def _infer_platform(url: str) -> str:
    url_l = (url or "").lower()
    if "youtube.com" in url_l or "youtu.be" in url_l:
        return "youtube"
    if "instagram.com" in url_l:
        return "instagram"
    if "tiktok.com" in url_l:
        return "tiktok"
    return ""


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("上传的文件为空")

    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "url" not in df.columns:
        raise ValueError("文件中缺少 url 列")

    if "platform" not in df.columns:
        df["platform"] = df["url"].apply(_infer_platform)

    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df["platform"] = df["platform"].astype(str).str.lower().str.strip()
    df["url"] = df["url"].astype(str).str.strip()

    df = df[df["url"].str.startswith("http")]
    df = df[df["platform"].isin(["youtube", "instagram", "tiktok"])]

    if df.empty:
        raise ValueError("未找到可识别的平台或链接")

    return df[["platform", "url", "creator", "campaign_id", "posted_at", "notes"]]


def _parse_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        return pd.to_datetime(value, utc=True).to_pydatetime()
    except Exception:
        return None


def process_file(file_bytes: bytes, filename: str, youtube_api_key: Optional[str]) -> Tuple[List[Dict], List[str]]:
    """Parse the uploaded file, fetch metrics and return results + error messages."""
    df = _normalize_dataframe(_load_dataframe(file_bytes, filename))

    results: List[Dict] = []
    errors: List[str] = []

    # YouTube batch (requires API key)
    yt_rows = df[df["platform"] == "youtube"]
    if not yt_rows.empty:
        if not youtube_api_key:
            errors.append("YouTube 数据未抓取：缺少 API Key")
        else:
            yt_rows = yt_rows.copy()
            yt_rows["video_id"] = yt_rows["url"].apply(extract_youtube_id)
            valid_rows = yt_rows[yt_rows["video_id"].notna()]
            ids = valid_rows["video_id"].tolist()

            stats_map: Dict[str, Dict] = {}
            chunk = 50
            for i in range(0, len(ids), chunk):
                batch = ids[i:i + chunk]
                try:
                    part = fetch_youtube_batch_stats(batch, youtube_api_key)
                    stats_map.update(part)
                except Exception as exc:  # pragma: no cover - network errors are runtime issues
                    errors.append(f"YouTube 抓取失败（{i + 1}-{i + len(batch)}）：{exc}")

            for _, row in valid_rows.iterrows():
                stats = stats_map.get(row["video_id"], {})
                views = int(stats.get("views", 0))
                likes = int(stats.get("likes", 0))
                comments = int(stats.get("comments", 0))
                engagement_rate = round(((likes + comments) / views * 100.0), 2) if views > 0 else 0.0
                results.append({
                    "platform": "youtube",
                    "url": row["url"],
                    "creator": stats.get("creator") or row.get("creator"),
                    "campaign_id": row.get("campaign_id"),
                    "posted_at": _parse_datetime(stats.get("posted_at") or row.get("posted_at")),
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "engagement_rate": engagement_rate,
                    "notes": row.get("notes"),
                })

    # Instagram & TikTok
    other_rows = df[df["platform"].isin(["instagram", "tiktok"])]
    for idx, row in other_rows.iterrows():
        url = row["url"]
        platform = row["platform"]
        try:
            stats = fetch_metrics(platform, url, youtube_api_key=None)
            views = int(stats.get("views", 0))
            likes = int(stats.get("likes", 0))
            comments = int(stats.get("comments", 0))
            engagement_rate = round(((likes + comments) / views * 100.0), 2) if views > 0 else 0.0
            results.append({
                "platform": platform,
                "url": url,
                "creator": stats.get("creator") or row.get("creator"),
                "campaign_id": row.get("campaign_id"),
                "posted_at": _parse_datetime(stats.get("posted_at") or row.get("posted_at")),
                "views": views,
                "likes": likes,
                "comments": comments,
                "engagement_rate": engagement_rate,
                "notes": row.get("notes"),
            })
        except Exception as exc:  # pragma: no cover - network errors at runtime
            errors.append(f"{platform} 抓取失败（第 {idx + 1} 行）：{exc}")

    return results, errors
