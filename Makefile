.PHONY: help up down restart logs ps build rebuild \
        api-logs web-logs db-logs redis-logs \
        shell-api shell-web shell-db shell-redis \
        format lint test migrate revision clean

# 默认目标：显示帮助
help:
	@echo "SparkLab 开发命令："
	@echo ""
	@echo "  容器编排"
	@echo "    make up             启动全部服务（后台）"
	@echo "    make down           停止全部服务"
	@echo "    make restart        重启全部服务"
	@echo "    make ps             查看服务状态"
	@echo "    make logs           跟随全部日志"
	@echo "    make build          构建镜像"
	@echo "    make rebuild        无缓存重新构建"
	@echo ""
	@echo "  单服务日志"
	@echo "    make api-logs       跟随 api 日志（默认最后 100 行）"
	@echo "    make web-logs       跟随 web 日志"
	@echo "    make db-logs        跟随 postgres 日志"
	@echo "    make redis-logs     跟随 redis 日志"
	@echo ""
	@echo "  进入容器"
	@echo "    make shell-api      进入 api-dev 容器"
	@echo "    make shell-web      进入 web-dev 容器"
	@echo "    make shell-db       进入 postgres psql"
	@echo "    make shell-redis    进入 redis-cli"
	@echo ""
	@echo "  开发"
	@echo "    make format         后端代码格式化（ruff format）"
	@echo "    make lint           后端代码检查（ruff check）"
	@echo "    make test           运行后端测试"
	@echo "    make migrate        应用数据库迁移到最新"
	@echo "    make revision m=xxx 生成新迁移（m 为描述）"
	@echo "    make clean          清理临时文件"

# --- 容器编排 ---
up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=100

build:
	docker compose build

rebuild:
	docker compose build --no-cache

# --- 单服务日志 ---
api-logs:
	docker logs -f --tail=100 sparklab-api-dev

web-logs:
	docker logs -f --tail=100 sparklab-web-dev

db-logs:
	docker logs -f --tail=100 sparklab-postgres

redis-logs:
	docker logs -f --tail=100 sparklab-redis

# --- 进入容器 ---
shell-api:
	docker exec -it sparklab-api-dev bash

shell-web:
	docker exec -it sparklab-web-dev sh

shell-db:
	docker exec -it sparklab-postgres psql -U postgres -d sparklab

shell-redis:
	docker exec -it sparklab-redis redis-cli

# --- 开发 ---
format:
	docker exec sparklab-api-dev uv run ruff format /app/server /app/package

lint:
	docker exec sparklab-api-dev uv run ruff check /app/server /app/package

test:
	docker exec sparklab-api-dev uv run pytest /app/test

migrate:
	docker exec sparklab-api-dev uv run alembic upgrade head

revision:
	@if [ -z "$(m)" ]; then echo "用法：make revision m=\"描述\""; exit 1; fi
	docker exec sparklab-api-dev uv run alembic revision --autogenerate -m "$(m)"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
