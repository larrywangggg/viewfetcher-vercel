from __future__ import annotations

import io
import csv
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select

from viewfetcher.db import Result, get_session, init_db, upsert_result
from viewfetcher.processor import process_file

init_db()

app = FastAPI(title="ViewFetcher API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


def _serialize(result: Result) -> dict:
    return {
        "id": result.id,
        "platform": result.platform,
        "url": result.url,
        "creator": result.creator,
        "campaign_id": result.campaign_id,
        "posted_at": result.posted_at.isoformat() if result.posted_at else None,
        "views": result.views,
        "likes": result.likes,
        "comments": result.comments,
        "engagement_rate": round(result.engagement_rate or 0.0, 2),
        "notes": result.notes,
        "fetched_at": result.fetched_at.isoformat() if result.fetched_at else None,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/fetch")
async def fetch_data(
    file: UploadFile = File(..., description="上传 CSV 或 XLSX 文件"),
    youtube_api_key: Optional[str] = Form(default=None, description="YouTube API Key，可选"),
) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传文件")

    payload = await file.read()
    try:
        results, errors = process_file(payload, file.filename, youtube_api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored = []
    with get_session() as session:
        for row in results:
            rec = upsert_result(session, row)
            stored.append(rec)

    return JSONResponse(
        {
            "status": "success",
            "saved": len(stored),
            "errors": errors,
            "items": [_serialize(r) for r in stored],
        }
    )


@app.get("/results")
async def list_results(limit: int = 200, platform: Optional[str] = None) -> dict:
    query = select(Result).order_by(Result.fetched_at.desc()).limit(limit)
    if platform:
        query = query.where(Result.platform == platform.lower())

    with get_session() as session:
        rows = session.execute(query).scalars().all()

    return {"items": [_serialize(r) for r in rows]}


@app.get("/export")
async def export_results() -> StreamingResponse:
    with get_session() as session:
        rows = session.execute(select(Result).order_by(Result.id.asc())).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="暂无数据")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id",
        "platform",
        "url",
        "creator",
        "campaign_id",
        "posted_at",
        "views",
        "likes",
        "comments",
        "engagement_rate",
        "notes",
        "fetched_at",
    ])
    for r in rows:
        writer.writerow([
            r.id,
            r.platform,
            r.url,
            r.creator or "",
            r.campaign_id or "",
            r.posted_at.isoformat() if r.posted_at else "",
            r.views,
            r.likes,
            r.comments,
            round(r.engagement_rate or 0.0, 4),
            r.notes or "",
            r.fetched_at.isoformat() if r.fetched_at else "",
        ])
    buffer.seek(0)

    headers = {
        "Content-Disposition": "attachment; filename=kol_results.csv"
    }
    return StreamingResponse(buffer, media_type="text/csv", headers=headers)
