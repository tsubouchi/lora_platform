#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import uuid
import threading
import logging
import datetime
import traceback
import signal
from queue import Queue, Empty
from typing import Dict, List, Optional, Any, Tuple
from backend.models.database import SessionLocal, Job, File, DatasetMetadata, DatasetShot, init_db, get_db_session
import shutil
import zipfile
from backend.dataset_generator import generate_dataset as generate_vrm_dataset

# グローバル変数
_processor = None
_stop_event = threading.Event()

# 定数定義
JOB_STATUSES = {
    "QUEUED": "queued",
    "PROCESSING": "processing",
    "COMPLETED": "completed",
    "ERROR": "error",
    "CANCELLED": "cancelled"
}

# ディレクトリ設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DATASET_DIR = os.path.join(STORAGE_DIR, "datasets")

# データベースパスを明示的に定義
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "lora_platform.db")

# データベースモデルのインポート
from backend.models.database import SessionLocal, Job, File, DatasetMetadata, DatasetShot, init_db
from backend.dataset_generator import generate_dataset, DatasetGenerationError, JobCancelledError

# ロギングの設定
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'storage', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'job_processor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("backend.job_processor")

# ディレクトリ設定
UPLOAD_DIR = os.path.join(BASE_DIR, 'storage', 'uploads')
RESULTS_DIR = os.path.join(BASE_DIR, 'storage', 'results')
TEMP_DIR = os.path.join(BASE_DIR, 'storage', 'temp')

# 必要なディレクトリの作成
for directory in [UPLOAD_DIR, DATASET_DIR, RESULTS_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)

# ジョブキューとジョブデータ
job_queue = Queue()
active_processors = {}
is_shutdown = False

# 以下はJobProcessorクラスのままで

