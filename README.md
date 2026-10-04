# Fintech API Test — Mock 信贷服务自动化测试

[![Tests](https://github.com/StillStream-ink/fintech-api-test/actions/workflows/test.yml/badge.svg)](https://github.com/StillStream-ink/fintech-api-test/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![pytest](https://img.shields.io/badge/pytest-7.x-green)
![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

一个完整的 **Mock 信贷服务 + 自动化测试框架**，覆盖 API 功能、边界、契约、数据一致性、状态机、安全、性能测试，并配备 **CI 流水线**、质量门禁和评分系统。

---

## 一、项目简介

模拟真实信贷业务的核心流程（授信、借款、还款、状态流转），用于：

- 学习/演示金融系统 API 的测试方法
- 作为团队内部的测试框架模板
- 练习 pytest + Allure + pydantic + Locust + CI/CD 的工程化组合

**核心特性**：

| 能力 | 说明 |
|---|---|
| Mock 服务 | Flask + SQLAlchemy + SQLite，实现完整贷款状态机 |
| 功能测试 | 118 个用例，覆盖注册、资格预审、贷款全生命周期 |
| 契约测试 | pydantic v2 校验响应字段名/类型/必填项 |
| 数据一致性 | 接口调用 + SQLite 直连双检 |
| 状态机测试 | PENDING → APPROVED → DISBURSED → SETTLED 全路径 |
| 安全测试 | 3 个 xfail 锁定已知安全缺陷（越权、未鉴权、无幂等） |
| 数据驱动 | YAML 驱动 17 个边界场景，新场景不改代码 |
| API 分层 | BaseAPI（通用）+ CreditAPI（业务），PO 思想 |
| 性能测试 | Locust 4 档梯度压测（10/30/60/100 并发），v2.0 100 并发 58 RPS / 0 失败 / P95 43ms |
| 报告专业化 | Allure step 全覆盖，失败可精确定位到步骤 |
| **CI/CD** | **GitHub Actions + Jenkinsfile 双流水线** |
| 质量门禁 | 通过率 <90% 或覆盖率 <80% 则 CI 失败 |
| 评分系统 | 0-20 分量化测试质量 |

---

## 二、技术栈

| 分类 | 技术 |
|---|---|
| 语言 | Python 3.11 |
| Web 框架 | Flask 3.x |
| ORM | SQLAlchemy 2.x |
| 数据库 | SQLite |
| 测试框架 | pytest 7.x |
| 报告 | Allure 2.x + allure-pytest |
| 数据校验 | pydantic v2 |
| HTTP 客户端 | requests |
| 性能测试 | Locust 2.x |
| 并行测试 | pytest-xdist（可选，实测本项目负优化） |

---

## 三、项目结构

```
fintech-api-test/
├── app.py                       # Mock 信贷服务（Flask）
├── credit_api.py                # 测试侧 HTTP 客户端封装
├── conftest.py                  # pytest fixtures + 自动拉起服务
├── locustfile.py                # Locust 性能压测脚本
├── pytest.ini                   # pytest 配置
├── README.md                    # 本文件
├── KNOWN_BUGS.md                # 已知 BUG 清单
├── .gitignore
├── instance/
│   └── loan.db                  # SQLite（运行后生成）
├── schemas/
│   └── credit_schemas.py        # pydantic 契约模型
├── scripts/
│   ├── archive_report.py        # 报告归档
│   ├── quality_gate.py          # 质量门禁
│   └── scorer.py                # 测试评分（0-20）
├── tests/
│   ├── test_credit.py           # 冒烟 + 安全 xfail
│   ├── test_boundary.py         # 参数化边界
│   ├── test_contract.py         # 契约校验
│   ├── test_db_consistency.py   # 接口 + DB 双检
│   ├── test_loan_state_machine.py  # 状态机
│   └── db_helper.py             # SQLite 直连
├── reports/                     # 报告归档目录
└── test-results/
    └── junit.xml                # pytest JUnit 输出
```

---

## 四、快速开始

### 1. 环境准备

```powershell
# 确认 Python 版本
py --version    # 应该 >= 3.11

# 创建虚拟环境（可选但推荐）
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖
py -m pip install pytest allure-pytest pydantic requests flask flask-sqlalchemy locust
```

### 2. 启动 Mock 服务（可选）

`conftest.py` 会自动拉起 Mock 服务，所以**跑测试时不用手动启动**。但如果想单独调试，可以：

```powershell
py app.py
```

启动后访问：`http://127.0.0.1:5000/api/v1/view-loan/1`

### 3. 跑测试

```powershell
# 全量测试
py -m pytest

# 按 marker 筛选
py -m pytest -m api
py -m pytest -m credit
py -m pytest -m loan
py -m pytest -m security
```

### 4. 查看 Allure 报告

```powershell
allure serve ./allure-results
```

浏览器自动打开，能看到：
- 6 个 Feature，104 个用例
- 每个用例展开后有分步骤（Allure step）
- 3 个 xfail 用例带标记

---

## 五、Mock 服务接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/register` | 客户注册 |
| POST | `/api/v1/check-eligibility` | 资格预审（只读） |
| POST | `/api/v1/loan` | 创建贷款 |
| GET | `/api/v1/view-loan/{id}` | 查询贷款详情 |
| POST | `/api/v1/loan/{id}/approve` | 审批通过 |
| POST | `/api/v1/loan/{id}/reject` | 拒绝 |
| POST | `/api/v1/loan/{id}/disburse` | 放款 |
| POST | `/api/v1/loan/{id}/repay` | 还款 |
| POST | `/api/v1/_reset_db` | 重置数据库（仅测试） |

**贷款状态机**：

```
PENDING ──→ APPROVED ──→ DISBURSED ──→ SETTLED
   │
   └──→ REJECTED
```

---

## 六、测试维度

| 文件 | 覆盖内容 | 用例数 |
|---|---|---|
| `test_credit.py` | 冒烟 + 安全 xfail | 6 |
| `test_boundary.py` | 参数化边界（缺失/类型/数值/协议） | 64 |
| `test_contract.py` | pydantic 契约校验 | 8 |
| `test_db_consistency.py` | 接口 + SQLite 双检 | 10 |
| `test_loan_state_machine.py` | 状态机全路径 + 非法流转 | 16 |
| **合计** | | **104** |

---

## 七、质量门禁

```powershell
py scripts/quality_gate.py --threshold 90
```

**逻辑**：
- 通过率 = passed / (passed + failed + broken)
- xfail / skipped 不计入分母
- 通过率 < 阈值 → 退出码 1（CI 判失败）

---

## 八、测试评分

```powershell
py scripts/scorer.py
```

**评分维度（总分 20）**：

| 维度 | 满分 | 说明 |
|---|---|---|
| 通过率 | 15 | passed / effective |
| 用例规模 | 3 | 满 100 用例得满分 |
| xfail 覆盖 | 2 | 真实读 Allure statusDetails 区分 xfail/skip |

**输出**：`reports/test_scores.txt`

---

## 九、性能测试

### 工具

**Locust 2.31.3** — Python 脚本化压测，支持无头模式与梯度压测。

---

### 一、梯度压测（当前版本 v2.0）

#### 执行方式

```powershell
# 终端 A：启动 Mock 服务
py app.py

# 终端 B：跑梯度压测（10/30/60/100 四档，每档 60 秒）
py scripts\run_load_test.py

# 汇总结果
py scripts\summarize_perf.py --timestamp <时间戳>
```

#### 结果

| 并发 | 总请求 | 失败率 | 平均响应 | P95 | P99 | RPS |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 10 | 396 | 0% | 13.0 ms | 26 ms | 60 ms | 6.7 |
| 30 | 1120 | 0% | 13.0 ms | 27 ms | 49 ms | 18.8 |
| 60 | 2165 | 0% | 11.4 ms | 31 ms | 57 ms | 36.4 |
| 100 | 3449 | 0% | 16.8 ms | 43 ms | 72 ms | 58.0 |

#### 各接口表现（100 并发）

| 接口 | 类型 | P95 | 说明 |
| :--- | :--- | :--- | :--- |
| `/api/v1/check-eligibility` | 只读 | 35 ms | 最快 |
| `/api/v1/view-loan/{id}` | 只读 | 39 ms | 快 |
| `/api/v1/loan/{id}/approve` | 写 | 69 ms | 状态流转 |
| `/api/v1/loan` | 写 | 53 ms | 创建借款 |
| `/api/v1/register` | 写 | 110 ms | 建连接 + 写库 |

### 二、性能演进对比

项目从 v1.0 到 v2.0 引入了风控规则（信用分 ≥600、收入 ≥5000、月借款 ≤5 次），业务行为发生变化，压测数据随之改变。

| 版本 | 服务特性 | 100 并发 RPS | P95 | 失败率 |
| :--- | :--- | :--- | :--- | :--- |
| v1.0 | 无风控，每用户可无限创建贷款 | 137.3 | 91 ms | 0% |
| v2.0 | 含风控规则，每用户最多 1 笔贷款 | 58.0 | 43 ms | 0% |

#### 差异分析

| 指标 | v1.0 | v2.0 | 变化原因 |
| :--- | :--- | :--- | :--- |
| RPS | 137.3 | 58.0 ↓ | 写接口被限流，流量结构从"密集写"转为"只读为主" |
| P95 | 91 ms | 43 ms ↓ | 减少 SQLite 写锁竞争，响应时间反而更优 |
| 失败率 | 0% | 0% | 两版本均稳定 |

**结论：**

- **RPS 下降不等于性能退化**——流量结构变化导致，而非系统变慢
- **v2.0 的 P95 更优**（43ms vs 91ms）——减少写竞争后，读性能显著提升
- **v2.0 更贴近真实场景**——真实信贷系统必然有风控规则，压测流量应以"大量查询 + 少量申请"为主

### 三、关键结论

- **RPS 随并发接近线性增长**（6.7 → 18.8 → 36.4 → 58.0），100 并发未饱和
- **响应时间稳定**：P95 从 26ms 到 43ms，服务健康
- **读写特征符合预期**：只读接口 P95 < 40ms，写接口 53~110ms
- **0 失败率**：v2.0 四档共 7130 次请求全部成功
- **瓶颈定位**：SQLite 单文件写锁；如需继续提升，可切换 PostgreSQL 或引入连接池

### 四、演进方向

| 方向 | 预期收益 |
| :--- | :--- |
| 切换 PostgreSQL | 解决单文件写锁，写接口 RPS 可提升 5~10 倍 |
| 引入 Redis 缓存 | 读接口响应可降至 <5ms |
| gunicorn 多 worker | 突破 Flask 单进程限制 |
| 读写分离 | 读写互不干扰，P99 更稳定 |
---

## 十、持续集成

项目支持两种 CI 方式：

| 平台 | 配置文件 | 触发条件 |
|---|---|---|
| GitHub Actions | `.github/workflows/test.yml` | push / PR / 手动 |
| Jenkins | `Jenkinsfile` | Jenkins 任务配置的 SCM 轮询 / Webhook |

两者执行一致的流程：
Checkout → Setup Python → Install Deps → pytest + 覆盖率 → 质量门禁 → 归档报告
```text

**门禁规则**：
- 测试通过率 < 90% → 失败
- 测试代码覆盖率 < 80% → 失败
```
---

## 十一、已知 BUG

见 [KNOWN_BUGS.md](./KNOWN_BUGS.md)。

| ID | 严重程度 | 描述 |
|---|---|---|
| BUG-004 | 🟠 中 | 创建贷款未实现幂等 |
| BUG-005 | 🔴 高 | 水平越权访问 |
| BUG-006 | 🔴 高 | 缺少 token 鉴权 |

这 3 个 BUG 对应 3 个 `xfail(strict=True)` 用例。修复后测试会 FAILED，强制移除 xfail 标记。

---

## 十一、开发指南

### 目录约定

- `tests/` 只放测试文件，辅助代码放 `tests/db_helper.py`
- `schemas/` 放 pydantic 模型
- `scripts/` 放工具脚本
- `reports/` 放归档产物（git 忽略，CI artifact 保留）

### 写新用例

```python
import allure

@allure.feature("功能模块名")
class TestXxx:

    @allure.story("子场景")
    @allure.title("TC_XXX_001 用例标题")
    def test_xxx(self, api_client, sample_customer):
        with allure.step("准备数据"):
            payload = {...}

        with allure.step("调用接口"):
            resp = api_client.some_method(payload)

        with allure.step("校验结果"):
            assert resp.status_code == 200
```

### 修复 BUG 后

1. 移除 `@pytest.mark.xfail(strict=True)`
2. 更新 `KNOWN_BUGS.md`
3. 重跑测试，确保 `passed`

---

## 十二、演进方向

- [ ] CI 接入（GitHub Actions / GitLab CI）
- [ ] 测试覆盖率统计（pytest-cov）
- [ ] 异常注入测试（模拟 DB 故障）
- [ ] 接口版本化（`/api/v2/...`）
- [ ] 引入真实鉴权（JWT）

---

## 十三、License

仅供学习交流使用。