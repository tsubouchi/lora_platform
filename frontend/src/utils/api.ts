import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// モックデータを定義
const MOCK_DATA = {
  jobs: [
    {
      job_id: 'job-123456',
      status: 'completed',
      submission_time: new Date(Date.now() - 3600000).toISOString(),
      error_message: null
    },
    {
      job_id: 'job-234567',
      status: 'processing',
      submission_time: new Date(Date.now() - 7200000).toISOString(),
      error_message: null
    },
    {
      job_id: 'job-345678',
      status: 'queued',
      submission_time: new Date(Date.now() - 10800000).toISOString(),
      error_message: null
    },
    {
      job_id: 'job-456789',
      status: 'error',
      submission_time: new Date(Date.now() - 14400000).toISOString(),
      error_message: 'ファイル形式が無効です'
    }
  ]
};

// API クライアント
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ジョブ関連の API メソッド
export const jobApi = {
  // ジョブ一覧の取得
  getJobs: async (page = 1, limit = 10) => {
    try {
      // モックデータを返す
      return MOCK_DATA.jobs.slice(0, limit);
      
      // バックエンドが準備できたら下記のコードを使用
      // const response = await api.get(`/api/job?skip=${(page - 1) * limit}&limit=${limit}`);
      // return response.data;
    } catch (error) {
      console.error('ジョブ取得エラー:', error);
      return [];
    }
  },

  // 特定のジョブの詳細を取得
  getJobDetails: async (jobId: string) => {
    try {
      // モックデータから該当するジョブを返す
      const job = MOCK_DATA.jobs.find(job => job.job_id === jobId);
      return job || { job_id: jobId, status: 'not_found', submission_time: new Date().toISOString(), error_message: 'ジョブが見つかりません' };
      
      // バックエンドが準備できたら下記のコードを使用
      // const response = await api.get(`/api/job/${jobId}`);
      // return response.data;
    } catch (error) {
      console.error(`ジョブ詳細取得エラー (${jobId}):`, error);
      throw error;
    }
  },
};

// ファイルダウンロード用
export const getFileUrl = (filePath: string) => {
  // ファイルパスをバックエンドのストレージURLに変換
  if (filePath.startsWith('/')) {
    filePath = filePath.substring(1);
  }
  return `/storage/${filePath}`;
};

export default api; 