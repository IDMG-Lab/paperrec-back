# -*- coding:utf-8 -*-
"""
@Des: 基础模型
"""

from tortoise import fields
from tortoise.models import Model


class TimestampMixin(Model):
    create_time = fields.DatetimeField(auto_now_add=True, description='创建时间')
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        abstract = True


class UserWechat(TimestampMixin):
    city = fields.CharField(null=True, max_length=255, description='城市')
    country = fields.CharField(null=True, max_length=255, description='国家')
    headimgurl = fields.CharField(null=True, max_length=255, description='微信头像')
    nickname = fields.CharField(null=True, max_length=255, description='微信昵称')
    openid = fields.CharField(unique=True, max_length=255, description='openid')
    unionid = fields.CharField(unique=True, null=True, max_length=255, description='unionid')
    province = fields.CharField(null=True, max_length=255, description='省份')
    sex = fields.IntField(null=True, description='性别')
    user: fields.OneToOneRelation["UserWechat"] = \
        fields.OneToOneField("arxivdb.User", related_name="wechat", on_delete=fields.CASCADE)

    class Meta:
        table_description = "用户微信"
        table = "user_wechat"


class User(TimestampMixin):
    role: fields.ManyToManyRelation["Role"] = \
        fields.ManyToManyField("arxivdb.Role", related_name="user", on_delete=fields.CASCADE)
    tag: fields.ManyToManyRelation["Tag"] = \
        fields.ManyToManyField("arxivdb.Tag", related_name="user", on_delete=fields.CASCADE)
    username = fields.CharField(null=True, max_length=20, description="用户名")
    user_type = fields.BooleanField(default=False, description="用户类型 True:超级管理员 False:普通管理员")
    password = fields.CharField(null=True, max_length=255)
    nickname = fields.CharField(default='binkuolo', max_length=255, description='昵称')
    user_phone = fields.CharField(null=True, description="手机号", max_length=11)
    user_email = fields.CharField(null=True, description='邮箱', max_length=255)
    full_name = fields.CharField(null=True, description='姓名', max_length=255)
    user_status = fields.IntField(default=0, description='0未激活 1正常 2禁用')
    header_img = fields.CharField(null=True, max_length=255, description='头像')
    sex = fields.IntField(default=0, null=True, description='0未知 1男 2女')
    remarks = fields.CharField(null=True, max_length=30, description="备注")
    client_host = fields.CharField(null=True, max_length=19, description="访问IP")
    has_selected_tags = fields.BooleanField(default=False, description="是否已选择标签")
    wechat: fields.OneToOneRelation[UserWechat]

    class Meta:
        table_description = "用户表"
        table = "user"


class Paper(TimestampMixin):
    tag: fields.ManyToManyRelation["Tag"] = \
        fields.ManyToManyField("arxivdb.Tag", related_name="paper", on_delete=fields.CASCADE)
    title = fields.CharField(max_length=255, description="论文标题")
    abstract = fields.TextField(null=True, description="论文摘要")
    authors = fields.TextField(null=True, description="作者列表")
    published_date = fields.DatetimeField(null=True, description="发表日期")
    source = fields.CharField(max_length=255, null=True, description="来源")
    popularity = fields.IntField(default=0, description="论文热度，用于排序推荐")

    class Meta:
        table_description = "论文表"
        table = "paper"


class Tag(TimestampMixin):
    user: fields.ManyToManyRelation[User]
    paper: fields.ManyToManyRelation[Paper]
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, unique=True, description="标签名称")
    popularity = fields.IntField(default=0, description="标签热度，用于发现流行主题")

    class Meta:
        table_description = "标签表"
        table = "tag"


class UserAction(TimestampMixin):
    user: fields.ForeignKeyRelation[User] = \
        fields.ForeignKeyField("arxivdb.User", related_name="actions", on_delete=fields.CASCADE)
    paper: fields.ForeignKeyRelation[Paper] = \
        fields.ForeignKeyField("arxivdb.Paper", related_name="actions", on_delete=fields.CASCADE)
    action_type = fields.CharField(max_length=50, description="行为类型，比如view（浏览）、like（点赞）、favorite（收藏）等")
    action_value = fields.FloatField(default=1.0, description="行为权重，用户行为对推荐的重要程度")
    extra_data = fields.JSONField(null=True, description="额外信息，比如行为来源、设备类型等")

    class Meta:
        table_description = "用户行为记录表"
        table = "user_action"


class UserProfile(TimestampMixin):
    user: fields.OneToOneRelation[User] = \
        fields.OneToOneField("arxivdb.User", related_name="profile", on_delete=fields.CASCADE)
    preferences = fields.JSONField(description="用户偏好，比如感兴趣的标签分布")
    last_updated = fields.DatetimeField(auto_now=True, description="最后更新时间")

    class Meta:
        table_description = "用户偏好画像表"
        table = "user_profile"


class Recommendation(TimestampMixin):
    tags: fields.ManyToManyRelation[Tag] = \
        fields.ManyToManyField("arxivdb.Tag", related_name="recommendation", on_delete=fields.CASCADE)
    user: fields.ForeignKeyRelation[User] = \
        fields.ForeignKeyField("arxivdb.User", related_name="recommendation", on_delete=fields.CASCADE)
    paper: fields.ForeignKeyRelation[Paper] = \
        fields.ForeignKeyField("arxivdb.Paper", related_name="recommendation", on_delete=fields.CASCADE)
    reason = fields.CharField(max_length=255, null=True, description="推荐理由")
    recommendation_type = fields.CharField(
        max_length=50, default="content_based", description="推荐类型 content_based/collaborative/hybrid"
    )

    class Meta:
        table_description = "推荐记录表"
        table = "recommendation"


