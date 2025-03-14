import React from 'react';
import Link from 'next/link';
import Head from 'next/head';
import { FiSun, FiMoon, FiGithub } from 'react-icons/fi';
import { Box, Flex, useColorMode, useColorModeValue, Container, IconButton, Text } from '@chakra-ui/react';
import { Squares } from "@/components/ui/squares-background";

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
}

const Layout: React.FC<LayoutProps> = ({
  children,
  title = 'LoRA作成クラウドサービス',
  description = 'VRMファイルから自動でLoRAモデルを生成するクラウドサービス',
}) => {
  const { colorMode, toggleColorMode } = useColorMode();
  
  // カラーモードに応じた色の設定
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const headerBgColor = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.800', 'white');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  return (
    <Box minH="100vh" position="relative">
      {colorMode === 'dark' && (
        <Box position="fixed" top="0" left="0" right="0" bottom="0" zIndex="-1">
          <Squares 
            direction="diagonal"
            speed={0.5}
            squareSize={40}
            borderColor="#333" 
            hoverFillColor="#222"
          />
        </Box>
      )}
      
      <Box minH="100vh" bg={colorMode === 'light' ? bgColor : 'transparent'}>
        <Head>
          <title>{title}</title>
          <meta name="description" content={description} />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <link rel="icon" href="/favicon.ico" />
        </Head>

        {/* ヘッダー */}
        <Box 
          as="header" 
          position="sticky" 
          top={0} 
          zIndex={10} 
          bg={headerBgColor} 
          borderBottomWidth="1px" 
          borderColor={borderColor}
          boxShadow="sm"
        >
          <Container maxW="container.xl" py={2}>
            <Flex justify="space-between" align="center">
              <Flex align="center">
                <Link href="/" style={{ textDecoration: 'none' }}>
                  <Text
                    fontWeight="bold" 
                    fontSize="xl" 
                    color={textColor}
                  >
                    VRM LoRAプラットフォーム
                  </Text>
                </Link>
              </Flex>
              
              <Flex align="center" gap={2}>
                <IconButton
                  aria-label={colorMode === 'light' ? 'ダークモードに切替' : 'ライトモードに切替'}
                  icon={colorMode === 'light' ? <FiMoon /> : <FiSun />}
                  onClick={toggleColorMode}
                  size="sm"
                  variant="ghost"
                />
                
                <IconButton
                  as="a"
                  href="https://github.com/yourusername/lora_platform"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="GitHubリポジトリ"
                  icon={<FiGithub />}
                  size="sm"
                  variant="ghost"
                />
              </Flex>
            </Flex>
          </Container>
        </Box>

        {/* メインコンテンツ */}
        <Box as="main" position="relative" zIndex="1">
          {children}
        </Box>

        {/* フッター */}
        <Box 
          as="footer" 
          py={6} 
          bg={headerBgColor} 
          borderTopWidth="1px" 
          borderColor={borderColor}
          mt={8}
          position="relative"
          zIndex="1"
        >
          <Container maxW="container.xl">
            <Flex 
              direction={{ base: 'column', md: 'row' }} 
              justify="space-between" 
              align={{ base: 'center', md: 'center' }}
              gap={4}
            >
              <Box color={textColor} fontSize="sm">
                © {new Date().getFullYear()} VRM LoRAプラットフォーム
              </Box>
              
              <Flex gap={4} fontSize="sm">
                <Link href="/privacy" style={{ textDecoration: 'none' }}>
                  <Text color={textColor} _hover={{ textDecoration: 'underline' }}>
                    プライバシーポリシー
                  </Text>
                </Link>
                
                <Link href="/terms" style={{ textDecoration: 'none' }}>
                  <Text color={textColor} _hover={{ textDecoration: 'underline' }}>
                    利用規約
                  </Text>
                </Link>
                
                <Link href="/contact" style={{ textDecoration: 'none' }}>
                  <Text color={textColor} _hover={{ textDecoration: 'underline' }}>
                    お問い合わせ
                  </Text>
                </Link>
              </Flex>
            </Flex>
          </Container>
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;
