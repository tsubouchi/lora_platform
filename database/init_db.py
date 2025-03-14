#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import sys

# データベースファイルのパス
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'lora_platform.db')

def init_database():
    """データベースを初期化する関数"""
    try:
        # データベースディレクトリの確認
        db_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        # SQLiteデータベースに接続
        conn = sqlite3.connect(DB_PATH)
        
        # スキーマファイルを読み込み
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
        with open(schema_path, 'r') as f:
            schema_script = f.read()
        
        # スキーマを実行
        conn.executescript(schema_script)
        conn.commit()
        
        print(f"データベースを初期化しました: {DB_PATH}")
        return True
    
    except sqlite3.Error as e:
        print(f"データベース初期化エラー: {e}", file=sys.stderr)
        return False
    
    except Exception as e:
        print(f"予期せぬエラー: {e}", file=sys.stderr)
        return False
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    init_database() 