class RecommendationParams(TimestampMixin):
    algorithm = fields.CharField(max_length=50, description="算法名称，例如content_based/collaborative/hybrid")
    params = fields.JSONField(description="算法的参数配置，例如权重、阈值等")
    description = fields.TextField(null=True, description="参数说明")

    class Meta:
        table_description = "推荐算法参数表"
        table = "recommendation_params"


class TagWeight(TimestampMixin):
    paper: fields.ForeignKeyRelation[Paper] = \
        fields.ForeignKeyField("arxivdb.Paper", related_name="tag_weights", on_delete=fields.CASCADE)
    tag: fields.ForeignKeyRelation[Tag] = \
        fields.ForeignKeyField("arxivdb.Tag", related_name="tag_weights", on_delete=fields.CASCADE)
    weight = fields.FloatField(description="权重值，用于表示该标签与论文的相关性")

    class Meta:
        table_description = "标签权重表"
        table = "tag_weight"


class PaperAnnotation(TimestampMixin):
    user: fields.ForeignKeyRelation["User"] = \
        fields.ForeignKeyField("arxivdb.User", related_name="annotations", on_delete=fields.CASCADE)
    arxiv_id = fields.CharField(max_length=100, description="外部论文唯一标识符")
    content = fields.TextField(description="标注内容")  # 用户标注的内容

    class Meta:
        table_description = "论文标注表"
        table = "paper_annotation"


class UserNotification(TimestampMixin):
    user: fields.ForeignKeyRelation["User"] = \
        fields.ForeignKeyField("arxivdb.User", related_name="notifications", on_delete=fields.CASCADE)
    message = fields.TextField(description="通知内容")
    is_read = fields.BooleanField(default=False, description="是否已读")

    class Meta:
        table_description = "用户通知表"
        table = "user_notification"


class PaperFavorite(TimestampMixin):
    user: fields.ForeignKeyRelation["User"] = \
        fields.ForeignKeyField("arxivdb.User", related_name="favorites", on_delete=fields.CASCADE)
    arxiv_id = fields.CharField(max_length=100, description="外部论文唯一标识符")

    class Meta:
        table_description = "论文收藏表"
        table = "paper_favorite"


class RecommendationLog(TimestampMixin):
    user: fields.ForeignKeyRelation["User"] = \
        fields.ForeignKeyField("arxivdb.User", related_name="recommendation_logs", on_delete=fields.CASCADE)
    recommendation: fields.ForeignKeyRelation["Recommendation"] = \
        fields.ForeignKeyField("arxivdb.Recommendation", related_name="logs", on_delete=fields.CASCADE)
    interaction = fields.CharField(max_length=50, description="用户交互行为，例如click（点击）、ignore（忽略）")
    timestamp = fields.DatetimeField(auto_now_add=True, description="行为时间")

    class Meta:
        table_description = "推荐日志表"
        table = "recommendation_log"


class LearningPath(TimestampMixin):
    user: fields.ForeignKeyRelation["User"] = \
        fields.ForeignKeyField("arxivdb.User", related_name="learning_paths", on_delete=fields.CASCADE)
    paper_ids = fields.JSONField(description="论文 ID 列表，按推荐顺序存储")
    progress = fields.FloatField(default=0.0, description="学习进度，百分比")

    class Meta:
        table_description = "用户学习路径表"
        table = "learning_path"


class Role(TimestampMixin):
    user: fields.ManyToManyRelation[User]
    role_name = fields.CharField(max_length=15, description="角色名称")
    access: fields.ManyToManyRelation["Access"] = \
        fields.ManyToManyField("arxivdb.Access", related_name="role", on_delete=fields.CASCADE)
    role_status = fields.BooleanField(default=False, description="True:启用 False:禁用")
    role_desc = fields.CharField(null=True, max_length=255, description='角色描述')

    class Meta:
        table_description = "角色表"
        table = "role"


class Access(TimestampMixin):
    role: fields.ManyToManyRelation[Role]
    access_name = fields.CharField(max_length=15, description="权限名称")
    parent_id = fields.IntField(default=0, description='父id')
    scopes = fields.CharField(unique=True, max_length=255, description='权限范围标识')
    access_desc = fields.CharField(null=True, max_length=255, description='权限描述')
    menu_icon = fields.CharField(null=True, max_length=255, description='菜单图标')
    is_check = fields.BooleanField(default=False, description='是否验证权限 True为验证 False不验证')
    is_menu = fields.BooleanField(default=False, description='是否为菜单 True菜单 False不是菜单')

    class Meta:
        table_description = "权限表"
        table = "access"


class AccessLog(TimestampMixin):
    user_id = fields.IntField(description="用户ID")
    target_url = fields.CharField(null=True, description="访问的url", max_length=255)
    user_agent = fields.CharField(null=True, description="访问UA", max_length=255)
    request_params = fields.JSONField(null=True, description="请求参数get|post")
    ip = fields.CharField(null=True, max_length=32, description="访问IP")
    note = fields.CharField(null=True, max_length=255, description="备注")

    class Meta:
        table_description = "用户操作记录表"
        table = "access_log"


class SystemParams(TimestampMixin):
    params_name = fields.CharField(unique=True, max_length=255, description="参数名")
    params = fields.JSONField(description="参数")

    class Meta:
        table_description = "系统参数表"
        table = "system_params"
