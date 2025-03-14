#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import asyncio
import os
from fastapi.staticfiles import StaticFiles
import backend.job_processor as job_processor
from backend.models.database import create_tables, get_db, engine, Base
from backend.services.job_service import create_job, get_job, get_all_jobs, add_file_to_job
from backend.utils.file_utils import save_upload_file
from backend.api import job as job_api
from backend.api import health as health_api
from backend.api import dataset as dataset_api
import logging
import time

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("storage/logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# モデル定義
class Job(BaseModel):
    job_id: str
    status: str
    submission_time: str
    error_message: Optional[str] = None

# アプリケーションインスタンスの作成
app = FastAPI(
    title="VRM to LoRA & Dataset Generator API",
    description="VRMファイルからLoRAモデルやデータセットを生成するためのAPI",
    version="1.0.0",
)

# CORSミドルウェアの設定
# すべてのオリジンからのリクエストを許可（開発用、本番環境では適切に制限すること）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境では全てのオリジンを許可
    allow_credentials=True,
    allow_methods=["*"],  # 全てのHTTPメソッドを許可
    allow_headers=["*"],  # 全てのHTTPヘッダーを許可
)

# データベーステーブルの作成
create_tables()

# 静的ファイル提供のディレクトリ設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

# モックデータ（開発用）- 実際の実装では削除する
JOBS = [
    Job(
        job_id=f"job-{uuid.uuid4().hex[:6]}",
        status="completed",
        submission_time=(datetime.now() - timedelta(hours=1)).isoformat(),
    ),
    Job(
        job_id=f"job-{uuid.uuid4().hex[:6]}",
        status="processing",
        submission_time=(datetime.now() - timedelta(hours=2)).isoformat(),
    ),
    Job(
        job_id=f"job-{uuid.uuid4().hex[:6]}",
        status="queued",
        submission_time=(datetime.now() - timedelta(hours=3)).isoformat(),
    ),
    Job(
        job_id=f"job-{uuid.uuid4().hex[:6]}",
        status="error",
        submission_time=(datetime.now() - timedelta(hours=4)).isoformat(),
        error_message="ファイル形式が無効です",
    ),
]

# ルーターの登録
app.include_router(health_api.router)
app.include_router(job_api.router)
app.include_router(dataset_api.router)

# ジョブプロセッサの初期化
job_processor.init_job_processor()

# Chromium管理システムの初期化（非同期に行うため、スタートアップイベントで実行）
@app.on_event("startup")
async def startup_event():
    """
    アプリケーション起動時の処理
    """
    logger.info("アプリケーションを起動しています...")
    
    # ストレージディレクトリの確認
    for dir_name in ["uploads", "datasets", "logs", "results", "temp", "chromium"]:
        dir_path = os.path.join(STORAGE_DIR, dir_name)
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"ストレージディレクトリの確認: {dir_path}")
    
    # Chromium管理システムの初期化
    try:
        from dataset_generator import initialize_chromium_environment
        logger.info("Chromium管理システムを初期化中...")
        initialize_chromium_environment()
        logger.info("Chromium管理システムの初期化が完了しました")
    except Exception as e:
        logger.error(f"Chromium初期化中にエラーが発生: {str(e)}")
        logger.info("エラーを無視して続行します")
    
    logger.info("アプリケーションの起動が完了しました")

