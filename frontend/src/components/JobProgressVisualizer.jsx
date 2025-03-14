import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Progress,
  Flex,
  Badge,
  Divider,
  IconButton,
  Tooltip,
  useColorModeValue,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  List,
  ListItem,
  ListIcon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Button,
  useToast,
  Spinner,
  Card,
  CardBody,
  Stack,
  StackDivider,
} from '@chakra-ui/react';
import {
  FiCheckCircle,
  FiXCircle,
  FiClock,
  FiAlertTriangle,
  FiLoader,
  FiRotateCw,
  FiDownload,
  FiInfo,
  FiArrowRight,
  FiRefreshCw,
} from 'react-icons/fi';

// ジョブタイプ別の処理ステップ定義
const PROCESS_STEPS = {
  lora: [
    { id: 'queued', label: 'ジョブ受付', description: 'VRMファイルとパラメータを受け付けました' },
    { id: 'analyzing', label: 'VRMファイル解析', description: 'モデル情報の抽出と解析' },
    { id: 'processing', label: 'テクスチャ処理', description: 'メッシュとテクスチャの処理' },
    { id: 'generating', label: '学習データ生成', description: '学習データセットの作成' },
    { id: 'training', label: 'LoRAモデル訓練', description: 'モデルの学習と最適化' },
    { id: 'optimizing', label: 'モデル最適化', description: 'モデルの圧縮と最適化' },
    { id: 'completed', label: '生成完了', description: 'LoRAモデル生成が完了しました' },
  ],
  dataset: [
    { id: 'queued', label: 'ジョブ受付', description: 'VRMファイルとパラメータを受け付けました' },
    { id: 'initializing', label: 'ブラウザ初期化', description: 'ヘッドレスブラウザの起動と初期化' },
    { id: 'uploading', label: 'VRMファイルアップロード', description: 'VRMビューアーへのファイル読み込み' },
    { id: 'capturing', label: 'スクリーンショット撮影', description: '各条件でのスクリーンショット撮影' },
    { id: 'processing', label: '画像処理', description: '画像のリサイズと最適化' },
    { id: 'compressing', label: 'ZIPファイル作成', description: 'データセットのパッケージング' },
    { id: 'completed', label: '生成完了', description: 'データセット生成が完了しました' },
  ]
};

// 進捗状況に応じたステップのステータスを決定
const getStepStatus = (stepIndex, currentStepIndex, jobStatus) => {
  if (jobStatus === 'error') {
    return stepIndex === currentStepIndex ? 'error' : 
           stepIndex < currentStepIndex ? 'complete' : 'waiting';
  }
  
  if (stepIndex < currentStepIndex) return 'complete';
  if (stepIndex === currentStepIndex) return 'active';
  return 'waiting';
};

// 進捗メッセージからステップインデックスを推定
const estimateCurrentStep = (message, progress, jobStatus, jobType) => {
  const steps = PROCESS_STEPS[jobType || 'dataset'];
  
  // ステータスによる判定
  if (jobStatus === 'queued') return 0;
  if (jobStatus === 'completed') return steps.length - 1;
  if (jobStatus === 'error') {
    // エラー時は進捗に応じて最も近いステップを推定
    return Math.max(1, Math.min(Math.floor(progress / (100 / (steps.length - 2))), steps.length - 2));
  }
  
  // メッセージの内容からステップを推定
  const messageLower = message.toLowerCase();
  
  if (messageLower.includes('ブラウザ初期化') || messageLower.includes('準備')) return 1;
  if (messageLower.includes('アップロード') || messageLower.includes('vrm')) return 2;
  if (messageLower.includes('スクリーンショット') || messageLower.includes('撮影')) return 3;
  if (messageLower.includes('処理') || messageLower.includes('リサイズ')) return 4;
  if (messageLower.includes('zip') || messageLower.includes('圧縮')) return 5;
  if (messageLower.includes('完了')) return 6;
  
  // 進捗率からの推定（データセット生成の場合）
  if (jobType === 'dataset') {
    if (progress < 5) return 0;
    if (progress < 10) return 1;
    if (progress < 15) return 2;
    if (progress < 90) return 3;
    if (progress < 95) return 4;
    if (progress < 100) return 5;
    return 6;
  }
  
  // 進捗率からの推定（LoRA生成の場合）
  if (progress < 10) return 0;
  if (progress < 20) return 1;
  if (progress < 40) return 2;
  if (progress < 50) return 3;
  if (progress < 90) return 4;
  if (progress < 95) return 5;
  return 6;
};

