import React from 'react';
import Layout from '@/components/Layout';
import FileUpload from '@/components/FileUpload';

export default function UploadPage() {
  return (
    <Layout 
      title="VRMファイルアップロード | LoRA作成クラウドサービス"
      showHero={false}
    >
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8 text-center">
          VRMファイルをアップロード
        </h1>
        
        <div className="mb-8">
          <p className="text-gray-700 dark:text-gray-300 mb-4 text-center">
            3DアバターのVRMファイルをアップロードして、高品質のLoRAモデルを自動生成します。
          </p>
          <p className="text-gray-700 dark:text-gray-300 mb-4 text-center">
            アップロード後は自動的に処理が開始され、完了すると結果をダウンロードできます。
          </p>
        </div>
        
        <div className="bg-white dark:bg-dark-100 rounded-xl p-8 shadow-lg border border-gray-200 dark:border-gray-800">
          <FileUpload 
            apiUrl="/api/upload"
            onSuccess={(data) => {
              console.log('アップロード成功:', data);
            }}
            onError={(error) => {
              console.error('アップロードエラー:', error);
            }}
          />
        </div>
        
        <div className="mt-12">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            アップロードの注意事項
          </h2>
          <ul className="list-disc pl-5 space-y-2 text-gray-700 dark:text-gray-300">
            <li>対応ファイル形式: VRMファイル (.vrm)</li>
            <li>最大ファイルサイズ: 50MB</li>
            <li>アップロードしたVRMモデルは自動的に処理されます</li>
            <li>処理時間はモデルの複雑さによって異なります（約15〜30分）</li>
            <li>結果はジョブページからダウンロード可能です</li>
          </ul>
        </div>
      </div>
    </Layout>
  );
} 