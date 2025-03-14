#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Text, create_engine, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.sqlite import JSON
import os
import datetime
import uuid
import json
import logging

# ロギング設定
logger = logging.getLogger(__name__)

# データベースディレクトリとファイルの確認
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'database')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'lora_platform.db')

# SQLAlchemyエンジンとベースクラスの作成
engine = create_engine(f'sqlite:///{DB_PATH}')
Base = declarative_base()

# セッションファクトリー
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """データベースセッションを取得するユーティリティ関数（FastAPIのDependsで使用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """コンテキストマネージャとして使用できるデータベースセッションを返す"""
    class SessionManager:
        def __init__(self):
            self.db = SessionLocal()
            
        def __enter__(self):
            return self.db
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                self.db.rollback()
            self.db.close()
    
    return SessionManager()

# ジョブモデル
class Job(Base):
    __tablename__ = "jobs"
    
    job_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String, nullable=False, default="lora")  # "lora" または "dataset"
    status = Column(String, nullable=False, default="queued")  # queued, processing, completed, error, cancelled
    submission_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    file_path = Column(String, nullable=True)  # 入力ファイルのパス
    result_path = Column(String, nullable=True)  # 結果ファイルのパス
    progress = Column(Integer, nullable=False, default=0)  # 進捗状況 (0-100%)
    message = Column(String, nullable=True)  # 現在の状態メッセージ
    job_parameters = Column(JSON, nullable=True)  # ジョブのパラメータ
    error_message = Column(Text, nullable=True)  # エラーメッセージ
    detailed_error = Column(Text, nullable=True)  # 詳細なエラー情報（トレースバックなど）
    
    # リレーションシップ
    files = relationship("File", back_populates="job", cascade="all, delete-orphan")
    report = relationship("EvaluationReport", back_populates="job", uselist=False, cascade="all, delete-orphan")
    dataset_metadata = relationship("DatasetMetadata", back_populates="job", uselist=False, cascade="all, delete-orphan")
    dataset_shots = relationship("DatasetShot", back_populates="job", cascade="all, delete-orphan")
    
    # インデックス
    __table_args__ = (
        Index('idx_job_status', status),
        Index('idx_job_type', job_type),
        Index('idx_job_submission_time', submission_time),
    )
    
    def to_dict(self):
        """ジョブ情報を辞書として返す"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "submission_time": self.submission_time.isoformat() if self.submission_time else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "file_path": self.file_path,
            "result_path": self.result_path,
            "progress": self.progress,
            "message": self.message,
            "parameters": json.loads(self.job_parameters) if isinstance(self.job_parameters, str) else self.job_parameters,
            "error_message": self.error_message
        }

# ファイルモデル
class File(Base):
    __tablename__ = "files"
    
    file_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=False)
    file_type = Column(String, nullable=False)  # "upload", "result", "log", "report"
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=True)  # オリジナルのファイル名
    file_size = Column(Integer, nullable=True)  # ファイルサイズ（バイト）
    mime_type = Column(String, nullable=True)  # MIMEタイプ
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    # リレーションシップ
    job = relationship("Job", back_populates="files")
    
    # インデックス
    __table_args__ = (
        Index('idx_file_job_id', job_id),
        Index('idx_file_type', file_type),
    )
    
    def to_dict(self):
        """ファイル情報を辞書として返す"""
        return {
            "file_id": self.file_id,
            "job_id": self.job_id,
            "file_type": self.file_type,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# 評価レポートモデル
class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"
    
    report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=False)
    evaluation_score = Column(Float, nullable=True)
    report_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    # リレーションシップ
    job = relationship("Job", back_populates="report")
    
    # インデックス
    __table_args__ = (
        Index('idx_report_job_id', job_id),
    )
    
    def to_dict(self):
        """レポート情報を辞書として返す"""
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "evaluation_score": self.evaluation_score,
            "report_data": json.loads(self.report_data) if isinstance(self.report_data, str) else self.report_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# データセットメタデータモデル
