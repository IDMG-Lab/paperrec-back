# -*- coding:utf-8 -*-
"""
@Des: 论文模型
"""

from tortoise import fields
from tortoise.models import Model


class Arxiv(Model):
    arxiv_id = fields.CharField(max_length=100, unique=True, pk=True)  # 主键
    title = fields.CharField(max_length=500)
    authors = fields.CharField(max_length=8000)
    date = fields.DateField()
    abstract = fields.CharField(max_length=5000)
    pdf_url = fields.CharField(max_length=500)
    primary_subject = fields.CharField(max_length=500)
    subjects = fields.CharField(max_length=1000)

    class Meta:
        table = "arxiv"  # 表名

