#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import APIRouter

# ルーターの作成
router = APIRouter(
    prefix="/api/health",
    tags=["health"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def health_check():
    """
    API健康チェックエンドポイント
    """
    return {"status": "healthy", "message": "API is running"} 