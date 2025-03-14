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
  useColorMode,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiServer, FiActivity, FiSettings, FiInfo, FiList, FiImage, FiCamera } from 'react-icons/fi';
import Layout from '../components/Layout';
import VRMtoLoRAConverter from '../components/VRMtoLoRAConverter';
import JobDetailsViewer from '../components/JobDetailsViewer';
import DatasetGenerator from '../components/DatasetGenerator';

// APIのベースURL
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Jobタイプインターフェース
const Job = {
  job_id: '',
  status: '',
  submission_time: '',
  progress: 0,
  message: '',
};

// ホームページコンポーネント
const HomePage = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const [tabIndex, setTabIndex] = useState(0);
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  // テーマカラーの設定
  const bgColor = useColorModeValue('white', 'gray.900');
  const textColor = useColorModeValue('gray.800', 'white');
  const cardBgColor = useColorModeValue('white', 'gray.800');
  const cardBorderColor = useColorModeValue('gray.200', 'gray.700');
  const tabBgColor = useColorModeValue('gray.50', 'gray.800');
  const highlightColor = useColorModeValue('blue.500', 'blue.300');

  // ジョブデータの取得
  const fetchJobs = async () => {
    try {
      // LoRA生成ジョブの取得
      const loraResponse = await fetch(`${API_URL}/jobs`);
      const loraJobs = await loraResponse.json();
      
      // データセット生成ジョブの取得
      const datasetResponse = await fetch(`${API_URL}/dataset/jobs`);
      const datasetJobs = await datasetResponse.json();
      
      // 全ジョブの結合とソート
      const allJobs = [...loraJobs, ...datasetJobs].sort(
        (a, b) => new Date(b.submission_time) - new Date(a.submission_time)
      );
      
      setJobs(allJobs);
    } catch (error) {
      console.error('ジョブデータの取得に失敗しました:', error);
    }
  };

  // 初回レンダリング時とタブ切替時にジョブ情報を更新
  useEffect(() => {
    fetchJobs();
    
    // 定期的な更新の設定
    const intervalId = setInterval(fetchJobs, 5000);
    return () => clearInterval(intervalId);
  }, []);

  // ジョブ選択ハンドラ
  const handleJobSelect = (jobId) => {
    setSelectedJobId(jobId);
    onOpen();
  };

  // タブ変更ハンドラ
  const handleTabChange = (index) => {
    setTabIndex(index);

    // ジョブタブに切り替えた時にジョブリストを更新
    if (index === 2) {
      fetchJobs();
    }
  };

  // ステータスに応じたカラーを取得
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'green.500';
      case 'processing':
        return 'blue.500';
      case 'queued':
        return 'orange.500';
      case 'error':
        return 'red.500';
      default:
        return 'gray.500';
    }
  };

  // ジョブタイプの表示名を取得
  const getJobTypeName = (jobType) => {
    switch (jobType) {
      case 'dataset':
        return 'データセット生成';
      default:
        return 'LoRA生成';
    }
  };

  return (
    <Layout>
      <Container maxW="container.xl" py={8} bg={bgColor} color={textColor}>
        <Heading mb={6} color={textColor}>
          VRM LoRAプラットフォーム
        </Heading>
        
        <Tabs 
          variant="enclosed" 
          colorScheme="blue" 
          index={tabIndex} 
          onChange={handleTabChange}
          bg={bgColor}
          borderColor={cardBorderColor}
          borderRadius="md"
          overflow="hidden"
        >
          <TabList bg={tabBgColor}>
            <Tab _selected={{ color: highlightColor, bg: bgColor, borderBottomColor: bgColor }}>
              <HStack><Icon as={FiServer} /><Text>LoRA変換</Text></HStack>
            </Tab>
            <Tab _selected={{ color: highlightColor, bg: bgColor, borderBottomColor: bgColor }}>
              <HStack><Icon as={FiCamera} /><Text>データセット生成</Text></HStack>
            </Tab>
            <Tab _selected={{ color: highlightColor, bg: bgColor, borderBottomColor: bgColor }}>
              <HStack><Icon as={FiList} /><Text>ジョブ管理</Text></HStack>
            </Tab>
            <Tab _selected={{ color: highlightColor, bg: bgColor, borderBottomColor: bgColor }}>
              <HStack><Icon as={FiInfo} /><Text>使い方</Text></HStack>
            </Tab>
            <Tab _selected={{ color: highlightColor, bg: bgColor, borderBottomColor: bgColor }}>
              <HStack><Icon as={FiSettings} /><Text>設定</Text></HStack>
            </Tab>
          </TabList>

          <TabPanels bg={bgColor}>
            {/* LoRA変換タブ */}
            <TabPanel>
              <VRMtoLoRAConverter />
            </TabPanel>

            {/* データセット生成タブ */}
            <TabPanel>
              <DatasetGenerator />
            </TabPanel>

            {/* ジョブ管理タブ */}
            <TabPanel>
              <VStack align="stretch" spacing={4}>
                <Heading size="md" color={textColor}>ジョブ一覧</Heading>
                <Divider borderColor={cardBorderColor} />
                
                {jobs.length === 0 ? (
                  <Text color={textColor}>ジョブがありません。LoRA変換またはデータセット生成を開始してください。</Text>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                    {jobs.map((job) => (
                      <Box
                        key={job.job_id}
                        p={4}
                        borderWidth="1px"
                        borderRadius="md"
                        shadow="sm"
                        bg={cardBgColor}
                        borderColor={cardBorderColor}
                        _hover={{
                          shadow: 'md',
                          borderColor: highlightColor,
                          cursor: 'pointer',
                        }}
                        onClick={() => handleJobSelect(job.job_id)}
                      >
                        <VStack align="stretch" spacing={2}>
                          <HStack justify="space-between">
                            <Text fontWeight="bold" isTruncated color={textColor}>
                              ジョブID: {job.job_id.substring(0, 8)}...
                            </Text>
                            <Text
                              color={getStatusColor(job.status)}
                              fontWeight="bold"
                              fontSize="sm"
                            >
                              {job.status}
                            </Text>
                          </HStack>
                          
                          <Text fontSize="sm" color={textColor}>
                            タイプ: {getJobTypeName(job.job_type || '')}
                          </Text>
                          
                          <Text fontSize="sm" color={textColor}>
                            提出日時:{' '}
                            {new Date(job.submission_time).toLocaleString()}
                          </Text>
                          
                          {job.progress !== undefined && (
                            <HStack>
                              <Text fontSize="sm" color={textColor}>進捗:</Text>
                              <Box
                                w="100%"
                                h="8px"
                                bg={useColorModeValue('gray.200', 'gray.600')}
                                borderRadius="full"
                              >
                                <Box
                                  h="100%"
                                  w={`${job.progress}%`}
                                  bg={getStatusColor(job.status)}
                                  borderRadius="full"
                                />
                              </Box>
                              <Text fontSize="sm" color={textColor}>{job.progress}%</Text>
                            </HStack>
                          )}
                          
                          <Text fontSize="xs" color={useColorModeValue('gray.500', 'gray.400')} noOfLines={2}>
                            {job.message || 'メッセージなし'}
                          </Text>
                        </VStack>
                      </Box>
                    ))}
                  </SimpleGrid>
                )}
                
                <Button 
                  size="sm" 
                  leftIcon={<Icon as={FiActivity} />} 
                  onClick={fetchJobs}
                  colorScheme="blue"
                >
                  ジョブリストを更新
                </Button>
              </VStack>
            </TabPanel>

            {/* 使い方タブ */}
            <TabPanel>
              <VStack align="stretch" spacing={6}>
                <Heading size="md" color={textColor}>使い方ガイド</Heading>
                <Divider borderColor={cardBorderColor} />
                
                <Box 
                  p={4} 
                  borderWidth="1px" 
                  borderRadius="md" 
                  bg={cardBgColor}
                  borderColor={cardBorderColor}
                >
                  <Heading size="sm" mb={3} color={textColor}>
                    <HStack>
                      <Icon as={FiServer} color={highlightColor} />
                      <Text>LoRA変換</Text>
                    </HStack>
                  </Heading>
                  <Text color={textColor}>
                    「LoRA変換」タブでVRMファイルをアップロードし、変換パラメータを設定してLoRAモデルを生成できます。
                    生成されたモデルはダウンロード可能です。
                  </Text>
                </Box>
                
                <Box 
                  p={4} 
                  borderWidth="1px" 
                  borderRadius="md" 
                  bg={cardBgColor}
                  borderColor={cardBorderColor}
                >
                  <Heading size="sm" mb={3} color={textColor}>
                    <HStack>
                      <Icon as={FiCamera} color={highlightColor} />
                      <Text>データセット生成</Text>
                    </HStack>
                  </Heading>
                  <Text color={textColor}>
                    「データセット生成」タブでVRMファイルをアップロードし、撮影パラメータを設定してデータセットを生成できます。
                    角度、表情、ライティング、カメラ距離などの様々な条件でスクリーンショットが撮影され、ZIPファイルとしてダウンロード可能です。
                  </Text>
                </Box>
                
                <Box 
                  p={4} 
                  borderWidth="1px" 
                  borderRadius="md" 
                  bg={cardBgColor}
                  borderColor={cardBorderColor}
                >
                  <Heading size="sm" mb={3} color={textColor}>
                    <HStack>
                      <Icon as={FiList} color={highlightColor} />
                      <Text>ジョブ管理</Text>
                    </HStack>
                  </Heading>
                  <Text color={textColor}>
                    「ジョブ管理」タブですべての変換ジョブの状態を確認できます。
                    各ジョブをクリックすると詳細情報や結果を表示できます。
                  </Text>
                </Box>
              </VStack>
            </TabPanel>

            {/* 設定タブ */}
            <TabPanel>
              <VStack align="stretch" spacing={6}>
                <Heading size="md" color={textColor}>設定</Heading>
                <Divider borderColor={cardBorderColor} />
                
                <Box 
                  p={4} 
                  borderWidth="1px" 
                  borderRadius="md" 
                  bg={cardBgColor}
                  borderColor={cardBorderColor}
                >
                  <HStack justify="space-between" align="center">
                    <Heading size="sm" color={textColor}>ダークモード</Heading>
                    <Button onClick={toggleColorMode} size="sm" colorScheme="blue">
                      {colorMode === 'light' ? 'ダークモードに切替' : 'ライトモードに切替'}
                    </Button>
                  </HStack>
                </Box>
                
                <Box 
                  p={4} 
                  borderWidth="1px" 
                  borderRadius="md" 
                  bg={cardBgColor}
                  borderColor={cardBorderColor}
                >
                  <Heading size="sm" mb={3} color={textColor}>その他の設定</Heading>
                  <Text color={textColor}>
                    その他の設定オプションはまもなく追加予定です。
                  </Text>
                </Box>
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Container>

      {/* ジョブ詳細モーダル */}
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent bg={cardBgColor} color={textColor}>
          <ModalHeader borderBottomWidth="1px" borderColor={cardBorderColor}>ジョブ詳細</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            {selectedJobId && (
              <JobDetailsViewer jobId={selectedJobId} />
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </Layout>
  );
};

export default HomePage; 