// 経過時間のフォーマット
const formatElapsedTime = (startTime) => {
  if (!startTime) return '--:--';
  
  const elapsed = Math.floor((Date.now() - new Date(startTime).getTime()) / 1000);
  
  if (elapsed < 60) return `${elapsed}秒`;
  
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  
  if (minutes < 60) return `${minutes}分${seconds}秒`;
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  return `${hours}時間${remainingMinutes}分`;
};

// 残り時間の推定
const estimateRemainingTime = (progress, startTime) => {
  if (!startTime || progress <= 0 || progress >= 100) return null;
  
  const elapsed = (Date.now() - new Date(startTime).getTime()) / 1000;
  const progressPerSecond = progress / elapsed;
  
  if (progressPerSecond <= 0) return null;
  
  const remainingProgress = 100 - progress;
  const remainingSeconds = Math.floor(remainingProgress / progressPerSecond);
  
  if (remainingSeconds < 60) return `${remainingSeconds}秒`;
  
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  
  if (minutes < 60) return `${minutes}分${seconds}秒`;
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  return `${hours}時間${remainingMinutes}分`;
};

// ステップのステータスアイコン
const StatusIcon = ({ status }) => {
  switch (status) {
    case 'complete':
      return <Icon as={FiCheckCircle} color="green.500" />;
    case 'active':
      return <Spinner size="sm" color="blue.500" />;
    case 'error':
      return <Icon as={FiXCircle} color="red.500" />;
    case 'waiting':
    default:
      return <Icon as={FiClock} color="gray.300" />;
  }
};

// ステップの進捗表示
const StepIndicator = ({ step, status, index, isLast }) => {
  const colors = {
    complete: 'green.500',
    active: 'blue.500',
    error: 'red.500',
    waiting: 'gray.300',
  };
  
  const bgColor = useColorModeValue('gray.100', 'gray.700');
  const lineColor = status === 'waiting' ? 'gray.200' : colors[status];
  
  return (
    <Flex direction="column" align="center">
      <Flex
        position="relative"
        direction="column"
        align="center"
        flex={1}
      >
        <Box
          borderRadius="full"
          bg={colors[status]}
          color="white"
          w="36px"
          h="36px"
          display="flex"
          alignItems="center"
          justifyContent="center"
          fontSize="sm"
          fontWeight="bold"
          zIndex={1}
        >
          {status === 'active' ? <Spinner size="sm" /> : index + 1}
        </Box>
        
        {!isLast && (
          <Box
            position="absolute"
            top="18px"
            width="2px"
            height="calc(100% + 12px)"
            bg={lineColor}
            zIndex={0}
          />
        )}
      </Flex>
      
      <VStack mt={2} spacing={0} align="center" w="120px">
        <Text fontSize="sm" fontWeight="bold" textAlign="center">
          {step.label}
        </Text>
        <Text fontSize="xs" color="gray.500" textAlign="center">
          {step.description}
        </Text>
      </VStack>
    </Flex>
  );
};

