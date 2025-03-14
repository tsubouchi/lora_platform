import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  HStack,
  Text,
  Heading,
  useToast,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  SliderMark,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Divider,
  Badge,
  Checkbox,
  CheckboxGroup,
  Select,
  Progress,
  Link,
  Card,
  CardBody,
  CardHeader,
  ListItem,
  List,
  ListIcon,
  Tooltip,
  IconButton,
  Flex,
  Spacer,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Switch,
  InputGroup,
  InputRightAddon,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  FormHelperText,
} from '@chakra-ui/react';
import { FiUpload, FiDownload, FiImage, FiSettings, FiCamera, FiSun, FiSmile, FiRotateCw, FiPlus, FiMinus, FiArrowRight, FiInfo, FiRefreshCw, FiChevronRight, FiX, FiCheck } from 'react-icons/fi';
import JobProgressVisualizer from './JobProgressVisualizer';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// データセット生成用デフォルトのパラメータ
const defaultParams = {
  angle_start: 0,
  angle_end: 350,
  angle_step: 10,
  expressions: ['Neutral'],
  lighting: ['Normal'],
  camera_distance: ['Mid'],
};

// 利用可能な表情のリスト
const availableExpressions = [
  'Neutral',
  'Happy',
  'Sad',
  'Angry',
  'Surprised',
  'Relaxed',
  'Worried',
  'Confused',
];

// 利用可能なライティングのリスト
const availableLighting = [
  'Normal',
  'Bright',
  'Dark',
  'Warm',
  'Cool',
  'Side',
  'Dramatic',
  'Soft',
];

// 利用可能なカメラ距離のリスト
const availableCameraDistances = [
  'Close',
  'Mid',
  'Far',
];

