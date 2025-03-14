import '@/styles/globals.css';
import type { AppProps } from 'next/app';
import { useEffect } from 'react';
import { ChakraProvider, ColorModeScript, extendTheme, ThemeConfig } from '@chakra-ui/react';

// カラーモード設定
const config: ThemeConfig = {
  initialColorMode: 'system',
  useSystemColorMode: true,
};

// テーマを拡張
const theme = extendTheme({ 
  config,
  styles: {
    global: (props: { colorMode: string }) => ({
      body: {
        bg: props.colorMode === 'dark' ? 'gray.900' : 'white',
        color: props.colorMode === 'dark' ? 'white' : 'gray.800',
      },
    }),
  },
  colors: {
    brand: {
      500: '#3182ce', // プライマリーカラー
    },
  },
});

function MyApp({ Component, pageProps }: AppProps) {
  // ダークモード設定を初期化
  useEffect(() => {
    // ローカルストレージからダークモード設定を取得
    const isDarkMode = localStorage.getItem('darkMode') === 'true' || 
      (!('darkMode' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
    
    // HTMLタグにdarkクラスを設定
    document.documentElement.classList.toggle('dark', isDarkMode);
  }, []);

  return (
    <>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      <ChakraProvider theme={theme}>
        <Component {...pageProps} />
      </ChakraProvider>
    </>
  );
}

export default MyApp; 