class JobProcessor:
    """VRMファイルからの変換ジョブを処理するクラス"""
    
    def __init__(self):
        self.job_queue = Queue()
        self.jobs_data = {}  # job_id -> job_data の辞書
        self.processing_thread = None
        self.is_running = False
        self.last_cleanup_time = time.time()
        
        # 必要なディレクトリの作成
        for directory in [UPLOAD_DIR, DATASET_DIR, RESULTS_DIR, TEMP_DIR]:
            os.makedirs(directory, exist_ok=True)
    
    def start(self):
        """ジョブ処理スレッドを開始"""
        if self.processing_thread and self.processing_thread.is_alive():
            logger.warn("ジョブ処理スレッドは既に実行中です")
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._process_jobs)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info("ジョブ処理スレッドが開始されました")
    
    def stop(self):
        """ジョブ処理スレッドを停止"""
        self.is_running = False
        logger.info("ジョブ処理スレッドの停止が要求されました")
        
        # アクティブジョブのキャンセル
        active_jobs = [job_id for job_id, job_data in self.jobs_data.items() 
                      if job_data.get('status') == 'processing']
        
        for job_id in active_jobs:
            self.cancel_job(job_id)
        
        if self.processing_thread:
            self.processing_thread.join(timeout=60)
            if self.processing_thread.is_alive():
                logger.warning("ジョブ処理スレッドが60秒以内に停止しませんでした")
            else:
                logger.info("ジョブ処理スレッドが停止しました")
                
        # データベース関連のリソースをクリーンアップ
        # このタイミングで必要なデータベース処理を行う
    
    def add_job(self, job_type, file_path, parameters=None):
        """ジョブをキューに追加し、ジョブIDを返す"""
        job_id = str(uuid.uuid4())
        submission_time = datetime.datetime.now().isoformat()
        
        job_data = {
            'job_id': job_id,
            'job_type': job_type,
            'status': 'queued',
            'submission_time': submission_time,
            'file_path': file_path,
            'parameters': parameters or {},
            'progress': 0,
            'message': 'ジョブがキューに追加されました'
        }
        
        self.jobs_data[job_id] = job_data
        self.job_queue.put(job_id)
        
        logger.info(f"ジョブが追加されました: {job_id}, タイプ: {job_type}")
        return job_id
    
    def get_job_status(self, job_id):
        """指定されたジョブIDのステータスを取得"""
        job_data = self.jobs_data.get(job_id)
        if not job_data:
            return {'status': 'not_found', 'message': 'ジョブが見つかりません'}
        
        # 深いコピーを返して、元のデータに影響を与えないようにする
        return dict(job_data)
    
    def get_all_jobs(self, limit=100, offset=0, status=None):
        """全てのジョブを取得、またはステータスでフィルタリング"""
        filtered_jobs = []
        for job_id, job_data in self.jobs_data.items():
            if status is None or job_data.get('status') == status:
                filtered_jobs.append(dict(job_data))
        
        # 提出時刻で降順ソート（新しい順）
        filtered_jobs.sort(key=lambda x: x.get('submission_time', ''), reverse=True)
        
        # ページネーション
        paginated_jobs = filtered_jobs[offset:offset+limit]
        
        return {
            'total': len(filtered_jobs),
            'offset': offset,
            'limit': limit,
            'jobs': paginated_jobs
        }
    
    def update_job_status(self, job_id, status=None, progress=None, message=None, 
                          result_path=None, error_message=None):
        """ジョブのステータスを更新"""
        job_data = self.jobs_data.get(job_id)
        if not job_data:
            logger.warning(f"更新対象のジョブが見つかりません: {job_id}")
            return
        
        if status:
            job_data['status'] = status
            
            # ステータスに応じて時間を記録
            if status == 'processing' and 'start_time' not in job_data:
                job_data['start_time'] = datetime.datetime.now().isoformat()
            elif status in ['completed', 'error', 'cancelled'] and 'end_time' not in job_data:
                job_data['end_time'] = datetime.datetime.now().isoformat()
        
        if progress is not None:
            job_data['progress'] = progress
        
        if message:
            job_data['message'] = message
            
        if result_path:
            job_data['result_path'] = result_path
            
        if error_message:
            job_data['error_message'] = error_message
        
        logger.info(f"ジョブステータスが更新されました: {job_id}, ステータス: {status}, 進捗: {progress}")

    def _generate_dataset(self, job_id: str, vrm_file_path: str, settings: Dict[str, Any]) -> str:
        """データセットを生成する

        Args:
            job_id: ジョブID
            vrm_file_path: VRMファイルのパス
            settings: 生成設定

        Returns:
            str: 生成されたZIPファイルのパス
        """
        logger.info(f"データセット生成ジョブを開始します: {job_id}")
        
        try:
            # 進捗更新コールバック関数を定義
            def progress_update_callback(progress_data: Dict[str, Any], message: str = None):
                # progress_dataから情報を取得
                if isinstance(progress_data, dict):
                    # 新しいインターフェース: 辞書型で進捗情報が渡される場合
                    progress = progress_data.get("progress", 0)
                    message = progress_data.get("status", message or "処理中...")
                else:
                    # 古いインターフェース: 進捗値が直接渡される場合
                    progress = progress_data
                    message = message or "処理中..."
                
                _update_dataset_progress(
                    job_id=job_id,
                    progress=progress,
                    message=message
                )
            
            # 引数チェック - use_minimal が settings ディクショナリ内に存在するようにする
            if 'use_minimal' not in settings:
                logger.info("use_minimal が settings に存在しないため、デフォルト値 False を設定します")
                settings['use_minimal'] = False
            
            # 実際のVRMビューワーを使用してデータセットを生成
            zip_file_path = generate_vrm_dataset(
                job_id=job_id,
                vrm_file_path=vrm_file_path,
                settings=settings,
                progress_callback=progress_update_callback
            )
            
            # ジョブディレクトリにコピー
            job_dir = os.path.join(STORAGE_DIR, job_id)
            os.makedirs(job_dir, exist_ok=True)
            
            dest_path = os.path.join(job_dir, f"{job_id}_dataset.zip")
            shutil.copy2(zip_file_path, dest_path)
            
            # 元のZIPファイルを削除
            os.unlink(zip_file_path)
            
            return dest_path
        except Exception as e:
            logger.error(f"データセット生成に失敗しました: {str(e)}")
            raise Exception(f"データセット生成に失敗しました: {str(e)}")

