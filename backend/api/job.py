#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import os
import json
import uuid
from datetime import datetime
import shutil
from typing import List, Optional, Dict, Any
import logging

from backend.models.database import get_db, Job, File as DBFile, EvaluationReport
from backend.models.schemas import JobCreate, JobResponse, JobStatus, FileResponse, StandardResponse
from backend.services.job_service import create_job, get_job, get_all_jobs, update_job_status
from backend.utils.file_utils import save_upload_file, get_file_path, UPLOAD_DIR
import backend.job_processor as job_processor

# ロギングの設定
logger = logging.getLogger(__name__)

# ルーターの作成
router = APIRouter(
    prefix="/api/job",
    tags=["jobs"],
    responses={404: {"description": "Not found"}},
)

@router.post("/upload", response_model=StandardResponse)
async def upload_vrm(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """VRMファイルをアップロードしてジョブを作成するエンドポイント"""
    try:
        # ファイル拡張子の確認
        if not file.filename.lower().endswith('.vrm'):
            return StandardResponse(
                success=False,
                message="VRMファイル (.vrm) のみアップロード可能です",
            )
        
        # ジョブの作成
        job_id = str(uuid.uuid4())
        job = create_job(db, job_id=job_id)
        
        # ファイルの保存
        file_path = os.path.join(UPLOAD_DIR, job_id, os.path.basename(file.filename))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # ファイル情報をDBに保存
        db_file = DBFile(
            job_id=job_id, 
            file_type="upload",
            file_path=file_path
        )
        db.add(db_file)
        db.commit()
        
        # バックグラウンドでジョブ処理を開始する例（本番環境ではキューに送信）
        # background_tasks.add_task(process_job, job_id)
        
        return StandardResponse(
            success=True, 
            message="ファイルアップロード成功。ジョブがキューに追加されました。",
            data={"job_id": job_id}
        )
    
    except Exception as e:
        db.rollback()
        return StandardResponse(
            success=False,
            message=f"アップロードエラー: {str(e)}",
        )

@router.get("/{job_id}", response_model=JobResponse)
def get_job_details(job_id: str, db: Session = Depends(get_db)):
    """指定したジョブの詳細情報を取得するエンドポイント"""
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    return job

@router.get("/", response_model=List[JobResponse])
def get_jobs(
    skip: int = 0, 
    limit: int = 10, 
    db: Session = Depends(get_db)
):
    """ジョブの一覧を取得するエンドポイント"""
    jobs = get_all_jobs(db, skip=skip, limit=limit)
    return jobs

@router.get("/{job_id}/status", response_model=JobStatus)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """指定したジョブのステータスを取得するエンドポイント"""
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
    # 進捗状況の計算は実際の処理に合わせて実装
    progress = None
    if job.status == "processing":
        # ここでは仮の進捗値を設定
        progress = 50.0
    
    return JobStatus(
        job_id=job.job_id,
        status=job.status,
        progress=progress,
        message=job.error_message
    )

@router.get("/{job_id}/files", response_model=List[FileResponse])
def get_job_files(job_id: str, db: Session = Depends(get_db)):
    """指定したジョブに関連するファイル一覧を取得するエンドポイント"""
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    return job.files

@router.post("", status_code=201)
async def create_job(
    file: UploadFile = File(...),
    rank: int = Form(16),
    alpha: int = Form(32),
    iterations: int = Form(1000),
    batch_size: int = Form(4),
    learning_rate: float = Form(0.0001),
    resolution: int = Form(512),
    use_advanced_features: bool = Form(False),
    animation_frames: int = Form(0),
    db: Session = Depends(get_db)
):
    """
    VRMファイルをアップロードして新しいジョブを作成する
    """
    # ファイル形式のチェック
    if not file.filename.lower().endswith(".vrm"):
        raise HTTPException(status_code=400, detail="VRMファイル形式のみ受け付けています")
    
    # ファイルサイズのチェック (50MB上限)
    file_size_limit = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > file_size_limit:
        raise HTTPException(status_code=400, detail=f"ファイルサイズは50MB以下である必要があります（現在: {file_size / (1024 * 1024):.2f}MB）")
    
    # ファイルを保存する
    job_id = str(uuid.uuid4())
    os.makedirs(os.path.join(UPLOAD_DIR, job_id), exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, job_id, file.filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 変換パラメータ
        params = {
            "rank": rank,
            "alpha": alpha,
            "iterations": iterations,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "resolution": resolution,
            "use_advanced_features": use_advanced_features,
            "animation_frames": animation_frames
        }
        
        # ジョブの記録
        new_job = Job(
            job_id=job_id,
            status="queued",
            file_path=file_path,
            job_parameters=json.dumps(params),
            submission_time=datetime.now()
        )
        
        db.add(new_job)
        db.commit()
        
        # ジョブプロセッサにジョブを追加
        success = job_processor.add_job(job_id, file_path, params)
        
        if not success:
            raise HTTPException(status_code=500, detail="ジョブの登録に失敗しました")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "ジョブがキューに追加されました"
        }
        
    except Exception as e:
        logger.error(f"ジョブ作成エラー: {str(e)}")
        # アップロード済みのファイルを削除
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"ジョブ作成中にエラーが発生しました: {str(e)}")

