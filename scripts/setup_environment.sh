#!/bin/bash

# 色の設定
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}LoRA プラットフォーム環境セットアップスクリプト${NC}"
echo "===========================================" 

# プロジェクトルートディレクトリの取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# 仮想環境のパス
VENV_DIR="$PROJECT_ROOT/venv"

# ディレクトリ作成
mkdir -p "$PROJECT_ROOT/storage/uploads"
mkdir -p "$PROJECT_ROOT/storage/results"
mkdir -p "$PROJECT_ROOT/storage/logs"
mkdir -p "$PROJECT_ROOT/storage/temp"
mkdir -p "$PROJECT_ROOT/scripts/lora"

# 既存の仮想環境を確認
if [ -d "$VENV_DIR" ]; then
    echo -e "${BLUE}既存の仮想環境が見つかりました: $VENV_DIR${NC}"
    read -p "既存の仮想環境を削除して再構築しますか？ [y/N]: " REBUILD
    if [[ $REBUILD =~ ^[Yy]$ ]]; then
        echo "既存の仮想環境を削除しています..."
        rm -rf "$VENV_DIR"
    else
        echo "既存の仮想環境を使用します。"
    fi
fi

# 仮想環境の作成（存在しない場合）
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}Python仮想環境を作成しています...${NC}"
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}仮想環境の作成に失敗しました。Python 3がインストールされていることを確認してください。${NC}"
        exit 1
    fi
    echo -e "${GREEN}仮想環境を作成しました: $VENV_DIR${NC}"
fi

# 仮想環境をアクティベート
echo -e "${BLUE}仮想環境をアクティベートしています...${NC}"
source "$VENV_DIR/bin/activate"

# Pipをアップグレード
echo -e "${BLUE}pipをアップグレードしています...${NC}"
pip install --upgrade pip

# バックエンドの依存関係をインストール
echo -e "${BLUE}バックエンドの依存関係をインストールしています...${NC}"
pip install -r "$PROJECT_ROOT/backend/requirements.txt"

echo -e "${GREEN}バックエンドの依存関係のインストールが完了しました！${NC}"

# データベーススキーマの初期化
echo -e "${BLUE}データベースの初期化を行います...${NC}"
# カレントディレクトリをバックエンドに変更
cd "$PROJECT_ROOT/backend"
# SQLiteデータベースのディレクトリ作成
mkdir -p "$PROJECT_ROOT/database"

# Python一行スクリプトで初期化を試みる
python -c "
try:
    from models.database import create_tables
    create_tables()
    print('データベースの初期化に成功しました')
except Exception as e:
    print(f'データベースの初期化中にエラーが発生しました: {str(e)}')
"

echo -e "${BLUE}フロントエンドのセットアップを行います...${NC}"
# フロントエンドのディレクトリに移動
cd "$PROJECT_ROOT/frontend"

# Node.jsの依存関係をインストール
echo -e "${BLUE}Node.jsの依存関係をインストールしています...${NC}"
npm install

echo -e "${GREEN}環境のセットアップが完了しました！${NC}"
echo -e "${BLUE}バックエンドサーバーを起動するには:${NC} ./scripts/run_backend.sh"
echo -e "${BLUE}フロントエンドサーバーを起動するには:${NC} ./scripts/run_frontend.sh"

# 環境変数設定ファイルの作成
cat > "$PROJECT_ROOT/.env" << EOL
# LoRAプラットフォーム環境設定
DATABASE_URL=sqlite:///$PROJECT_ROOT/database/lora_platform.db
STORAGE_DIR=$PROJECT_ROOT/storage
UPLOAD_DIR=$PROJECT_ROOT/storage/uploads
RESULT_DIR=$PROJECT_ROOT/storage/results
LOG_DIR=$PROJECT_ROOT/storage/logs
TEMP_DIR=$PROJECT_ROOT/storage/temp
DEBUG=True
EOL

echo -e "${GREEN}環境変数の設定が完了しました!${NC}"
echo -e "${GREEN}LoRAプラットフォームの環境セットアップが完了しました!${NC}" 