class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"
    
    metadata_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=False)
    vrm_file_name = Column(String, nullable=True)  # 元のVRMファイル名
    angle_start = Column(Integer, nullable=True)  # 開始角度
    angle_end = Column(Integer, nullable=True)  # 終了角度
    angle_step = Column(Integer, nullable=True)  # 角度間隔
    expressions = Column(JSON, nullable=True)  # 表情設定
    lighting = Column(JSON, nullable=True)  # ライティング設定
    camera_distance = Column(JSON, nullable=True)  # カメラ距離設定
    total_shots = Column(Integer, nullable=True)  # 合計ショット数
    completed_shots = Column(Integer, nullable=True, default=0)  # 完了したショット数
    output_format = Column(String, nullable=True, default="png")  # 出力形式
    output_resolution = Column(String, nullable=True, default="512x512")  # 出力解像度
    output_quality = Column(Integer, nullable=True, default=90)  # 出力品質
    background_color = Column(String, nullable=True, default="#FFFFFF")  # 背景色
    use_minimal = Column(Boolean, nullable=True, default=False)  # 最小構成を使用したか
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    # リレーションシップ
    job = relationship("Job", back_populates="dataset_metadata")
    
    # インデックス
    __table_args__ = (
        Index('idx_metadata_job_id', job_id),
    )
    
    def to_dict(self):
        """メタデータ情報を辞書として返す"""
        return {
            "metadata_id": self.metadata_id,
            "job_id": self.job_id,
            "vrm_file_name": self.vrm_file_name,
            "angle_start": self.angle_start,
            "angle_end": self.angle_end,
            "angle_step": self.angle_step,
            "expressions": json.loads(self.expressions) if isinstance(self.expressions, str) else self.expressions,
            "lighting": json.loads(self.lighting) if isinstance(self.lighting, str) else self.lighting,
            "camera_distance": json.loads(self.camera_distance) if isinstance(self.camera_distance, str) else self.camera_distance,
            "total_shots": self.total_shots,
            "completed_shots": self.completed_shots,
            "output_format": self.output_format,
            "output_resolution": self.output_resolution,
            "output_quality": self.output_quality,
            "background_color": self.background_color,
            "use_minimal": self.use_minimal,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# データセットショットモデル
class DatasetShot(Base):
    __tablename__ = "dataset_shots"
    
    shot_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=False)
    file_name = Column(String, nullable=False)  # ファイル名
    file_path = Column(String, nullable=True)  # ファイルパス
    expression = Column(String, nullable=True)  # 表情
    lighting = Column(String, nullable=True)  # ライティング
    camera_distance = Column(String, nullable=True)  # カメラ距離
    angle = Column(Integer, nullable=True)  # 角度
    width = Column(Integer, nullable=True)  # 画像幅
    height = Column(Integer, nullable=True)  # 画像高さ
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    # リレーションシップ
    job = relationship("Job", back_populates="dataset_shots")
    
    # インデックス
    __table_args__ = (
        Index('idx_shot_job_id', job_id),
        Index('idx_shot_expression', expression),
        Index('idx_shot_angle', angle),
    )
    
    def to_dict(self):
        """ショット情報を辞書として返す"""
        return {
            "shot_id": self.shot_id,
            "job_id": self.job_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "expression": self.expression,
            "lighting": self.lighting,
            "camera_distance": self.camera_distance,
            "angle": self.angle,
            "width": self.width,
            "height": self.height,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# モデルの作成（必要な場合）
def create_tables():
    """テーブルを作成"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("データベーステーブルが作成されました")
    except Exception as e:
        logger.error(f"データベーステーブル作成中にエラーが発生しました: {str(e)}")

# マイグレーション関数
def run_migrations():
    """データベースマイグレーションを実行"""
    try:
        # 既存のテーブルがあるか確認
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        # テーブルが存在し、jobsテーブルにjob_typeカラムがない場合、追加
        if "jobs" in inspector.get_table_names():
            jobs_columns = [col["name"] for col in inspector.get_columns("jobs")]
            
            if "job_type" not in jobs_columns:
                # 既存のテーブルを変更するためのDDLを実行
                with engine.connect() as conn:
                    conn.execute("ALTER TABLE jobs ADD COLUMN job_type TEXT DEFAULT 'lora'")
                    logger.info("jobs テーブルに job_type カラムを追加しました")
            
            if "progress" not in jobs_columns:
                with engine.connect() as conn:
                    conn.execute("ALTER TABLE jobs ADD COLUMN progress INTEGER DEFAULT 0")
                    logger.info("jobs テーブルに progress カラムを追加しました")
                    
            if "message" not in jobs_columns:
                with engine.connect() as conn:
                    conn.execute("ALTER TABLE jobs ADD COLUMN message TEXT")
                    logger.info("jobs テーブルに message カラムを追加しました")
                    
            if "result_path" not in jobs_columns:
                with engine.connect() as conn:
                    conn.execute("ALTER TABLE jobs ADD COLUMN result_path TEXT")
                    logger.info("jobs テーブルに result_path カラムを追加しました")
                    
            if "file_path" not in jobs_columns:
                with engine.connect() as conn:
                    conn.execute("ALTER TABLE jobs ADD COLUMN file_path TEXT")
                    logger.info("jobs テーブルに file_path カラムを追加しました")
                    
            if "detailed_error" not in jobs_columns:
                with engine.connect() as conn:
                    conn.execute("ALTER TABLE jobs ADD COLUMN detailed_error TEXT")
                    logger.info("jobs テーブルに detailed_error カラムを追加しました")
        
        # 既存のテーブルにインデックスを追加
        try:
            with engine.connect() as conn:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_job_status ON jobs(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_job_type ON jobs(job_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_job_submission_time ON jobs(submission_time)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_file_job_id ON files(job_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_file_type ON files(file_type)")
                logger.info("既存のテーブルにインデックスを追加しました")
        except Exception as e:
            logger.warning(f"インデックス作成中にエラーが発生しました（既に存在する可能性があります）: {str(e)}")
        
        # 新しいテーブルを作成
        if "dataset_metadata" not in inspector.get_table_names():
            DatasetMetadata.__table__.create(engine)
            logger.info("dataset_metadata テーブルを作成しました")
            
        if "dataset_shots" not in inspector.get_table_names():
            DatasetShot.__table__.create(engine)
            logger.info("dataset_shots テーブルを作成しました")
        
        logger.info("データベースマイグレーションが完了しました")
        
    except Exception as e:
        logger.error(f"データベースマイグレーション中にエラーが発生しました: {str(e)}")

# データベースの初期化
def init_db():
    """データベースを初期化"""
    create_tables()
    run_migrations()

# モジュールのロード時に自動的に初期化
if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    init_db() 