import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUploadCloud, FiFile, FiX } from 'react-icons/fi';

interface FileWithPreview extends File {
  preview?: string;
}

interface DropZoneProps {
  onFileAccepted: (files: File[]) => void;
  maxFiles?: number;
  maxSize?: number;
  accept?: Record<string, string[]>;
  disabled?: boolean;
  className?: string;
}

const DropZone: React.FC<DropZoneProps> = ({
  onFileAccepted,
  maxFiles = 1,
  maxSize = 50 * 1024 * 1024, // 50MB
  accept = {
    'application/octet-stream': ['.vrm'],
  },
  disabled = false,
  className = '',
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      if (rejectedFiles.length > 0) {
        const { code } = rejectedFiles[0].errors[0];
        if (code === 'file-too-large') {
          setError(`ファイルサイズが大きすぎます (最大 ${maxSize / (1024 * 1024)}MB)`);
        } else if (code === 'file-invalid-type') {
          setError('対応していないファイル形式です (.vrm形式のみ対応)');
        } else if (code === 'too-many-files') {
          setError(`一度にアップロードできるファイル数は${maxFiles}個までです`);
        } else {
          setError('ファイルのアップロードに失敗しました');
        }
        return;
      }

      setError(null);
      const newFiles = acceptedFiles.map((file) => 
        Object.assign(file, {
          preview: URL.createObjectURL(file),
        })
      );
      setFiles(newFiles);
      onFileAccepted(newFiles);
    },
    [maxFiles, maxSize, onFileAccepted]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles,
    maxSize,
    accept,
    disabled,
  });

  const removeFile = () => {
    setFiles([]);
    // revokeObjectURLs
    files.forEach((file) => {
      if (file.preview) {
        URL.revokeObjectURL(file.preview);
      }
    });
  };

  return (
    <div className={`w-full ${className}`}>
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          ${
            isDragActive
              ? 'border-primary-500 bg-primary-500/5 dark:border-primary-400 dark:bg-primary-900/20'
              : error
                ? 'border-red-500 bg-red-50 dark:border-red-400 dark:bg-red-900/20'
                : files.length > 0
                  ? 'border-green-500 bg-green-50 dark:border-green-400 dark:bg-green-900/20'
                  : 'border-gray-300 bg-white dark:bg-dark-100 hover:border-primary-500 hover:bg-primary-50 dark:border-gray-600 dark:hover:border-primary-400 dark:hover:bg-primary-900/20'
          }`}
      >
        <input {...getInputProps()} />

        {files.length === 0 ? (
          <div className="space-y-2">
            <FiUploadCloud className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
            <p className="text-gray-600 dark:text-gray-300">
              {isDragActive
                ? 'ファイルをドロップしてください'
                : 'クリックまたはドラッグ&ドロップでファイルをアップロード'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              VRMファイル (.vrm) が対応しています (最大 {maxSize / (1024 * 1024)}MB)
            </p>
          </div>
        ) : (
          files.map((file) => (
            <div key={file.name} className="flex items-center space-x-2">
              <FiFile className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              <span className="flex-1 truncate text-sm text-gray-700 dark:text-gray-300">
                {file.name}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {(file.size / (1024 * 1024)).toFixed(2)} MB
              </span>
            </div>
          ))
        )}

        {error && (
          <p className="mt-2 text-sm font-medium text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>

      {files.length > 0 && (
        <div className="mt-2 flex justify-end">
          <button
            type="button"
            onClick={removeFile}
            className="inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium text-gray-700 hover:text-gray-900 bg-white hover:bg-gray-50 dark:bg-dark-100 dark:text-gray-300 dark:hover:text-white dark:hover:bg-dark-200"
          >
            <FiX className="mr-1 -ml-0.5 h-4 w-4" aria-hidden="true" />
            削除
          </button>
        </div>
      )}
    </div>
  );
};

export default DropZone; 