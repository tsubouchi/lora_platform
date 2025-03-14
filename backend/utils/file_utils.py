#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import uuid
from fastapi import UploadFile
import aiofiles
from typing import Optional, List, Tuple
import logging

# ディレクトリ設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "storage", "uploads")
RESULT_DIR = os.path.join(BASE_DIR, "storage", "results")
LOG_DIR = os.path.join(BASE_DIR, "storage", "logs")

# 初期化時にディレクトリを作成
for directory in [UPLOAD_DIR, RESULT_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

async def save_upload_file(upload_file: UploadFile, job_id: str) -> str:
    """アップロードされたファイルを保存する非同期関数
    
    Args:
        upload_file: アップロードされたファイル
        job_id: ジョブID
        
    Returns:
        保存されたファイルの絶対パス
    """
    # ジョブごとのディレクトリを作成
    job_upload_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_upload_dir, exist_ok=True)
    
    # ファイル名から安全なファイル名を作成
    file_name = os.path.basename(upload_file.filename)
    file_path = os.path.join(job_upload_dir, file_name)
    
    # 非同期でファイルを保存
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await upload_file.read()
        await out_file.write(content)
    
    return file_path

def save_result_file(content: bytes, job_id: str, file_name: str) -> str:
    """生成結果ファイルを保存する関数
    
    Args:
        content: ファイル内容
        job_id: ジョブID
        file_name: ファイル名
        
    Returns:
        保存されたファイルの絶対パス
    """
    # ジョブごとの結果ディレクトリを作成
    job_result_dir = os.path.join(RESULT_DIR, job_id)
    os.makedirs(job_result_dir, exist_ok=True)
    
    # ファイルパスを作成
    file_path = os.path.join(job_result_dir, file_name)
    
    # ファイルを保存
    with open(file_path, 'wb') as f:
        f.write(content)
    
    return file_path

def get_file_path(file_type: str, job_id: str, file_name: Optional[str] = None) -> str:
    """ファイルの保存先パスを取得する関数
    
    Args:
        file_type: ファイルタイプ ("upload", "result", "log")
        job_id: ジョブID
        file_name: ファイル名（指定がない場合はランダム名）
        
    Returns:
        ファイルパス
    """
    if file_type == "upload":
        base_dir = UPLOAD_DIR
    elif file_type == "result":
        base_dir = RESULT_DIR
    elif file_type == "log":
        base_dir = LOG_DIR
    else:
        raise ValueError(f"不明なファイルタイプ: {file_type}")
    
    job_dir = os.path.join(base_dir, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    if file_name is None:
        file_name = f"{uuid.uuid4()}.bin"
    
    return os.path.join(job_dir, file_name)

def delete_job_files(job_id: str) -> bool:
    """ジョブに関連するファイルを削除する関数
    
    Args:
        job_id: ジョブID
        
    Returns:
        削除成功した場合はTrue
    """
    try:
        # ジョブの各ディレクトリを削除
        for dir_path in [
            os.path.join(UPLOAD_DIR, job_id),
            os.path.join(RESULT_DIR, job_id),
            os.path.join(LOG_DIR, job_id)
        ]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
        return True
    except Exception as e:
        logging.error(f"ファイル削除エラー: {e}")
        return False 