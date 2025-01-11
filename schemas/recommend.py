# -*- coding:utf-8 -*-
"""
@Des: schemas模型-个性化推荐
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TagBase(BaseModel):
    id: int
    name: str = Field(..., description="标签名称")
    popularity: Optional[int] = Field(None, description="标签热度")


class PaperBase(BaseModel):
    id: str
    title: str = Field(..., max_length=255, description="论文标题")
    abstract: Optional[str] = Field(None, description="论文摘要")
    authors: Optional[str] = Field(None, description="作者列表")
    published_date: Optional[datetime] = Field(None, description="发表日期")
    source: Optional[str] = Field(None, max_length=255, description="来源")
    tags: Optional[str] = Field(None, description="关联标签")


class UserActionBase(BaseModel):
    user_id: int = Field(..., description="用户ID")
    arxiv_id: str = Field(..., max_length=100, description="外部论文唯一标识符")
    action_type: str = Field(..., max_length=50,description="行为类型，比如click（点击）、view（浏览）、search（搜索）、favorite（收藏）等")
    action_value: float = Field(1.0, description="行为权重，用户行为对推荐的重要程度")
    session_id: Optional[str] = Field(None, max_length=255, description="用户会话ID，便于关联用户连续行为")
    ip_address: Optional[str] = Field(None, max_length=45, description="用户IP地址")
    device_type: Optional[str] = Field(None, max_length=50, description="设备类型，比如 PC、Mobile")
    location: Optional[Dict] = Field(None, description="用户地理位置信息，比如国家、省、市")
    extra_data: Optional[Dict] = Field(None, description="额外信息，比如搜索关键词、停留时间等")


class UserProfileResponse(BaseModel):
    user_id: int = Field(..., description="用户ID")
    preferences: Dict = Field(..., description="用户偏好，比如感兴趣的标签分布")
    activity_score: float = Field(0.0, description="用户活跃度分数")
    tags: Optional[Dict] = Field(None, description="用户标签，比如领域、主题等")


class RecommendationBase(BaseModel):
    user_id: int = Field(..., description="用户ID")
    arxiv_id: str = Field(..., max_length=100, description="外部论文唯一标识符")
    reason: Optional[str] = Field(None, max_length=255, description="推荐理由")
    recommendation_type: str = Field("content_based",max_length=50,description="推荐类型 content_based/collaborative/hybrid")
    status: str = Field("pending",max_length=50,description="推荐状态 pending/viewed/accepted/ignored")
    priority: int = Field(0, description="推荐优先级，用于排序推荐结果")
    extra_data: Optional[Dict] = Field(None, description="额外信息，如推荐模型参数或调试信息")
    tags: Optional[List[str]] = Field(None, description="推荐相关的标签列表")


class RecommendationResponse(BaseModel):
    user_id: Optional[int] = Field(None, description="用户ID")
    paper: PaperBase = Field(..., description="推荐论文详情")