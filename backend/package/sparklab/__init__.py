"""SparkLab 业务包。

模块分层：
- config        全局配置
- auth          认证、激活码、JWT、密码哈希
- storage       Postgres / Redis 基础设施
- models        SQLAlchemy 模型
- schemas       Pydantic 数据结构
- repositories  数据访问层
- services      用例层（业务流程）
- utils         通用工具
"""

__version__ = "0.1.0"
