#!/bin/bash
# LoRA作成クラウドサービス セットアップスクリプト

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

# 環境確認
print_blue "環境確認中..."
if ! command -v python &> /dev/null; then
    print_red "Pythonがインストールされていません"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    print_red "Node.js/npmがインストールされていません"
    exit 1
fi

# Pythonのバージョン確認
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
print_green "Python バージョン: $PYTHON_VERSION"

# Node.jsのバージョン確認
NODE_VERSION=$(node --version 2>&1)
print_green "Node.js バージョン: $NODE_VERSION"

# 仮想環境のセットアップ
print_blue "Pythonの仮想環境をセットアップ中..."
python -m venv venv
if [ $? -ne 0 ]; then
    print_red "仮想環境の作成に失敗しました"
    exit 1
fi

# 仮想環境の有効化
source venv/bin/activate
if [ $? -ne 0 ]; then
    print_red "仮想環境の有効化に失敗しました"
    exit 1
fi

# バックエンドの依存パッケージインストール
print_blue "バックエンドの依存パッケージをインストール中..."
pip install -r backend/requirements.txt
if [ $? -ne 0 ]; then
    print_red "バックエンドの依存パッケージインストールに失敗しました"
    exit 1
fi

# データベースの初期化
print_blue "データベースを初期化中..."
cd database && python init_db.py && cd ..
if [ $? -ne 0 ]; then
    print_red "データベースの初期化に失敗しました"
    exit 1
fi

# フロントエンドの依存パッケージインストール
print_blue "フロントエンドの依存パッケージをインストール中..."
cd frontend && npm install && cd ..
if [ $? -ne 0 ]; then
    print_red "フロントエンドの依存パッケージインストールに失敗しました"
    exit 1
fi

# ストレージディレクトリの作成
print_blue "ストレージディレクトリを作成中..."
mkdir -p storage/uploads storage/results storage/logs
if [ $? -ne 0 ]; then
    print_red "ストレージディレクトリの作成に失敗しました"
    exit 1
fi

print_green "セットアップが完了しました！"
print_blue "バックエンドの起動方法:"
print_blue "  source venv/bin/activate"
print_blue "  cd backend"
print_blue "  uvicorn main:app --reload"
print_blue "フロントエンドの起動方法:"
print_blue "  cd frontend"
print_blue "  npm run dev" 