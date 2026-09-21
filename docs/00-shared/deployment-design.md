# 部署设计

Docker Compose 服务：`frontend`（Nginx）、`backend`（FastAPI）、`postgres`。前端 `/api` 和 SSE 反代到 backend；SSE 关闭代理缓冲并增加读取超时。

仓库根目录已提供 `docker-compose.yml`，启动顺序为 PostgreSQL 健康检查 → Alembic 迁移 → 固定 Seed → RAG 索引 → 后端 → 前端。前端 Nginx 对执行事件流单独设置 `proxy_buffering off`、`X-Accel-Buffering: no` 和长读取超时。

- 后端非 root 用户，健康检查 `/health/live`、`/health/ready`。
- PostgreSQL 使用命名卷；迁移为独立一次性命令，不在多副本启动时隐式执行。
- 环境分 local/test/demo/prod；Demo 固定 Seed 和数据截止日。
- 镜像使用版本标签和不可变 digest；发布保留上一版镜像。
- 日志写 stdout；生产环境由平台采集。
- 备份应用库后迁移；回滚优先回退镜像，破坏性迁移必须提供 downgrade/恢复方案。

验收命令目标：`docker compose up -d --build` → migration → seed → ready → smoke。

2026-09-20 已在 Windows 11、WSL 2.7.14、Docker Desktop 4.91.0、Docker Engine 29.8.0、Docker Compose 5.5.1 环境完成首次实机启动验收：镜像构建、PostgreSQL 健康检查、Alembic 迁移、固定 Seed、RAG 索引、后端健康检查及前端 Nginx 代理均通过。后端镜像固定安装 CPU 版 PyTorch，RAG 索引与 API 共享 Hugging Face 命名缓存卷，避免下载无用 CUDA 依赖和重复下载向量模型。

## 生产编排

生产部署使用根目录 `docker-compose.prod.yml`，不得直接使用演示编排：

- PostgreSQL 不发布宿主机端口，只允许 Compose 内部网络访问。
- `migration_owner`、`app_rw`、`text2sql_ro` 使用不同密码。
- 数据库密码和 `MODEL_SECRET_KEY` 通过只存在于服务器的 Secret 文件挂载。
- 后端以 `APP_ENV=prod` 启动，未配置可用真实模型时失败关闭，不回退 Fake。
- 前端和 API 只通过 Caddy 暴露；Caddy 使用域名自动申请和续期 HTTPS 证书。
- 常驻服务使用 `unless-stopped`，设置资源上限和 `json-file` 日志轮转。
- 默认只执行迁移和 RAG 知识索引，不向生产库写入固定演示经营数据。

### 首次部署

```bash
cp .env.prod.example .env.prod
mkdir -p secrets
openssl rand -base64 36 | tr -d '\n' > secrets/postgres_password.txt
openssl rand -base64 36 | tr -d '\n' > secrets/app_rw_password.txt
openssl rand -base64 36 | tr -d '\n' > secrets/text2sql_ro_password.txt
openssl rand -base64 48 | tr -d '\n' > secrets/model_secret_key.txt
chmod 600 .env.prod secrets/*.txt

docker compose --env-file .env.prod -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps -a
```

`.env.prod` 中的 `APP_DOMAIN` 必须先解析到服务器公网 IP，80/443 必须可访问，Caddy 才能签发证书。
模型 API Key 建议在 HTTPS 页面中首次录入，由后端使用稳定的 `MODEL_SECRET_KEY` 加密保存。

如果部署的是固定演示环境，先显式运行 Seed，再启动完整服务：

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d postgres
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm migrate
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile demo-data run --rm seed-demo
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm rag-index
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d backend frontend gateway
```

Secret 文件不会被 Git 跟踪。`model_secret_key.txt` 必须和数据库备份一起安全保管；丢失或替换后，
数据库内已有的模型 API Key 无法解密。PostgreSQL 初始化脚本仅在空数据卷首次启动时运行，已有数据卷
不能通过修改 Secret 文件自动轮换角色密码，密码轮换需执行受控 SQL 并同步 Secret。

### 发布前验收

- 在干净 Linux 主机上完成从零构建和启动。
- 验证 `migrate`、`rag-index` 为 `Exited (0)`，常驻服务为 healthy。
- 通过 HTTPS 验证问答、SSE 断线续传和大结果导出。
- 完成数据库备份与恢复演练。
- 验证宿主机和公网均不能访问 PostgreSQL 5432 与后端 8000。
