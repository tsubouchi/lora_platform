import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { FiSun, FiMoon, FiHome, FiList, FiUploadCloud, FiGithub } from 'react-icons/fi';
import Head from 'next/head';
import Header from './Header';
import { Squares } from './ui/squares-background';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  showHero?: boolean; // heroセクションを表示するかどうか
}

const Layout: React.FC<LayoutProps> = ({
  children,
  title = 'LoRA作成クラウドサービス',
  description = 'VRMファイルから自動でLoRAモデルを生成するクラウドサービス',
  showHero = true, // デフォルトではheroセクションを表示
}) => {
  const router = useRouter();
  const [darkMode, setDarkMode] = useState(false);
  
  // ダークモード設定の初期化と変更監視
  useEffect(() => {
    // ローカルストレージまたはシステム設定からダークモード設定を取得
    const isDarkMode = localStorage.getItem('darkMode') === 'true' || 
      (!('darkMode' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
    
    setDarkMode(isDarkMode);
    document.documentElement.classList.toggle('dark', isDarkMode);
    
    // システム設定の変更を監視
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      if (!('darkMode' in localStorage)) {
        setDarkMode(e.matches);
        document.documentElement.classList.toggle('dark', e.matches);
      }
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);
  
  // ダークモード切り替え
  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    document.documentElement.classList.toggle('dark', newDarkMode);
    localStorage.setItem('darkMode', newDarkMode.toString());
  };
  
  // アクティブなナビゲーションリンクのスタイル
  const isActiveLink = (path: string) => {
    return router.pathname === path || 
      (path !== '/' && router.pathname.startsWith(path));
  };
  
  const navLinks = [
    { path: '/', label: 'ホーム', icon: <FiHome className="w-5 h-5" /> },
    { path: '/jobs', label: 'ジョブ一覧', icon: <FiList className="w-5 h-5" /> },
    { path: '/upload', label: 'アップロード', icon: <FiUploadCloud className="w-5 h-5" /> },
  ];

  return (
    <div className={`flex flex-col min-h-screen bg-gray-50 dark:bg-dark-200 text-gray-900 dark:text-white transition-colors duration-200`}>
      <Head>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <header className="bg-white dark:bg-dark-100 shadow-sm sticky top-0 z-50 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="flex items-center">
                <span className="text-xl font-bold bg-gradient-to-r from-primary-500 to-purple-600 bg-clip-text text-transparent">
                  LoRA Platform
                </span>
              </Link>
            </div>
            
            <nav className="hidden md:flex items-center space-x-4">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  href={link.path}
                  className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors
                    ${isActiveLink(link.path) 
                      ? 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20' 
                      : 'text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-gray-100 dark:hover:bg-dark-300'
                    }`}
                >
                  <span className="mr-1.5">{link.icon}</span>
                  {link.label}
                </Link>
              ))}
            </nav>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-full text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-300 focus:outline-none transition-colors"
                aria-label={darkMode ? 'ライトモードに切り替え' : 'ダークモードに切り替え'}
              >
                {darkMode ? (
                  <FiSun className="h-5 w-5" />
                ) : (
                  <FiMoon className="h-5 w-5" />
                )}
              </button>
              
              <a
                href="https://github.com/yourusername/lora-platform"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-full text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-300 focus:outline-none transition-colors"
                aria-label="GitHubリポジトリ"
              >
                <FiGithub className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Heroセクション - showHeroがtrueの場合のみ表示 */}
      {showHero && (
        <div className="relative h-[400px] w-full overflow-hidden">
          <Squares
            direction="diagonal"
            speed={0.5}
            squareSize={40}
            borderColor={darkMode ? "#333" : "#ddd"}
            hoverFillColor={darkMode ? "#222" : "#f0f0f0"}
          />
          <div className="absolute inset-0 flex items-center justify-center z-5">
            <h1 className="text-4xl md:text-5xl font-bold text-white text-center px-4">
              VRMから<span className="text-primary-400">高品質LoRA</span>を自動生成
            </h1>
          </div>
        </div>
      )}

      <main className={`flex-grow ${!showHero ? 'pt-8' : ''}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </div>
      </main>

      <footer className="bg-white dark:bg-dark-100 border-t border-gray-200 dark:border-dark-300 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              &copy; 2025 Bonginkan. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