def add_job(job_type: str, file_path: str, parameters: Dict[str, Any] = None) -> str:
    """新しいジョブをデータベースに追加"""
    if parameters is None:
        parameters = {}
        
    job_id = str(uuid.uuid4())
    
    try:
        # ログは残しますが、デバッグログを整理
        logger.info(f"ジョブを追加します: タイプ={job_type}, ファイル={file_path}")
        
        # DB接続とジョブ追加
        with get_db_session() as session:
            # ジョブエントリの作成
            new_job = Job(
                job_id=job_id,
                job_type=job_type,
                status="queued",
                submission_time=datetime.datetime.now(),
                file_path=file_path,
                job_parameters=parameters,
                progress=0,
                message="キューに追加されました"
            )
            session.add(new_job)
            
            # ファイルエントリの作成
            try:
                file_size = os.path.getsize(file_path)
            except Exception:
                file_size = 0
                
            new_file = File(
                file_id=str(uuid.uuid4()),
                job_id=job_id,
                file_type="upload",
                file_path=file_path,
                file_size=file_size,
                mime_type="application/octet-stream",  # デフォルト値
                created_at=datetime.datetime.now()
            )
            session.add(new_file)
            
            # データセットジョブの場合はメタデータも追加
            if job_type == "dataset":
                metadata = DatasetMetadata(
                    metadata_id=str(uuid.uuid4()),
                    job_id=job_id,
                    angle_start=parameters.get('angle_start', 0),
                    angle_end=parameters.get('angle_end', 360),
                    angle_step=parameters.get('angle_step', 10),
                    expressions=parameters.get('expressions', []),
                    lighting=parameters.get('lighting', []),
                    camera_distance=parameters.get('camera_distance', []),
                    use_minimal=parameters.get('use_minimal', False)
                )
                session.add(metadata)
            
            session.commit()
        
        # キューにジョブを追加
        processor = _get_processor()
        if processor:
            processor.add_job(job_type, file_path, parameters)
        else:
            # プロセッサが初期化されていない場合はここで処理を開始
            _process_job_async(job_id)
            
        logger.info(f"ジョブが追加されました: {job_id}, タイプ: {job_type}")
        return job_id
    except Exception as e:
        logger.error(f"ジョブの追加中にエラーが発生しました: {str(e)}")
        if "stack trace" not in str(e).lower():
            logger.error(traceback.format_exc())
        raise

def get_job_status(job_id: str) -> Dict[str, Any]:
    """指定されたジョブIDのステータスを取得"""
    try:
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            
            if not job:
                return {"status": "not_found", "message": "ジョブが見つかりません"}
            
            result = job.to_dict()
            
            # データセットジョブの場合はメタデータも取得
            if job.job_type == "dataset":
                metadata = db.query(DatasetMetadata).filter(DatasetMetadata.job_id == job_id).first()
                if metadata:
                    result["metadata"] = metadata.to_dict()
            
            return result
        except Exception as e:
            logger.error(f"ジョブステータスの取得中にデータベースエラーが発生しました: {str(e)}")
            return {"status": "error", "message": f"データベースエラー: {str(e)}"}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"ジョブステータスの取得中にエラーが発生しました: {str(e)}")
        return {"status": "error", "message": f"エラー: {str(e)}"}

def get_all_jobs(limit: int = 100, offset: int = 0, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """全てのジョブを取得、またはステータスでフィルタリング"""
    try:
        db = SessionLocal()
        try:
            query = db.query(Job)
            
            if status:
                query = query.filter(Job.status == status)
            
            total = query.count()
            jobs = query.order_by(Job.submission_time.desc()).offset(offset).limit(limit).all()
            
            return {
                "total": total,
                "offset": offset,
                "limit": limit,
                "jobs": [job.to_dict() for job in jobs]
            }
        except Exception as e:
            logger.error(f"ジョブ一覧の取得中にデータベースエラーが発生しました: {str(e)}")
            return {"total": 0, "offset": offset, "limit": limit, "jobs": []}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"ジョブ一覧の取得中にエラーが発生しました: {str(e)}")
        return {"total": 0, "offset": offset, "limit": limit, "jobs": []}

