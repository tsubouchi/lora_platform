import '@/styles/globals.css';
import type { AppProps } from 'next/app';
import { useEffect } from 'react';

function MyApp({ Component, pageProps }: AppProps) {
  // ダークモード設定を初期化
  useEffect(() => {
    // ローカルストレージからダークモード設定を取得
    const isDarkMode = localStorage.getItem('darkMode') === 'true' || 
      (!('darkMode' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
    
    // HTMLタグにdarkクラスを設定
    document.documentElement.classList.toggle('dark', isDarkMode);
  }, []);

  return <Component {...pageProps} />;
}

export default MyApp; 