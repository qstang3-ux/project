# 经管之星 Agent 平台测试执行记录

> 执行日期：2026-09-20  
> 测试环境：Windows / Chrome Chromium / PostgreSQL 16 / Seed `20260915`  
> 前端：`http://127.0.0.1:5173`  
> 后端：`http://127.0.0.1:8000`  
> 状态：已完成；功能与安全通过，真实模型性能偏差已由产品方接受，不阻断发布

## 1. 代码与质量门禁

| 时间 | 项目 | 命令 | 结果 | 证据/备注 |
|---|---|---|---|---|
| 10:30 | 前端 | `pnpm lint` | Pass | 0 error / 0 warning |
| 10:30 | 前端 | `pnpm typecheck` | Pass | TypeScript 严格检查通过 |
| 10:31 | 前端 | `pnpm test` | Pass | 30 files / 63 tests；仅 jsdom pseudo-element 能力提示 |
| 10:31 | 前端 | `pnpm build` | Pass with warning | `ResultChart` 634.77kB、主包 708.38kB 超过 500kB |
| 10:32 | 前端 | `pnpm e2e` | Pass | 首轮 10/10 |
| 11:01 | 前端 | 修复后重跑 lint/typecheck/test/build | Pass | 30 files / 63 tests；构建 warning 同上 |
| 11:02 | 前端 | `pnpm e2e` | Pass | 11/11，含 1024/1280/1440 响应式回归 |
| 10:30 | 后端 | `ruff check .` | Pass | 静态规范通过 |
| 10:30 | 后端 | `ruff format --check .` | Pass | 85 files（首轮） |
| 10:30 | 后端 | `mypy app` | Pass | 45 source files |
| 10:31 | 后端 | `pytest -q` | Pass/Skip | 169 passed / 27 skipped；未注入 PostgreSQL 测试 URL |
| 10:33 | 后端 | PostgreSQL 集成测试 | Pass | 27 passed / 169 deselected |
| 10:35 | 后端 | 首轮 coverage | Fail | overall 59%，低于 overall 80% / services 85% / validator branch 100% 门槛 |
| 11:05 | 后端 | 修复后 ruff/format/mypy | Pass | 88 files formatted；mypy 45 source files |
| 11:06 | 后端 | PostgreSQL 全量 pytest + branch coverage | Pass | 222/222；overall 86.10% |
| 11:06 | 后端 | `scripts/check_coverage.py` | Pass | services 85.43%，validator 100% |
| 11:06 | 后端 | 集成测试状态隔离 | Pass | 测试前后 DeepSeek active ID 一致 |

## 2. 数据库、迁移与健康检查

| 检查 | 结果 | 说明 |
|---|---|---|
| PostgreSQL 就绪 | Pass | 本地 5432 可连接 |
| Alembic current | Pass | `20260918_0013 (head)` |
| Seed verify | Pass | `python -m app.seed --verify` exit 0 |
| `/health/live` | Pass | HTTP 200，service ok |
| `/health/ready` | Pass | HTTP 200，database ok |
| 只读查询账号 | Pass | PostgreSQL 集成链路与安全测试通过 |

## 3. Agent、RAG 与安全

| 测试 | 结果 | 关键指标 | 产物 |
|---|---|---|---|
| RAG 30 题 | Pass | Recall@5 100%，MRR 0.7539，18 docs，BAAI/bge-small-zh-v1.5，512 维 | `../backend/.runtime/qa-rag-evaluation-20260920.json` |
| Prompt Injection 16 题 | Pass | attack 16/16，regression 30/30，containment 100%，modelCalls 0 | `../backend/.runtime/qa-prompt-injection-report-20260920.json` |
| 真实模型 8 条核心 | 首轮 Fail / 修复后 Pass | 6/8 -> 8/8；最终报告离线重校验通过 | `../backend/.runtime/qa-real-model-smoke-20260920-final.json` |
| 真实模型危险请求 | Pass | 5/5 安全拒绝，均未进入 SQL 执行 | 同上 |
| 真实模型性能 | Accepted deviation | 首轮 avg 14,567.6ms；修复后 avg 13,165ms、P50 11,995ms、max 21,657ms；产品方确认本轮不作为发布门槛 | 同上 |
| Fake 20 并发问数 | Pass | 20/20 completed，P50 4,069.1ms，P95 4,162.3ms，max 4,205.4ms | 本执行记录 |
| CRUD 性能 | Pass | 120 requests，全部 2xx，P50 6.33ms，P95 19.16ms，max 43.64ms | 本执行记录 |

## 4. 真实平台交互记录

| 场景 | 结果 | 实际观察 |
|---|---|---|
| 商业目标 Top 5 | Pass | 5 行降序；北京 7950、上海 7070、浙江 6460、江苏 5560、山东 4090 万；表格/图表/总结一致 |
| 简单算术 `1+1` | Pass | 识别为 chat，返回 `1 + 1 = 2。`，符合后端意图设计 |
| 域外天气问题 | Pass | 固定边界提示，无 SQL |
| `SELECT 1; DROP TABLE` | Pass | 安全拒绝；无 selected objects、无 RAG、无 SQL 执行节点 |
| 模型配置密钥 | Pass | 前端不回显明文 API Key，仅显示 mask |
| 问答日志 | Pass | 列表、筛选、分页、详情、节点轨迹可用 |
| 1024×720 图表 | 首轮 Fail / 修复后 Pass | 首轮 assistant 512/686、chart 468/664；修复后 E2E 三档视口无横向溢出 |
| 测试后真实模型配置 | 首轮 Fail / 修复后 Pass | 全量 222 tests 前后 DeepSeek active ID 保持一致 |

## 5. 缺陷沟通闭环

| 缺陷 | 负责人 | 首轮反馈 | 当前状态 |
|---|---|---|---|
| FE-001 1024 图表横向溢出 | 前端任务“实现经管之星前端” | 增加容器宽度约束、ResizeObserver、三档 E2E | Fixed / 独立 E2E Pass |
| BE-001 集成测试污染 active 模型 | 后端任务“实现经管之星后端” | 保存并恢复测试前 active 集合，增加回归断言 | Closed / 独立全套复验 Pass |
| BE-002 coverage 门禁不达标 | 后端任务“实现经管之星后端” | 新增 branch coverage 与分层门禁 | Closed / 86.10%、85.43%、100% |
| BE-003 真实模型核心 6/8 | 后端任务“实现经管之星后端” | 精确处理标量 CTE；约束分类输出并增加闭集兜底 | Closed / 8/8 + 5/5 |
| PERF-001 真实模型平均耗时超标 | 后端任务“实现经管之星后端” | BGE 预热后改善到 13.17s；供应商串行调用仍是瓶颈 | Accepted / 不阻断发布 |

## 6. 截图索引

### BE-001 修复前：测试污染后真实问答不可用

![集成测试污染 active 模型后，真实问答提示未配置可用真实模型](evidence/BUG-BE-001-model-config-pollution.jpg)

### BE-001 恢复后：真实模型、SQL、表格与图表重新可用

![恢复 active 模型后，产品线收入占比真实问答成功](evidence/VERIFY-BE-001-model-config-restored.jpg)

> FE-001 在用户提出截图要求前已经完成修复；修复前仅保留 DOM 尺寸证据，没有截图。报告明确保留该证据缺口，不用修复后画面冒充修复前截图。
