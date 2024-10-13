# -*- coding:utf-8 -*-
"""
@Des: api路由
"""

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1",tags=["api路由"])


@api_router.get('/')
async def home(num: int):

    return num