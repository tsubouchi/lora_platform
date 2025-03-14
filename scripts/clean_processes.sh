#!/bin/bash
# 実行中のプロセスをクリーンアップするスクリプト

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

print_blue "実行中のプロセスをクリーンアップしています..."

# ポート3000を使用しているNext.jsのプロセスを検索
FRONTEND_PIDS=$(lsof -i :3000 -t)
if [ -n "$FRONTEND_PIDS" ]; then
    print_blue "ポート3000で実行中のNext.jsプロセスを終了します: $FRONTEND_PIDS"
    for PID in $FRONTEND_PIDS; do
        echo "プロセスを終了: $PID"
        kill -9 $PID
    done
    print_green "ポート3000が解放されました"
else
    print_blue "ポート3000を使用しているプロセスはありません"
fi

# ポート8000を使用しているバックエンドプロセスを検索
BACKEND_PIDS=$(lsof -i :8000 -t)
if [ -n "$BACKEND_PIDS" ]; then
    print_blue "ポート8000で実行中のバックエンドプロセスを終了します: $BACKEND_PIDS"
    for PID in $BACKEND_PIDS; do
        echo "プロセスを終了: $PID"
        kill -9 $PID
    done
    print_green "ポート8000が解放されました"
else
    print_blue "ポート8000を使用しているプロセスはありません"
fi

# Next.jsのビルドプロセスをクリーンアップ
NODE_PIDS=$(ps aux | grep "next" | grep -v grep | awk '{print $2}')
if [ -n "$NODE_PIDS" ]; then
    print_blue "Next.jsのビルドプロセスを終了します"
    for PID in $NODE_PIDS; do
        echo "Next.jsプロセスを終了: $PID"
        kill -9 $PID
    done
else
    print_blue "実行中のNext.jsビルドプロセスはありません"
fi

# Uvicornプロセスをクリーンアップ
UVICORN_PIDS=$(ps aux | grep "uvicorn" | grep -v grep | awk '{print $2}')
if [ -n "$UVICORN_PIDS" ]; then
    print_blue "Uvicornプロセスを終了します"
    for PID in $UVICORN_PIDS; do
        echo "Uvicornプロセスを終了: $PID"
        kill -9 $PID
    done
else
    print_blue "実行中のUvicornプロセスはありません"
fi

print_green "プロセスのクリーンアップが完了しました！" 