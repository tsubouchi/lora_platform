import React, { useState, useRef } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  FormControl,
  FormLabel,
  Input,
  FormHelperText,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Text,
  Heading,
  Divider,
  Card,
  Select,
  Checkbox,
  Alert,
  AlertIcon,
  Spinner,
  Progress,
  Tooltip,
} from '@chakra-ui/react';
import { FiUpload, FiSettings, FiPlay, FiInfo, FiCheckCircle, FiAlertTriangle } from 'react-icons/fi';
import JobProgressTracker from './JobProgressTracker';

// 変換パラメータの型定義
interface ConversionParams {
  rank: number;
  alpha: number;
  iterations: number;
  batch_size: number;
  learning_rate: number;
  resolution: number;
  use_advanced_features: boolean;
  animation_frames: number;
}

// デフォルト変換パラメータ
const defaultParams: ConversionParams = {
  rank: 16,
  alpha: 32,
  iterations: 1000,
  batch_size: 4,
  learning_rate: 0.0001,
  resolution: 512,
  use_advanced_features: false,
  animation_frames: 0,
};

// VRMからLoRAへの変換コンポーネント
const VRMtoLoRAConverter: React.FC = () => {
  // ファイル選択用のRef
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // 選択されたファイル
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  // 変換パラメータ
  const [params, setParams] = useState<ConversionParams>(defaultParams);
  // アップロード状態
  const [isUploading, setIsUploading] = useState<boolean>(false);
  // ジョブID
  const [jobId, setJobId] = useState<string | null>(null);
  // エラーメッセージ
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // 成功メッセージ
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // ファイル選択ダイアログの表示
  const handleBrowseClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // ファイルが選択された時の処理
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      // VRMファイルのみを許可
      if (file.name.endsWith('.vrm')) {
        setSelectedFile(file);
        setErrorMessage(null);
      } else {
        setErrorMessage('VRMファイル（.vrm）のみがサポートされています。');
        setSelectedFile(null);
      }
    }
  };

  // パラメータの更新
  const updateParam = (paramName: keyof ConversionParams, value: number | boolean) => {
    setParams(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  // 変換処理の開始
  const startConversion = async () => {
    if (!selectedFile) {
      setErrorMessage('VRMファイルを選択してください。');
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      // FormDataの作成
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      // パラメータの追加
      Object.entries(params).forEach(([key, value]) => {
        formData.append(key, value.toString());
      });

      // ファイルのアップロードとジョブの作成
      const response = await fetch('/api/jobs', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`APIエラー: ${response.status}`);
      }

      const data = await response.json();
      setJobId(data.job_id);
      setSuccessMessage('変換ジョブが正常に作成されました。');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : '不明なエラーが発生しました。');
    } finally {
      setIsUploading(false);
    }
  };

  // ジョブが完了した時のコールバック
  const handleJobCompletion = () => {
    setSuccessMessage('変換が完了しました！結果を確認してください。');
  };

  // パラメータのリセット
  const resetParams = () => {
    setParams(defaultParams);
  };

  return (
    <Box>
      <Card p={6} mb={4} boxShadow="md">
        <VStack spacing={6} align="stretch">
          <Heading size="md" mb={2}>VRMからLoRAへの変換</Heading>
          <Text>VRMファイルからLoRAモデルを生成します。ファイルを選択して変換パラメータを設定してください。</Text>
          
          <Divider />
          
          {/* ファイル選択エリア */}
          <Box>
            <Heading size="sm" mb={3}>1. VRMファイルの選択</Heading>
            <HStack>
              <Input
                type="file"
                accept=".vrm"
                onChange={handleFileChange}
                ref={fileInputRef}
                style={{ display: 'none' }}
              />
              <Button 
                leftIcon={<FiUpload />} 
                onClick={handleBrowseClick}
                colorScheme="blue"
                isDisabled={isUploading}
              >
                VRMファイルを選択
              </Button>
              {selectedFile && (
                <Text>選択済み: {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)</Text>
              )}
            </HStack>
          </Box>
          
          <Divider />
          
          {/* パラメータ設定エリア */}
          <Box>
            <Heading size="sm" mb={3}>2. 変換パラメータの設定</Heading>
            <VStack spacing={4} align="stretch">
              {/* Rank設定 */}
              <FormControl>
                <FormLabel>Rank</FormLabel>
                <HStack>
                  <Slider
                    aria-label="rank-slider"
                    min={4}
                    max={128}
                    step={4}
                    value={params.rank}
                    onChange={(val) => updateParam('rank', val)}
                    isDisabled={isUploading}
                    flex="1"
                  >
                    <SliderTrack>
                      <SliderFilledTrack />
                    </SliderTrack>
                    <SliderThumb />
                  </Slider>
                  <NumberInput
                    maxW="100px"
                    min={4}
                    max={128}
                    step={4}
                    value={params.rank}
                    onChange={(_, val) => updateParam('rank', val)}
                    isDisabled={isUploading}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </HStack>
                <FormHelperText>LoRAモデルのランク（次元数）。高いほど詳細な特徴を捉えますが、モデルサイズが大きくなります。</FormHelperText>
              </FormControl>
              
              {/* Alpha設定 */}
              <FormControl>
                <FormLabel>Alpha</FormLabel>
                <HStack>
                  <Slider
                    aria-label="alpha-slider"
                    min={1}
                    max={64}
                    step={1}
                    value={params.alpha}
                    onChange={(val) => updateParam('alpha', val)}
                    isDisabled={isUploading}
                    flex="1"
                  >
                    <SliderTrack>
                      <SliderFilledTrack />
                    </SliderTrack>
                    <SliderThumb />
                  </Slider>
                  <NumberInput
                    maxW="100px"
                    min={1}
                    max={64}
                    step={1}
                    value={params.alpha}
                    onChange={(_, val) => updateParam('alpha', val)}
                    isDisabled={isUploading}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </HStack>
                <FormHelperText>スケーリング係数。通常はRankと同じかやや大きい値を設定します。</FormHelperText>
              </FormControl>
              
              {/* イテレーション設定 */}
              <FormControl>
                <FormLabel>イテレーション数</FormLabel>
                <HStack>
                  <Slider
                    aria-label="iterations-slider"
                    min={100}
                    max={5000}
                    step={100}
                    value={params.iterations}
                    onChange={(val) => updateParam('iterations', val)}
                    isDisabled={isUploading}
                    flex="1"
                  >
                    <SliderTrack>
                      <SliderFilledTrack />
                    </SliderTrack>
                    <SliderThumb />
                  </Slider>
                  <NumberInput
                    maxW="100px"
                    min={100}
                    max={5000}
                    step={100}
                    value={params.iterations}
                    onChange={(_, val) => updateParam('iterations', val)}
                    isDisabled={isUploading}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </HStack>
                <FormHelperText>学習のイテレーション回数。多いほど品質が向上しますが、処理時間が長くなります。</FormHelperText>
              </FormControl>
              
              {/* バッチサイズ設定 */}
              <FormControl>
                <FormLabel>バッチサイズ</FormLabel>
                <Select
                  value={params.batch_size}
                  onChange={(e) => updateParam('batch_size', parseInt(e.target.value))}
                  isDisabled={isUploading}
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={4}>4</option>
                  <option value={8}>8</option>
                  <option value={16}>16</option>
                </Select>
                <FormHelperText>一度に処理するサンプル数。大きいほど処理が速くなりますが、メモリ使用量が増加します。</FormHelperText>
              </FormControl>
              
              {/* 学習率設定 */}
              <FormControl>
                <FormLabel>学習率</FormLabel>
                <HStack>
                  <Slider
                    aria-label="learning-rate-slider"
                    min={0.00001}
                    max={0.001}
                    step={0.00001}
                    value={params.learning_rate}
                    onChange={(val) => updateParam('learning_rate', val)}
                    isDisabled={isUploading}
                    flex="1"
                  >
                    <SliderTrack>
                      <SliderFilledTrack />
                    </SliderTrack>
                    <SliderThumb />
                  </Slider>
                  <NumberInput
                    maxW="100px"
                    min={0.00001}
                    max={0.001}
                    step={0.00001}
                    precision={5}
                    value={params.learning_rate}
                    onChange={(_, val) => updateParam('learning_rate', val)}
                    isDisabled={isUploading}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </HStack>
                <FormHelperText>学習の更新ステップの大きさ。小さすぎると学習が遅く、大きすぎると収束しない可能性があります。</FormHelperText>
              </FormControl>
              
              {/* 解像度設定 */}
              <FormControl>
                <FormLabel>解像度</FormLabel>
                <Select
                  value={params.resolution}
                  onChange={(e) => updateParam('resolution', parseInt(e.target.value))}
                  isDisabled={isUploading}
                >
                  <option value={256}>256 x 256</option>
                  <option value={512}>512 x 512</option>
                  <option value={768}>768 x 768</option>
                  <option value={1024}>1024 x 1024</option>
                </Select>
                <FormHelperText>生成される画像の解像度。高いほど詳細な特徴を捉えますが、処理時間とメモリ使用量が増加します。</FormHelperText>
              </FormControl>
              
              {/* 高度な設定 */}
              <FormControl>
                <Checkbox
                  isChecked={params.use_advanced_features}
                  onChange={(e) => updateParam('use_advanced_features', e.target.checked)}
                  isDisabled={isUploading}
                >
                  高度な特徴を使用する
                </Checkbox>
                <FormHelperText>テクスチャやノーマルマップなどの追加特徴を利用します。処理時間は長くなりますが、品質が向上します。</FormHelperText>
              </FormControl>
              
              {/* アニメーションフレーム数 */}
              {params.use_advanced_features && (
                <FormControl>
                  <FormLabel>アニメーションフレーム数</FormLabel>
                  <HStack>
                    <Slider
                      aria-label="animation-frames-slider"
                      min={0}
                      max={30}
                      step={1}
                      value={params.animation_frames}
                      onChange={(val) => updateParam('animation_frames', val)}
                      isDisabled={isUploading}
                      flex="1"
                    >
                      <SliderTrack>
                        <SliderFilledTrack />
                      </SliderTrack>
                      <SliderThumb />
                    </Slider>
                    <NumberInput
                      maxW="100px"
                      min={0}
                      max={30}
                      step={1}
                      value={params.animation_frames}
                      onChange={(_, val) => updateParam('animation_frames', val)}
                      isDisabled={isUploading}
                    >
                      <NumberInputField />
                      <NumberInputStepper>
                        <NumberIncrementStepper />
                        <NumberDecrementStepper />
                      </NumberInputStepper>
                    </NumberInput>
                  </HStack>
                  <FormHelperText>アニメーション用のポーズを含める場合のフレーム数。0の場合は静的なモデルのみ使用します。</FormHelperText>
                </FormControl>
              )}
              
              {/* パラメータリセットボタン */}
              <Button
                leftIcon={<FiSettings />}
                onClick={resetParams}
                colorScheme="gray"
                size="sm"
                isDisabled={isUploading}
              >
                デフォルト設定に戻す
              </Button>
            </VStack>
          </Box>
          
          <Divider />
          
          {/* 処理実行エリア */}
          <Box>
            <Heading size="sm" mb={3}>3. 変換処理の実行</Heading>
            <VStack spacing={4} align="stretch">
              <Button
                leftIcon={<FiPlay />}
                onClick={startConversion}
                colorScheme="green"
                size="lg"
                isLoading={isUploading}
                loadingText="アップロード中..."
                isDisabled={!selectedFile || isUploading}
              >
                変換開始
              </Button>
              
              {errorMessage && (
                <Alert status="error">
                  <AlertIcon />
                  {errorMessage}
                </Alert>
              )}
              
              {successMessage && (
                <Alert status="success">
                  <AlertIcon />
                  {successMessage}
                </Alert>
              )}
              
              {jobId && (
                <Box mt={4} p={4} borderWidth={1} borderRadius="md">
                  <Heading size="xs" mb={2}>ジョブステータス</Heading>
                  <JobProgressTracker 
                    jobId={jobId} 
                    onComplete={handleJobCompletion}
                    refreshInterval={5000}
                    showDetails
                  />
                </Box>
              )}
            </VStack>
          </Box>
        </VStack>
      </Card>
    </Box>
  );
};

export default VRMtoLoRAConverter; 