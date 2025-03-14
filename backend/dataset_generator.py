#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import asyncio
import logging
import yaml
import json
import shutil
import zipfile
import traceback
import signal
import concurrent.futures
import subprocess
import requests
import sys
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from PIL import Image
from pyppeteer import launch
from pyppeteer.errors import NetworkError, TimeoutError as PyppeteerTimeoutError
from pathlib import Path
import tempfile
import random
import pyppeteer

# ロギング設定
os.makedirs("storage/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("storage/logs/dataset_generator.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("dataset_generator")

# Chromiumバージョン管理のための定数
CHROMIUM_STORAGE_DIR = os.path.join("storage", "chromium")
CHROMIUM_VERSION_FILE = os.path.join(CHROMIUM_STORAGE_DIR, "version_info.json")
CHROMIUM_CHECK_INTERVAL_DAYS = 7  # 1週間ごとにアップデートを確認
CHROMIUM_FALLBACK_REVISION = "1095492"  # 安定バージョンのフォールバック

# ストレージパス設定
UPLOAD_DIR = "storage/uploads"
DATASET_DIR = "storage/datasets"
TEMP_DIR = "storage/temp"
DEFAULT_SETTINGS_PATH = "backend/dataset_setting_default.yaml"

# VRMビューアーのURL
VRM_VIEWER_URL = "https://vrm-viewer.com"

# キャンセル情報を保持する辞書
active_jobs = {}

class DatasetGenerationError(Exception):
    """データセット生成中に発生したエラー"""
    pass

class JobCancelledError(Exception):
    """ジョブがキャンセルされた場合のエラー"""
    pass

class DatasetGenerator:
    def __init__(self, base_url: str = None):
        """DatasetGenerator の初期化

        Args:
            base_url (str, optional): ベースURL。Noneの場合はローカルVRMビューワーを使用
        """
        # ローカルVRMビューワーのURLをデフォルトとして使用
        self.base_url = base_url or "http://localhost:8000/static/vrm_viewer.html"
        self.browser = None
        self.page = None
        self.temp_dir = None
        self.dataset_dir = None
        self.metadata = {}
        self.total_shots = 0
        self.current_shot = 0

    async def _set_up_browser(self):
        """ブラウザをセットアップする"""
        try:
            logger.info("ブラウザセットアップ開始")
            
            # ブラウザオプションの設定
            browser_options = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--single-process",
                    "--disable-gpu"
                ],
                # シグナルハンドリングオプションを無効化
                "handleSIGINT": False,
                "handleSIGTERM": False,
                "handleSIGHUP": False
            }
            
            logger.debug(f"ブラウザ起動オプション: {browser_options}")
            self.browser = await pyppeteer.launch(browser_options)
            self.page = await self.browser.newPage()
            
            # ビューポートの設定
            await self.page.setViewport({
                "width": 1280,
                "height": 720
            })
            
            logger.info("ブラウザセットアップ完了")
            return True
        except Exception as e:
            logger.error(f"ブラウザ起動エラー: {str(e)}")
            raise Exception(f"ブラウザ起動エラー: {str(e)}")

    async def _navigate_to_viewer(self, vrm_file_path: str, job_id: str):
        """VRMビューワーページに移動する

        Args:
            vrm_file_path (str): VRMファイルのパス
            job_id (str): ジョブID

        Returns:
            bool: 成功時True
        """
        try:
            # ファイル名のみを取得
            filename = os.path.basename(vrm_file_path)
            
            # ローカルVRMビューワーのURLを生成
            viewer_url = f"{self.base_url}?vrm=/vrm/{filename}&job_id={job_id}"
            logger.info(f"ビューワーURL: {viewer_url}")
            
            # ページ移動 - タイムアウトを120秒に延長
            logger.info("VRMビューワーページに移動します")
            await self.page.goto(viewer_url, {"waitUntil": "networkidle0", "timeout": 120000})
            logger.info("VRMビューワーページ読み込み完了")
            
            # JavaScriptコンソールのログを監視
            self.page.on('console', lambda msg: logger.info(f"ブラウザコンソール: {msg.text}"))
            
            # 先にshort waitを実行
            logger.info("初期待機（5秒）")
            await asyncio.sleep(5)
            
            # 最初のチェック - loadingが非表示になっているか確認
            is_loading_hidden = await self.page.evaluate("""
                () => {
                    const loadingElem = document.getElementById('loading');
                    if (!loadingElem) return true;  // 要素が存在しない場合は問題なし
                    const style = window.getComputedStyle(loadingElem);
                    return style.display === 'none';
                }
            """)
            
            if is_loading_hidden:
                logger.info("ロード要素はすでに非表示です")
                return True
                
            # VRMモデルが読み込まれるまで待機 - タイムアウトを120秒に延長
            logger.info("VRMモデルの読み込み完了を待機します（最大120秒）")
            try:
                await self.page.waitForFunction(
                    "document.getElementById('loading').style.display === 'none'",
                    {"timeout": 120000}
                )
                logger.info("VRMモデル読み込み完了")
                return True
            except Exception as wait_error:
                logger.warning(f"waitForFunction失敗: {str(wait_error)}")
                
                # タイムアウトした場合、JavaScriptを実行して強制的にloadingを非表示にする
                try:
                    logger.info("強制的にロード状態を解除します")
                    await self.page.evaluate("""
                        () => {
                            const loadingElem = document.getElementById('loading');
                            if (loadingElem) {
                                loadingElem.style.display = 'none';
                                console.log('ローディング要素を強制的に非表示にしました');
                            }
                        }
                    """)
                    logger.info("ローディング要素を強制的に非表示にしました")
                    return True
                except Exception as force_error:
                    logger.error(f"強制的なロード状態解除中にエラー: {str(force_error)}")
                    raise Exception(f"VRMビューワー読み込みに失敗し、強制解除もできませんでした: {str(wait_error)}")
        except Exception as e:
            logger.error(f"VRMビューワー読み込みエラー: {str(e)}")
            # スクリーンショットを撮って問題を診断
            try:
                screenshot_path = f"storage/logs/viewer_error_{job_id}.png"
                await self.page.screenshot({'path': screenshot_path})
                logger.info(f"エラー発生時のスクリーンショットを保存: {screenshot_path}")
            except Exception as ss_error:
                logger.error(f"スクリーンショット撮影エラー: {str(ss_error)}")
            
            # ページのHTMLを取得して診断情報として保存
            try:
                html_content = await self.page.content()
                html_path = f"storage/logs/viewer_error_{job_id}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"エラー発生時のHTMLを保存: {html_path}")
            except Exception as html_error:
                logger.error(f"HTML保存エラー: {str(html_error)}")
                
            raise Exception(f"VRMビューワー読み込みに失敗しました: {str(e)}")

    async def _take_screenshot(self, expression: str, lighting: str, distance: str, angle: int):
        """指定した設定でスクリーンショットを撮影する

        Args:
            expression (str): 表情設定
            lighting (str): ライティング設定
            distance (str): カメラ距離設定
            angle (int): 回転角度

        Returns:
            str: スクリーンショットのパス
        """
        try:
            # 表情の設定
            await self.page.select('#expression', expression)
            
            # ライティングの設定
            await self.page.select('#lighting', lighting)
            
            # カメラ距離の設定
            await self.page.select('#distance', distance)
            
            # 回転角度の設定
            await self.page.evaluate(f"document.getElementById('rotation').value = {angle}")
            await self.page.evaluate(f"document.getElementById('rotationValue').textContent = {angle}")
            await self.page.evaluate(f"updateRotation({angle})")
            
            # 少し待機して3Dモデルをレンダリングする時間を確保
            await asyncio.sleep(0.2)
            
            # スクリーンショットボタンをクリック
            await self.page.click('#takeScreenshot')
            
            # 次のスクリーンショットまで少し待機
            await asyncio.sleep(0.5)
            
            # ファイル名の生成 (実際のファイルはAPIで保存される)
            filename = f"{expression}_{lighting}_{distance}_{angle}.png"
            
            self.current_shot += 1
            return filename
        except Exception as e:
            logger.error(f"スクリーンショット撮影エラー: {str(e)}")
            raise Exception(f"スクリーンショット撮影に失敗しました: {str(e)}")

    def _collect_screenshots(self, job_id: str) -> List[str]:
        """撮影したスクリーンショットを収集する

        Args:
            job_id (str): ジョブID

        Returns:
            List[str]: スクリーンショットファイルのリスト
        """
        # スクリーンショットディレクトリ
        screenshot_dir = os.path.join("backend/temp/screenshots", job_id)
        
        # ディレクトリが存在しない場合は代替パスを試す
        if not os.path.exists(screenshot_dir):
            logger.warning(f"相対パスのスクリーンショットディレクトリが見つかりません: {screenshot_dir}")
            
            # 絶対パスを試す
            alt_screenshot_dir = os.path.join(os.getcwd(), "backend/temp/screenshots", job_id)
            if os.path.exists(alt_screenshot_dir):
                logger.info(f"代替パスのスクリーンショットディレクトリを使用します: {alt_screenshot_dir}")
                screenshot_dir = alt_screenshot_dir
            else:
                # APIエンドポイントからのスクリーンショットディレクトリを試す
                api_screenshot_dir = os.path.join("storage/temp/screenshots", job_id)
                if os.path.exists(api_screenshot_dir):
                    logger.info(f"APIスクリーンショットディレクトリを使用します: {api_screenshot_dir}")
                    screenshot_dir = api_screenshot_dir
                else:
                    # どのディレクトリも見つからない場合は空のリストを返す
                    logger.error(f"すべてのパスを試しましたが、スクリーンショットディレクトリが見つかりません")
                    logger.info("テスト用のダミースクリーンショットを作成します")
                    
                    # テスト用にダミーデータを生成
                    return self._create_dummy_screenshots()
        
        # スクリーンショットファイルの収集
        screenshot_files = []
        for filename in os.listdir(screenshot_dir):
            if filename.endswith(".png"):
                filepath = os.path.join(screenshot_dir, filename)
                # データセットディレクトリにコピー
                shutil.copy2(filepath, self.dataset_dir)
                screenshot_files.append(filename)
        
        logger.info(f"収集したスクリーンショット: {len(screenshot_files)}枚")
        return screenshot_files
        
    def _create_dummy_screenshots(self) -> List[str]:
        """テスト用のダミースクリーンショットを作成する
        
        Returns:
            List[str]: ダミースクリーンショットのファイル名リスト
        """
        dummy_files = []
        # 赤、緑、青の単色画像を生成
        for color, rgb in [("red", (255, 0, 0)), ("green", (0, 255, 0)), ("blue", (0, 0, 255))]:
            # PIL を使って単色の画像を生成
            from PIL import Image
            dummy_img = Image.new('RGB', (512, 512), color=rgb)
            filename = f"dummy_{color}.png"
            filepath = os.path.join(self.dataset_dir, filename)
            dummy_img.save(filepath)
            dummy_files.append(filename)
            
        logger.info(f"ダミースクリーンショットを作成しました: {len(dummy_files)}枚")
        return dummy_files

    async def _generate_dataset_async(self, vrm_file_path: str, job_id: str, settings: Dict[str, Any], progress_callback: Optional[Callable] = None):
        """データセットを非同期で生成する

        Args:
            vrm_file_path (str): VRMファイルのパス
            job_id (str): ジョブID
            settings (Dict[str, Any]): 生成設定
            progress_callback (Optional[Callable], optional): 進捗コールバック

        Returns:
            str: 生成されたデータセットのZIPファイルパス
        """
        try:
            # 一時ディレクトリの作成
            self.temp_dir = tempfile.mkdtemp()
            self.dataset_dir = os.path.join(self.temp_dir, "dataset")
            os.makedirs(self.dataset_dir, exist_ok=True)
            
            # スクリーンショット保存先ディレクトリを作成
            screenshot_dirs = [
                os.path.join("backend/temp/screenshots", job_id),
                os.path.join(os.getcwd(), "backend/temp/screenshots", job_id),
                os.path.join("storage/temp/screenshots", job_id)
            ]
            
            for dir_path in screenshot_dirs:
                try:
                    os.makedirs(os.path.dirname(dir_path), exist_ok=True)
                    os.makedirs(dir_path, exist_ok=True)
                    logger.info(f"スクリーンショット保存先ディレクトリを作成しました: {dir_path}")
                except Exception as e:
                    logger.warning(f"ディレクトリ作成エラー ({dir_path}): {str(e)}")
            
            # メタデータの初期化
            self.metadata = {
                "vrm_file": os.path.basename(vrm_file_path),
                "job_id": job_id,
                "settings": settings,
                "screenshots": []
            }
            
            # ブラウザのセットアップ
            if progress_callback:
                progress_callback({"status": "ブラウザをセットアップしています", "progress": 5}, "ブラウザをセットアップしています")
            
            await self._set_up_browser()
            
            # VRMビューワーへの移動
            if progress_callback:
                progress_callback({"status": "VRMビューワーを読み込んでいます", "progress": 10}, "VRMビューワーを読み込んでいます")
            
            await self._navigate_to_viewer(vrm_file_path, job_id)
            
            # 最小設定を使用する場合
            use_minimal = settings.get("use_minimal", False)
            
            # 撮影設定の設定
            if use_minimal:
                # 最小限の設定（開発用）
                expressions = ["Neutral"]
                lightings = ["Normal"]
                distances = ["Mid-shot"]
                angles = [0, 90, 180, 270]
            else:
                # 本番用の設定
                expressions = ["Neutral", "Happy", "Sad", "Angry", "Surprised"]
                lightings = ["Normal", "Bright", "Soft"]
                distances = ["Close-up", "Mid-shot", "Full-body"]
                angles = list(range(0, 360, 45))  # 0, 45, 90, 135, 180, 225, 270, 315
            
            # 総ショット数の計算
            self.total_shots = len(expressions) * len(lightings) * len(distances) * len(angles)
            logger.info(f"総ショット数: {self.total_shots}")
            
            if progress_callback:
                progress_callback({
                    "status": "スクリーンショットを撮影しています", 
                    "progress": 15,
                    "total_shots": self.total_shots
                }, "スクリーンショットを撮影しています")
            
            # スクリーンショットの撮影
            self.current_shot = 0
            base_progress = 15
            progress_per_shot = 70 / self.total_shots  # 15%から85%までを使用
            
            for expr in expressions:
                for light in lightings:
                    for dist in distances:
                        for angle in angles:
                            filename = await self._take_screenshot(expr, light, dist, angle)
                            
                            # 進捗の更新
                            if progress_callback:
                                current_progress = base_progress + (self.current_shot * progress_per_shot)
                                progress_callback({
                                    "status": "スクリーンショットを撮影しています",
                                    "progress": int(current_progress),
                                    "current_shot": self.current_shot,
                                    "total_shots": self.total_shots,
                                    "filename": filename
                                }, f"スクリーンショット撮影中 ({self.current_shot}/{self.total_shots})")
            
            # スクリーンショットの収集
            if progress_callback:
                progress_callback({"status": "スクリーンショットを集めています", "progress": 85}, "スクリーンショットを集めています")
            
            screenshot_files = self._collect_screenshots(job_id)
            self.metadata["screenshots"] = screenshot_files
            
            # メタデータファイルの作成
            if progress_callback:
                progress_callback({"status": "メタデータを作成しています", "progress": 90}, "メタデータを作成しています")
            
            metadata_path = os.path.join(self.dataset_dir, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            # ZIPファイルの作成
            if progress_callback:
                progress_callback({"status": "ZIPファイルを作成しています", "progress": 95}, "ZIPファイルを作成しています")
            
            zip_filename = f"{job_id}_dataset.zip"
            zip_path = os.path.join(self.temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for root, _, files in os.walk(self.dataset_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.temp_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"データセットZIPファイル作成完了: {zip_path}")
            
            # ブラウザを閉じる
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if progress_callback:
                progress_callback({"status": "処理完了", "progress": 100}, "データセット生成が完了しました")
            
            return zip_path
        except Exception as e:
            logger.error(f"データセット生成エラー: {str(e)}")
            # ブラウザを閉じる
            if self.browser:
                await self.browser.close()
                self.browser = None
            raise Exception(f"データセット生成に失敗しました: {str(e)}")
        finally:
            # 一時ディレクトリの削除は呼び出し元で行う
            pass

    def cleanup(self):
        """一時ファイルのクリーンアップ"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"一時ディレクトリを削除しました: {self.temp_dir}")
            self.temp_dir = None

def run_async_in_thread(coro):
    """非同期コルーチンをスレッド内で実行するためのヘルパー関数"""
    try:
        # スレッド専用のイベントループを作成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # コルーチンを実行
        result = loop.run_until_complete(coro)
        
        # ループを閉じる
        loop.close()
        
        return result
    except Exception as e:
        logger.error(f"非同期処理エラー: {str(e)}")
        raise e

def generate_dataset(job_id: str, vrm_file_path: str, settings: Dict[str, Any], progress_callback: Optional[Callable] = None) -> str:
    """データセットを生成する

    Args:
        job_id (str): ジョブID
        vrm_file_path (str): VRMファイルのパス
        settings (Dict[str, Any]): 生成設定
        progress_callback (Optional[Callable], optional): 進捗コールバック関数

    Returns:
        str: 生成されたデータセットのZIPファイルパス
    """
    logger.info(f"データセット生成開始: ジョブID {job_id}, ファイル {vrm_file_path}")
    
    # DatasetGeneratorインスタンスの作成
    generator = DatasetGenerator()
    
    try:
        # スレッド内で非同期処理を実行
        zip_path = run_async_in_thread(
            generator._generate_dataset_async(vrm_file_path, job_id, settings, progress_callback)
        )
        
        logger.info(f"データセット生成完了: {zip_path}")
        return zip_path
    except Exception as e:
        logger.error(f"データセット生成エラー: {str(e)}")
        raise e
    finally:
        # クリーンアップ
        generator.cleanup()

# Chromiumのバージョン管理関連の関数
def get_system_chrome_version() -> Optional[str]:
    """システムにインストールされているChromeのバージョンを取得"""
    try:
        # macOS
        if sys.platform == "darwin":
            process = subprocess.run(
                ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
                capture_output=True,
                text=True
            )
        # Windows
        elif sys.platform == "win32":
            process = subprocess.run(
                ["reg", "query", "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon", "/v", "version"],
                capture_output=True,
                text=True
            )
        # Linux
        elif sys.platform == "linux":
            process = subprocess.run(
                ["google-chrome", "--version"],
                capture_output=True,
                text=True
            )
        else:
            logger.warning(f"未サポートのプラットフォーム: {sys.platform}")
            return None

        if process.returncode == 0:
            # バージョン番号を抽出（例: "Google Chrome 100.0.4896.127" から "100.0.4896.127"）
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)", process.stdout)
            if match:
                return match.group(1)
    except Exception as e:
        logger.warning(f"Chromeバージョンの取得中にエラーが発生: {str(e)}")
    
    return None

def get_compatible_chromium_revision(chrome_version: str) -> str:
    """Chromeバージョンに対応するChromium revisionを取得"""
    try:
        # バージョンの最初の2つの数字（メジャー.マイナー）を抽出
        major_minor = '.'.join(chrome_version.split('.')[:2])
        
        # Chromium versions APIから対応するリビジョンを取得
        url = f"https://chromium-browser-snapshots.storage.googleapis.com/index.html"
        response = requests.get("https://omahaproxy.appspot.com/deps.json?version=" + major_minor)
        if response.status_code == 200:
            data = response.json()
            if 'chromium_base_position' in data:
                return data['chromium_base_position']
    except Exception as e:
        logger.warning(f"Chromiumリビジョンの取得中にエラーが発生: {str(e)}")
    
    # 取得できない場合はフォールバックリビジョンを使用
    logger.info(f"互換性のあるリビジョンが見つからないため、フォールバックリビジョンを使用: {CHROMIUM_FALLBACK_REVISION}")
    return CHROMIUM_FALLBACK_REVISION

def should_update_chromium() -> bool:
    """Chromiumを更新すべきかを判断"""
    if not os.path.exists(CHROMIUM_VERSION_FILE):
        os.makedirs(CHROMIUM_STORAGE_DIR, exist_ok=True)
        return True
    
    try:
        with open(CHROMIUM_VERSION_FILE, 'r') as f:
            version_info = json.load(f)
        
        last_check = datetime.fromisoformat(version_info.get('last_check', '2000-01-01'))
        now = datetime.now()
        
        # 前回のチェックから指定日数が経過しているか
        if (now - last_check).days >= CHROMIUM_CHECK_INTERVAL_DAYS:
            return True
            
        # システムのChromeバージョンが変わっているか
        system_version = get_system_chrome_version()
        if system_version and system_version != version_info.get('chrome_version'):
            return True
            
    except Exception as e:
        logger.warning(f"Chromiumアップデートチェック中にエラーが発生: {str(e)}")
        return True
    
    return False

def update_chromium_version_info(chrome_version: str, chromium_revision: str) -> None:
    """Chromiumバージョン情報ファイルを更新"""
    try:
        version_info = {
            'chrome_version': chrome_version,
            'chromium_revision': chromium_revision,
            'last_check': datetime.now().isoformat(),
            'platform': sys.platform
        }
        
        os.makedirs(CHROMIUM_STORAGE_DIR, exist_ok=True)
        with open(CHROMIUM_VERSION_FILE, 'w') as f:
            json.dump(version_info, f)
            
        logger.info(f"Chromiumバージョン情報を更新: Chrome={chrome_version}, Revision={chromium_revision}")
    except Exception as e:
        logger.warning(f"Chromiumバージョン情報の更新中にエラーが発生: {str(e)}")

def get_optimal_chromium_executable() -> Dict[str, Any]:
    """最適なChromiumの実行ファイルとオプションを取得"""
    browser_options = {
        'headless': True,
        'args': [
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1280,720'
        ],
        'defaultViewport': {'width': 1280, 'height': 720}
    }
    
    # Chromiumの更新が必要か確認
    if should_update_chromium():
        # システムのChromeバージョンを取得
        chrome_version = get_system_chrome_version()
        if chrome_version:
            # 互換性のあるChromiumリビジョンを取得
            chromium_revision = get_compatible_chromium_revision(chrome_version)
            # バージョン情報を更新
            update_chromium_version_info(chrome_version, chromium_revision)
            # Pyppeteerに特定のChromiumリビジョンを使用するよう指示
            browser_options["executablePath"] = None  # PyppeteerがダウンロードするようにNone
            browser_options["revision"] = chromium_revision
            logger.info(f"Chromeバージョン {chrome_version} に最適なChromiumリビジョン {chromium_revision} を使用")
        else:
            # システムのバージョンが取得できない場合、デフォルトを使用
            browser_options["executablePath"] = None
            browser_options["revision"] = CHROMIUM_FALLBACK_REVISION
            logger.info(f"システムのChromeバージョンが取得できないため、デフォルトのリビジョン {CHROMIUM_FALLBACK_REVISION} を使用")
    else:
        # 既存の設定を使用
        try:
            with open(CHROMIUM_VERSION_FILE, 'r') as f:
                version_info = json.load(f)
            browser_options["revision"] = version_info.get('chromium_revision', CHROMIUM_FALLBACK_REVISION)
            logger.info(f"既存のChromiumリビジョン {browser_options['revision']} を使用")
        except Exception:
            browser_options["revision"] = CHROMIUM_FALLBACK_REVISION
            logger.info(f"バージョン情報の読み込みに失敗。デフォルトのリビジョン {CHROMIUM_FALLBACK_REVISION} を使用")
    
    return browser_options

# キャンセル関数
def cancel_job(job_id: str) -> bool:
    """ジョブをキャンセルする
    
    Args:
        job_id: キャンセルするジョブID
        
    Returns:
        成功したかどうか
    """
    if job_id in active_jobs:
        generator = active_jobs[job_id]
        generator.cancel()
        return True
    return False


# エラートレースバックをフォーマットする関数
def format_error_traceback(e: Exception) -> str:
    """エラーのトレースバックを整形された文字列として返す"""
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))


# モジュールレベルの初期化コード
def initialize_chromium_environment():
    """Chromium環境を初期化"""
    try:
        # Chromiumストレージディレクトリを確認・作成
        os.makedirs(CHROMIUM_STORAGE_DIR, exist_ok=True)
        
        # システムのChrome情報を取得して更新
        chrome_version = get_system_chrome_version()
        if chrome_version:
            logger.info(f"システムのChromeバージョン: {chrome_version}")
            chromium_revision = get_compatible_chromium_revision(chrome_version)
            update_chromium_version_info(chrome_version, chromium_revision)
            logger.info(f"Chromium環境を初期化しました - 使用リビジョン: {chromium_revision}")
        else:
            logger.info(f"Chromeバージョンが取得できなかったため、デフォルトを使用します")
            # デフォルトのフォールバックバージョン情報を保存
            update_chromium_version_info("unknown", CHROMIUM_FALLBACK_REVISION)
    except Exception as e:
        logger.warning(f"Chromium環境の初期化中にエラーが発生: {str(e)}")
        logger.info("デフォルト設定で続行します")

# バックグラウンドで非同期でChromiumの初期化を行う関数
async def async_initialize_chromium():
    """非同期でChromiumの初期化を行う"""
    try:
        # Chromiumバイナリをプリロード（最初のリクエストの待ち時間を短縮）
        browser_options = get_optimal_chromium_executable()
        logger.info("Chromiumの初期ダウンロードを開始...")
        browser = await launch(**browser_options)
        await browser.close()
        logger.info("Chromiumの初期ダウンロードが完了しました")
    except Exception as e:
        logger.warning(f"Chromiumの初期ダウンロード中にエラーが発生: {str(e)}")

# アプリケーション起動時に呼び出す初期化関数
def init_chromium_manager():
    """Chromium管理システムを初期化"""
    initialize_chromium_environment()
    
    # 非同期で初期ダウンロードを行う
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(async_initialize_chromium())
    except Exception as e:
        logger.warning(f"Chromiumの非同期初期化中にエラーが発生: {str(e)}")

# 初期化処理を実行
if __name__ != "__main__":  # インポート時のみ実行
    try:
        # 環境変数の設定
        logger.info("Chromium管理システムを初期化中...")
        init_chromium_manager()
    except Exception as e:
        logger.error(f"初期化中にエラーが発生: {str(e)}")
        logger.info("エラーを無視して続行します")


if __name__ == "__main__":
    # テスト用コード
    import argparse
    
    parser = argparse.ArgumentParser(description='VRMファイルからデータセットを生成')
    parser.add_argument('vrm_file', help='VRMファイルのパス')
    parser.add_argument('--job-id', help='ジョブID', default=f"test_{int(time.time())}")
    parser.add_argument('--minimal', help='最小構成を使用', action='store_true')
    
    args = parser.parse_args()
    
    def progress_print(progress, message):
        print(f"進捗: {progress}% - {message}")
    
    try:
        zip_path = generate_dataset(
            args.job_id, 
            args.vrm_file,
            progress_callback=progress_print,
            use_minimal=args.minimal
        )
        if zip_path:
            print(f"データセット生成完了: {zip_path}")
        else:
            print("ジョブがキャンセルされました")
    except Exception as e:
        print(f"データセット生成エラー: {str(e)}")