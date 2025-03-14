#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import logging
import yaml
import json
import time
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Query, Response, Header
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, validator
import aiofiles

from backend.models.database import get_db, Job, File as DBFile
from backend.models.schemas import JobCreate, JobResponse, JobStatus, FileResponse, StandardResponse
from backend.services.job_service import create_job, get_job, get_all_jobs, add_file_to_job
from backend.utils.file_utils import save_upload_file, get_file_path
import backend.job_processor as job_processor

from backend.job_processor import (
    add_job, 
    get_job_status, 
    cancel_job, 
    JOB_STATUSES,
    DATASET_DIR
)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("storage/logs/dataset_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dataset_api")

# デフォルト設定ファイルパス
DEFAULT_SETTINGS_PATH = "backend/dataset_setting_default.yaml"

# ルーター作成
router = APIRouter(
    prefix="/dataset",
    tags=["dataset"],
    responses={404: {"description": "Not found"}},
)

# データセットパラメータのモデル
class DatasetParams(BaseModel):
    # カメラ角度設定
    angle: Dict[str, int] = Field(
        default_factory=lambda: {"start": 0, "end": 350, "step": 10}
    )
    
    # 表情リスト
    expressions: List[str] = Field(
        default_factory=lambda: ["Neutral", "Happy", "Sad", "Angry", "Surprised"]
    )
    
    # ライティング条件
    lighting: List[str] = Field(
        default_factory=lambda: ["Bright", "Normal", "Soft"]
    )
    
    # カメラ距離
    camera_distance: List[str] = Field(
        default_factory=lambda: ["Close-up", "Mid-shot", "Full-body"]
    )
    
    # 最小構成の使用
    use_minimal: bool = Field(default=False)
    
    # 最小構成設定
    minimal_config: Optional[Dict[str, List[str]]] = None
    
    # 出力設定
    output: Dict[str, Any] = Field(
        default_factory=lambda: {
            "format": "png",
            "resolution": "512x512",
            "quality": 90,
            "background": "#FFFFFF"
        }
    )
    
    # メタデータ設定
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "include_params": True,
            "timestamp": True,
            "naming_format": "shot_{expression}_{lighting}_{distance}_angle{angle:03d}.png"
        }
    )
    
    # バリデーション
    @validator("angle")
    def validate_angle(cls, v):
        if not all(key in v for key in ["start", "end", "step"]):
            raise ValueError("角度設定には start, end, step が必要です")
        if v["start"] < 0 or v["start"] >= 360:
            raise ValueError("開始角度は 0-359 度の範囲内である必要があります")
        if v["end"] < 0 or v["end"] >= 360:
            raise ValueError("終了角度は 0-359 度の範囲内である必要があります")
        if v["step"] <= 0 or v["step"] >= 360:
            raise ValueError("角度間隔は 1-359 度の範囲内である必要があります")
        return v
    
    # 計算ヘルパー
    def calculate_total_shots(self) -> int:
        """合計ショット数を計算"""
        # 使用する設定を決定
        if self.use_minimal and self.minimal_config:
            expressions = self.minimal_config.get("expressions", ["Neutral"])
            lighting = self.minimal_config.get("lighting", ["Normal"])
            distances = self.minimal_config.get("camera_distance", ["Mid-shot", "Close-up"])
        else:
            expressions = self.expressions
            lighting = self.lighting
            distances = self.camera_distance
        
        # 角度の数を計算
        angle_count = (self.angle["end"] - self.angle["start"]) // self.angle["step"] + 1
        # 調整: endが含まれる場合
        if (self.angle["start"] + (angle_count - 1) * self.angle["step"]) < self.angle["end"]:
            angle_count += 1
        
        return angle_count * len(expressions) * len(lighting) * len(distances)
    
    def estimated_time(self) -> float:
        """推定処理時間（分）"""
        shots = self.calculate_total_shots()
        return round(shots * 0.5 / 60, 1)  # 1ショット0.5秒と仮定
    
    def estimated_size_mb(self) -> float:
        """推定サイズ（MB）"""
        shots = self.calculate_total_shots()
        # 解像度からサイズを推定
        resolution = self.output.get("resolution", "512x512")
        try:
            width, height = map(int, resolution.split("x"))
            # PNGファイルの推定サイズ（圧縮率仮定）
            size_per_image = width * height * 4 * 0.5 / (1024 * 1024)  # MB単位
            return round(shots * size_per_image, 1)
        except:
            # 解像度解析失敗時のデフォルト
            return round(shots * 0.25, 1)  # デフォルト: 1枚あたり0.25MB

