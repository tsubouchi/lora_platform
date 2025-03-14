import React from 'react';
import Link from 'next/link';

interface JobCardProps {
  jobId: string;
  status: string;
  submissionTime: string;
  errorMessage?: string | null;
}

// ステータスに応じた色とテキストを取得する関数
const getStatusInfo = (status: string) => {
  switch (status) {
    case 'queued':
      return { color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300', text: 'キュー待ち' };
    case 'processing':
      return { color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300', text: '処理中' };
    case 'completed':
      return { color: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300', text: '完了' };
    case 'error':
      return { color: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300', text: 'エラー' };
    default:
      return { color: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300', text: '不明' };
  }
};

const JobCard: React.FC<JobCardProps> = ({ jobId, status, submissionTime, errorMessage }) => {
  const { color, text } = getStatusInfo(status);
  const formattedDate = new Date(submissionTime).toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="card hover:shadow-lg transition-shadow bg-white dark:bg-dark-100 border border-gray-200 dark:border-gray-800">
      <div className="flex justify-between items-start">
        <div>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${color}`}>
            {text}
          </span>
          <h3 className="mt-2 text-lg font-medium text-gray-900 dark:text-white">ジョブID: {jobId}</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">提出日時: {formattedDate}</p>
        </div>
        <Link href={`/job/${jobId}`} className="btn btn-primary">
          詳細を見る
        </Link>
      </div>
      
      {status === 'error' && errorMessage && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 dark:bg-red-900/20 dark:border-red-800 rounded-md">
          <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
        </div>
      )}
    </div>
  );
};

export default JobCard; 