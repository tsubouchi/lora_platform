-- LoRA作成クラウドサービス データベーススキーマ

-- Jobsテーブル：ジョブの管理情報
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,  -- UUIDを使用
    status TEXT NOT NULL,     -- "queued", "processing", "completed", "error"
    submission_time TIMESTAMP NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    job_parameters JSON,      -- VRMファイルパラメーターやオプション設定
    error_message TEXT        -- エラー発生時のメッセージ
);

-- Filesテーブル：ファイル管理
CREATE TABLE IF NOT EXISTS files (
    file_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    file_type TEXT NOT NULL,  -- "upload", "result", "log", "report"
    file_path TEXT NOT NULL,  -- ローカルパスまたはCloud Storageのパス
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- EvaluationReportsテーブル：評価レポート
CREATE TABLE IF NOT EXISTS evaluation_reports (
    report_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    evaluation_score REAL,    -- 例：0〜100
    report_data JSON,         -- 評価詳細
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
); 