import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Heading, 
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel,
  Flex,
  Text,
  useColorMode,
  VStack,
  HStack,
  Button,
  Icon,
  Divider,
  SimpleGrid,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
} from '@chakra-ui/react';
import { FiUpload, FiList, FiInfo, FiSettings, FiUser } from 'react-icons/fi';
import Layout from '../components/Layout';
import VRMtoLoRAConverter from '../components/VRMtoLoRAConverter';
import JobDetailsViewer from '../components/JobDetailsViewer';

// ジョブの型定義
interface Job {
  job_id: string;
  status: string;
  submission_time: string;
  progress: number;
  message: string;
}

// ホームページコンポーネント
const HomePage: React.FC = () => {
  // 選択されたタブのインデックス
  const [tabIndex, setTabIndex] = useState<number>(0);
  // ジョブリスト
  const [jobs, setJobs] = useState<Job[]>([]);
  // 選択されたジョブID
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  // ジョブ詳細モーダル
  const { isOpen, onOpen, onClose } = useDisclosure();
  // カラーモード
  const { colorMode } = useColorMode();

  // ジョブリストの取得
  const fetchJobs = async () => {
    try {
      const response = await fetch('/api/jobs');
      
      if (!response.ok) {
        console.error('ジョブリストの取得に失敗しました');
        return;
      }
      
      const data = await response.json();
      setJobs(data);
    } catch (error) {
      console.error('ジョブリスト取得エラー:', error);
    }
  };

  // コンポーネントマウント時にジョブリストを取得
  useEffect(() => {
    fetchJobs();
    
    // 定期的なジョブリストの更新
    const intervalId = setInterval(fetchJobs, 10000);
    
    // クリーンアップ
    return () => clearInterval(intervalId);
  }, []);

  // ジョブ選択時の処理
  const handleJobSelect = (jobId: string) => {
    setSelectedJobId(jobId);
    onOpen();
  };

  // ステータスカラーの取得
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'green.500';
      case 'processing':
        return 'orange.500';
      case 'error':
        return 'red.500';
      case 'queued':
        return 'blue.500';
      default:
        return 'gray.500';
    }
  };

  // タブ変更時の処理
  const handleTabChange = (index: number) => {
    setTabIndex(index);
    
    // ジョブリストタブに切り替わった時、最新のジョブ情報を取得
    if (index === 1) {
      fetchJobs();
    }
  };

  return (
    <Layout>
      <Container maxW="container.xl" py={8}>
        <VStack spacing={6} align="stretch">
          {/* ヘッダー */}
          <Box mb={6}>
            <Heading as="h1" size="xl" mb={2}>VRM to LoRA コンバーター</Heading>
            <Text fontSize="lg" color={colorMode === 'dark' ? 'gray.400' : 'gray.600'}>
              3Dキャラクターモデル（VRM）からLoRAモデルを生成するクラウドサービス
            </Text>
          </Box>
          
          <Divider />
          
          {/* メインコンテンツ */}
          <Tabs 
            variant="enclosed-colored" 
            colorScheme="blue" 
            index={tabIndex} 
            onChange={handleTabChange}
            isFitted
          >
            <TabList>
              <Tab>
                <HStack>
                  <Icon as={FiUpload} />
                  <Text>変換</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <Icon as={FiList} />
                  <Text>ジョブ管理</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <Icon as={FiInfo} />
                  <Text>使い方</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <Icon as={FiSettings} />
                  <Text>設定</Text>
                </HStack>
              </Tab>
            </TabList>
            
            <TabPanels>
              {/* 変換タブ */}
              <TabPanel>
                <VRMtoLoRAConverter />
              </TabPanel>
              
              {/* ジョブ管理タブ */}
              <TabPanel>
                <Box>
                  <Flex justifyContent="space-between" mb={4} alignItems="center">
                    <Heading size="md">ジョブリスト</Heading>
                    <Button size="sm" onClick={fetchJobs} colorScheme="blue">更新</Button>
                  </Flex>
                  
                  {jobs.length === 0 ? (
                    <Box p={6} textAlign="center" bg={colorMode === 'dark' ? 'gray.700' : 'gray.100'} borderRadius="md">
                      <Text>ジョブがありません。「変換」タブからVRMファイルをアップロードしてください。</Text>
                    </Box>
                  ) : (
                    <Box overflowX="auto">
                      <Box as="table" width="100%" borderWidth="1px" borderRadius="md">
                        <Box as="thead" bg={colorMode === 'dark' ? 'gray.700' : 'gray.100'}>
                          <Box as="tr">
                            <Box as="th" px={4} py={2} textAlign="left">ジョブID</Box>
                            <Box as="th" px={4} py={2} textAlign="center">ステータス</Box>
                            <Box as="th" px={4} py={2} textAlign="center">進捗</Box>
                            <Box as="th" px={4} py={2} textAlign="left">開始日時</Box>
                            <Box as="th" px={4} py={2} textAlign="left">操作</Box>
                          </Box>
                        </Box>
                        <Box as="tbody">
                          {jobs.map(job => (
                            <Box 
                              as="tr" 
                              key={job.job_id}
                              _hover={{ bg: colorMode === 'dark' ? 'gray.700' : 'gray.50' }}
                              cursor="pointer"
                              onClick={() => handleJobSelect(job.job_id)}
                            >
                              <Box as="td" px={4} py={2}>{job.job_id.substring(0, 8)}...</Box>
                              <Box as="td" px={4} py={2} textAlign="center">
                                <Text color={getStatusColor(job.status)} fontWeight="bold">
                                  {job.status}
                                </Text>
                              </Box>
                              <Box as="td" px={4} py={2} textAlign="center">
                                {job.progress}%
                              </Box>
                              <Box as="td" px={4} py={2}>{new Date(job.submission_time).toLocaleString('ja-JP')}</Box>
                              <Box as="td" px={4} py={2}>
                                <Button 
                                  size="sm" 
                                  colorScheme="blue" 
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleJobSelect(job.job_id);
                                  }}
                                >
                                  詳細
                                </Button>
                              </Box>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    </Box>
                  )}
                </Box>
              </TabPanel>
              
              {/* 使い方タブ */}
              <TabPanel>
                <Box>
                  <Heading size="md" mb={4}>VRM to LoRA コンバーターの使い方</Heading>
                  
                  <VStack spacing={6} align="stretch">
                    <Box p={6} borderWidth="1px" borderRadius="md">
                      <Heading size="sm" mb={3}>1. VRMファイルの準備</Heading>
                      <Text>
                        変換したいVRMファイルを準備してください。VRMファイルは3Dキャラクターモデルのフォーマットで、
                        VRoidStudioなどのツールで作成できます。
                      </Text>
                    </Box>
                    
                    <Box p={6} borderWidth="1px" borderRadius="md">
                      <Heading size="sm" mb={3}>2. ファイルのアップロード</Heading>
                      <Text>
                        「変換」タブでVRMファイルをアップロードします。ファイルサイズは50MB以内にしてください。
                        アップロード後、変換パラメータを設定できます。
                      </Text>
                    </Box>
                    
                    <Box p={6} borderWidth="1px" borderRadius="md">
                      <Heading size="sm" mb={3}>3. 変換パラメータの設定</Heading>
                      <Text mb={3}>
                        LoRAモデルの品質や特性を決定する各種パラメータを設定します。主なパラメータは以下の通りです：
                      </Text>
                      <VStack align="start" spacing={2} pl={4}>
                        <Text><strong>Rank:</strong> LoRAモデルの次元数（高いほど詳細だが重い）</Text>
                        <Text><strong>Alpha:</strong> スケーリング係数（通常はRankと同等か少し大きい値）</Text>
                        <Text><strong>イテレーション数:</strong> 学習の繰り返し回数（多いほど品質が向上）</Text>
                        <Text><strong>バッチサイズ:</strong> 一度に処理するサンプル数（大きいほど速いがメモリを消費）</Text>
                        <Text><strong>学習率:</strong> 学習の更新幅（小さすぎると遅く、大きすぎると不安定）</Text>
                        <Text><strong>解像度:</strong> 生成画像の解像度（高いほど詳細だが処理が重い）</Text>
                      </VStack>
                    </Box>
                    
                    <Box p={6} borderWidth="1px" borderRadius="md">
                      <Heading size="sm" mb={3}>4. 変換処理の実行</Heading>
                      <Text>
                        「変換開始」ボタンをクリックすると、ファイルがアップロードされ変換処理が開始されます。
                        処理状況は進捗バーとステータスメッセージで確認できます。
                        変換処理は数分から数十分かかる場合があります。
                      </Text>
                    </Box>
                    
                    <Box p={6} borderWidth="1px" borderRadius="md">
                      <Heading size="sm" mb={3}>5. 結果の確認とダウンロード</Heading>
                      <Text>
                        変換が完了すると、「ジョブ管理」タブで詳細を確認できます。
                        生成されたLoRAモデルファイル（.safetensors）、サンプルレンダリング画像、
                        メタデータなどをダウンロードできます。
                      </Text>
                    </Box>
                  </VStack>
                </Box>
              </TabPanel>
              
              {/* 設定タブ */}
              <TabPanel>
                <Box>
                  <Heading size="md" mb={4}>設定</Heading>
                  
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                    <Box p={6} borderWidth="1px" borderRadius="md">
                      <Heading size="sm" mb={3}>アカウント情報</Heading>
                      <HStack>
                        <Icon as={FiUser} boxSize={12} />
                        <VStack align="start" spacing={1}>
                          <Text fontWeight="bold">ゲストユーザー</Text>
                          <Text fontSize="sm" color="gray.500">ログインすると追加機能が利用できます</Text>
                          <Button size="sm" colorScheme="blue" mt={2}>ログイン / 登録</Button>
                        </VStack>
                      </HStack>
                    </Box>
                    
                    <Box p={6} borderWidth="1px" borderRadius="md">
                      <Heading size="sm" mb={3}>使用状況</Heading>
                      <VStack align="start" spacing={2}>
                        <Text>変換回数: 0 / 10</Text>
                        <Text>ストレージ使用量: 0 MB / 1 GB</Text>
                        <Text fontSize="sm" color="gray.500">
                          ゲストユーザーは月10回まで変換可能です。
                          有料プランへのアップグレードで制限が解除されます。
                        </Text>
                        <Button size="sm" colorScheme="green" mt={2}>プランを見る</Button>
                      </VStack>
                    </Box>
                  </SimpleGrid>
                </Box>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </VStack>
        
        {/* ジョブ詳細モーダル */}
        <Modal isOpen={isOpen} onClose={onClose} size="xl">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>ジョブ詳細</ModalHeader>
            <ModalCloseButton />
            <ModalBody pb={6}>
              {selectedJobId && (
                <JobDetailsViewer jobId={selectedJobId} />
              )}
            </ModalBody>
          </ModalContent>
        </Modal>
      </Container>
    </Layout>
  );
};

export default HomePage;