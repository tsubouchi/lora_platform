# VRM-LoRA プラットフォーム

VRMファイルから3Dアバターの自動処理を行うクラウドプラットフォームで、以下の機能を提供します：

1. **LoRAモデル生成機能** - VRMファイルからAI生成用のLoRAモデルを自動生成
2. **データセット生成機能** - ヘッドレスブラウザによる自動スクリーンショット撮影

## 主な機能

### LoRA生成機能
- VRMファイルのアップロードと自動処理
- カスタム学習パラメータの設定（ランク、アルファ、イテレーション数など）
- 生成されたモデルのダウンロード

### データセット生成機能
- 360度回転スクリーンショットの自動撮影
- 表情、ライティング、カメラ距離などの組み合わせによる多様なデータセット生成
- 結果のZIPファイル形式でのダウンロード
- **環境適応型Chromium管理** - ユーザー環境に最適なChromiumバージョンを自動選択
- **改良されたVRMビューワー** - タイムアウト処理とエラー耐性を強化

### 共通機能
- 非同期ジョブ処理によるバックグラウンド実行
- リアルタイムの進捗状況追跡
- ジョブ管理とステータス表示
- 永続的なジョブ履歴とデータベース管理
- **統一されたファイル管理構造** - ストレージディレクトリの一貫した管理

## 技術スタック

### バックエンド
- **言語**: Python 3.8+
- **Webフレームワーク**: FastAPI
- **データベース**: SQLAlchemy + SQLite
- **非同期処理**: asyncio, BackgroundTasks
- **ヘッドレスブラウザ**: Pyppeteer (Chromiumベース)
- **ファイル処理**: zipfile, Pillow
- **バージョン管理**: 動的Chromiumリビジョン選択

### フロントエンド
- **フレームワーク**: React
- **UIライブラリ**: Chakra UI
- **状態管理**: React Hooks
- **アイコン**: react-icons
- **API通信**: Fetch API

## 開発環境のセットアップ

### 前提条件
- Python 3.8以上
- Node.js 16以上
- Git
- Google Chrome（データセット生成時にはローカル環境のChromeバージョンが参照されます）

### システム全体のセットアップ

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/lora_platform.git
cd lora_platform

# ディレクトリ構造の確認
mkdir -p storage/{uploads,datasets,results,logs,chromium,temp}
```

### バックエンドのセットアップ

```bash
# 仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# 依存パッケージのインストール
cd backend
pip install -r requirements.txt

# Pyppeteerの依存関係をインストール（Linuxの場合）
sudo apt-get update
sudo apt-get install -y gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 \
  libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 \
  libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 \
  libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 \
  libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release \
  xdg-utils wget libgbm-dev
```

### フロントエンドのセットアップ

```bash
# 依存パッケージのインストール
cd frontend
npm install

# Chakra UIと関連パッケージのインストール
npm install @chakra-ui/react @emotion/react @emotion/styled framer-motion react-icons
```

## システムの起動

### 事前準備（重要）

システムを起動する前に、必ず以下の確認と準備を行ってください：

1. **ストレージディレクトリの作成**:
   ```bash
   # プロジェクトルートで実行
   mkdir -p storage/{uploads,datasets,logs,results,temp,chromium}
   ```

2. **依存パッケージのインストール**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **データベースの初期化**:
   ```bash
   cd backend
   python -c "from models.database import Base, engine; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
   ```

### バックエンドの起動

```bash
# 仮想環境が有効化されていることを確認
cd backend

# ⚠️ 非推奨: この方法は相対インポートエラーを引き起こす可能性があります
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# ✅ 推奨: パッケージとして実行
cd lora_platform  # プロジェクトルートディレクトリ
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# または提供されたスクリプトを使用
# cd scripts
# ./run_backend.sh
```

### フロントエンドの起動

```bash
cd frontend

# 開発サーバーの起動
npm run dev

# または提供されたスクリプトを使用
cd ../scripts
./run_frontend.sh
```

### プロセスのクリーンアップ

サーバーを正常に終了できなかった場合、以下のスクリプトを使用してプロセスをクリーンアップできます：

```bash
cd scripts
./clean_processes.sh
```

## 使用方法

### LoRAモデル生成の使用方法

1. ブラウザで http://localhost:3000 にアクセス
2. 「LoRA変換」タブを選択
3. VRMファイルをアップロード
4. 必要に応じてパラメータを調整（ランク、アルファなど）
5. 「変換開始」ボタンをクリック
6. ジョブの進捗状況を確認
7. 処理完了後、生成されたLoRAモデルをダウンロード

### データセット生成の使用方法

1. ブラウザで http://localhost:3000 にアクセス
2. 「データセット生成」タブを選択
3. VRMファイルをアップロード
4. 撮影パラメータを設定：
   - 角度設定（開始角度、終了角度、角度間隔）
   - 表情設定（複数選択可能）
   - ライティング設定（複数選択可能）
   - カメラ距離設定（複数選択可能）
5. 「データセット生成開始」ボタンをクリック
6. 進捗状況を確認
7. 処理完了後、生成されたZIPファイルをダウンロード

#### ミニマルモード
複雑なデータセットを必要としない場合、以下のオプションが利用可能：

- **use_minimal=true** パラメータを指定：シンプルな設定で高速にデータセットを生成します
- 例: `curl -F "file=@maria.vrm" -F "use_minimal=true" http://localhost:8000/dataset/generate`

