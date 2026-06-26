"""数据访问层 - 封装 SQLAlchemy 查询。

设计约定：
- 每个仓储管理单一聚合根（User / Template / Playbook ...）
- 路由层不许绕过仓储直接操作模型
- 仓储不感知 HTTP，参数是普通 Python 类型或 Pydantic 模型
"""
