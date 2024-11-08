# -*- coding:utf-8 -*-
"""
@Des: 中间件
"""

import time
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send, Message
from starlette.requests import Request  # 注意这里从 starlette 而不是 fastapi 导入
from core.Utils import random_str


class BaseMiddleware:
    """
    Middleware
    """

    def __init__(
            self,
            app: ASGIApp,
    ) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        start_time = time.time()
        # 仅当 scope 类型为 "http" 时才创建 Request 对象
        if scope["type"] == "http":
            req = Request(scope)
            # 确保 session 是可用的，并且可以设置默认值
            if not req.session.get("session"):
                req.session.setdefault("session", random_str())

        async def send_wrapper(message: Message) -> None:
            nonlocal start_time  # 使用 nonlocal 声明 start_time，以便在嵌套函数中修改
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message.get("headers", []))
                process_time = time.time() - start_time
                headers.append("X-Process-Time", str(process_time))
                message["headers"] = headers.raw  # 更新消息中的 headers
            await send(message)

        # 调用下一个应用，传入 send_wrapper 作为修改后的 send 函数
        await self.app(scope, receive, send_wrapper)