## プロジェクト構造

```
lora_platform/
├── backend/
│   ├── api/
│   │   ├── dataset.py  - データセット生成API
│   │   ├── health.py   - ヘルスチェックAPI
│   │   └── job.py      - LoRA生成ジョブAPI
│   ├── models/
│   │   └── database.py - データベースモデル
│   ├── services/
│   │   └── job_service.py - ジョブサービス
│   ├── utils/
│   │   └── file_utils.py - ファイル操作ユーティリティ
│   ├── dataset_generator.py - データセット生成モジュール
│   ├── job_processor.py - ジョブ処理モジュール
│   ├── main.py - アプリケーションエントリポイント
│   └── requirements.txt - 依存関係
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DatasetGenerator.jsx - データセット生成UI
│   │   │   ├── JobDetailsViewer.jsx - ジョブ詳細表示
│   │   │   ├── JobProgressTracker.jsx - ジョブ進捗表示
│   │   │   ├── JobProgressVisualizer.jsx - ジョブ進捗可視化
│   │   │   ├── Layout.jsx - レイアウトコンポーネント
│   │   │   └── VRMtoLoRAConverter.jsx - LoRA変換UI
│   │   ├── pages/
│   │   │   └── index.jsx - メインページ
│   │   └── App.js - アプリケーションコンポーネント
│   └── package.json - フロントエンド依存関係
├── scripts/
│   ├── clean_processes.sh - プロセスクリーンアップスクリプト
│   ├── install_chakra_ui.sh - Chakra UI インストールスクリプト
│   └── run_frontend.sh - フロントエンド起動スクリプト
├── storage/ - ファイル保存ディレクトリ
│   ├── chromium/ - Chromiumバージョン管理
│   ├── datasets/ - 生成されたデータセット
│   ├── logs/ - ログファイル
│   ├── results/ - 生成結果
│   ├── temp/ - 一時ファイル
│   │   └── screenshots/ - スクリーンショット一時保存
│   └── uploads/ - アップロードファイル
├── database/ - SQLiteデータベース
│   └── lora_platform.db - メインデータベース
└── README.md - プロジェクト説明
```

## トラブルシューティング

### 一般的な問題

1. **ポートが既に使用されているエラー**：
   ```
   cd scripts
   ./clean_processes.sh
   ```

2. **ヘッドレスブラウザが起動しない**：
   Linuxの場合、必要な依存関係がインストールされているか確認してください。また、`--no-sandbox`オプションが正しく設定されているか確認してください。

3. **ChakraUIコンポーネントが読み込まれない**：
   ```
   cd scripts
   ./install_chakra_ui.sh
   ```

4. **VRMビューワーのタイムアウトエラー**：
   - ファイルパスが正しく設定されているか確認してください
   - ストレージディレクトリ構造が正しく作成されているか確認してください
   - ブラウザがVRMファイルにアクセスできるか確認してください

5. **「table jobs has no column named job_type」エラー**：
   データベースのスキーマが最新でない可能性があります。以下のコマンドでデータベースを再初期化してください：
   ```bash
   cd backend
   python -c "from models.database import Base, engine; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
   ```

## Chromiumバージョン管理システム

本プラットフォームは、異なる環境でもデータセット生成機能が安定して動作するように、環境適応型のChromiumバージョン管理システムを実装しています。

### 主な機能

1. **環境検出** - ユーザーのシステムにインストールされているGoogle Chromeのバージョンを自動検出
2. **互換性マッピング** - 検出されたChromeバージョンに最適なChromiumリビジョンを決定
3. **自動ダウンロード** - 必要なChromiumバージョンを自動でダウンロードして使用
4. **定期更新** - 7日ごとにChromiumバージョンの最適性をチェックし、必要に応じて更新
5. **フォールバック機能** - 問題発生時には安定バージョンにフォールバック

### Chromiumの設定ファイル

Chromiumの設定情報は `storage/chromium/version_info.json` に保存され、以下の情報が含まれます：

```json
{
  "chrome_version": "114.0.5735.133",
  "chromium_revision": "1097615",
  "last_check": "2023-09-01T12:00:00.000000",
  "platform": "darwin"
}
```

この機能により、データセット生成のプロセスがより安定し、異なる環境でも一貫した結果を得ることができます。

## ライセンス

MIT 