def update_job_status(job_id: str, status: str, progress: int = None, message: str = None, 
                     result_path: str = None, error_message: str = None, detailed_error: str = None,
                     metadata_updates: Dict[str, Any] = None) -> None:
    """ジョブのステータスを更新"""
    try:
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            
            if not job:
                logger.warning(f"更新対象のジョブが見つかりません: {job_id}")
                return
            
            # ステータスの更新
            if status:
                job.status = status
                
                # ステータスに応じた時間の更新
                if status == "processing" and not job.start_time:
                    job.start_time = datetime.datetime.now()
                elif status in ["completed", "error", "cancelled"] and not job.end_time:
                    job.end_time = datetime.datetime.now()
            
            # その他のフィールドの更新
            if progress is not None:
                job.progress = progress
            if message:
                job.message = message
            if result_path:
                job.result_path = result_path
            if error_message:
                job.error_message = error_message
            if detailed_error:
                job.detailed_error = detailed_error
            
            # データセットジョブのメタデータ更新
            if metadata_updates and job.job_type == "dataset":
                metadata = db.query(DatasetMetadata).filter(DatasetMetadata.job_id == job_id).first()
                if metadata:
                    for key, value in metadata_updates.items():
                        if hasattr(metadata, key):
                            setattr(metadata, key, value)
            
            db.commit()
            logger.info(f"ジョブステータスが更新されました: {job_id}, ステータス: {status}, 進捗: {progress}")
        except Exception as e:
            db.rollback()
            logger.error(f"ジョブステータス更新中にデータベースエラーが発生しました: {str(e)}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"ジョブステータス更新中にエラーが発生しました: {str(e)}")

def cancel_job(job_id: str) -> Dict[str, Any]:
    """指定されたジョブをキャンセル"""
    try:
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            
            if not job:
                return {"success": False, "message": "ジョブが見つかりません"}
            
            if job.status in ["completed", "error", "cancelled"]:
                return {"success": False, "message": f"ジョブは既に {job.status} 状態です"}
                
            # キューに入っているだけの場合は単純に状態を変更
            if job.status == "queued":
                job.status = "cancelled"
                job.end_time = datetime.datetime.now()
                job.message = "ジョブがキャンセルされました"
                db.commit()
                return {"success": True, "message": "ジョブがキャンセルされました"}
            
            # 処理中のジョブはプロセッサに通知
            if job_id in active_processors:
                active_processors[job_id]["cancel_requested"] = True
                job.message = "キャンセル要求が送信されました"
                db.commit()
                return {"success": True, "message": "キャンセル要求が送信されました"}
            else:
                # 処理中だがプロセッサがない場合（通常は起きない）
                job.status = "cancelled"
                job.end_time = datetime.datetime.now()
                job.message = "ジョブがキャンセルされました（非アクティブ）"
                db.commit()
                return {"success": True, "message": "非アクティブなジョブがキャンセルされました"}
                
        except Exception as e:
            db.rollback()
            logger.error(f"ジョブキャンセル中にデータベースエラーが発生しました: {str(e)}")
            return {"success": False, "message": f"エラー: {str(e)}"}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"ジョブキャンセル中にエラーが発生しました: {str(e)}")
        return {"success": False, "message": f"エラー: {str(e)}"}

def add_dataset_shot(job_id: str, file_name: str, file_path: str, expression: str, 
                   lighting: str, camera_distance: str, angle: int, width: int, height: int) -> None:
    """データセットの個別のショット情報をデータベースに追加"""
    try:
        db = SessionLocal()
        try:
            shot = DatasetShot(
                job_id=job_id,
                file_name=file_name,
                file_path=file_path,
                expression=expression,
                lighting=lighting,
                camera_distance=camera_distance,
                angle=angle,
                width=width,
                height=height
            )
            db.add(shot)
            
            # メタデータの完了ショット数を更新
            metadata = db.query(DatasetMetadata).filter(DatasetMetadata.job_id == job_id).first()
            if metadata:
                metadata.completed_shots += 1
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"データセットショット追加中にデータベースエラーが発生しました: {str(e)}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"データセットショット追加中にエラーが発生しました: {str(e)}")

