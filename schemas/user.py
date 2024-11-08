# -*- coding:utf-8 -*-
"""
@Des: schemas模型
"""
from datetime import datetime
from pydantic import Field, BaseModel, field_validator
from typing import Optional, List
from schemas.base import BaseResp, ResAntTable


class CreateUser(BaseModel):
    username: str = Field(min_length=3, max_length=10)
    password: str = Field(min_length=6, max_length=12)
    user_phone: Optional[str] = Field(default=None, pattern="^1[34567890]\\d{9}$")
    user_status: Optional[bool] = None
    remarks: Optional[str] = None
    roles: Optional[List[int]] = None


class UpdateUser(BaseModel):
    id: int
    username: Optional[str] = Field(default=None, min_length=3, max_length=10)
    password: Optional[str] = Field(default=None, min_length=6, max_length=12)
    user_phone: Optional[str] = Field(default=None, pattern="^1[34567890]\\d{9}$")
    user_status: Optional[bool] = None
    remarks: Optional[str] = None


class SetRole(BaseModel):
    user_id: int
    roles: Optional[List[int]] = Field(default=[], description="角色")


class AccountLogin(BaseModel):
    username: Optional[str] = Field(min_length=3, max_length=10, description="用户名", default=None)
    password: Optional[str] = Field(min_length=6, max_length=12, description="密码", default=None)
    mobile: Optional[str] = Field(pattern="^1[34567890]\\d{9}$", description="手机号", default=None)
    captcha: Optional[str] = Field(min_length=6, max_length=6, description="6位验证码", default=None)


class ModifyMobile(BaseModel):
    mobile: str = Field(pattern="^1[34567890]\\d{9}$", description="手机号")
    captcha: str = Field(min_length=6, max_length=6, description="6位验证码")


class UserInfo(BaseModel):
    username: str
    age: Optional[int] = None
    user_type: bool
    nickname: Optional[str] = None
    user_phone: Optional[str] = None
    user_email: Optional[str] = None
    full_name: Optional[str] = None
    scopes: Optional[List[str]] = None
    user_status: bool
    header_img: Optional[str] = None
    sex: int


class UserListItem(BaseModel):
    key: int
    id: int
    username: str
    age: Optional[int] = None
    user_type: bool
    nickname: Optional[str] = None
    user_phone: Optional[str] = None
    user_email: Optional[str] = None
    full_name: Optional[str] = None
    user_status: bool
    header_img: Optional[str] = None
    sex: int
    remarks: Optional[str] = None
    create_time: datetime
    update_time: datetime


class CurrentUser(BaseResp):
    data: UserInfo


class AccessToken(BaseModel):
    token: Optional[str] = None
    expires_in: Optional[int] = None


class UserLogin(BaseResp):
    data: AccessToken


class UserListData(ResAntTable):
    data: List[UserListItem]


class UpdateUserInfo(BaseModel):
    nickname: Optional[str] = None
    user_email: Optional[str] = None
    header_img: Optional[str] = None
    user_phone: Optional[str] = Field(pattern="^1[34567890]\\d{9}$", description="手机号", default=None)
    password: Optional[str] = Field(min_length=6, max_length=12, description="密码", default=None)

    @field_validator('*', mode='before')
    def blank_strings(cls, v):
        if v == "":
            return None
        return v
