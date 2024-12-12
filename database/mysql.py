# -*- coding:utf-8 -*-
"""
@Des: mysql数据库
"""

from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise
import os

# -----------------------数据库配置-----------------------------------
DB_ORM_CONFIG = {
    "connections": {
        "arxivdb": {
            'engine': 'tortoise.backends.mysql',
            "credentials": {
                'host': os.getenv('BASE_HOST', '10.101.168.97'),
                'user': os.getenv('BASE_USER', 'hudan'),
                'password': os.getenv('BASE_PASSWORD', '123456'),
                'port': int(os.getenv('BASE_PORT', 3336)),
                'database': os.getenv('BASE_DB', 'arxivdb'),
            }
        },
        "scrape": {
            'engine': 'tortoise.backends.mysql',
            "credentials": {
                'host': os.getenv('DB2_HOST', '10.101.168.97'),
                'user': os.getenv('DB2_USER', 'hudan'),
                'password': os.getenv('DB2_PASSWORD', '123456'),
                'port': int(os.getenv('DB2_PORT', 3336)),
                'database': os.getenv('DB2_DB', 'scrape'),
            }
        },
        # "db3": {
        #     'engine': 'tortoise.backends.mysql',
        #     "credentials": {
        #         'host': os.getenv('DB3_HOST', '127.0.0.1'),
        #         'user': os.getenv('DB3_USER', 'root'),
        #         'password': os.getenv('DB3_PASSWORD', '123456'),
        #         'port': int(os.getenv('DB3_PORT', 3306)),
        #         'database': os.getenv('DB3_DB', 'db3'),
        #     }
        # },

    },
    "apps": {
        "arxivdb": {"models": ["models.arxivdb"], "default_connection": "arxivdb"},
        "scrape": {"models": ["models.scrape"], "default_connection": "scrape"},
        # "db3": {"models": ["models.db3"], "default_connection": "db3"}
    },
    'use_tz': False,
    'timezone': 'Asia/Shanghai'
}


async def register_mysql(app: FastAPI):
    # 注册数据库
    try:
        await Tortoise.init(config=DB_ORM_CONFIG)
        print("数据库连接成功。")
        # await Tortoise.generate_schemas()  # 添加表

    except Exception as e:
        print(f"错误: {e}")
    finally:
        await Tortoise.close_connections()
