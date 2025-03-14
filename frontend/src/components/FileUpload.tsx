import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import DropZone from './DropZone';
import Squares from './Squares';

interface FileUploadProps {
  apiUrl?: string;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  apiUrl = '/api/upload',
  onSuccess,
  onError,
}) => {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);

  // ダークモードの検出
  useEffect(() => {
    const isDark = document.documentElement.classList.contains('dark');
    setIsDarkMode(isDark);
    
    // DOMの監視を設定して、クラスの変更を検出する
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          const isDark = document.documentElement.classList.contains('dark');
          setIsDarkMode(isDark);
        }
      });
    });
    
    observer.observe(document.documentElement, { attributes: true });
    
    return () => observer.disconnect();
  }, []);

  const handleFileUpload = async (files: File[]) => {
    if (files.length === 0) {
      return;
    }

    const file = files[0];
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const response = JSON.parse(xhr.responseText);
          setIsUploading(false);
          if (onSuccess) {
            onSuccess(response);
          } else {
            // デフォルトの挙動: jobIdページへリダイレクト
            router.push(`/jobs/${response.job_id}`);
          }
        } else {
          throw new Error(xhr.statusText || 'アップロード中にエラーが発生しました');
        }
      });

      xhr.addEventListener('error', () => {
        throw new Error('ネットワークエラーが発生しました');
      });

      xhr.addEventListener('abort', () => {
        throw new Error('アップロードがキャンセルされました');
      });

      xhr.open('POST', apiUrl);
      xhr.send(formData);
    } catch (err: any) {
      setIsUploading(false);
      setError(err.message || 'アップロード中にエラーが発生しました');
      if (onError) {
        onError(err);
      }
    }
  };

  return (
    <div className="relative w-full max-w-xl mx-auto">
      {/* 背景のSquaresコンポーネント */}
      <div className="absolute inset-0 -z-10 opacity-30">
        <Squares 
          count={15}
          minSize={20}
          maxSize={60}
          colors={['#6366F1', '#8B5CF6', '#EC4899', '#10B981']}
          isDarkMode={isDarkMode}
        />
      </div>
      
      {/* DropZoneコンポーネント */}
      <div className="relative z-10 p-6 rounded-xl bg-white/90 dark:bg-dark-100/80 backdrop-blur-sm shadow-lg border border-gray-200 dark:border-dark-300">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 text-center">
          VRMファイルをアップロード
        </h2>
        
        <DropZone
          onFileAccepted={handleFileUpload}
          disabled={isUploading}
          className="mb-4"
        />
        
        {isUploading && (
          <div className="mt-4">
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">アップロード中...</span>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{uploadProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-dark-300 rounded-full h-2">
              <div 
                className="bg-primary-500 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}
        
        {error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-md">
            <p>{error}</p>
          </div>
        )}
        
        <p className="mt-4 text-sm text-gray-500 dark:text-gray-400 text-center">
          アップロードが完了すると自動的に処理が開始されます
        </p>
      </div>
    </div>
  );
};

export default FileUpload; 