def _process_job(job_id: str) -> None:
    """ジョブを処理する内部関数"""
    try:
        # ジョブ情報を取得
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            
            if not job:
                logger.error(f"処理対象のジョブが見つかりません: {job_id}")
                return
            
            # ジョブ情報の取得
            job_type = job.job_type
            file_path = job.file_path
            parameters = json.loads(job.job_parameters) if isinstance(job.job_parameters, str) else job.job_parameters
            
            # キャンセル要求をモニタリングするための辞書を作成
            processor_data = {"cancel_requested": False}
            active_processors[job_id] = processor_data
            
            # ジョブの開始
            update_job_status(job_id, "processing", 0, "処理を開始しています")
            
            # ジョブタイプに応じた処理
            if job_type == "lora":
                result_path = _convert_vrm_to_lora(job_id, file_path, parameters, processor_data)
            elif job_type == "dataset":
                result_path = _generate_dataset(job_id, file_path, parameters, processor_data)
            else:
                raise ValueError(f"未対応のジョブタイプです: {job_type}")
            
            # 処理が完了した場合
            if processor_data["cancel_requested"]:
                update_job_status(job_id, "cancelled", 100, "ジョブがキャンセルされました")
            else:
                # 結果ファイルのエントリを作成
                if result_path:
                    file_name = os.path.basename(result_path)
                    file_size = os.path.getsize(result_path) if os.path.exists(result_path) else 0
                    
                    new_file = File(
                        job_id=job_id,
                        file_type="result",
                        file_path=result_path,
                        file_name=file_name,
                        file_size=file_size,
                        mime_type="application/zip"
                    )
                    db.add(new_file)
                    db.commit()
                
                update_job_status(job_id, "completed", 100, "処理が完了しました", result_path=result_path)
                logger.info(f"ジョブが完了しました: {job_id}, 結果: {result_path}")
                
        except JobCancelledError:
            update_job_status(job_id, "cancelled", progress=None, message="ジョブがキャンセルされました")
            logger.info(f"ジョブがキャンセルされました: {job_id}")
            
        except DatasetGenerationError as e:
            error_message = str(e)
            detailed_error = traceback.format_exc()
            update_job_status(
                job_id, "error", 
                message="データセット生成中にエラーが発生しました", 
                error_message=error_message,
                detailed_error=detailed_error
            )
            logger.error(f"データセット生成エラー: {job_id} - {error_message}")
            logger.debug(detailed_error)
            
        except Exception as e:
            error_message = str(e)
            detailed_error = traceback.format_exc()
            update_job_status(
                job_id, "error", 
                message="処理中にエラーが発生しました", 
                error_message=error_message,
                detailed_error=detailed_error
            )
            logger.error(f"ジョブ処理エラー: {job_id} - {error_message}")
            logger.debug(detailed_error)
            
        finally:
            # 完了したらアクティブプロセッサから削除
            if job_id in active_processors:
                del active_processors[job_id]
            db.close()
    
    except Exception as e:
        logger.error(f"ジョブ処理中に予期しないエラーが発生しました: {job_id} - {str(e)}")
        traceback.print_exc()
        try:
            update_job_status(
                job_id, "error", 
                message="予期しないエラーが発生しました", 
                error_message=str(e),
                detailed_error=traceback.format_exc()
            )
        except:
            pass

def _convert_vrm_to_lora(job_id: str, file_path: str, parameters: Dict[str, Any], processor_data: Dict[str, bool]) -> str:
    """VRMファイルからLoRAモデルを生成"""
    # この関数の実装はプロジェクトの要件に応じて行う
    # 現在はダミー実装
    update_job_status(job_id, None, 10, "VRMモデルを解析中...")
    time.sleep(2)
    
    if processor_data["cancel_requested"]:
        raise JobCancelledError("ジョブがキャンセルされました")
    
    update_job_status(job_id, None, 30, "LoRAモデルを生成中...")
    time.sleep(2)
    
    if processor_data["cancel_requested"]:
        raise JobCancelledError("ジョブがキャンセルされました")
    
    update_job_status(job_id, None, 70, "モデルを最適化中...")
    time.sleep(2)
    
    if processor_data["cancel_requested"]:
        raise JobCancelledError("ジョブがキャンセルされました")
    
    # ダミーの結果ファイルパス
    result_path = os.path.join(RESULTS_DIR, f"{job_id}.zip")
    with open(result_path, 'w') as f:
        f.write("Dummy LoRA model file")
    
    return result_path

def _generate_dataset(job_id: str, file_path: str, parameters: Dict[str, Any], processor_data: Dict[str, bool]) -> str:
    """データセット生成ジョブの処理"""
    logger.info(f"データセット生成ジョブを開始: {job_id}, ファイル: {file_path}")
    
    try:
        # 実際のVRMビューワーを使用したデータセット生成を実装
        # signal only works in main thread of the main interpreterエラーを回避するための実装
        import threading
        from backend.dataset_generator import generate_dataset
        
        # 進捗を更新するためのコールバック関数 - 新しいインターフェースに合わせて修正
        def progress_update_callback(progress_data: Dict[str, Any], message: str = None):
            # progress_dataから情報を取得
            if isinstance(progress_data, dict):
                # 新しいインターフェース: 辞書型で進捗情報が渡される場合
                progress = progress_data.get("progress", 0)
                message = progress_data.get("status", message or "処理中...")
            else:
                # 古いインターフェース: 進捗値が直接渡される場合
                progress = progress_data
                message = message or "処理中..."
            
            _update_dataset_progress(
                job_id=job_id,
                progress=progress,
                message=message
            )
        
        # use_minimalが設定にあれば、settingsに含める
        if 'use_minimal' in parameters:
            # すでにsettingsに入っているので何もしない
            pass
        else:
            parameters['use_minimal'] = False
        
        # 実際のデータセット生成関数を呼び出し
        result_path = generate_dataset(
            job_id=job_id,
            vrm_file_path=file_path,
            settings=parameters,
            progress_callback=progress_update_callback
        )
        
        return result_path
        
    except Exception as e:
        logger.error(f"データセット生成中にエラーが発生: {str(e)}", exc_info=True)
        raise

