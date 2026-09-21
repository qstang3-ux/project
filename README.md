# 经管之星

企业经营数据智能问数平台。当前前后端主链路、真实模型 Agent、向量 RAG、澄清、问答日志、反馈校对和结果导出均已实现。

## 文档入口

从 [`docs/README.md`](docs/README.md) 开始。前后端开发分别从各自目录进入：

- [前端任务入口](frontend/README.md)
- [后端任务入口](backend/README.md)
- [共享产品范围](docs/00-shared/product-scope.md)
- [开发 Backlog](docs/01-project-management/backlog.md)

## 目标技术栈

- Frontend：React + TypeScript + Vite + Ant Design + ECharts
- Backend：Python + FastAPI + SQLAlchemy + Alembic
- Database：PostgreSQL
- Deploy：Docker Compose + Nginx

前端和后端可以在两个独立对话中并行开发，但必须共同遵循后端维护的 OpenAPI 契约。

## 目录归属

- `frontend/`：全部前端源代码、测试、构建配置和前端文档。
- `backend/`：全部后端源代码、测试、迁移、Seed、评测、部署配置和后端文档。
- `docs/`：前后端共享的产品、验收、架构和项目管理基线。
- `docs/DEMONSTRATION.md`：唯一的演示资料归档；不作为正式需求或开发优先级。

两个独立开发对话分别复制 `frontend/README.md` 和 `backend/README.md` 中的“新对话开始方式”即可。两侧都通过根目录规则和共享文档获得完整需求，通过 OpenAPI 协作，避免重复或猜测字段。

## 全栈容器启动

根目录 `docker-compose.yml` 编排 PostgreSQL、迁移、Seed、RAG 索引、FastAPI 和 Nginx。模型密钥只通过环境变量注入，不写入 Compose 文件。

```powershell
Copy-Item .env.example .env
# 在 .env 中设置 MODEL_SECRET_KEY 和真实模型变量
docker compose up -d --build
```

启动完成后访问 `http://127.0.0.1:8080/qa`。Nginx 已为问答 SSE 路由关闭代理缓冲并设置长连接超时。

## 生产部署

生产环境使用独立的 `docker-compose.prod.yml`：数据库不发布宿主机端口，数据库角色密码和
`MODEL_SECRET_KEY` 从 Docker Secret 文件读取，Caddy 在 80/443 提供自动 HTTPS。完整步骤见
[`docs/00-shared/deployment-design.md`](docs/00-shared/deployment-design.md)。

```bash
cp .env.prod.example .env.prod
mkdir -p secrets
# 分别生成 secrets/README.md 列出的四个 Secret 文件
docker compose --env-file .env.prod -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

生产编排默认不写入演示经营数据；需要固定演示 Seed 时，必须显式运行 `seed-demo` profile。

## 质量门禁

`.github/workflows/ci.yml` 在 push 和 pull request 时执行前端 Lint、类型检查、单测、构建、
Chromium E2E，后端 Ruff、格式、MyPy、覆盖率测试，以及开发/生产 Compose 校验和镜像构建。
