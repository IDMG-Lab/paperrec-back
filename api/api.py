# -*- coding:utf-8 -*-
"""
@Des: api路由
"""

from fastapi import APIRouter
from api.endpoints import user

api_router = APIRouter(prefix="/api/v1", tags=["api路由"])
api_router.include_router(user.router, prefix='/admin', tags=["用户管理"])