@router.get("", response_model=List[Dict[str, Any]])
async def get_jobs(db: Session = Depends(get_db)):
    """
    すべてのジョブのリストを取得する
    """
    try:
        # メモリ内ジョブデータを優先して取得
        jobs = job_processor.get_all_jobs()
        
        # データベースから足りないジョブ情報を補完
        if not jobs:
            db_jobs = db.query(Job).order_by(Job.submission_time.desc()).all()
            jobs = []
            
            for job in db_jobs:
                job_data = {
                    "job_id": job.job_id,
                    "status": job.status,
                    "submission_time": job.submission_time.isoformat(),
                    "progress": 0,
                    "message": ""
                }
                
                # ジョブプロセッサからの情報で補完
                job_progress = job_processor.get_job_progress(job.job_id)
                if job_progress["status"] != "not_found":
                    job_data["progress"] = job_progress["progress"]
                    job_data["message"] = job_progress["message"]
                    job_data["status"] = job_progress["status"]
                
                jobs.append(job_data)
        
        return jobs
    
    except Exception as e:
        logger.error(f"ジョブリスト取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ジョブリスト取得中にエラーが発生しました: {str(e)}")

@router.get("/{job_id}", response_model=Dict[str, Any])
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """
    特定のジョブの詳細情報を取得する
    """
    try:
        # メモリ内ジョブデータを優先
        job_data = job_processor.get_job(job_id)
        
        # ジョブが見つからない場合はデータベースから検索
        if job_data["status"] == "not_found":
            job = db.query(Job).filter(Job.job_id == job_id).first()
            
            if not job:
                raise HTTPException(status_code=404, detail=f"ジョブID {job_id} が見つかりません")
            
            # 基本的なジョブ情報
            job_data = {
                "job_id": job.job_id,
                "status": job.status,
                "submission_time": job.submission_time.isoformat(),
                "file_path": job.file_path,
                "params": json.loads(job.job_parameters) if job.job_parameters else {},
                "files": []
            }
        
        return job_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ詳細取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ジョブ詳細取得中にエラーが発生しました: {str(e)}")

@router.get("/{job_id}/progress", response_model=Dict[str, Any])
async def get_job_progress(job_id: str):
    """
    特定のジョブの進捗状況を取得する
    """
    try:
        progress_data = job_processor.get_job_progress(job_id)
        
        if progress_data["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"ジョブID {job_id} が見つかりません")
        
        return progress_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ進捗取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ジョブ進捗取得中にエラーが発生しました: {str(e)}")

@router.delete("/{job_id}", response_model=Dict[str, Any])
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """
    特定のジョブをキャンセルする
    """
    try:
        # ジョブの存在確認
        job = db.query(Job).filter(Job.job_id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail=f"ジョブID {job_id} が見つかりません")
        
        # 処理済みのジョブはキャンセル不可
        if job.status not in ["queued", "processing"]:
            return {
                "job_id": job_id,
                "status": job.status,
                "message": f"ステータスが {job.status} のジョブはキャンセルできません"
            }
        
        # ジョブのキャンセル処理
        success = job_processor.cancel_job(job_id)
        
        if success:
            # データベースのステータス更新
            job.status = "cancelled"
            db.commit()
            
            return {
                "job_id": job_id,
                "status": "cancelled",
                "message": "ジョブがキャンセルされました"
            }
        else:
            return {
                "job_id": job_id,
                "status": job.status,
                "message": "ジョブのキャンセルに失敗しました"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブキャンセルエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ジョブキャンセル中にエラーが発生しました: {str(e)}") 