# -*- coding:utf-8 -*-
"""
@Des: 个性化推荐
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Security
from typing import List, Optional
from datetime import datetime

from tortoise.expressions import Q
from core.Auth import get_current_user, check_permissions
from core.Response import success
from schemas.recommend import RecommendationResponse, UserProfileResponse, UserActionBase, PaperBase
from models.arxivdb import Paper, UserAction, UserProfile, Tag
from models.scrape import Arxiv

router = APIRouter(prefix="/personalized")


@router.get("/search", summary="搜索论文", response_model=List[PaperBase])
async def search_arxiv_papers(
    query: str = Query(..., description="用户输入的搜索内容"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    搜索论文
    :param query: 用户输入的搜索关键词或内容
    :param limit: 每页数量
    :param offset: 偏移量
    :return: 搜索结果
    """
    # 搜索标题、摘要、作者和分类
    papers = await Arxiv.filter(
        Q(title__icontains=query) |
        Q(abstract__icontains=query) |
        Q(authors__icontains=query) |
        Q(primary_subject__icontains=query) |
        Q(subjects__icontains=query)
    ).order_by("-date").offset(offset).limit(limit)

    # 如果没有找到相关论文
    if not papers:
        raise HTTPException(status_code=404, detail="没有找到相关论文")

    return [
        PaperBase(
            id=paper.arxiv_id,
            title=paper.title,
            authors=paper.authors,
            abstract=paper.abstract,
            published_date=paper.date,
            source=paper.pdf_url,
            tags=paper.primary_subject,
        )
        for paper in papers
    ]


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

    # 获取用户偏好的标签
    preferences = user_profile.preferences
    preferred_tags = preferences.get("preferred_tags", [])
    if not preferred_tags:
        raise HTTPException(status_code=400, detail="用户未设置任何偏好标签")

    # 默认使用用户偏好的第一个标签 ID
    tag_id_to_use = tag_id or preferred_tags[0]

    # 从 Tag 表中获取标签名称
    tag = await Tag.get_or_none(id=tag_id_to_use)
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    tag_name = tag.name  # 标签名称

    # 查询匹配的论文
    query = Arxiv.filter(Q(primary_subject__startswith=tag_name)).distinct()

    # 如果传入了 tag_id，进行标签筛选
    if tag_id:
        tag = await Tag.get_or_none(id=tag_id)
        tag_name = tag.name
        query = query.filter(Q(primary_subject__icontains=tag_name)).distinct()

    # 按时间降序获取推荐论文
    papers = await query.order_by("-date").limit(limit)

    # 构建推荐列表
    recommendations = []
    current_id = 1

    for paper in papers:
        recommendation = RecommendationResponse(
            id=current_id,
            user_id=user_id,
            paper={
                "id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.date,
                "source": paper.pdf_url,
                "tags": paper.primary_subject,
            },
            reason="匹配您的兴趣标签",
            recommendation_type="content_based",
            tags=None,
            algorithm_details=None,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        recommendations.append(recommendation)
        current_id += 1
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


@router.get("/user/actions", summary="获取用户行为历史", dependencies=[Security(check_permissions)])
async def get_user_actions(
    current_user: dict = Depends(get_current_user),
    start_time: Optional[datetime] = Query(None, description="起始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    action_type: Optional[str] = Query(None, description="行为类型（如浏览、收藏、点赞）"),
    page: int = Query(1, ge=1, description="页码，默认第 1 页"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数，默认 10 条"),
):
    """
    获取用户行为历史记录
    :param current_user: 当前登录用户信息
    :param start_time: 行为记录的起始时间
    :param end_time: 行为记录的结束时间
    :param action_type: 行为类型过滤条件
    :param page: 页码
    :param page_size: 每页条数
    """
    user_id = current_user["user_id"]

    # 构建查询条件
    query = Q(user_id=user_id)
    if start_time:
        query &= Q(create_time__gte=start_time)
    if end_time:
        query &= Q(create_time__lte=end_time)
    if action_type:
        query &= Q(action_type=action_type)

    # 获取分页数据
    total_count = await UserAction.filter(query).count()
    actions = (
        await UserAction.filter(query)
        .order_by("-create_time")
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    if not actions:
        raise HTTPException(status_code=404, detail="用户行为历史记录未找到")

    # 格式化返回结果
    actions_data = [
        UserActionBase(
            paper_id=action.paper_id,
            action_type=action.action_type,
            action_value=action.action_value,
            extra_data=action.extra_data,
            create_time=action.create_time,
        )
        for action in actions
    ]

    return success(
        data={
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "actions": actions_data,
        }
    )


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
    # 获取所有标签名称
    tags = await Tag.all()
    tag_names = [tag.name for tag in tags]

    # 查询符合标签的论文
    query_filter = Q(primary_subject__startswith=tag_names[0])
    for tag_name in tag_names[1:]:
        query_filter |= Q(primary_subject__startswith=tag_name)

    # 按时间降序排列
    papers = await Arxiv.filter(query_filter).order_by("-date").limit(limit)

    # 构建推荐列表
    recommendations = []
    current_id = 1

    for paper in papers:
        recommendation = RecommendationResponse(
            id=current_id,
            user_id=None,
            paper={
                "id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.date,
                "source": paper.pdf_url,
                "tags": paper.primary_subject,
            },
            reason="基于标签表生成的热门推荐",
            recommendation_type="popular",
            tags=None,
            algorithm_details=None,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        recommendations.append(recommendation)
        current_id += 1

    return recommendations
