#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# ジョブ関連のスキーマ

class JobBase(BaseModel):
    """ジョブのベーススキーマ"""
    job_parameters: Optional[Dict[str, Any]] = None

class JobCreate(JobBase):
    """ジョブ作成用スキーマ"""
    pass

class JobResponse(JobBase):
    """ジョブレスポンス用スキーマ"""
    job_id: str
    status: str
    submission_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class JobStatus(BaseModel):
    """ジョブステータス取得用スキーマ"""
    job_id: str
    status: str
    progress: Optional[float] = None
    message: Optional[str] = None

# ファイル関連のスキーマ

class FileBase(BaseModel):
    """ファイルのベーススキーマ"""
    file_type: str
    file_path: str

class FileCreate(FileBase):
    """ファイル作成用スキーマ"""
    job_id: str

class FileResponse(FileBase):
    """ファイルレスポンス用スキーマ"""
    file_id: str
    job_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# 評価レポート関連のスキーマ

class EvaluationReportBase(BaseModel):
    """評価レポートのベーススキーマ"""
    evaluation_score: Optional[float] = None
    report_data: Optional[Dict[str, Any]] = None

class EvaluationReportCreate(EvaluationReportBase):
    """評価レポート作成用スキーマ"""
    job_id: str

class EvaluationReportResponse(EvaluationReportBase):
    """評価レポートレスポンス用スキーマ"""
    report_id: str
    job_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# レスポンス用共通スキーマ

class StandardResponse(BaseModel):
    """標準APIレスポンス"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None 