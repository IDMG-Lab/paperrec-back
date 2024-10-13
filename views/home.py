# -*- coding:utf-8 -*-
"""
@Des: views home
"""

from fastapi import Request, Form


async def home(request: Request, id: str):

    return request.app.state.views.TemplateResponse("index.html", {"request": request, "id": id})


async def reg_page(req: Request):
    """
    注册页面
    :param reg:
    :return: html
    """
    return req.app.state.views.TemplateResponse("reg_page.html", {"request": req})


async def result_page(req: Request, username: str = Form(...), password: str = Form(...)):
    """
    注册结果页面
    :param password: str
    :param username: str
    :param reg:
    :return: html
    """
    return req.app.state.views.TemplateResponse("reg_result.html", {"request": req, "username": username, "password": password})