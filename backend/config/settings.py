#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # 基本設定
    APP_NAME: str = "LoRA作成クラウドサービス"
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    
    # データベース設定
    DATABASE_URL: Optional[str] = None
    
    # ストレージ設定
    STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "storage")
    UPLOAD_DIR: str = os.path.join(STORAGE_DIR, "uploads")
    RESULT_DIR: str = os.path.join(STORAGE_DIR, "results")
    LOG_DIR: str = os.path.join(STORAGE_DIR, "logs")
    
    # アップロード設定
    MAX_UPLOAD_SIZE_MB: int = 50  # 最大アップロードサイズ（MB）
    ALLOWED_EXTENSIONS: list = [".vrm"]
    
    # ジョブ設定
    JOB_TIMEOUT_SECONDS: int = 3600  # ジョブタイムアウト（秒）
    
    # GCPサービス設定（本番環境用）
    GCP_PROJECT_ID: Optional[str] = None
    GCP_BUCKET_NAME: Optional[str] = None
    USE_GCP: bool = False  # ローカル環境ではFalse
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 設定のインスタンス
settings = Settings()

# ディレクトリが存在するか確認し、なければ作成
for directory in [settings.STORAGE_DIR, settings.UPLOAD_DIR, settings.RESULT_DIR, settings.LOG_DIR]:
    os.makedirs(directory, exist_ok=True) 