const JobProgressVisualizer = ({ 
  jobData, 
  refreshInterval = 3000,
  onRefresh = () => {},
  onDownload = () => {},
  onRetry = () => {},
  onCancel = () => {},
  showDetails = true
}) => {
  const [elapsedTime, setElapsedTime] = useState('--:--');
  const [remainingTime, setRemainingTime] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const toast = useToast();
  
  const {
    job_id = '',
    job_type = 'dataset',
    status = 'queued',
    progress = 0,
    message = '',
    submission_time = '',
    start_time = '',
    end_time = '',
    error_message = '',
  } = jobData || {};
  
  // 経過時間の計算
  useEffect(() => {
    if (!submission_time) return;
    
    // 初期化
    setStartTime(submission_time);
    
    // 処理中の場合は経過時間を定期的に更新
    if (status === 'processing' || status === 'queued') {
      const timer = setInterval(() => {
        setElapsedTime(formatElapsedTime(submission_time));
        
        if (status === 'processing' && progress > 0) {
          setRemainingTime(estimateRemainingTime(progress, start_time || submission_time));
        }
      }, 1000);
      
      return () => clearInterval(timer);
    } else {
      // 完了/エラー時は最終の経過時間を表示
      setElapsedTime(formatElapsedTime(submission_time));
      setRemainingTime(null);
    }
  }, [submission_time, status, progress, start_time]);
  
  // 現在のステップを推定
  const currentStepIndex = estimateCurrentStep(message, progress, status, job_type);
  const steps = PROCESS_STEPS[job_type] || PROCESS_STEPS.dataset;
  
  // ステータスに応じた色
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'green';
      case 'processing': return 'blue';
      case 'queued': return 'yellow';
      case 'error': return 'red';
      default: return 'gray';
    }
  };
  
  // ステータスバッジ
  const StatusBadge = ({ status }) => (
    <Badge colorScheme={getStatusColor(status)} fontSize="sm" px={2} py={1} borderRadius="full">
      {status === 'completed' ? '完了' : 
       status === 'processing' ? '処理中' :
       status === 'queued' ? '待機中' :
       status === 'error' ? 'エラー' : status}
    </Badge>
  );
  
  return (
    <Card>
      <CardBody>
        <VStack spacing={4} align="stretch">
          {/* ヘッダー情報 */}
          <Flex justifyContent="space-between" alignItems="center">
            <HStack>
              <Heading size="md">
                {job_type === 'dataset' ? 'データセット生成' : 'LoRAモデル生成'}
              </Heading>
              <StatusBadge status={status} />
            </HStack>
            
            <HStack spacing={2}>
              <Tooltip label="更新">
                <IconButton
                  icon={<FiRefreshCw />}
                  size="sm"
                  aria-label="更新"
                  onClick={onRefresh}
                />
              </Tooltip>
              
              {status === 'completed' && (
                <Tooltip label="ダウンロード">
                  <IconButton
                    icon={<FiDownload />}
                    size="sm"
                    colorScheme="green"
                    aria-label="ダウンロード"
                    onClick={onDownload}
                  />
                </Tooltip>
              )}
              
              {status === 'error' && (
                <Tooltip label="再試行">
                  <IconButton
                    icon={<FiRotateCw />}
                    size="sm"
                    colorScheme="blue"
                    aria-label="再試行"
                    onClick={onRetry}
                  />
                </Tooltip>
              )}
              
              {(status === 'queued' || status === 'processing') && (
                <Tooltip label="キャンセル">
                  <IconButton
                    icon={<FiXCircle />}
                    size="sm"
                    colorScheme="red"
                    aria-label="キャンセル"
                    onClick={onCancel}
                  />
                </Tooltip>
              )}
            </HStack>
          </Flex>
          
          {/* 進捗バー */}
          <Box>
            <HStack justify="space-between" mb={1}>
              <Text fontSize="sm" fontWeight="bold">総合進捗: {Math.round(progress)}%</Text>
              <Text fontSize="sm" color="gray.500">ジョブID: {job_id}</Text>
            </HStack>
            <Progress 
              value={progress} 
              colorScheme={getStatusColor(status)}
              size="md"
              borderRadius="full"
              hasStripe={status === 'processing'}
              isAnimated={status === 'processing'}
            />
          </Box>
          
          {/* 時間情報 */}
          <HStack spacing={8} justify="center">
            <Stat size="sm">
              <StatLabel fontSize="xs">経過時間</StatLabel>
              <StatNumber fontSize="md">{elapsedTime}</StatNumber>
            </Stat>
            
            {remainingTime && (
              <Stat size="sm">
                <StatLabel fontSize="xs">推定残り時間</StatLabel>
                <StatNumber fontSize="md">{remainingTime}</StatNumber>
              </Stat>
            )}
            
            <Stat size="sm">
              <StatLabel fontSize="xs">ステータス</StatLabel>
              <StatNumber fontSize="md">{message}</StatNumber>
            </Stat>
          </HStack>
          
          <Divider />
          
          {/* ステップ表示 - 横方向 */}
          <Box overflowX="auto" py={4}>
            <Flex minWidth="max-content" h="200px">
              {steps.map((step, index) => {
                const stepStatus = getStepStatus(index, currentStepIndex, status);
                return (
                  <Flex key={step.id} direction="column" align="center" flex={1} minW="120px">
                    <StepIndicator
                      step={step}
                      status={stepStatus}
                      index={index}
                      isLast={index === steps.length - 1}
                    />
                  </Flex>
                );
              })}
            </Flex>
          </Box>
          
          {/* エラーメッセージ */}
          {status === 'error' && error_message && (
            <Box bg="red.50" p={3} borderRadius="md" borderLeft="4px solid" borderColor="red.500">
              <HStack>
                <Icon as={FiAlertTriangle} color="red.500" />
                <Text fontWeight="bold" color="red.500">エラーが発生しました</Text>
              </HStack>
              <Text fontSize="sm" mt={1}>{error_message}</Text>
            </Box>
          )}
          
          {/* 詳細情報 */}
          {showDetails && (
            <Accordion allowToggle>
              <AccordionItem>
                <h2>
                  <AccordionButton>
                    <Box flex="1" textAlign="left">
                      詳細情報
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                </h2>
                <AccordionPanel pb={4}>
                  <Stack divider={<StackDivider />} spacing={4}>
                    <Box>
                      <Text fontWeight="bold" fontSize="sm">ジョブ情報</Text>
                      <List spacing={2} mt={2}>
                        <ListItem fontSize="xs">
                          <Text><strong>ジョブID:</strong> {job_id}</Text>
                        </ListItem>
                        <ListItem fontSize="xs">
                          <Text><strong>ジョブタイプ:</strong> {job_type === 'dataset' ? 'データセット生成' : 'LoRAモデル生成'}</Text>
                        </ListItem>
                        <ListItem fontSize="xs">
                          <Text><strong>登録時間:</strong> {new Date(submission_time).toLocaleString()}</Text>
                        </ListItem>
                        {start_time && (
                          <ListItem fontSize="xs">
                            <Text><strong>開始時間:</strong> {new Date(start_time).toLocaleString()}</Text>
                          </ListItem>
                        )}
                        {end_time && (
                          <ListItem fontSize="xs">
                            <Text><strong>終了時間:</strong> {new Date(end_time).toLocaleString()}</Text>
                          </ListItem>
                        )}
                      </List>
                    </Box>
                    
                    <Box>
                      <Text fontWeight="bold" fontSize="sm">現在のステップ</Text>
                      <HStack mt={2}>
                        <StatusIcon status={status === 'error' ? 'error' : 'active'} />
                        <Text fontSize="sm">{steps[currentStepIndex]?.label || 'Unknown'}</Text>
                      </HStack>
                      <Text fontSize="xs" ml={6} color="gray.500">
                        {steps[currentStepIndex]?.description}
                      </Text>
                    </Box>
                  </Stack>
                </AccordionPanel>
              </AccordionItem>
            </Accordion>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

export default JobProgressVisualizer; 