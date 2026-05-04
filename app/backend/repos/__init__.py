"""仓储层: 17 张业务表 + 1 元数据表的 CRUD。

设计: 不为每张表写独立 repo 类, 而是用 TableSpec(specs.py) + GenericRepo(generic.py)
配置驱动, 避免 17 份高度雷同的样板代码。
"""
