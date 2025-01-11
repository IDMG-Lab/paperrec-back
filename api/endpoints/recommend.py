# -*- coding:utf-8 -*-
"""
@Des: 个性化推荐
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Security, Body
from typing import List, Optional
from datetime import datetime

from tortoise.expressions import Q
from core.Auth import get_current_user, check_permissions
from core.Response import success
from schemas.recommend import RecommendationResponse, UserProfileResponse, UserActionBase, PaperBase
from models.arxivdb import Paper, UserAction, UserProfile, Tag, PaperFavorite, PaperAnnotation, Recommendation
from models.scrape import Arxiv

router = APIRouter(prefix="/personalized")


@router.get("/search", summary="搜索论文")
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
    :return: 搜索结果和总条目数
    """
    # 搜索条件
    search_condition = (
        Q(title__icontains=query) |
        Q(abstract__icontains=query) |
        Q(authors__icontains=query) |
        Q(primary_subject__icontains=query) |
        Q(subjects__icontains=query)
    )

    # 获取总条目数
    total_count = await Arxiv.filter(search_condition).count()

    # 获取当前页数据
    papers = await Arxiv.filter(search_condition).order_by("-date").offset(offset).limit(limit)

    # 如果没有找到相关论文
    if not papers:
        raise HTTPException(status_code=404, detail="没有找到相关论文")

    # 构造返回数据
    result = {
        "total_count": total_count,
        "papers": [
            {
                "id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "published_date": paper.date,
                "source": paper.pdf_url,
                "tags": paper.primary_subject,
            }
            for paper in papers
        ],
    }

    return success(msg="搜索成功", data=result)


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

    for paper in papers:
        # 保存推荐记录到数据库
        await Recommendation.create(
            user_id=user_id,
            arxiv_id=paper.arxiv_id,
            reason=f"推荐标签: {tag_name}",
            recommendation_type="tag_based",  # 推荐类型
            status="pending",  # 初始状态
            priority=0,  # 推荐优先级
            extra_data={"source": paper.pdf_url, "tags": paper.primary_subject},
        )

        # 构建响应对象
        recommendation = RecommendationResponse(
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
        )
        recommendations.append(recommendation)

    return recommendations


@router.get("/user/recommendations",
            summary="获取用户历史推荐列表",
            dependencies=[Security(check_permissions)]
            )
