import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  Heading,
  Text,
  Badge,
  Button,
  VStack,
  HStack,
  Divider,
  Flex,
  Link,
  Image,
  Spinner,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Code,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  List,
  ListItem,
  ListIcon,
  Icon,
} from '@chakra-ui/react';
import { FiDownload, FiFile, FiFileText, FiImage, FiCheckCircle, FiAlertCircle, FiClock } from 'react-icons/fi';
import JobProgressTracker from './JobProgressTracker';

// ファイルの型定義
interface JobFile {
  file_id: string;
  file_type: string;
  file_path: string;
  created_at: string;
}

// 評価レポートの型定義
interface EvaluationReport {
  report_id: string;
  evaluation_score: number;
  report_data: any;
  created_at: string;
}

// ジョブの型定義
interface JobDetails {
  job_id: string;
  status: string;
  submission_time: string;
  start_time?: string;
  end_time?: string;
  error_message?: string;
  files: JobFile[];
  report?: EvaluationReport;
}

// コンポーネントのプロパティ
interface JobDetailsViewerProps {
  jobId: string;
  onRefresh?: () => void;
}

// フォーマットされた日時を取得する関数
const formatDateTime = (dateTimeStr: string): string => {
  if (!dateTimeStr) return '-';
  const date = new Date(dateTimeStr);
  return date.toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// ファイルタイプに基づいたアイコンを取得する関数
const getFileIcon = (fileType: string): React.ReactElement => {
  switch (fileType) {
    case 'upload':
      return <Icon as={FiFile} />;
    case 'result':
      return <Icon as={FiImage} />;
    case 'log':
      return <Icon as={FiFileText} />;
    default:
      return <Icon as={FiFile} />;
  }
};

// ステータスアイコンを取得する関数
const getStatusIcon = (status: string): React.ReactElement => {
  switch (status) {
    case 'completed':
      return <ListIcon as={FiCheckCircle} color="green.500" />;
    case 'error':
      return <ListIcon as={FiAlertCircle} color="red.500" />;
    case 'processing':
    case 'queued':
      return <ListIcon as={FiClock} color="blue.500" />;
    default:
      return <ListIcon as={FiFile} color="gray.500" />;
  }
};

// ファイルタイプをラベルに変換する関数
const getFileTypeLabel = (fileType: string): string => {
  switch (fileType) {
    case 'upload':
      return 'アップロードファイル';
    case 'result':
      return '生成結果';
    case 'log':
      return 'ログファイル';
    default:
      return fileType;
  }
};

/**
 * ジョブの詳細情報を表示するコンポーネント
 */
const JobDetailsViewer: React.FC<JobDetailsViewerProps> = ({ jobId, onRefresh }) => {
  // ジョブ詳細の状態
  const [jobDetails, setJobDetails] = useState<JobDetails | null>(null);
  // ローディング状態
  const [loading, setLoading] = useState<boolean>(true);
  // エラー状態
  const [error, setError] = useState<string | null>(null);
  // 選択されたファイル
  const [selectedFile, setSelectedFile] = useState<JobFile | null>(null);
  // ファイルのプレビュー
  const [filePreview, setFilePreview] = useState<string | null>(null);

  // ジョブ詳細の取得
  const fetchJobDetails = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/jobs/${jobId}`);
      if (!response.ok) {
        throw new Error(`APIリクエストエラー: ${response.status}`);
      }
      const data = await response.json();
      setJobDetails(data);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : '不明なエラー');
      setLoading(false);
    }
  };

  // ファイルのプレビュー取得
  const fetchFilePreview = async (file: JobFile) => {
    if (!file) return;

    // 画像ファイルのプレビュー
    if (file.file_path.endsWith('.png') || file.file_path.endsWith('.jpg') || file.file_path.endsWith('.jpeg')) {
      // ファイルパスからURLを作成
      const filePath = file.file_path.replace(/^\/Users\/bongin\/lora_platform\//, '/');
      setFilePreview(filePath);
      return;
    }

    // テキストファイルのプレビュー
    if (file.file_path.endsWith('.txt') || file.file_path.endsWith('.log') || file.file_path.endsWith('.json')) {
      try {
        const response = await fetch(file.file_path);
        if (!response.ok) {
          throw new Error(`ファイル取得エラー: ${response.status}`);
        }
        const text = await response.text();
        setFilePreview(text);
      } catch (err) {
        setFilePreview(`ファイルのプレビューを取得できませんでした: ${err instanceof Error ? err.message : '不明なエラー'}`);
      }
      return;
    }

    // 未対応のファイル形式
    setFilePreview('このファイル形式のプレビューはサポートされていません');
  };

  // コンポーネントのマウント時にジョブ詳細を取得
  useEffect(() => {
    fetchJobDetails();
  }, [jobId]);

  // ファイル選択時のプレビュー取得
  useEffect(() => {
    if (selectedFile) {
      fetchFilePreview(selectedFile);
    } else {
      setFilePreview(null);
    }
  }, [selectedFile]);

  // ローディング中の表示
  if (loading && !jobDetails) {
    return (
      <Flex justifyContent="center" alignItems="center" p={4}>
        <Spinner size="md" mr={2} />
        <Text>ジョブ詳細を取得中...</Text>
      </Flex>
    );
  }

  // エラー時の表示
  if (error) {
    return (
      <Card p={4} bg="red.50" borderColor="red.200" borderWidth={1}>
        <Text color="red.500">エラーが発生しました: {error}</Text>
        <Button mt={2} size="sm" onClick={fetchJobDetails}>再試行</Button>
      </Card>
    );
  }

  // ジョブが見つからない場合
  if (!jobDetails) {
    return (
      <Card p={4} bg="gray.50">
        <Text>ジョブ情報が見つかりません: {jobId}</Text>
        <Button mt={2} size="sm" onClick={fetchJobDetails}>再試行</Button>
      </Card>
    );
  }

  // 結果ファイルの抽出
  const resultFiles = jobDetails.files.filter(file => file.file_type === 'result');
  const uploadFiles = jobDetails.files.filter(file => file.file_type === 'upload');
  const logFiles = jobDetails.files.filter(file => file.file_type === 'log');

  return (
    <Box>
      <Card p={4} mb={4} boxShadow="sm">
        <VStack spacing={4} align="stretch">
          <Flex justifyContent="space-between" alignItems="center">
            <Heading size="md">ジョブ詳細</Heading>
            <Button size="sm" colorScheme="blue" onClick={fetchJobDetails}>更新</Button>
          </Flex>

          <Divider />

          {/* ジョブの基本情報 */}
          <Box>
            <HStack mb={2}>
              <Heading size="sm">ステータス:</Heading>
              <Badge colorScheme={
                jobDetails.status === 'completed' ? 'green' :
                jobDetails.status === 'error' ? 'red' :
                jobDetails.status === 'processing' ? 'orange' : 'blue'
              }>
                {jobDetails.status}
              </Badge>
            </HStack>

            <JobProgressTracker jobId={jobId} />

            <List spacing={2} mt={4}>
              <ListItem>
                {getStatusIcon(jobDetails.status)}
                <Text as="span" fontWeight="bold">ジョブID:</Text> {jobDetails.job_id}
              </ListItem>
              <ListItem>
                {getStatusIcon(jobDetails.status)}
                <Text as="span" fontWeight="bold">提出日時:</Text> {formatDateTime(jobDetails.submission_time)}
              </ListItem>
              {jobDetails.start_time && (
                <ListItem>
                  {getStatusIcon(jobDetails.status)}
                  <Text as="span" fontWeight="bold">開始日時:</Text> {formatDateTime(jobDetails.start_time)}
                </ListItem>
              )}
              {jobDetails.end_time && (
                <ListItem>
                  {getStatusIcon(jobDetails.status)}
                  <Text as="span" fontWeight="bold">完了日時:</Text> {formatDateTime(jobDetails.end_time)}
                </ListItem>
              )}
              {jobDetails.error_message && (
                <ListItem>
                  <ListIcon as={FiAlertCircle} color="red.500" />
                  <Text as="span" fontWeight="bold">エラー:</Text> {jobDetails.error_message}
                </ListItem>
              )}
            </List>
          </Box>

          <Divider />

          {/* ファイルタブと評価レポート */}
          <Tabs variant="enclosed">
            <TabList>
              <Tab>ファイル ({jobDetails.files.length})</Tab>
              {jobDetails.report && <Tab>評価レポート</Tab>}
            </TabList>

            <TabPanels>
              {/* ファイルリスト */}
              <TabPanel>
                <VStack spacing={4} align="stretch">
                  {/* アップロードファイル */}
                  {uploadFiles.length > 0 && (
                    <Accordion allowToggle defaultIndex={[0]}>
                      <AccordionItem>
                        <h2>
                          <AccordionButton>
                            <Box flex="1" textAlign="left">
                              <HStack>
                                <Icon as={FiFile} />
                                <Text fontWeight="bold">アップロードファイル ({uploadFiles.length})</Text>
                              </HStack>
                            </Box>
                            <AccordionIcon />
                          </AccordionButton>
                        </h2>
                        <AccordionPanel pb={4}>
                          <List spacing={2}>
                            {uploadFiles.map(file => (
                              <ListItem key={file.file_id}>
                                <Flex justifyContent="space-between" alignItems="center">
                                  <HStack>
                                    {getFileIcon(file.file_type)}
                                    <Text>{file.file_path.split('/').pop()}</Text>
                                  </HStack>
                                  <Button 
                                    size="xs" 
                                    leftIcon={<FiDownload />} 
                                    onClick={() => window.open(file.file_path, '_blank')}
                                  >
                                    ダウンロード
                                  </Button>
                                </Flex>
                              </ListItem>
                            ))}
                          </List>
                        </AccordionPanel>
                      </AccordionItem>
                    </Accordion>
                  )}

                  {/* 結果ファイル */}
                  {resultFiles.length > 0 && (
                    <Accordion allowToggle defaultIndex={[0]}>
                      <AccordionItem>
                        <h2>
                          <AccordionButton>
                            <Box flex="1" textAlign="left">
                              <HStack>
                                <Icon as={FiImage} />
                                <Text fontWeight="bold">生成結果 ({resultFiles.length})</Text>
                              </HStack>
                            </Box>
                            <AccordionIcon />
                          </AccordionButton>
                        </h2>
                        <AccordionPanel pb={4}>
                          <List spacing={2}>
                            {resultFiles.map(file => (
                              <ListItem key={file.file_id}>
                                <Flex justifyContent="space-between" alignItems="center">
                                  <HStack>
                                    {getFileIcon(file.file_type)}
                                    <Text>{file.file_path.split('/').pop()}</Text>
                                  </HStack>
                                  <HStack>
                                    <Button 
                                      size="xs" 
                                      onClick={() => setSelectedFile(file)}
                                    >
                                      プレビュー
                                    </Button>
                                    <Button 
                                      size="xs" 
                                      leftIcon={<FiDownload />} 
                                      onClick={() => window.open(file.file_path, '_blank')}
                                    >
                                      ダウンロード
                                    </Button>
                                  </HStack>
                                </Flex>
                              </ListItem>
                            ))}
                          </List>
                        </AccordionPanel>
                      </AccordionItem>
                    </Accordion>
                  )}

                  {/* ログファイル */}
                  {logFiles.length > 0 && (
                    <Accordion allowToggle>
                      <AccordionItem>
                        <h2>
                          <AccordionButton>
                            <Box flex="1" textAlign="left">
                              <HStack>
                                <Icon as={FiFileText} />
                                <Text fontWeight="bold">ログファイル ({logFiles.length})</Text>
                              </HStack>
                            </Box>
                            <AccordionIcon />
                          </AccordionButton>
                        </h2>
                        <AccordionPanel pb={4}>
                          <List spacing={2}>
                            {logFiles.map(file => (
                              <ListItem key={file.file_id}>
                                <Flex justifyContent="space-between" alignItems="center">
                                  <HStack>
                                    {getFileIcon(file.file_type)}
                                    <Text>{file.file_path.split('/').pop()}</Text>
                                  </HStack>
                                  <HStack>
                                    <Button 
                                      size="xs" 
                                      onClick={() => setSelectedFile(file)}
                                    >
                                      ログ表示
                                    </Button>
                                    <Button 
                                      size="xs" 
                                      leftIcon={<FiDownload />} 
                                      onClick={() => window.open(file.file_path, '_blank')}
                                    >
                                      ダウンロード
                                    </Button>
                                  </HStack>
                                </Flex>
                              </ListItem>
                            ))}
                          </List>
                        </AccordionPanel>
                      </AccordionItem>
                    </Accordion>
                  )}
                  
                  {/* プレビュー表示エリア */}
                  {selectedFile && (
                    <Box mt={4} p={4} borderWidth={1} borderRadius="md">
                      <Flex justifyContent="space-between" mb={2}>
                        <Heading size="sm">
                          {getFileTypeLabel(selectedFile.file_type)}: {selectedFile.file_path.split('/').pop()}
                        </Heading>
                        <Button 
                          size="xs" 
                          onClick={() => setSelectedFile(null)}
                        >
                          閉じる
                        </Button>
                      </Flex>
                      <Divider mb={4} />
                      
                      {filePreview ? (
                        selectedFile.file_path.match(/\.(jpg|jpeg|png|gif)$/i) ? (
                          <Image src={filePreview} alt="File preview" maxH="500px" mx="auto" />
                        ) : (
                          <Code p={2} borderRadius="md" fontSize="sm" whiteSpace="pre-wrap" maxH="500px" overflow="auto">
                            {filePreview}
                          </Code>
                        )
                      ) : (
                        <Spinner size="sm" />
                      )}
                    </Box>
                  )}
                </VStack>
              </TabPanel>

              {/* 評価レポート */}
              {jobDetails.report && (
                <TabPanel>
                  <VStack spacing={4} align="stretch">
                    <Box p={4} borderWidth={1} borderRadius="md">
                      <Heading size="sm" mb={2}>評価スコア</Heading>
                      <Badge colorScheme={
                        jobDetails.report.evaluation_score >= 0.8 ? 'green' :
                        jobDetails.report.evaluation_score >= 0.6 ? 'yellow' :
                        'red'
                      } fontSize="md" p={2}>
                        {(jobDetails.report.evaluation_score * 100).toFixed(1)}%
                      </Badge>
                    </Box>

                    <Box>
                      <Heading size="sm" mb={2}>レポート詳細</Heading>
                      <Code p={4} borderRadius="md" fontSize="sm" whiteSpace="pre-wrap">
                        {JSON.stringify(jobDetails.report.report_data, null, 2)}
                      </Code>
                    </Box>
                  </VStack>
                </TabPanel>
              )}
            </TabPanels>
          </Tabs>
        </VStack>
      </Card>
    </Box>
  );
};

export default JobDetailsViewer; 