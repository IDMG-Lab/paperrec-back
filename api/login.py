# -*- coding:utf-8 -*-
"""
@Des: login
"""

from fastapi import Request


async def index(req: Request):
    return {"Hello": "World"}


async def login(req: Request):
    return {"Hello": "World"}