@app.on_event("shutdown")
async def shutdown_event():
    """
    アプリケーション終了時の処理
    """
    logger.info("アプリケーションをシャットダウンしています...")
    # ジョブプロセッサの停止
    if hasattr(job_processor, "job_processor") and job_processor.job_processor is not None:
        job_processor.job_processor.stop_processor()
    logger.info("アプリケーションのシャットダウンが完了しました")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    グローバル例外ハンドラ
    """
    logger.error(f"予期しないエラーが発生しました: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"サーバーエラーが発生しました: {str(exc)}"}
    )

@app.get("/")
async def root():
    """
    ルートエンドポイント
    """
    return {
        "message": "VRM to LoRA & Dataset Generator API",
        "version": "1.0.0",
        "status": "running"
    }

# API エンドポイント
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# モック版 API
@app.get("/api/job", response_model=List[Job])
def get_jobs_mock(skip: int = 0, limit: int = 10):
    return JOBS[skip : skip + limit]

@app.get("/api/job/{job_id}", response_model=Job)
def get_job_mock(job_id: str):
    for job in JOBS:
        if job.job_id == job_id:
            return job
    raise HTTPException(status_code=404, detail="Job not found")

# 実際のAPI実装
@app.get("/api/jobs", tags=["jobs"])
async def get_jobs_real(skip: int = 0, limit: int = 10, db = Depends(get_db)):
    """すべてのジョブを取得する

    Args:
        skip: スキップするレコード数
        limit: 取得するレコード数
        db: データベースセッション

    Returns:
        ジョブのリスト
    """
    jobs = get_all_jobs(db, skip=skip, limit=limit)
    return [
        {
            "job_id": job.job_id,
            "status": job.status,
            "submission_time": job.submission_time.isoformat(),
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "error_message": job.error_message,
        }
        for job in jobs
    ]

@app.get("/api/jobs/{job_id}", tags=["jobs"])
async def get_job_real(job_id: str, db = Depends(get_db)):
    """特定のジョブを取得する

    Args:
        job_id: ジョブID
        db: データベースセッション

    Returns:
        ジョブの詳細情報
    """
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "submission_time": job.submission_time.isoformat(),
        "start_time": job.start_time.isoformat() if job.start_time else None,
        "end_time": job.end_time.isoformat() if job.end_time else None,
        "error_message": job.error_message,
        "files": [
            {
                "file_id": file.file_id,
                "file_type": file.file_type,
                "file_path": file.file_path,
                "created_at": file.created_at.isoformat(),
            }
            for file in job.files
        ],
        "report": {
            "report_id": job.report.report_id,
            "evaluation_score": job.report.evaluation_score,
            "report_data": job.report.report_data,
            "created_at": job.report.created_at.isoformat(),
        } if job.report else None,
    }

@app.get("/api/jobs/{job_id}/status", tags=["jobs"])
async def get_job_status(job_id: str):
    """ジョブの処理状況を取得する

    Args:
        job_id: ジョブID

    Returns:
        ジョブの処理状況
    """
    status = await job_processor.check_job_status(job_id)
    return status

@app.post("/api/jobs/{job_id}/process", tags=["jobs"])
async def process_job(job_id: str, background_tasks: BackgroundTasks):
    """ジョブの処理を開始する

    Args:
        job_id: ジョブID
        background_tasks: バックグラウンドタスク

    Returns:
        処理開始結果
    """
    success = job_processor.submit_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start job processing")
    
    return {"success": True, "message": "Job processing started", "job_id": job_id}

@app.post("/api/jobs/{job_id}/cancel", tags=["jobs"])
async def cancel_job(job_id: str):
    """ジョブの処理をキャンセルする

    Args:
        job_id: ジョブID

    Returns:
        キャンセル結果
    """
    success = job_processor.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel job")
    
    return {"success": True, "message": "Job cancelled", "job_id": job_id}

@app.post("/api/upload", tags=["upload"])
async def upload_file(
    file: UploadFile = File(...),
    job_parameters: Optional[str] = Form(None),
    db = Depends(get_db)
):
    """VRMファイルをアップロードして処理ジョブを作成する

    Args:
        file: アップロードするVRMファイル
        job_parameters: ジョブパラメータ（JSON文字列）
        db: データベースセッション

    Returns:
        作成されたジョブID
    """
    # ファイル形式をチェック
    if not file.filename.lower().endswith('.vrm'):
        raise HTTPException(status_code=400, detail="Invalid file format. Only VRM files are supported.")
    
    # ジョブIDを生成
    job_id = str(uuid.uuid4())
    
    # ジョブパラメータを解析
    parameters = None
    if job_parameters:
        try:
            import json
            parameters = json.loads(job_parameters)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid job parameters: {str(e)}")
    
    # ジョブ作成
    db_job = create_job(db, job_id=job_id, job_parameters=parameters)
    
    # ファイル保存
    file_path = await save_upload_file(file, job_id)
    
    # ファイル情報を保存
    add_file_to_job(db, job_id, "upload", file_path)
    
    # ジョブを自動的に処理キューに登録（オプション）
    # job_processor.submit_job(job_id)
    
    return {
        "success": True,
        "job_id": job_id,
        "status": db_job.status,
        "message": "File uploaded successfully",
    }

# アプリケーション起動（直接実行時のみ）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,  # 開発時の自動リロード
        log_level="info"
    ) 