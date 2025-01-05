# -*- coding:utf-8 -*-
"""
@Des: schemas模型-个性化推荐
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from schemas.base import ResAntTable


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


class UserProfileSchema(BaseModel):
    user_id: int
    preferences: Dict[str, Any] = Field(..., description="用户偏好画像，例如标签分布")
    last_updated: datetime = Field(..., description="最后更新时间")


class UserActionBase(BaseModel):
    paper_id: str = Field(..., description="论文ID")
    action_type: str = Field(..., description="用户行为类型（view/like/favorite等）")
    action_value: float = Field(..., description="行为权重")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="额外信息，例如设备类型或行为来源")
    create_time: datetime = Field(..., description="行为发生时间")


class RecommendationBase(BaseModel):
    id: int
    user_id: int = Field(..., description="用户ID")
    paper_id: str = Field(..., description="论文ID")
    reason: Optional[str] = Field(None, max_length=255, description="推荐理由")
    recommendation_type: Optional[str] = Field(
        "content_based",
        description="推荐类型（content_based/collaborative/hybrid）"
    )
    tags: Optional[List[TagBase]] = Field(None, description="推荐关联标签")
    algorithm_details: Optional[Dict[str, Any]] = Field(None, description="推荐算法的详细信息，例如使用的参数、得分等")


class CreateRecommendation(BaseModel):
    user_id: int = Field(..., description="用户ID")
    paper_id: str = Field(..., description="论文ID")
    reason: Optional[str] = Field(None, max_length=255, description="推荐理由")
    recommendation_type: Optional[str] = Field(
        "content_based",
        description="推荐类型（content_based/collaborative/hybrid）"
    )
    tag_ids: Optional[List[int]] = Field(None, description="推荐标签ID列表")


class UpdateRecommendation(BaseModel):
    reason: Optional[str] = Field(None, max_length=255, description="推荐理由")
    recommendation_type: Optional[str] = Field(
        None,
        description="推荐类型（content_based/collaborative/hybrid）"
    )
    tag_ids: Optional[List[int]] = Field(None, description="推荐标签ID列表")


class RecommendationResponse(BaseModel):
    id: int
    user_id: Optional[int] = Field(None, description="用户ID")
    paper: PaperBase = Field(..., description="推荐论文详情")
    reason: Optional[str] = Field(None, max_length=255, description="推荐理由")
    recommendation_type: Optional[str] = Field(
        None,
        description="推荐类型（content_based/collaborative/hybrid）"
    )
    tags: Optional[List[TagBase]] = Field(None, description="推荐关联标签")
    algorithm_details: Optional[Dict[str, Any]] = Field(
        None, description="推荐算法的详细信息，例如得分"
    )
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")


class RecommendationTable(ResAntTable):
    records: List[RecommendationResponse] = Field(..., description="推荐记录列表")


class UserActionTable(ResAntTable):
    records: List[UserActionBase] = Field(..., description="用户行为记录列表")


class UserProfileResponse(BaseModel):
    user_id: int
    preferences: Dict[str, Any] = Field(..., description="用户偏好画像")
    last_updated: datetime = Field(..., description="最后更新时间")
