# -*- coding:utf-8 -*-
"""
@Des: api路由
"""

from fastapi import APIRouter
from api.login import index, login
from api.test_redis import test_my_redis, test_my_redis_depends

api_router = APIRouter(prefix="/api/v1", tags=["api路由"])

api_router.get("/index", tags=["api路由"], summary="注册接口")(index)

api_router.get("/login", tags=["api路由"], summary="登录接口")(login)

api_router.get("/test/my/redis", tags=["api路由"], summary="fastapi的state方式")(test_my_redis)

api_router.get("/test/my/redis/depends", tags=["api路由"], summary="依赖注入方式")(test_my_redis_depends)
