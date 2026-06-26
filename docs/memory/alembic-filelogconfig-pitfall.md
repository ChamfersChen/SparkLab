---
name: alembic-filelogconfig-pitfall
description: alembic env.py 的 fileConfig 会默认禁用已有 logger，必须传 disable_existing_loggers=False
metadata: 
  node_type: memory
  type: reference
  originSessionId: 715cefc0-c1a6-4ffe-b33c-199a4e7c0eb8
---

**症状**：FastAPI 应用启动时能打印前几条日志（如 "SparkLab API starting..."），但之后所有业务日志和访问日志都不再输出，看上去像"请求没进来"。

**根因**：Python 标准库 `logging.config.fileConfig()` 默认 `disable_existing_loggers=True`，会**禁用调用之前已经创建的所有 logger**。

Alembic 模板的 `env.py` 顶部就有：

```python
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
```

如果 `_run_migrations()` 在 lifespan 中被同步调用（如 SparkLab 现在的做法），执行顺序是：

1. `setup_logging()` 创建 `sparklab` 和 `sparklab.access` logger
2. lifespan 调 `_run_migrations()` → Alembic 调 `fileConfig()` → **禁用所有现有 logger**
3. 之后 `logger.info(...)` 全部静默

**修复**：

```python
fileConfig(config.config_file_name, disable_existing_loggers=False)
```

**验证**：`backend/test/unit/test_alembic_logging.py` 已加回归测试，扫描 env.py 源码确保该参数存在。

**适用范围**：任何在应用进程内调用 Alembic 命令（`command.upgrade` / `command.revision` 等）的项目，都要注意这个坑。仅在 CLI 单独跑 `alembic` 命令时不会触发，因为彼时还没有其他 logger。

相关：[[sparklab-dev-constraints]]
