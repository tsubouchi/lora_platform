#!/bin/bash
# LoRA作成クラウドサービス フロントエンド起動スクリプト

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

# 起動オプション
PORT="3000"
DEV_MODE="--dev"
PROD_MODE=""
CURRENT_MODE=$DEV_MODE
CLEAN_PROCESSES=false

# コマンドライン引数のパース
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --prod)
        CURRENT_MODE=$PROD_MODE
        shift
        ;;
        --port=*)
        PORT="${key#*=}"
        shift
        ;;
        --clean)
        CLEAN_PROCESSES=true
        shift
        ;;
        *)
        shift
        ;;
    esac
done

# ポート3000が使用中かチェック
PORT_IN_USE=$(lsof -i :$PORT -t || echo "")
if [ -n "$PORT_IN_USE" ]; then
    print_red "ポート $PORT はすでに使用されています。"
    print_blue "既存のプロセスをクリーンアップしますか？ [y/N]"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]] || [ "$CLEAN_PROCESSES" = true ]; then
        print_blue "既存のプロセスをクリーンアップしています..."
        # クリーンアップスクリプトの実行
        "$SCRIPT_DIR/clean_processes.sh"
    else
        print_red "別のポートを指定するか、既存のプロセスを終了してください。"
        print_blue "既存のプロセスをクリーンアップするには: ./scripts/clean_processes.sh"
        exit 1
    fi
fi

# フロントエンドディレクトリへの移動
cd "$FRONTEND_DIR" || {
    print_red "フロントエンドディレクトリが見つかりません: $FRONTEND_DIR"
    exit 1
}

# node_modulesの存在確認
if [ ! -d "node_modules" ]; then
    print_red "node_modulesディレクトリが見つかりません。依存関係をインストールします。"
    npm install
    if [ $? -ne 0 ]; then
        print_red "npm installに失敗しました。セットアップスクリプトを実行してください。"
        print_blue "セットアップスクリプトの実行方法: ./scripts/setup_environment.sh"
        exit 1
    fi
fi

# Next.jsの設定ファイルをチェック
if [ ! -f "next.config.js" ]; then
    print_red "next.config.jsが見つかりません。基本設定を作成します。"
    cat > next.config.js << EOL
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: "standalone",
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
EOL
    print_green "next.config.jsを作成しました。"
fi

# _app.jsファイルをチェック
if [ ! -f "pages/_app.js" ] && [ ! -f "pages/_app.tsx" ]; then
    print_red "Next.jsの_appファイルが見つかりません。基本的な_app.jsファイルを作成します。"
    mkdir -p pages
    cat > pages/_app.js << EOL
import '../styles/globals.css';

function MyApp({ Component, pageProps }) {
  return <Component {...pageProps} />;
}

export default MyApp;
EOL
    print_green "_app.jsファイルを作成しました。"
fi

# 開発モードで起動するか本番モードで起動するか
if [ "$CURRENT_MODE" = "$DEV_MODE" ]; then
    print_blue "開発モードでフロントエンドを起動しています... (Ctrl+Cで停止)"
    print_blue "アプリケーションは http://localhost:$PORT で利用可能です"
    
    # 起動コマンドを実行
    npm run dev -- --port $PORT
    
    # エラーがあった場合のフォールバック
    if [ $? -ne 0 ]; then
        print_red "開発サーバーの起動に失敗しました。クリーンな状態で再試行します。"
        "$SCRIPT_DIR/clean_processes.sh"
        # .nextディレクトリをクリーンアップ
        rm -rf .next
        print_blue "再試行中..."
        npm run dev -- --port $PORT
    fi
else
    print_blue "本番モードでフロントエンドを起動しています..."
    print_blue "ビルドを開始します..."
    
    # 既存のビルドをクリーンアップ
    rm -rf .next
    
    # ビルド実行
    npm run build
    if [ $? -ne 0 ]; then
        print_red "ビルドに失敗しました。"
        exit 1
    fi
    
    print_green "ビルドが完了しました。"
    print_blue "アプリケーションは http://localhost:$PORT で利用可能です"
    npm run start -- --port $PORT
fi 