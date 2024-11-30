# -*- coding:utf-8 -*-
"""
@Des: 个性化推荐
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Security
from typing import List, Optional, Dict, Any
from datetime import datetime

from tortoise.expressions import Q
from core.Auth import get_current_user, check_permissions
from core.Response import success
from schemas.recommend import RecommendationResponse, UserProfileResponse, UserActionBase
from models.arxivdb import Paper, UserAction, UserProfile

router = APIRouter(prefix="/personalized")


@router.get("/recommendations",
            summary="获取个性化推荐列表",
            response_model=List[RecommendationResponse],
            dependencies=[Security(check_permissions)]
            )
async def get_personalized_recommendations(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50, description="返回的推荐数量"),
    tag_id: Optional[int] = Query(None, description="根据标签筛选"),
):
    """
    获取个性化推荐列表
    :param current_user: 当前用户信息
    :param limit: 推荐数量
    :param tag_id: 标签筛选
    """
    # 获取用户画像
    user_id = current_user["user_id"]
    user_profile = await UserProfile.get_or_none(user_id=user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="用户画像未找到，请记录用户行为")

    preferences = user_profile.preferences
    preferred_tags = preferences.get("preferred_tags", [])
    # 获取与用户标签相关的论文
    query = Paper.filter(Q(tag__id__in=preferred_tags)).distinct()

    # 如果传入了 tag_id，进行标签筛选
    if tag_id:
        query = query.filter(Q(tag__id=tag_id))

    papers = await query.order_by("-popularity").limit(limit).prefetch_related("tag")
    recommendations = [
        RecommendationResponse(
            id=paper.id,
            user_id=user_id,
            paper={
                "id": paper.id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.published_date,
                "source": paper.source,
                "tags": [{"id": t.id, "name": t.name, "popularity": t.popularity} for t in await paper.tag.all()],
                "popularity": paper.popularity,
            },
            reason="匹配您的兴趣标签",
            recommendation_type="content_based",
            tags=None,
            algorithm_details=None,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        for paper in papers
    ]
    return recommendations


@router.post("/user/actions", summary="记录用户行为", dependencies=[Security(check_permissions)])
async def record_user_action(action: UserActionBase, current_user: dict = Depends(get_current_user)):
    """
    记录用户行为
    :param current_user: 当前用户信息
    :param action: 用户行为数据
    """
    user_id = current_user["user_id"]
    await UserAction.create(
        user_id=user_id,
        paper_id=action.paper_id,
        action_type=action.action_type,
        action_value=action.action_value,
        extra_data=action.extra_data,
        create_time=datetime.now(),
    )
    # 基于行为更新用户画像
    await update_user_profile(action, user_id)

    return success(msg="行为记录成功")


@router.get("/user/profile",
            summary="获取用户画像",
            response_model=UserProfileResponse,
            dependencies=[Security(check_permissions)]
            )
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """
    获取用户画像
    :param current_user: 当前用户信息
    """
    user_id = current_user["user_id"]
    user_profile = await UserProfile.get_or_none(user_id=user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="用户画像未找到")
    return {
        "user_id": user_profile.user_id,
        "preferences": user_profile.preferences,
        "last_updated": user_profile.last_updated.isoformat()
    }


@router.post("/user/profile",
             summary="更新用户画像",
             response_model=UserProfileResponse,
             dependencies=[Security(check_permissions)]
             )
async def update_user_profile(action: UserActionBase, user_id: int):
    """
    更新用户画像
    :param user_id: 用户id
    :param action: 用户行为记录
    """
    # 获取用户画像
    user_profile = await UserProfile.get_or_none(user_id=user_id)
    if not user_profile:
        # 如果用户画像不存在，创建一个新的用户画像
        user_profile = await UserProfile.create(user_id=user_id, preferences={})

    # 获取论文的标签
    paper = await Paper.get_or_none(id=action.paper_id)
    if not paper:
        return  # 如果没有找到论文，返回
    paper_tags = [t.id for t in await paper.tag.all()]

    # 获取当前的用户偏好
    preferences = user_profile.preferences

    # 更新偏好标签
    if action.action_type == "like":
        # 用户喜欢行为 - 增加对标签的兴趣
        preferences["preferred_tags"] = preferences.get("preferred_tags", [])
        for tag_id in paper_tags:
            if tag_id not in preferences["preferred_tags"]:
                preferences["preferred_tags"].append(tag_id)

    # 更新用户画像
    user_profile.preferences = preferences
    user_profile.last_updated = datetime.now()  # 更新最后更新时间

    # 保存用户画像
    await user_profile.save()
    return {
        "user_id": user_profile.user_id,
        "preferences": user_profile.preferences,
        "last_updated": user_profile.last_updated.isoformat()
    }


@router.get("/popular", summary="获取热门推荐", response_model=List[RecommendationResponse])
async def get_popular_recommendations(limit: int = Query(10, ge=1, le=50, description="返回的热门数量")):
    """
    获取热门推荐
    :param limit: 热门数量
    """
    papers = await Paper.all().order_by("-popularity").limit(limit).prefetch_related("tag")
    recommendations = []
    current_id = 1
    for paper in papers:
        recommendation = RecommendationResponse(
            id=current_id,
            user_id=None,
            paper={
                "id": paper.id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.published_date,
                "source": paper.source,
                "tags": [{"id": t.id, "name": t.name, "popularity": t.popularity} for t in await paper.tag.all()],
                "popularity": paper.popularity,
            },
            reason="热门论文推荐",
            recommendation_type="popular",
            tags=None,
            algorithm_details=None,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        recommendations.append(recommendation)
        current_id += 1
    return recommendations
