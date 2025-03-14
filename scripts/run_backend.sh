#!/bin/bash
# LoRA作成クラウドサービス バックエンド起動スクリプト

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

# 仮想環境のパス
VENV_DIR="$PROJECT_ROOT/venv"

# デフォルトでは仮想環境チェックを有効
SKIP_VENV=false

# コマンドライン引数のパース
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --no-reload)
        RELOAD=""
        shift
        ;;
        --port=*)
        PORT="${key#*=}"
        shift
        ;;
        --host=*)
        HOST="${key#*=}"
        shift
        ;;
        --skip-venv)
        SKIP_VENV=true
        shift
        ;;
        *)
        shift
        ;;
    esac
done

if [ "$SKIP_VENV" != "true" ]; then
    # 仮想環境の確認
    if [ ! -d "$VENV_DIR" ]; then
        print_red "仮想環境が見つかりません。セットアップスクリプトを実行してください。"
        print_blue "セットアップスクリプトの実行方法: ./scripts/setup_environment.sh"
        exit 1
    fi

    # 仮想環境の有効化
    source "$VENV_DIR/bin/activate"
    if [ $? -ne 0 ]; then
        print_red "仮想環境の有効化に失敗しました"
        exit 1
    fi

    # Python のパスを確認
    PYTHON_PATH=$(which python)
    print_green "Python パス: $PYTHON_PATH"
fi

# バックエンドディレクトリへ移動
cd "$PROJECT_ROOT/backend"

# 起動オプション
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}
RELOAD=${RELOAD:-"--reload"}

print_blue "バックエンドサーバーを起動中... (Ctrl+Cで停止)"
print_blue "API ドキュメント: http://localhost:$PORT/docs"
print_blue "ヘルスチェック: http://localhost:$PORT/health"

# PYTHONPATHを設定して相対インポートの問題を修正
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 既存のmain.pyを修正して相対インポートを絶対インポートに変更
TEMP_FILE=$(mktemp)
cat "$PROJECT_ROOT/backend/main.py" | sed 's/from \. import job_processor/import backend.job_processor as job_processor/g' > "$TEMP_FILE"
mv "$TEMP_FILE" "$PROJECT_ROOT/backend/main.py"

# job_processor.pyも同様に修正
if [ -f "$PROJECT_ROOT/backend/job_processor.py" ]; then
    TEMP_FILE=$(mktemp)
    cat "$PROJECT_ROOT/backend/job_processor.py" | sed 's/from \./from backend/g' > "$TEMP_FILE"
    mv "$TEMP_FILE" "$PROJECT_ROOT/backend/job_processor.py"
fi

# FastAPIサーバーの起動
# システムにuvicornがインストールされていなければpipでインストールする
if ! command -v uvicorn &> /dev/null; then
    print_blue "uvicornをインストールしています..."
    pip install uvicorn fastapi
fi

# FastAPIサーバーの起動（pythonパスを設定して起動）
cd "$PROJECT_ROOT"
uvicorn backend.main:app --host $HOST --port $PORT $RELOAD 