# デフォルト設定の読み込み
def load_default_settings() -> Dict[str, Any]:
    """デフォルト設定ファイルの読み込み"""
    try:
        if os.path.exists(DEFAULT_SETTINGS_PATH):
            with open(DEFAULT_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
                return settings
        else:
            logger.warning(f"デフォルト設定ファイルが見つかりません: {DEFAULT_SETTINGS_PATH}")
            return {}
    except Exception as e:
        logger.error(f"デフォルト設定の読み込みエラー: {str(e)}")
        return {}

# 設定のマージ
def merge_settings(user_settings: Dict[str, Any], default_settings: Dict[str, Any]) -> Dict[str, Any]:
    """ユーザー設定とデフォルト設定をマージ"""
    result = default_settings.copy()
    
    # ユーザー設定で上書き
    for key, value in user_settings.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            # ネストした辞書はマージ
            result[key] = merge_settings(value, result[key])
        else:
            # その他はそのまま上書き
            result[key] = value
    
    return result

# データセット生成ジョブのキュー追加
@router.post("/generate", status_code=202)
async def generate_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    params: Optional[str] = Form(None),
    use_minimal: Optional[bool] = Form(False)
):
    """
    VRMファイルからデータセットを生成するジョブを作成
    
    - **file**: VRMファイル（必須）
    - **params**: JSON形式のパラメータ（省略可）
    - **use_minimal**: 最小構成を使用するか（省略可、デフォルトはFalse）
    """
    try:
        # VRMファイルの検証
        if not file.filename or not file.filename.lower().endswith('.vrm'):
            raise HTTPException(status_code=400, detail="VRM形式のファイルを選択してください")
        
        # ファイルサイズのチェック（最大50MB）
        content = await file.read()
        await file.seek(0)  # ファイルポインタをリセット
        
        if len(content) > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=400, detail="ファイルサイズは50MB以下にしてください")
        
        # ジョブIDの生成
        job_id = str(uuid.uuid4())
        
        # アップロードディレクトリ確認
        upload_dir = os.path.join("storage", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # ファイル保存
        file_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(content)
        
        # パラメータの解析
        job_params = {}
        use_minimal_param = use_minimal
        
        if params:
            try:
                user_params = json.loads(params)
                # use_minimalパラメータを更新
                if 'use_minimal' in user_params:
                    use_minimal_param = user_params['use_minimal']
                job_params = user_params
            except json.JSONDecodeError:
                logger.error(f"パラメータのJSON解析エラー: {params}")
                raise HTTPException(status_code=400, detail="パラメータの形式が無効です")
        
        # デフォルト設定の読み込みとマージ
        default_settings = load_default_settings()
        job_params = merge_settings(job_params, default_settings)
        
        # use_minimalパラメータを設定
        job_params['use_minimal'] = use_minimal_param
        
        # パラメータの検証
        try:
            dataset_params = DatasetParams(**job_params)
            job_params = dataset_params.dict()
        except Exception as e:
            logger.error(f"パラメータ検証エラー: {str(e)}")
            raise HTTPException(status_code=400, detail=f"パラメータが無効です: {str(e)}")
        
        # 合計ショット数とデータサイズの計算
        total_shots = dataset_params.calculate_total_shots()
        estimated_size = dataset_params.estimated_size_mb()
        estimated_time = dataset_params.estimated_time()
        
        logger.info(f"データセット生成ジョブ作成: {job_id}, ファイル: {file.filename}, " +
                     f"ショット数: {total_shots}, 推定サイズ: {estimated_size}MB, 推定時間: {estimated_time}分")
        
        # ジョブをキューに追加
        try:
            job_id = add_job(
                "dataset", 
                file_path, 
                job_params
            )
        except Exception as e:
            logger.error(f"ジョブの追加に失敗しました: {str(e)}")
            raise HTTPException(status_code=500, detail=f"ジョブの追加に失敗しました: {str(e)}")
        
        # レスポンス
        return {
            "job_id": job_id,
            "filename": file.filename,
            "status": "queued",
            "message": "データセット生成ジョブがキューに追加されました",
            "total_shots": total_shots,
            "estimated_size_mb": estimated_size,
            "estimated_time_minutes": estimated_time
        }
        
    except HTTPException:
        # HTTPExceptionはそのまま再送
        raise
    except Exception as e:
        logger.error(f"データセット生成リクエスト処理エラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")

# ジョブリストの取得
@router.get("/jobs")
async def get_dataset_jobs():
    """データセット生成ジョブのリストを取得"""
    try:
        # すべてのジョブを取得
        all_jobs = get_job_status()
        
        # データセットジョブのみをフィルタリング
        dataset_jobs = [
            job for job in all_jobs 
            if job.get("job_type") == "dataset"
        ]
        
        return {
            "jobs": dataset_jobs,
            "count": len(dataset_jobs)
        }
        
    except Exception as e:
        logger.error(f"ジョブリスト取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")

# 特定のジョブの詳細取得
@router.get("/jobs/{job_id}")
async def get_dataset_job(job_id: str):
    """指定されたジョブの詳細情報を取得"""
    try:
        # ジョブ情報を取得
        job_info = get_job_status(job_id)
        
        # ジョブが見つからない場合
        if job_info.get("status") == JOB_STATUSES["not_found"]:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        # データセットジョブかどうかを確認
        if job_info.get("job_type") != "dataset":
            raise HTTPException(status_code=400, detail="指定されたジョブはデータセットジョブではありません")
        
        return job_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ詳細取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")

# データセットのダウンロード
@router.get("/download/{job_id}")
async def download_dataset(
    job_id: str,
    response: Response,
    range: Optional[str] = Header(None)
):
    """生成されたデータセットをダウンロード"""
    try:
        # ジョブ情報を取得
        job_info = get_job_status(job_id)
        
        # ジョブが見つからない場合
        if job_info.get("status") == JOB_STATUSES["not_found"]:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        # データセットジョブかどうかを確認
        if job_info.get("job_type") != "dataset":
            raise HTTPException(status_code=400, detail="指定されたジョブはデータセットジョブではありません")
        
        # ジョブが完了していることを確認
        if job_info.get("status") != JOB_STATUSES["completed"]:
            raise HTTPException(status_code=400, detail="ジョブはまだ完了していません")
        
        # 結果ファイルパスの取得
        result_path = job_info.get("result_path")
        if not result_path or not os.path.exists(result_path):
            raise HTTPException(status_code=404, detail="データセットファイルが見つかりません")
        
        # ファイル名の取得
        file_name = os.path.basename(result_path)
        
        # ファイルのレスポンス
        return FileResponse(
            result_path,
            media_type="application/zip",
            filename=file_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"データセットダウンロードエラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")

# ジョブのキャンセル
@router.post("/jobs/{job_id}/cancel")
async def cancel_dataset_job(job_id: str):
    """指定されたデータセット生成ジョブをキャンセル"""
    try:
        # ジョブ情報を取得
        job_info = get_job_status(job_id)
        
        # ジョブが見つからない場合
        if job_info.get("status") == JOB_STATUSES["not_found"]:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        # データセットジョブかどうかを確認
        if job_info.get("job_type") != "dataset":
            raise HTTPException(status_code=400, detail="指定されたジョブはデータセットジョブではありません")
        
        # すでに完了またはエラーの場合
        if job_info.get("status") in [JOB_STATUSES["completed"], JOB_STATUSES["error"], JOB_STATUSES["cancelled"]]:
            return {
                "success": False,
                "message": f"ジョブはすでに {job_info.get('status')} 状態のためキャンセルできません"
            }
        
        # ジョブをキャンセル
        success = cancel_job(job_id)
        
        if success:
            logger.info(f"データセットジョブがキャンセルされました: {job_id}")
            return {
                "success": True,
                "message": "ジョブのキャンセルが完了しました"
            }
        else:
            logger.error(f"データセットジョブのキャンセルに失敗しました: {job_id}")
            return {
                "success": False,
                "message": "ジョブのキャンセルに失敗しました"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"データセットジョブのキャンセルエラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")

# 計算エンドポイント - 設定に基づく合計ショット数などの計算
@router.post("/calculate")
async def calculate_dataset_info(params: DatasetParams):
    """データセット設定に基づく情報計算"""
    try:
        total_shots = params.calculate_total_shots()
        estimated_size = params.estimated_size_mb()
        estimated_time = params.estimated_time()
        
        return {
            "total_shots": total_shots,
            "estimated_size_mb": estimated_size,
            "estimated_time_minutes": estimated_time
        }
        
    except Exception as e:
        logger.error(f"データセット情報計算エラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"計算エラー: {str(e)}")

# デフォルト設定の取得
@router.get("/default-settings")
async def get_default_settings():
    """データセット生成のデフォルト設定を取得"""
    try:
        # デフォルト設定の読み込み
        settings = load_default_settings()
        
        # 設定が見つからない場合
        if not settings:
            raise HTTPException(status_code=404, detail="デフォルト設定が見つかりません")
        
        return settings
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"デフォルト設定取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")