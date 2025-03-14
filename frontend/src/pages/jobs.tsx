import React, { useState, useEffect } from 'react';
import Layout from '@/components/Layout';
import JobCard from '@/components/JobCard';
import { jobApi } from '@/utils/api';
import Link from 'next/link';

interface Job {
  job_id: string;
  status: string;
  submission_time: string;
  error_message?: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setLoading(true);
        const fetchedJobs = await jobApi.getJobs(1, 10);
        setJobs(fetchedJobs);
      } catch (err) {
        console.error('ジョブ取得エラー:', err);
        setError('ジョブ情報の取得に失敗しました');
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();
  }, []);

  return (
    <Layout title="ジョブ一覧 | LoRA作成クラウドサービス">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-white">ジョブ一覧</h1>
          <Link href="/upload" className="btn btn-primary">
            新規アップロード
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-900/20 border border-red-800 text-red-300 px-6 py-4 rounded-md">
            {error}
          </div>
        ) : jobs.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {jobs.map((job) => (
              <JobCard
                key={job.job_id}
                jobId={job.job_id}
                status={job.status}
                submissionTime={job.submission_time}
                errorMessage={job.error_message}
              />
            ))}
          </div>
        ) : (
          <div className="bg-dark-200 border border-gray-800 text-gray-300 px-6 py-12 rounded-md text-center">
            <p className="text-xl mb-4">まだジョブがありません</p>
            <p className="mb-6">VRMファイルをアップロードして、LoRAモデルの生成を開始しましょう。</p>
            <Link href="/upload" className="btn btn-primary">
              今すぐアップロード
            </Link>
          </div>
        )}
      </div>
    </Layout>
  );
} 