# SparkLab Web 镜像（多阶段：development 用于 vite dev server，production 用于构建产物）

# ============================================================================
# 基础阶段：装 pnpm 和依赖
# ============================================================================
FROM node:20-alpine AS base

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# 先复制依赖清单以利用 Docker 层缓存
COPY web/package.json web/pnpm-lock.yaml* /app/

RUN pnpm install --frozen-lockfile || pnpm install

# ============================================================================
# 开发阶段：源码通过 volume 挂载，vite dev server 热重载
# ============================================================================
FROM base AS development

EXPOSE 5173

CMD ["pnpm", "run", "dev", "--host"]

# ============================================================================
# 生产阶段：构建静态产物（后续如需部署再用）
# ============================================================================
FROM base AS production

COPY web/ /app/

RUN pnpm run build

# 用 nginx 或其他静态服务器托管 /app/dist，留待生产部署时定义
