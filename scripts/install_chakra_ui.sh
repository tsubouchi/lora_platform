#!/bin/bash
# Chakra UIと必要な依存関係をインストールするスクリプト

# 色付きの出力用関数
print_green() {
    echo -e "\033[0;32m$1\033[0m"
}

print_blue() {
    echo -e "\033[0;34m$1\033[0m"
}

print_red() {
    echo -e "\033[0;31m$1\033[0m"
}

# 現在のディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# フロントエンドディレクトリへの移動
cd "$FRONTEND_DIR" || {
    print_red "フロントエンドディレクトリが見つかりません: $FRONTEND_DIR"
    exit 1
}

print_blue "Chakra UIと必要な依存関係をインストールしています..."

# Chakra UIの依存関係をインストール
npm install @chakra-ui/react @emotion/react @emotion/styled framer-motion

if [ $? -ne 0 ]; then
    print_red "Chakra UIのインストールに失敗しました。"
    exit 1
fi

print_green "Chakra UIのインストールが完了しました！"

# Chakra UIプロバイダーを追加
if [ -f "pages/_app.js" ]; then
    APP_FILE="pages/_app.js"
elif [ -f "pages/_app.tsx" ]; then
    APP_FILE="pages/_app.tsx"
else 
    print_red "_app.jsまたは_app.tsxが見つかりません。"
    print_blue "新しく_app.jsを作成します。"
    
    mkdir -p pages
    APP_FILE="pages/_app.js"
fi

# _app.jsまたは_app.tsxを更新
print_blue "${APP_FILE}にChakra UIプロバイダーを追加しています..."

TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE" << EOL
import { ChakraProvider } from '@chakra-ui/react';
import '../styles/globals.css';

function MyApp({ Component, pageProps }) {
  return (
    <ChakraProvider>
      <Component {...pageProps} />
    </ChakraProvider>
  );
}

export default MyApp;
EOL

# ファイルの置き換え
mv "$TEMP_FILE" "$APP_FILE"

print_green "Chakra UIプロバイダーの設定が完了しました！"
print_blue "フロントエンドサーバーを再起動して変更を適用してください。" 