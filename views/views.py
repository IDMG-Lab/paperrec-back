# -*- coding:utf-8 -*-
"""
@Des: 视图路由
"""

from fastapi import APIRouter
from views.home import home, reg_page, result_page
from starlette.responses import HTMLResponse

views_router = APIRouter(tags=["视图路由"])

views_router.get("/items/{id}", response_class=HTMLResponse)(home)
views_router.get("/reg", response_class=HTMLResponse)(reg_page)
views_router.post("/reg/form", response_class=HTMLResponse)(result_page)
