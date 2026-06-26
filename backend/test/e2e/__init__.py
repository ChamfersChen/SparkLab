"""端到端测试 - 启动 FastAPI 应用，发真实 HTTP 请求。

依赖 conftest.py 提供的 `client` fixture，会触发 lifespan，因此需要
postgres + redis 容器在运行。
"""
