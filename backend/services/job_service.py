#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any

from backend.models.database import Job, File, EvaluationReport
from backend.models.schemas import JobCreate, JobResponse, JobStatus

def create_job(db: Session, job_id: Optional[str] = None, job_parameters: Optional[Dict[str, Any]] = None) -> Job:
    """新しいジョブを作成する
    
    Args:
        db: データベースセッション
        job_id: ジョブID（指定がない場合は自動生成）
        job_parameters: ジョブパラメーター
        
    Returns:
        作成されたジョブ
    """
    if job_id is None:
        job_id = str(uuid.uuid4())
    
    db_job = Job(
        job_id=job_id,
        status="queued",
        job_parameters=job_parameters
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job(db: Session, job_id: str) -> Optional[Job]:
    """ジョブIDでジョブを取得する
    
    Args:
        db: データベースセッション
        job_id: ジョブID
        
    Returns:
        ジョブ（存在しない場合はNone）
    """
    return db.query(Job).filter(Job.job_id == job_id).first()

def get_all_jobs(db: Session, skip: int = 0, limit: int = 100) -> List[Job]:
    """ジョブの一覧を取得する
    
    Args:
        db: データベースセッション
        skip: スキップする数
        limit: 取得する上限数
        
    Returns:
        ジョブのリスト
    """
    return db.query(Job).order_by(Job.submission_time.desc()).offset(skip).limit(limit).all()

def update_job_status(db: Session, job_id: str, status: str, error_message: Optional[str] = None) -> Optional[Job]:
    """ジョブのステータスを更新する
    
    Args:
        db: データベースセッション
        job_id: ジョブID
        status: 新しいステータス
        error_message: エラーメッセージ（エラー時のみ）
        
    Returns:
        更新されたジョブ（存在しない場合はNone）
    """
    db_job = get_job(db, job_id)
    if db_job is None:
        return None
    
    db_job.status = status
    
    if status == "processing" and db_job.start_time is None:
        db_job.start_time = datetime.utcnow()
    
    if status in ["completed", "error"]:
        db_job.end_time = datetime.utcnow()
    
    if error_message:
        db_job.error_message = error_message
    
    db.commit()
    db.refresh(db_job)
    return db_job

def delete_job(db: Session, job_id: str) -> bool:
    """ジョブを削除する
    
    Args:
        db: データベースセッション
        job_id: ジョブID
        
    Returns:
        削除成功した場合はTrue
    """
    db_job = get_job(db, job_id)
    if db_job is None:
        return False
    
    db.delete(db_job)
    db.commit()
    return True

def add_file_to_job(db: Session, job_id: str, file_type: str, file_path: str) -> Optional[File]:
    """ジョブにファイルを追加する
    
    Args:
        db: データベースセッション
        job_id: ジョブID
        file_type: ファイルタイプ
        file_path: ファイルパス
        
    Returns:
        作成されたファイルオブジェクト（ジョブが存在しない場合はNone）
    """
    db_job = get_job(db, job_id)
    if db_job is None:
        return None
    
    db_file = File(
        file_id=str(uuid.uuid4()),
        job_id=job_id,
        file_type=file_type,
        file_path=file_path
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def add_evaluation_report(
    db: Session, 
    job_id: str, 
    evaluation_score: Optional[float] = None,
    report_data: Optional[Dict[str, Any]] = None
) -> Optional[EvaluationReport]:
    """ジョブに評価レポートを追加する
    
    Args:
        db: データベースセッション
        job_id: ジョブID
        evaluation_score: 評価スコア
        report_data: レポートデータ
        
    Returns:
        作成された評価レポート（ジョブが存在しない場合はNone）
    """
    db_job = get_job(db, job_id)
    if db_job is None:
        return None
    
    # 既存のレポートを確認
    existing_report = db.query(EvaluationReport).filter(EvaluationReport.job_id == job_id).first()
    if existing_report:
        # 既存レポートを更新
        existing_report.evaluation_score = evaluation_score
        existing_report.report_data = report_data
        db.commit()
        db.refresh(existing_report)
        return existing_report
    
    # 新規レポートを作成
    db_report = EvaluationReport(
        report_id=str(uuid.uuid4()),
        job_id=job_id,
        evaluation_score=evaluation_score,
        report_data=report_data
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report 