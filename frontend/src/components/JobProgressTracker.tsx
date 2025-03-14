import React, { useState, useEffect } from 'react';
import { Progress, Card, Text, Badge, Box, Flex, Heading, VStack, HStack, Spinner } from '@chakra-ui/react';

// ジョブステータスの型定義
type JobStatus = 'queued' | 'processing' | 'completed' | 'error' | 'not_found';

// ジョブ進捗情報の型定義
interface JobProgress {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
}

// コンポーネントのプロパティ
interface JobProgressTrackerProps {
  jobId: string;
  onComplete?: (jobId: string) => void;
  refreshInterval?: number; // ミリ秒単位、デフォルトは2秒
  showDetails?: boolean;
}

// ステータスに応じた色の取得
const getStatusColor = (status: JobStatus): string => {
  switch (status) {
    case 'queued':
      return 'blue';
    case 'processing':
      return 'orange';
    case 'completed':
      return 'green';
    case 'error':
      return 'red';
    case 'not_found':
    default:
      return 'gray';
  }
};

// ステータスに応じたラベルの取得
const getStatusLabel = (status: JobStatus): string => {
  switch (status) {
    case 'queued':
      return '待機中';
    case 'processing':
      return '処理中';
    case 'completed':
      return '完了';
    case 'error':
      return 'エラー';
    case 'not_found':
    default:
      return '不明';
  }
};

/**
 * ジョブの進捗を追跡するコンポーネント
 */
const JobProgressTracker: React.FC<JobProgressTrackerProps> = ({
  jobId,
  onComplete,
  refreshInterval = 2000,
  showDetails = true,
}) => {
  // ジョブ進捗状態
  const [jobProgress, setJobProgress] = useState<JobProgress | null>(null);
  // ローディング状態
  const [loading, setLoading] = useState<boolean>(true);
  // エラー状態
  const [error, setError] = useState<string | null>(null);

  // ジョブ進捗の取得
  const fetchJobProgress = async () => {
    try {
      const response = await fetch(`/api/jobs/${jobId}/status`);
      if (!response.ok) {
        throw new Error(`APIリクエストエラー: ${response.status}`);
      }
      const data = await response.json();
      setJobProgress(data);
      setLoading(false);

      // ジョブが完了またはエラーの場合、コールバックを実行
      if (data.status === 'completed' || data.status === 'error') {
        if (onComplete) {
          onComplete(jobId);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '不明なエラー');
      setLoading(false);
    }
  };

  // 初期ロードとインターバル設定
  useEffect(() => {
    // 初回ロード
    fetchJobProgress();

    // インターバルの設定（ジョブが完了またはエラーでない場合）
    const intervalId = setInterval(() => {
      if (!jobProgress || (jobProgress.status !== 'completed' && jobProgress.status !== 'error')) {
        fetchJobProgress();
      }
    }, refreshInterval);

    // クリーンアップ関数
    return () => {
      clearInterval(intervalId);
    };
  }, [jobId, refreshInterval, jobProgress?.status]);

  // ローディング中の表示
  if (loading && !jobProgress) {
    return (
      <Flex justifyContent="center" alignItems="center" p={4}>
        <Spinner size="md" mr={2} />
        <Text>ジョブ情報を取得中...</Text>
      </Flex>
    );
  }

  // エラー時の表示
  if (error) {
    return (
      <Card p={4} bg="red.50" borderColor="red.200" borderWidth={1}>
        <Text color="red.500">エラーが発生しました: {error}</Text>
      </Card>
    );
  }

  // ジョブが見つからない場合
  if (!jobProgress) {
    return (
      <Card p={4} bg="gray.50">
        <Text>ジョブ情報が見つかりません: {jobId}</Text>
      </Card>
    );
  }

  // 進捗をパーセンテージで表示
  const progressPercent = Math.round(jobProgress.progress * 100);
  const statusColor = getStatusColor(jobProgress.status);
  const statusLabel = getStatusLabel(jobProgress.status);

  // 詳細表示モードか簡易表示モード
  if (showDetails) {
    return (
      <Card p={4} boxShadow="sm" borderRadius="md" borderTopWidth={3} borderTopColor={`${statusColor}.400`}>
        <VStack spacing={3} align="stretch">
          <Flex justify="space-between" alignItems="center">
            <Heading size="sm">ジョブ状況</Heading>
            <Badge colorScheme={statusColor} px={2} py={1} borderRadius="md">
              {statusLabel}
            </Badge>
          </Flex>

          <Box>
            <HStack justifyContent="space-between" mb={1}>
              <Text fontSize="sm">進捗: {progressPercent}%</Text>
              <Text fontSize="sm">{jobProgress.message}</Text>
            </HStack>
            <Progress
              value={progressPercent}
              colorScheme={statusColor}
              size="sm"
              borderRadius="full"
              hasStripe={jobProgress.status === 'processing'}
              isAnimated={jobProgress.status === 'processing'}
            />
          </Box>

          <Text fontSize="xs" color="gray.500">
            ジョブID: {jobProgress.job_id}
          </Text>
        </VStack>
      </Card>
    );
  }

  // 簡易表示モード
  return (
    <Box>
      <HStack justifyContent="space-between" mb={1}>
        <Badge colorScheme={statusColor}>{statusLabel}</Badge>
        <Text fontSize="sm">{progressPercent}%</Text>
      </HStack>
      <Progress
        value={progressPercent}
        colorScheme={statusColor}
        size="sm"
        borderRadius="full"
        hasStripe={jobProgress.status === 'processing'}
        isAnimated={jobProgress.status === 'processing'}
      />
      {jobProgress.message && (
        <Text fontSize="xs" mt={1} color="gray.600">
          {jobProgress.message}
        </Text>
      )}
    </Box>
  );
};

export default JobProgressTracker; 