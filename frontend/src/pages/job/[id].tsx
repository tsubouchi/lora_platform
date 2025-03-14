import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '@/components/Layout';
import { jobApi } from '@/utils/api';
import Link from 'next/link';

interface Job {
  job_id: string;
  status: string;
  submission_time: string;
  error_message?: string | null;
}

// ステータスに応じた色とテキストを取得する関数
const getStatusInfo = (status: string) => {
  switch (status) {
    case 'queued':
      return { color: 'bg-yellow-900/20 text-yellow-300 border-yellow-700', text: 'キュー待ち' };
    case 'processing':
      return { color: 'bg-blue-900/20 text-blue-300 border-blue-700', text: '処理中' };
    case 'completed':
      return { color: 'bg-green-900/20 text-green-300 border-green-700', text: '完了' };
    case 'error':
      return { color: 'bg-red-900/20 text-red-300 border-red-700', text: 'エラー' };
    default:
      return { color: 'bg-gray-900/20 text-gray-300 border-gray-700', text: '不明' };
  }
};

export default function JobDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const fetchJobDetails = async () => {
      try {
        setLoading(true);
        const jobDetails = await jobApi.getJobDetails(id as string);
        setJob(jobDetails);
      } catch (err) {
        console.error('ジョブ詳細取得エラー:', err);
        setError('ジョブ情報の取得に失敗しました');
      } finally {
        setLoading(false);
      }
    };

    fetchJobDetails();
  }, [id]);

  if (!id) {
    return (
      <Layout title="ジョブ詳細読み込み中 | LoRA作成クラウドサービス">
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title={`ジョブ詳細: ${id} | LoRA作成クラウドサービス`}>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center mb-4">
          <Link href="/jobs" className="text-primary-400 hover:text-primary-300 flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            ジョブ一覧に戻る
          </Link>
        </div>

        <h1 className="text-2xl font-bold text-white mb-6">ジョブ詳細: {id}</h1>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-900/20 border border-red-800 text-red-300 px-6 py-4 rounded-md">
            {error}
          </div>
        ) : job ? (
          <div className="bg-dark-100 rounded-xl p-6 shadow-lg border border-gray-800">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h2 className="text-lg font-semibold text-white mb-4">基本情報</h2>
                <div className="space-y-3">
                  <div>
                    <span className="text-gray-400">ジョブID:</span>
                    <span className="ml-2 text-white">{job.job_id}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">提出日時:</span>
                    <span className="ml-2 text-white">
                      {new Date(job.submission_time).toLocaleString('ja-JP', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">ステータス:</span>
                    <span className={`ml-2 px-2 py-1 rounded-md text-sm ${getStatusInfo(job.status).color}`}>
                      {getStatusInfo(job.status).text}
                    </span>
                  </div>
                  {job.error_message && (
                    <div>
                      <span className="text-gray-400">エラー:</span>
                      <span className="ml-2 text-red-300">{job.error_message}</span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h2 className="text-lg font-semibold text-white mb-4">アクション</h2>
                <div className="space-y-4">
                  {job.status === 'completed' && (
                    <div>
                      <h3 className="text-sm font-medium text-white mb-2">生成されたファイル</h3>
                      <div className="space-y-2">
                        <button className="btn btn-primary w-full">
                          LoRAモデルをダウンロード
                        </button>
                        <button className="btn btn-secondary w-full">
                          評価レポートを表示
                        </button>
                      </div>
                    </div>
                  )}

                  {job.status === 'error' && (
                    <button className="btn btn-primary w-full">
                      再試行する
                    </button>
                  )}

                  <button className="btn btn-secondary w-full">
                    同じ設定で新規ジョブを開始
                  </button>
                </div>
              </div>
            </div>

            {job.status === 'processing' && (
              <div className="mt-8">
                <h2 className="text-lg font-semibold text-white mb-3">処理の進捗</h2>
                <div className="w-full bg-dark-300 rounded-full h-4">
                  <div
                    className="bg-primary-500 h-4 rounded-full transition-all duration-500"
                    style={{ width: '60%' }}
                  ></div>
                </div>
                <p className="text-center mt-2 text-gray-400">処理中...約60%完了</p>
              </div>
            )}

            <div className="mt-8">
              <h2 className="text-lg font-semibold text-white mb-3">詳細ログ</h2>
              <div className="bg-dark-300 rounded-md p-3 font-mono text-sm text-gray-300 h-64 overflow-auto">
                <p>[{new Date(job.submission_time).toISOString()}] ジョブを受信しました（ID: {job.job_id}）</p>
                <p>[{new Date(job.submission_time).toISOString()}] 処理を開始しています...</p>
                {job.status === 'processing' && (
                  <>
                    <p>[{new Date(Date.now() - 600000).toISOString()}] VRMファイルの解析中...</p>
                    <p>[{new Date(Date.now() - 300000).toISOString()}] モデルのレンダリング中...</p>
                    <p>[{new Date(Date.now() - 120000).toISOString()}] LoRA学習を準備中...</p>
                  </>
                )}
                {job.status === 'completed' && (
                  <>
                    <p>[{new Date(Date.now() - 600000).toISOString()}] VRMファイルの解析が完了しました</p>
                    <p>[{new Date(Date.now() - 400000).toISOString()}] モデルのレンダリングが完了しました</p>
                    <p>[{new Date(Date.now() - 300000).toISOString()}] LoRA学習を開始します</p>
                    <p>[{new Date(Date.now() - 100000).toISOString()}] LoRA学習が完了しました</p>
                    <p>[{new Date(Date.now() - 60000).toISOString()}] 最終的な評価と検証を実施します</p>
                    <p>[{new Date(Date.now() - 30000).toISOString()}] 処理が完了しました</p>
                  </>
                )}
                {job.status === 'error' && (
                  <>
                    <p>[{new Date(Date.now() - 300000).toISOString()}] VRMファイルの解析を開始しました</p>
                    <p>[{new Date(Date.now() - 240000).toISOString()}] エラー: {job.error_message}</p>
                    <p>[{new Date(Date.now() - 230000).toISOString()}] エラーにより処理を中断しました</p>
                  </>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-dark-200 border border-gray-800 text-gray-300 px-6 py-12 rounded-md text-center">
            <p className="text-xl mb-4">ジョブが見つかりません</p>
            <p className="mb-6">指定されたIDのジョブは存在しないか、アクセス権がありません。</p>
            <Link href="/jobs" className="btn btn-primary">
              ジョブ一覧に戻る
            </Link>
          </div>
        )}
      </div>
    </Layout>
  );
} 