// データセット生成コンポーネント
const DatasetGenerator = () => {
  // ファイル選択と状態管理
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState('');
  
  // 計算された値
  const [calculatedInfo, setCalculatedInfo] = useState({
    totalShots: 0,
    estimatedSize: 0,
    estimatedTime: 0
  });
  
  // 設定パラメータ
  const [settings, setSettings] = useState({
    angle: {
      start: 0,
      end: 350,
      step: 10
    },
    expressions: ['Neutral'],
    lighting: ['Normal'],
    camera_distance: ['Mid-shot'],
    use_minimal: false,
    output: {
      resolution: '512x512',
      quality: 90
    }
  });
  
  // ジョブ状態管理
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeJob, setActiveJob] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [pollingTimer, setPollingTimer] = useState(null);
  const [hasError, setHasError] = useState(false);
  const [jobList, setJobList] = useState([]);
  
  const toast = useToast();
  
  // ジョブリストの取得
  const fetchJobList = useCallback(async () => {
    try {
      const response = await fetch('/api/dataset/jobs');
      if (response.ok) {
        const jobs = await response.json();
        setJobList(jobs);
        
        // 処理中または待機中のジョブを設定
        const activeJob = jobs.find(j => j.status === 'processing' || j.status === 'queued');
        if (activeJob && !jobStatus) {
          setActiveJob(activeJob);
          setJobStatus({
            job_id: activeJob.job_id,
            status: activeJob.status,
            progress: activeJob.progress || 0,
            message: activeJob.message || '',
            error_message: activeJob.error_message || ''
          });
          startPolling(activeJob.job_id);
        }
      }
    } catch (error) {
      console.error("ジョブリスト取得エラー:", error);
    }
  }, [jobStatus]);

  // コンポーネント初期化時にジョブリストを取得
  useEffect(() => {
    fetchJobList();
    return () => {
      // コンポーネントのアンマウント時にポーリングを停止
      if (pollingTimer) {
        clearInterval(pollingTimer);
      }
    };
  }, [fetchJobList]);
  
  // 進捗のポーリング開始
  const startPolling = (jobId) => {
    if (pollingTimer) {
      clearInterval(pollingTimer);
    }
    
    const timer = setInterval(() => {
      fetchJobStatus(jobId);
    }, 2000);
    
    setPollingTimer(timer);
  };
  
  // ジョブステータスの取得
  const fetchJobStatus = async (jobId) => {
    try {
      const response = await fetch(`/api/dataset/jobs/${jobId}`);
      if (response.ok) {
        const data = await response.json();
        setJobStatus(data);
        
        // 処理完了またはエラー時にポーリングを停止
        if (data.status === 'completed' || data.status === 'error') {
          if (pollingTimer) {
            clearInterval(pollingTimer);
            setPollingTimer(null);
          }
          
          // 処理完了時の通知
          if (data.status === 'completed') {
            toast({
              title: "データセット生成完了",
              description: "データセットの生成が完了しました。ダウンロードできます。",
              status: "success",
              duration: 5000,
              isClosable: true,
            });
          } 
          // エラー時の通知
          else if (data.status === 'error') {
            setHasError(true);
            toast({
              title: "エラーが発生しました",
              description: data.error_message || "データセット生成中にエラーが発生しました。",
              status: "error",
              duration: 5000,
              isClosable: true,
            });
          }
        }
      }
    } catch (error) {
      console.error("ジョブステータス取得エラー:", error);
    }
  };
  
  // ジョブのリフレッシュ
  const handleRefreshJob = () => {
    if (activeJob) {
      fetchJobStatus(activeJob.job_id);
    }
  };
  
  // データセットのダウンロード
  const handleDownloadDataset = () => {
    if (activeJob && jobStatus && jobStatus.status === 'completed') {
      window.location.href = `/api/dataset/jobs/${activeJob.job_id}/download`;
    }
  };
  
  // ジョブの再試行
  const handleRetryJob = async () => {
    if (!selectedFile) {
      toast({
        title: "ファイルが選択されていません",
        description: "再試行するにはVRMファイルを選択してください。",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setHasError(false);
    await handleGenerateDataset();
  };
  
  // ジョブのキャンセル
  const handleCancelJob = async () => {
    if (activeJob) {
      try {
        const response = await fetch(`/api/dataset/jobs/${activeJob.job_id}/cancel`, {
          method: 'POST'
        });
        
        if (response.ok) {
          toast({
            title: "ジョブをキャンセルしました",
            status: "info",
            duration: 3000,
            isClosable: true,
          });
          
          // ポーリングを停止
          if (pollingTimer) {
            clearInterval(pollingTimer);
            setPollingTimer(null);
          }
          
          // 状態をリセット
          setActiveJob(null);
          setJobStatus(null);
          setHasError(false);
        }
      } catch (error) {
        console.error("ジョブキャンセルエラー:", error);
        toast({
          title: "キャンセルに失敗しました",
          description: error.message || "ジョブのキャンセルに失敗しました。",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    }
  };

  const calculateDatasetSize = useCallback(() => {
    // 角度の計算
    const { start, end, step } = settings.angle;
    const angles = Math.floor((end - start) / step) + 1;
    
    // 表情、ライティング、カメラ距離の数を取得
    const expressionCount = settings.expressions.length;
    const lightingCount = settings.lighting.length;
    const distanceCount = settings.camera_distance.length;
    
    // 総ショット数と推定サイズを計算
    const totalShots = angles * expressionCount * lightingCount * distanceCount;
    const estimatedSizeKB = totalShots * 50; // 1ショットあたり平均50KB
    const estimatedSizeMB = estimatedSizeKB / 1024;
    
    // 推定時間（ショット数 x 0.5秒）
    const estimatedTimeSeconds = totalShots * 0.5;
    const estimatedTimeMinutes = estimatedTimeSeconds / 60;
    
    setCalculatedInfo({
      totalShots,
      estimatedSize: estimatedSizeMB,
      estimatedTime: estimatedTimeMinutes
    });

    // 警告判定（3,000枚以上で警告）
    if (totalShots > 3000) {
      toast({
        title: "大量ショット警告",
        description: `${totalShots}枚のショットは処理に時間がかかります。パラメータを見直すことをお勧めします。`,
        status: "warning",
        duration: 5000,
        isClosable: true,
      });
    }
  }, [settings, toast]);

  // 設定変更時に自動計算
  useEffect(() => {
    calculateDatasetSize();
  }, [settings, calculateDatasetSize]);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) {
      setSelectedFile(null);
      setFileError(null);
      return;
    }
    
    // ファイル検証
    if (!file.name.toLowerCase().endsWith('.vrm')) {
      setFileError('VRM形式のファイルを選択してください');
      setSelectedFile(null);
      return;
    }
    
    if (file.size > 50 * 1024 * 1024) { // 50MB制限
      setFileError('ファイルサイズは50MB以下にしてください');
      setSelectedFile(null);
      return;
    }
    
    setSelectedFile(file);
    setFileError(null);
  };

  const handleSettingChange = (category, field, value) => {
    setSettings(prev => {
      const newSettings = { ...prev };
      
      if (category) {
        newSettings[category] = {
          ...newSettings[category],
          [field]: value
        };
      } else {
        newSettings[field] = value;
      }
      
      return newSettings;
    });
  };

  const handleMultiSelectChange = (field, values) => {
    setSettings(prev => ({
      ...prev,
      [field]: values
    }));
  };

  const handleGenerateDataset = async () => {
    if (!selectedFile) {
      toast({
        title: "ファイルが選択されていません",
        description: "VRMファイルを選択してください",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    // 確認ダイアログ（大量ショットの場合）
    if (calculatedInfo.totalShots > 1000 && !window.confirm(
      `${calculatedInfo.totalShots}枚のスクリーンショットを撮影します。\n生成には約${Math.ceil(calculatedInfo.estimatedTime)}分かかる可能性があります。\n本当に続行しますか？`
    )) {
      return;
    }
    
    setIsSubmitting(true);
    setHasError(false);
    
    try {
      // フォームデータを作成
      const formData = new FormData();
      formData.append('vrm_file', selectedFile);
      
      // useDefaultSettings フラグを設定
      const useDefaultSettings = settings.use_minimal;
      formData.append('use_default_settings', useDefaultSettings);
      
      if (!useDefaultSettings) {
        // カスタム設定をJSONとして追加
        const params = {
          angle_start: settings.angle.start,
          angle_end: settings.angle.end,
          angle_step: settings.angle.step,
          expressions: settings.expressions,
          lighting: settings.lighting,
          camera_distance: settings.camera_distance,
          use_minimal: settings.use_minimal
        };
        formData.append('params', JSON.stringify(params));
      }
      
      // リクエスト送信
      const response = await fetch('/api/dataset/generate', {
        method: 'POST',
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        
        toast({
          title: "データセット生成ジョブを開始しました",
          description: "バックグラウンドで処理が実行されます",
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        
        // アクティブジョブの設定
        setActiveJob({
          job_id: result.job_id,
          status: result.status,
          job_type: 'dataset'
        });
        
        // 初期ステータスの設定
        setJobStatus({
          job_id: result.job_id,
          job_type: 'dataset',
          status: result.status,
          progress: 0,
          message: result.message || 'ジョブがキューに追加されました',
          submission_time: new Date().toISOString()
        });
        
        // ポーリング開始
        startPolling(result.job_id);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || '不明なエラーが発生しました');
      }
    } catch (error) {
      console.error("データセット生成エラー:", error);
      setHasError(true);
      toast({
        title: "データセット生成に失敗しました",
        description: error.message || "不明なエラーが発生しました。",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetParams = () => {
    // デフォルト設定にリセット
    setSettings({
      angle: {
        start: 0,
        end: 350,
        step: 10
      },
      expressions: ['Neutral'],
      lighting: ['Normal'],
      camera_distance: ['Mid-shot'],
      use_minimal: false
    });
    
    // ファイル選択をリセット
    setSelectedFile(null);
    setFileError(null);
    
    // 他の状態をリセット
    setHasError(false);
    
    if (!activeJob || (jobStatus && (jobStatus.status === 'completed' || jobStatus.status === 'error'))) {
      setActiveJob(null);
      setJobStatus(null);
    }
    
    toast({
      title: "設定をリセットしました",
      status: "info",
      duration: 3000,
      isClosable: true,
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // 使用可能な表情、ライティング、カメラ距離の選択肢
  const expressionOptions = ['Neutral', 'Happy', 'Sad', 'Angry', 'Surprised'];
  const lightingOptions = ['Normal', 'Bright', 'Soft', 'Warm', 'Cool', 'Dark'];
  const cameraDistanceOptions = ['Close-up', 'Mid-shot', 'Full-body'];

  return (
    <Box>
      <Heading size="lg" mb={6}>VRMからのデータセット生成</Heading>
      
      {/* 進捗ビジュアライザー */}
      {jobStatus && (
        <Box mb={6}>
          <JobProgressVisualizer 
            jobData={jobStatus}
            onRefresh={handleRefreshJob}
            onDownload={handleDownloadDataset}
            onRetry={handleRetryJob}
            onCancel={handleCancelJob}
          />
        </Box>
      )}
      
      {/* データセット生成フォーム */}
      {(!activeJob || (jobStatus && (jobStatus.status === 'completed' || jobStatus.status === 'error'))) && (
        <Card>
          <CardBody>
            <VStack spacing={6} align="stretch">
              {/* ファイルアップロード */}
              <FormControl isInvalid={fileError}>
                <FormLabel>VRMファイル</FormLabel>
                <Flex>
                  <Input
                    type="file"
                    accept=".vrm"
                    onChange={handleFileChange}
                    py={1}
                    height="auto"
                  />
                  <Button
                    leftIcon={<FiRefreshCw />}
                    ml={2}
                    onClick={() => {
                      document.querySelector('input[type="file"]').value = '';
                      setSelectedFile(null);
                      setFileError(null);
                    }}
                  >
                    クリア
                  </Button>
                </Flex>
                {fileError && <Text color="red.500" fontSize="sm" mt={1}>{fileError}</Text>}
                {selectedFile && (
                  <Text fontSize="sm" mt={1}>
                    {selectedFile.name} ({formatFileSize(selectedFile.size)})
                  </Text>
                )}
              </FormControl>
              
              <Divider />
              
              {/* 撮影設定 */}
              <Box>
                <Heading size="md" mb={3}>撮影パラメータ</Heading>
                
                <FormControl mb={4}>
                  <HStack justify="space-between" mb={2}>
                    <FormLabel mb={0}>最小構成を使用</FormLabel>
                    <Switch
                      isChecked={settings.use_minimal}
                      onChange={(e) => handleSettingChange(null, 'use_minimal', e.target.checked)}
                    />
                  </HStack>
                  <FormHelperText>
                    オンにすると処理時間を短縮できます (Neutral表情、Normal照明のみ)
                  </FormHelperText>
                </FormControl>
                
                {/* 角度設定 */}
                <FormControl mb={4}>
                  <FormLabel>角度設定</FormLabel>
                  <HStack spacing={4}>
                    <Box flex={1}>
                      <Text fontSize="sm">開始角度: {settings.angle.start}°</Text>
                      <Slider
                        min={0}
                        max={359}
                        step={1}
                        value={settings.angle.start}
                        onChange={(val) => handleSettingChange('angle', 'start', val)}
                        isDisabled={settings.use_minimal}
                      >
                        <SliderTrack>
                          <SliderFilledTrack />
                        </SliderTrack>
                        <SliderThumb />
                      </Slider>
                    </Box>
                    <Box flex={1}>
                      <Text fontSize="sm">終了角度: {settings.angle.end}°</Text>
                      <Slider
                        min={0}
                        max={359}
                        step={1}
                        value={settings.angle.end}
                        onChange={(val) => handleSettingChange('angle', 'end', val)}
                        isDisabled={settings.use_minimal}
                      >
                        <SliderTrack>
                          <SliderFilledTrack />
                        </SliderTrack>
                        <SliderThumb />
                      </Slider>
                    </Box>
                    <Box flex={1}>
                      <Text fontSize="sm">角度間隔: {settings.angle.step}°</Text>
                      <Slider
                        min={1}
                        max={90}
                        step={1}
                        value={settings.angle.step}
                        onChange={(val) => handleSettingChange('angle', 'step', val)}
                        isDisabled={settings.use_minimal}
                      >
                        <SliderTrack>
                          <SliderFilledTrack />
                        </SliderTrack>
                        <SliderThumb />
                      </Slider>
                    </Box>
                  </HStack>
                </FormControl>
                
                {/* 表情設定 */}
                <FormControl mb={4} isDisabled={settings.use_minimal}>
                  <FormLabel>表情</FormLabel>
                  <CheckboxGroup
                    value={settings.expressions}
                    onChange={(values) => handleMultiSelectChange('expressions', values)}
                  >
                    <HStack spacing={4} wrap="wrap">
                      {expressionOptions.map(option => (
                        <Checkbox key={option} value={option}>
                          {option}
                        </Checkbox>
                      ))}
                    </HStack>
                  </CheckboxGroup>
                </FormControl>
                
                {/* ライティング設定 */}
                <FormControl mb={4} isDisabled={settings.use_minimal}>
                  <FormLabel>ライティング</FormLabel>
                  <CheckboxGroup
                    value={settings.lighting}
                    onChange={(values) => handleMultiSelectChange('lighting', values)}
                  >
                    <HStack spacing={4} wrap="wrap">
                      {lightingOptions.map(option => (
                        <Checkbox key={option} value={option}>
                          {option}
                        </Checkbox>
                      ))}
                    </HStack>
                  </CheckboxGroup>
                </FormControl>
                
                {/* カメラ距離設定 */}
                <FormControl mb={4} isDisabled={settings.use_minimal}>
                  <FormLabel>カメラ距離</FormLabel>
                  <CheckboxGroup
                    value={settings.camera_distance}
                    onChange={(values) => handleMultiSelectChange('camera_distance', values)}
                  >
                    <HStack spacing={4}>
                      {cameraDistanceOptions.map(option => (
                        <Checkbox key={option} value={option}>
                          {option}
                        </Checkbox>
                      ))}
                    </HStack>
                  </CheckboxGroup>
                </FormControl>
              </Box>
              
              <Divider />
              
              {/* 計算情報 */}
              <Box bg="blue.50" p={4} borderRadius="md">
                <Heading size="sm" mb={2}>生成情報</Heading>
                <HStack spacing={6}>
                  <Box>
                    <Text fontSize="sm">総ショット数</Text>
                    <Text fontSize="lg" fontWeight="bold">{calculatedInfo.totalShots}枚</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm">推定サイズ</Text>
                    <Text fontSize="lg" fontWeight="bold">{calculatedInfo.estimatedSize.toFixed(1)}MB</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm">推定時間</Text>
                    <Text fontSize="lg" fontWeight="bold">{Math.ceil(calculatedInfo.estimatedTime)}分</Text>
                  </Box>
                </HStack>
              </Box>
              
              {/* 警告メッセージ */}
              {calculatedInfo.totalShots > 1000 && (
                <Alert status="warning">
                  <AlertIcon />
                  <Box>
                    <AlertTitle>処理に時間がかかります</AlertTitle>
                    <AlertDescription>
                      {calculatedInfo.totalShots}枚の画像を生成するには約{Math.ceil(calculatedInfo.estimatedTime)}分かかります。
                      必要に応じてパラメータを調整してください。
                    </AlertDescription>
                  </Box>
                </Alert>
              )}
              
              {/* 操作ボタン */}
              <HStack justify="flex-end" spacing={4} mt={4}>
                <Button 
                  variant="outline" 
                  onClick={handleResetParams}
                  leftIcon={<FiX />}
                >
                  リセット
                </Button>
                <Button
                  colorScheme="blue"
                  onClick={handleGenerateDataset}
                  isLoading={isSubmitting}
                  loadingText="送信中..."
                  isDisabled={!selectedFile || fileError || isSubmitting}
                  leftIcon={<FiCheck />}
                >
                  データセット生成
                </Button>
              </HStack>
            </VStack>
          </CardBody>
        </Card>
      )}
    </Box>
  );
};

export default DatasetGenerator;