def _update_dataset_progress(job_id: str, progress: int, message: str, **kwargs) -> None:
    """データセット生成の進捗を更新"""
    metadata_updates = {}
    
    # メタデータの更新があれば反映
    for key, value in kwargs.items():
        if key in ['completed_shots', 'total_shots']:
            metadata_updates[key] = value
    
    update_job_status(job_id, None, progress, message, metadata_updates=metadata_updates)

def _add_dataset_shot(job_id: str, **kwargs) -> None:
    """データセットのショット情報を追加"""
    required_fields = ['file_name', 'file_path', 'expression', 'lighting', 'camera_distance', 'angle', 'width', 'height']
    
    # 必須フィールドの確認
    for field in required_fields:
        if field not in kwargs:
            logger.warning(f"データセットショット情報に必須フィールドがありません: {field}")
            return
    
    add_dataset_shot(
        job_id=job_id,
        file_name=kwargs['file_name'],
        file_path=kwargs['file_path'],
        expression=kwargs['expression'],
        lighting=kwargs['lighting'],
        camera_distance=kwargs['camera_distance'],
        angle=kwargs['angle'],
        width=kwargs['width'],
        height=kwargs['height']
    )

def process_jobs() -> None:
    """ジョブキューからジョブを処理"""
    logger.info("ジョブプロセッサが開始されました")
    
    while not is_shutdown:
        try:
            # キューからジョブを取得（タイムアウト付き）
            try:
                job_id = job_queue.get(timeout=1)
            except Empty:
                continue
            
            # ジョブを処理
            logger.info(f"ジョブの処理を開始します: {job_id}")
            threading.Thread(target=_process_job, args=(job_id,)).start()
            
        except Exception as e:
            logger.error(f"ジョブキュー処理中にエラーが発生しました: {str(e)}")
            traceback.print_exc()
            time.sleep(5)  # エラー時は少し待機

def init_job_processor() -> None:
    """ジョブプロセッサを初期化"""
    # データベースの初期化
    init_db()
    
    # 未完了のジョブの復旧処理
    db = SessionLocal()
    try:
        # 処理中または待機中だったジョブを検索
        incomplete_jobs = db.query(Job).filter(
            Job.status.in_(["queued", "processing"])
        ).all()
        
        # 未完了のジョブを再キューイングまたはエラー状態に更新
        for job in incomplete_jobs:
            if job.status == "queued":
                # キューに追加
                job_queue.put(job.job_id)
                logger.info(f"未完了のキュー済みジョブを再キューイングしました: {job.job_id}")
            else:
                # 処理中だったジョブはエラー状態に更新
                job.status = "error"
                job.error_message = "サーバーが再起動したため、ジョブが中断されました"
                job.end_time = datetime.datetime.now()
                logger.warning(f"処理中だったジョブをエラー状態に更新しました: {job.job_id}")
        
        db.commit()
    except Exception as e:
        logger.error(f"未完了ジョブの復旧中にエラーが発生しました: {str(e)}")
        db.rollback()
    finally:
        db.close()
    
    # ジョブ処理スレッドの開始
    threading.Thread(target=process_jobs, daemon=True).start()
    logger.info("ジョブプロセッサが初期化されました")

def shutdown_job_processor() -> None:
    """ジョブプロセッサのシャットダウン"""
    global is_shutdown
    logger.info("ジョブプロセッサをシャットダウンしています...")
    is_shutdown = True
    
    # アクティブなプロセッサにキャンセル要求を送信
    for job_id, processor_data in active_processors.items():
        processor_data["cancel_requested"] = True
        logger.info(f"アクティブなジョブにキャンセル要求を送信しました: {job_id}")
    
    logger.info("ジョブプロセッサがシャットダウンされました")

def _get_processor():
    """現在のJobProcessorインスタンスを取得"""
    global _processor
    return _processor

def _process_job_async(job_id: str):
    """非同期でジョブを処理するスレッドを開始"""
    threading.Thread(target=_process_job, args=(job_id,)).start()

# 起動時に自動初期化
if __name__ == "__main__":
    init_job_processor() 