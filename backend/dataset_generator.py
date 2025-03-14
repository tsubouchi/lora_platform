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
    """VRMファイルからデータセットを生成するクラス"""
    
    def __init__(self, job_id: str, vrm_file_path: str, settings: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            job_id: ジョブID
            vrm_file_path: VRMファイルのパス
            settings: データセット生成設定（指定しない場合はデフォルト設定を使用）
        """
        self.job_id = job_id
        self.vrm_file_path = vrm_file_path
        self.vrm_file_name = os.path.basename(vrm_file_path)
        self.output_dir = os.path.join(TEMP_DIR, job_id)
        self.settings = settings or self._load_default_settings()
        self.metadata = {
            "job_id": job_id,
            "vrm_file": self.vrm_file_name,
            "parameters": {},
            "total_shots": 0,
            "shots": [],
            "timestamp": datetime.now().isoformat(),
        }
        self.browser = None
        self.page = None
        self.progress_callback = None
        self.current_progress = 0
        self.is_cancelled = False
        self.current_step = "initializing"
        
        # キャンセル状態を追跡するための辞書に登録
        active_jobs[job_id] = self
        
    def __del__(self):
        """デストラクタ - ジョブ辞書から削除"""
        if self.job_id in active_jobs:
            del active_jobs[self.job_id]
        
    def _load_default_settings(self) -> Dict[str, Any]:
        """デフォルト設定をロード"""
        try:
            with open(DEFAULT_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"デフォルト設定ファイルの読み込みに失敗しました: {str(e)}")
            # 基本的なデフォルト設定を返す
            return {
                "angle": {"start": 0, "end": 350, "step": 10},
                "expressions": ["Neutral"],
                "lighting": ["Normal"],
                "camera_distance": ["Mid-shot", "Close-up"],
                "output": {
                    "format": "png",
                    "resolution": "512x512",
                    "quality": 90,
                    "background": "#FFFFFF"
                }
            }
            
    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """進捗コールバックを設定"""
        self.progress_callback = callback
            
    def _update_progress(self, progress: int, message: str = "", step: str = None):
        """
        進捗状況を更新
        
        Args:
            progress: 進捗率（0-100）
            message: 進捗メッセージ
            step: 現在のステップ識別子
        """
        self.current_progress = progress
        if step:
            self.current_step = step
            
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info(f"進捗: {progress}% - {message}")
        
        # キャンセル状態をチェック
        if self.is_cancelled:
            raise JobCancelledError("ジョブがキャンセルされました")
            
    def cancel(self):
        """ジョブをキャンセル"""
        logger.info(f"ジョブ {self.job_id} をキャンセルします")
        self.is_cancelled = True
        # ブラウザを非同期でクローズ
        if self.browser:
            asyncio.create_task(self._close_browser())
            
    async def _close_browser(self):
        """ブラウザを安全にクローズ"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
        except Exception as e:
            logger.error(f"ブラウザのクローズに失敗しました: {str(e)}")
            
    def calculate_total_shots(self) -> int:
        """撮影する総枚数を計算"""
        angle_settings = self.settings.get("angle", {})
        start = angle_settings.get("start", 0)
        end = angle_settings.get("end", 350)
        step = angle_settings.get("step", 10)
        
        angle_count = len(range(start, end + 1, step))
        expressions = self.settings.get("expressions", ["Neutral"])
        lighting = self.settings.get("lighting", ["Normal"])
        camera_distance = self.settings.get("camera_distance", ["Mid-shot"])
        
        total = angle_count * len(expressions) * len(lighting) * len(camera_distance)
        return total
            
    async def generate_dataset(self, use_minimal: bool = False) -> str:
        """
        データセットを生成
        
        Args:
            use_minimal: 最小構成を使用するかどうか
            
        Returns:
            生成されたZIPファイルのパス
        """
        try:
            start_time = time.time()
            
            # 出力ディレクトリを作成
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 総枚数を計算
            if use_minimal and "minimal_config" in self.settings:
                # 最小構成の場合は設定を上書き
                expressions = self.settings["minimal_config"].get("expressions", ["Neutral"])
                lighting = self.settings["minimal_config"].get("lighting", ["Normal"])
                camera_distance = self.settings["minimal_config"].get("camera_distance", ["Mid-shot", "Close-up"])
                self.settings["expressions"] = expressions
                self.settings["lighting"] = lighting
                self.settings["camera_distance"] = camera_distance
                
            total_shots = self.calculate_total_shots()
            self.metadata["parameters"] = {
                "angle_start": self.settings["angle"]["start"],
                "angle_end": self.settings["angle"]["end"],
                "angle_step": self.settings["angle"]["step"],
                "expressions": self.settings["expressions"],
                "lighting": self.settings["lighting"],
                "camera_distance": self.settings["camera_distance"],
                "use_minimal": use_minimal
            }
            self.metadata["total_shots"] = total_shots
            
            logger.info(f"データセット生成開始: 総枚数 {total_shots}枚")
            self._update_progress(1, f"ブラウザ初期化中...", "initializing")
            
            # ブラウザを起動
            await self._set_up_browser()
            
            # VRMファイルをアップロード
            self._update_progress(10, f"VRMファイルをアップロード中: {self.vrm_file_name}", "uploading")
            try:
                await self._upload_vrm_file()
            except Exception as e:
                logger.error(f"VRMファイルのアップロードに失敗しました: {str(e)}")
                raise DatasetGenerationError(f"VRMファイルのアップロードに失敗しました: {str(e)}")
            
            # モデルが読み込まれるまで待機
            await asyncio.sleep(3)
            
            # スクリーンショット撮影
            self._update_progress(15, f"スクリーンショット撮影開始...", "capturing")
            try:
                await self._capture_screenshots()
            except JobCancelledError:
                raise
            except Exception as e:
                logger.error(f"スクリーンショット撮影中にエラーが発生しました: {str(e)}")
                raise DatasetGenerationError(f"スクリーンショット撮影に失敗しました: {str(e)}")
            
            # メタデータを保存
            self._update_progress(92, f"メタデータを保存中...", "processing")
            metadata_path = os.path.join(self.output_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
                
            # ZIPファイルを作成
            self._update_progress(95, f"ZIPファイル作成中...", "compressing")
            zip_path = os.path.join(DATASET_DIR, f"{self.job_id}.zip")
            try:
                self._create_zip_archive(zip_path)
            except Exception as e:
                logger.error(f"ZIPファイル作成中にエラーが発生しました: {str(e)}")
                raise DatasetGenerationError(f"ZIPファイル作成に失敗しました: {str(e)}")
            
            # 一時ディレクトリを削除
            try:
                shutil.rmtree(self.output_dir)
            except Exception as e:
                logger.warning(f"一時ディレクトリの削除に失敗しました: {str(e)}")
            
            elapsed_time = time.time() - start_time
            logger.info(f"データセット生成完了: 所要時間 {elapsed_time:.2f}秒")
            self._update_progress(100, f"データセット生成完了: 合計 {total_shots}枚", "completed")
            
            return zip_path
            
        except JobCancelledError:
            logger.info(f"ジョブ {self.job_id} がキャンセルされました")
            # 一時ファイルのクリーンアップ
            if os.path.exists(self.output_dir):
                try:
                    shutil.rmtree(self.output_dir)
                except:
                    pass
            raise
            
        except Exception as e:
            logger.error(f"データセット生成エラー: {str(e)}", exc_info=True)
            self._update_progress(0, f"エラー: {str(e)}", "error")
            # 一時ファイルのクリーンアップ
            if os.path.exists(self.output_dir):
                try:
                    shutil.rmtree(self.output_dir)
                except:
                    pass
            raise
            
        finally:
            # ブラウザを確実に閉じる
            if self.browser:
                try:
                    await self.browser.close()
                    self.browser = None
                except:
                    logger.error("ブラウザのクローズに失敗しました", exc_info=True)
            
            # アクティブジョブから削除
            if self.job_id in active_jobs:
                del active_jobs[self.job_id]
                
    async def _set_up_browser(self) -> None:
        """ブラウザを起動し、VRM Viewerページを開く"""
        try:
            # システムに最適なChromiumオプションを取得
            browser_options = get_optimal_chromium_executable()
            logger.info(f"ブラウザ起動オプション: {browser_options}")
            
            self.browser = await launch(**browser_options)
            self.page = await self.browser.newPage()
            
            # VRM Viewerページを開く
            await self.page.goto("https://vrm-viewer.com/", {
                "waitUntil": "networkidle0",
                "timeout": 60000
            })
            logger.info("VRM Viewerページを開きました")
            
            # ページが読み込まれたか確認
            await self.page.waitForSelector("#app", {"timeout": 30000})
            logger.info("VRM Viewerページの読み込みを確認")
        
        except PyppeteerTimeoutError:
            error_msg = "VRM Viewerページの読み込みタイムアウト"
            logger.error(error_msg)
            raise DatasetGenerationError(error_msg)
        except Exception as e:
            error_msg = f"ブラウザ起動エラー: {str(e)}"
            logger.error(error_msg)
            raise DatasetGenerationError(error_msg)
            
    async def _upload_vrm_file(self):
        """VRMファイルをアップロード"""
        # ファイル選択エレメントを取得
        file_input = await self.page.querySelector('input[type="file"]')
        if not file_input:
            raise ValueError("ファイル選択エレメントが見つかりません")
            
        # VRMファイルをアップロード
        await file_input.uploadFile(self.vrm_file_path)
        
        # モデルがロードされるのを待機
        try:
            await self.page.waitForFunction(
                'document.querySelector(".model-loaded") !== null || document.querySelector(".error-message") !== null',
                {"timeout": 30000}
            )
            
            # エラーメッセージをチェック
            error_element = await self.page.querySelector(".error-message")
            if error_element:
                error_text = await self.page.evaluate('(element) => element.textContent', error_element)
                raise ValueError(f"モデルのロードに失敗: {error_text}")
                
        except PyppeteerTimeoutError:
            raise TimeoutError("VRMファイルのロードがタイムアウトしました")
            
        logger.info(f"VRMファイルアップロード成功: {self.vrm_file_name}")
                
    async def _capture_screenshots(self):
        """スクリーンショットを撮影"""
        angle_settings = self.settings.get("angle", {})
        start = angle_settings.get("start", 0)
        end = angle_settings.get("end", 350)
        step = angle_settings.get("step", 10)
        
        expressions = self.settings.get("expressions", ["Neutral"])
        lighting = self.settings.get("lighting", ["Normal"])
        camera_distance = self.settings.get("camera_distance", ["Mid-shot"])
        
        total_shots = self.calculate_total_shots()
        current_shot = 0
        
        # 全ての組み合わせでスクリーンショットを撮影
        for expression_idx, expression in enumerate(expressions):
            try:
                await self._set_expression(expression)
            except Exception as e:
                logger.warning(f"表情設定エラー: {expression}: {str(e)}")
                continue
                
            for light_idx, light in enumerate(lighting):
                try:
                    await self._set_lighting(light)
                except Exception as e:
                    logger.warning(f"ライティング設定エラー: {light}: {str(e)}")
                    continue
                    
                for dist_idx, distance in enumerate(camera_distance):
                    try:
                        await self._set_camera_distance(distance)
                    except Exception as e:
                        logger.warning(f"カメラ距離設定エラー: {distance}: {str(e)}")
                        continue
                        
                    for angle in range(start, end + 1, step):
                        # キャンセル状態をチェック
                        if self.is_cancelled:
                            raise JobCancelledError("ジョブがキャンセルされました")
                            
                        try:
                            await self._rotate_model(angle)
                            
                            # スクリーンショットを撮影
                            file_name = self._get_file_name(expression, light, distance, angle)
                            file_path = os.path.join(self.output_dir, file_name)
                            await self._take_screenshot(file_path)
                            
                            # メタデータに追加
                            self.metadata["shots"].append({
                                "filename": file_name,
                                "expression": expression,
                                "lighting": light,
                                "camera_distance": distance,
                                "angle": angle
                            })
                            
                            # 進捗更新
                            current_shot += 1
                            progress = int(15 + (current_shot / total_shots * 75))
                            self._update_progress(
                                progress,
                                f"撮影中: {current_shot}/{total_shots} - {expression}, {light}, {distance}, 角度{angle}°",
                                "capturing"
                            )
                            
                            # 短い待機（負荷軽減）
                            await asyncio.sleep(0.1)
                            
                        except JobCancelledError:
                            raise
                        except Exception as e:
                            logger.warning(f"角度 {angle}° での撮影に失敗: {str(e)}")
                            continue
                        
    async def _set_expression(self, expression: str):
        """表情を設定"""
        logger.info(f"表情設定: {expression}")
        try:
            # 表情パネルを開く
            await self.page.click('.expression-panel-button')
            await asyncio.sleep(0.5)
            
            # 表情を選択（表情に対応するボタンをクリック）
            expression_selectors = {
                "Neutral": ".expression-neutral",
                "Happy": ".expression-happy",
                "Sad": ".expression-sad",
                "Angry": ".expression-angry",
                "Surprised": ".expression-surprised"
            }
            
            if expression in expression_selectors:
                await self.page.click(expression_selectors[expression])
            else:
                logger.warning(f"未対応の表情: {expression}、デフォルトを使用します")
                await self.page.click(".expression-neutral")
                
            # 表情パネルを閉じる
            await asyncio.sleep(0.5)
            await self.page.click('.expression-panel-close')
        except Exception as e:
            logger.error(f"表情設定中にエラーが発生しました: {str(e)}")
            raise ValueError(f"表情設定に失敗しました: {str(e)}")
        
    async def _set_lighting(self, lighting: str):
        """ライティングを設定"""
        logger.info(f"ライティング設定: {lighting}")
        try:
            # ライティングパネルを開く
            await self.page.click('.lighting-panel-button')
            await asyncio.sleep(0.5)
            
            # ライティングを選択
            lighting_selectors = {
                "Bright": ".lighting-bright",
                "Normal": ".lighting-normal",
                "Soft": ".lighting-soft",
                "Dark": ".lighting-dark",
                "Warm": ".lighting-warm",
                "Cool": ".lighting-cool"
            }
            
            if lighting in lighting_selectors:
                await self.page.click(lighting_selectors[lighting])
            else:
                logger.warning(f"未対応のライティング: {lighting}、デフォルトを使用します")
                await self.page.click(".lighting-normal")
                
            # ライティングパネルを閉じる
            await asyncio.sleep(0.5)
            await self.page.click('.lighting-panel-close')
        except Exception as e:
            logger.error(f"ライティング設定中にエラーが発生しました: {str(e)}")
            raise ValueError(f"ライティング設定に失敗しました: {str(e)}")
        
    async def _set_camera_distance(self, distance: str):
        """カメラ距離を設定"""
        logger.info(f"カメラ距離設定: {distance}")
        try:
            # カメラパネルを開く
            await self.page.click('.camera-panel-button')
            await asyncio.sleep(0.5)
            
            # カメラ距離を選択
            distance_selectors = {
                "Close-up": ".camera-closeup",
                "Mid-shot": ".camera-midshot",
                "Full-body": ".camera-fullbody"
            }
            
            if distance in distance_selectors:
                await self.page.click(distance_selectors[distance])
            else:
                logger.warning(f"未対応のカメラ距離: {distance}、デフォルトを使用します")
                await self.page.click(".camera-midshot")
                
            # カメラパネルを閉じる
            await asyncio.sleep(0.5)
            await self.page.click('.camera-panel-close')
        except Exception as e:
            logger.error(f"カメラ距離設定中にエラーが発生しました: {str(e)}")
            raise ValueError(f"カメラ距離設定に失敗しました: {str(e)}")
        
    async def _rotate_model(self, angle: int):
        """モデルを回転"""
        try:
            # モデル回転スライダーを操作
            await self.page.evaluate(f"""() => {{
                document.querySelector('.rotation-slider').value = {angle};
                document.querySelector('.rotation-slider').dispatchEvent(new Event('input'));
            }}""")
            await asyncio.sleep(0.2)  # 回転アニメーションが完了するまで待機
        except Exception as e:
            logger.error(f"モデル回転中にエラーが発生しました: {str(e)}")
            raise ValueError(f"モデル回転に失敗しました: {str(e)}")
        
    async def _take_screenshot(self, file_path: str):
        """スクリーンショットを撮影"""
        try:
            # スクリーンショットを撮影
            viewport_area = await self.page.evaluate("""() => {
                const modelViewer = document.querySelector('.model-viewer');
                if (!modelViewer) return null;
                const rect = modelViewer.getBoundingClientRect();
                return {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                };
            }""")
            
            if not viewport_area:
                raise ValueError("モデルビューア要素が見つかりません")
            
            await self.page.screenshot({
                'path': file_path,
                'clip': viewport_area,
                'type': 'png',
                'omitBackground': True
            })
            
            # 解像度を調整
            self._resize_image(file_path)
            
        except Exception as e:
            logger.error(f"スクリーンショット撮影中にエラーが発生しました: {str(e)}")
            raise ValueError(f"スクリーンショット撮影に失敗しました: {str(e)}")
        
    def _resize_image(self, file_path: str):
        """画像の解像度を調整"""
        resolution = self.settings.get("output", {}).get("resolution", "512x512")
        try:
            width, height = map(int, resolution.split("x"))
            with Image.open(file_path) as img:
                resized_img = img.resize((width, height), Image.LANCZOS)
                resized_img.save(file_path, quality=self.settings.get("output", {}).get("quality", 90))
        except Exception as e:
            logger.warning(f"画像リサイズエラー: {str(e)}")
            raise ValueError(f"画像リサイズに失敗しました: {str(e)}")
            
    def _get_file_name(self, expression: str, lighting: str, distance: str, angle: int) -> str:
        """ファイル名を生成"""
        naming_format = self.settings.get("metadata", {}).get(
            "naming_format", 
            "shot_{expression}_{lighting}_{distance}_angle{angle:03d}.png"
        )
        return naming_format.format(
            expression=expression,
            lighting=lighting,
            distance=distance,
            angle=angle
        )
        
    def _create_zip_archive(self, zip_path: str):
        """ZIPアーカイブを作成"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(self.output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.output_dir)
                    zipf.write(file_path, arcname)
        logger.info(f"ZIPアーカイブ作成完了: {zip_path}")


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


async def generate_dataset_async(job_id: str, vrm_file_path: str, settings: Optional[Dict[str, Any]] = None, 
                                progress_callback=None, use_minimal: bool = False) -> str:
    """
    非同期でデータセットを生成
    
    Args:
        job_id: ジョブID
        vrm_file_path: VRMファイルのパス
        settings: データセット生成設定
        progress_callback: 進捗コールバック関数
        use_minimal: 最小構成を使用するかどうか
        
    Returns:
        生成されたZIPファイルのパス
    """
    # ディレクトリが存在することを確認
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(DATASET_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # データセット生成
    generator = DatasetGenerator(job_id, vrm_file_path, settings)
    if progress_callback:
        generator.set_progress_callback(progress_callback)
        
    try:
        return await generator.generate_dataset(use_minimal)
    except JobCancelledError:
        logger.info(f"ジョブ {job_id} がキャンセルされました")
        return None
    except Exception as e:
        logger.error(f"データセット生成エラー: {str(e)}", exc_info=True)
        error_detail = format_error_traceback(e)
        raise DatasetGenerationError(f"データセット生成に失敗しました: {str(e)}\n{error_detail}")


def generate_dataset(job_id: str, vrm_file_path: str, settings: Optional[Dict[str, Any]] = None,
                   progress_callback=None, use_minimal: bool = False) -> str:
    """
    同期的にデータセットを生成（非同期関数のラッパー）
    
    Args:
        job_id: ジョブID
        vrm_file_path: VRMファイルのパス
        settings: データセット生成設定
        progress_callback: 進捗コールバック関数
        use_minimal: 最小構成を使用するかどうか
        
    Returns:
        生成されたZIPファイルのパス
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # イベントループが存在しない場合は新規作成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        return loop.run_until_complete(
            generate_dataset_async(job_id, vrm_file_path, settings, progress_callback, use_minimal)
        )
    except JobCancelledError:
        logger.info(f"ジョブ {job_id} がキャンセルされました")
        return None


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