async def get_user_recommendations(
    current_user: dict = Depends(get_current_user),
    start_time: Optional[datetime] = Query(None, description="起始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    recommendation_type: Optional[str] = Query(None, description="推荐类型（如content_based、collaborative）"),
    status: Optional[str] = Query(None, description="推荐状态（如pending、viewed、accepted、ignored）"),
    page: int = Query(1, ge=1, description="页码，默认第 1 页"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数，默认 10 条"),
):
    """
    获取用户历史推荐列表
    :param current_user: 当前登录用户信息
    :param start_time: 推荐记录的起始时间
    :param end_time: 推荐记录的结束时间
    :param recommendation_type: 推荐类型过滤条件
    :param status: 推荐状态过滤条件
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
    if recommendation_type:
        query &= Q(recommendation_type=recommendation_type)
    if status:
        query &= Q(status=status)

    # 获取分页数据
    total_count = await Recommendation.filter(query).count()
    recommendations = (
        await Recommendation.filter(query)
        .order_by("-create_time")
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    if not recommendations:
        raise HTTPException(status_code=404, detail="用户历史推荐记录未找到")

    # 格式化返回结果
    recommendations_data = [
        {
            "arxiv_id": recommendation.arxiv_id,
            "reason": recommendation.reason,
            "recommendation_type": recommendation.recommendation_type,
            "status": recommendation.status,
            "priority": recommendation.priority,
            "extra_data": recommendation.extra_data,
            "create_time": recommendation.create_time,
        }
        for recommendation in recommendations
    ]

    return success(
        data={
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "recommendations": recommendations_data,
        }
    )


@router.post("/user/actions", summary="记录用户行为", dependencies=[Security(check_permissions)])
async def record_user_action(action: UserActionBase, current_user: dict = Depends(get_current_user)):
    """
    记录用户行为
    :param current_user: 当前用户信息
    :param action: 用户行为数据
    """
    user_id = current_user["user_id"]

    # 在用户行为表中记录行为数据
    await UserAction.create(
        user_id=user_id,
        arxiv_id=action.arxiv_id,
        action_type=action.action_type,
        action_value=action.action_value,
        session_id=action.session_id,
        ip_address=action.ip_address,
        device_type=action.device_type,
        location=action.location,
        extra_data=action.extra_data,  # 保存额外数据
    )

    # 基于行为更新用户画像
    # await update_user_profile(action, user_id)

    return success(msg="行为记录成功")


@router.get("/user/actions", summary="获取用户行为历史", dependencies=[Security(check_permissions)])
async def get_user_actions(
    current_user: dict = Depends(get_current_user),
    start_time: Optional[datetime] = Query(None, description="起始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    action_type: Optional[str] = Query(None, description="行为类型（如浏览、收藏、点赞等）"),
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

    # 获取总记录数
    total_count = await UserAction.filter(query).count()

    # 查询用户行为数据并分页
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
        {
            "arxiv_id": action.arxiv_id,
            "action_type": action.action_type,
            "action_value": action.action_value,
            "session_id": action.session_id,
            "ip_address": action.ip_address,
            "device_type": action.device_type,
            "location": action.location,
            "extra_data": action.extra_data,
        }
        for action in actions
    ]

    # 返回分页结果
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

    # 获取用户画像数据
    user_profile = await UserProfile.get_or_none(user_id=user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="用户画像未找到")

    # 返回用户画像数据
    return UserProfileResponse(
        user_id=user_profile.user_id,
        preferences=user_profile.preferences,
        activity_score=user_profile.activity_score,
        tags=user_profile.tags,
        last_updated=user_profile.update_time
    )


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

    for paper in papers:
        recommendation = RecommendationResponse(
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
        )
        recommendations.append(recommendation)

    return recommendations


@router.post("/favorites", summary="收藏论文", dependencies=[Security(check_permissions)])
async def add_favorite(
    arxiv_id: str = Body(..., description="论文ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    收藏论文
    :param arxiv_id: 外部论文ID
    :param current_user: 当前用户信息
    """
    user_id = current_user["user_id"]

    # 检查是否已经收藏过
    existing_favorite = await PaperFavorite.get_or_none(user_id=user_id, arxiv_id=arxiv_id)
    if existing_favorite:
        raise HTTPException(status_code=400, detail="该论文已收藏")

    # 添加收藏
    await PaperFavorite.create(user_id=user_id, arxiv_id=arxiv_id)
    return success(msg="论文收藏成功")


@router.delete("/favorites", summary="取消收藏论文", dependencies=[Security(check_permissions)])
async def remove_favorite(
    arxiv_id: str = Query(..., description="论文ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    取消收藏论文
    :param arxiv_id: 外部论文ID
    :param current_user: 当前用户信息
    """
    user_id = current_user["user_id"]

    # 检查是否存在收藏记录
    favorite = await PaperFavorite.get_or_none(user_id=user_id, arxiv_id=arxiv_id)
    if not favorite:
        raise HTTPException(status_code=404, detail="收藏记录不存在")

    # 删除收藏记录
    await favorite.delete()
    return success(msg="论文收藏已取消")


@router.get("/favorites", summary="获取收藏论文列表", dependencies=[Security(check_permissions)])
async def get_favorites(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取用户收藏的论文列表
    :param current_user: 当前用户信息
    :param limit: 每页条数
    :param offset: 偏移量
    """
    user_id = current_user["user_id"]
    favorites = await PaperFavorite.filter(user_id=user_id).offset(offset).limit(limit)

    # 从数据库获取论文详细信息
    result = []
    for favorite in favorites:
        paper = await Arxiv.get_or_none(arxiv_id=favorite.arxiv_id)
        if paper:
            result.append({
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors,
                "published_date": paper.date,
                "source": paper.pdf_url,
                "tags": paper.primary_subject,
            })

    return success(msg="收藏论文列表获取成功", data=result)


@router.post("/annotations", summary="添加论文标注", dependencies=[Security(check_permissions)])
async def create_annotation(
    arxiv_id: str,
    content: str,
    current_user: dict = Depends(get_current_user),
):
    """
    添加论文标注
    :param arxiv_id: 论文ID
    :param content: 标注内容
    :param current_user: 当前登录用户
    """
    user_id = current_user["user_id"]

    # 创建新的标注
    annotation = await PaperAnnotation.create(user_id=user_id, arxiv_id=arxiv_id, content=content)
    return success(msg="标注创建成功", data={
        "id": annotation.id,
        "content": annotation.content,
        "create_time": annotation.create_time,
    })


@router.put("/annotations/{annotation_id}", summary="修改论文标注", dependencies=[Security(check_permissions)])
async def update_annotation(
    annotation_id: int,
    content: str,
    current_user: dict = Depends(get_current_user),
):
    """
    修改论文标注
    :param annotation_id: 标注ID
    :param content: 新的标注内容
    :param current_user: 当前登录用户
    """
    user_id = current_user["user_id"]

    # 获取标注
    annotation = await PaperAnnotation.get_or_none(id=annotation_id, user_id=user_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="标注不存在或无权限修改")

    # 更新标注
    annotation.content = content
    await annotation.save()

    return success(msg="标注更新成功", data={
        "id": annotation.id,
        "content": annotation.content,
        "update_time": annotation.update_time,
    })


@router.delete("/annotations/{annotation_id}", summary="删除论文标注", dependencies=[Security(check_permissions)])
async def delete_annotation(annotation_id: int, current_user: dict = Depends(get_current_user)):
    """
    删除论文标注
    :param annotation_id: 标注ID
    :param current_user: 当前登录用户
    """
    user_id = current_user["user_id"]

    # 获取标注
    annotation = await PaperAnnotation.get_or_none(id=annotation_id, user_id=user_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="标注不存在或无权限删除")

    # 删除标注
    await annotation.delete()
    return success(msg="标注删除成功")


@router.get("/annotations/{paper_id}", summary="获取论文标注", dependencies=[Security(check_permissions)])
async def get_annotations(paper_id: str):
    """
    获取论文标注
    :param paper_id: 论文ID
    """
    # 查询标注信息并关联用户表
    annotations = await PaperAnnotation.filter(arxiv_id=paper_id).select_related("user").all()
    if not annotations:
        raise HTTPException(status_code=404, detail="标注不存在")

    result = []
    for annotation in annotations:
        result.append({
            "id": annotation.id,
            "content": annotation.content,
            "create_time": annotation.create_time,
            "user": {
                "username": annotation.user.username,  # 用户名
                "nickname": annotation.user.nickname,  # 昵称
            },
        })

    return success(msg="标注获取成功", data=result)