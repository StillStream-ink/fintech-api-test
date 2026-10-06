# Fintech API Test — 测试用例文档

> **项目**：Mock 信贷服务自动化测试框架  
> **用例总数**：69 个核心场景（P0 41 个 / P1 28 个）  
> **覆盖模块**：注册 / 资格预审 / 贷款创建 / 贷款查询 / 状态流转 / 金融对账 / DB 双检 / 安全 / 契约

---

## 一、注册模块（8 条）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| REG-001 | 正常注册 | 服务已启动 | 1.POST /register | name=张三, age=22, income=8000, credit_score=700 | 201, 返回 customer_id（int） | P0 | 功能 |
| REG-002 | 缺少 name | 同上 | 1.POST /register 不传 name | age=22, income=8000, credit_score=700 | 400, error="缺少必填字段" | P0 | 边界 |
| REG-003 | 缺少 age | 同上 | 不传 age | name=张三, income=8000, credit_score=700 | 400 | P0 | 边界 |
| REG-004 | age 传字符串 | 同上 | age="22" | name=张三, age="22", income=8000, credit_score=700 | 400, error="age 必须为整数" | P1 | 边界 |
| REG-005 | age 传负数 | 同上 | age=-1 | age=-1 | 400, error="age 不能小于 0" | P1 | 边界 |
| REG-006 | age 超大值 | 同上 | age=999 | age=999 | 400, error="age 不能大于 150" | P1 | 边界 |
| REG-007 | name 为空串 | 同上 | name="" | name="" | 400, error="name 不能为空" | P1 | 边界 |
| REG-008 | 非法 JSON | 同上 | Body="{not valid json" | — | 400 | P1 | 协议 |

---

## 二、资格预审模块（10 条）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| ELI-001 | 资质合格 | 服务已启动 | POST /check-eligibility | age=22, income=8000, credit_score=700 | 200, eligible=true, max_amount=100000 | P0 | 功能 |
| ELI-002 | 年龄不足 18 | 同上 | 同上 | age=17 | 200, eligible=false, reason="年龄不符合要求" | P0 | 边界 |
| ELI-003 | 年龄刚好 18 | 同上 | 同上 | age=18 | 200, eligible=true | P0 | 边界 |
| ELI-004 | 年龄刚好 60 | 同上 | 同上 | age=60 | 200, eligible=true | P0 | 边界 |
| ELI-005 | 年龄超过 60 | 同上 | 同上 | age=61 | 200, eligible=false | P0 | 边界 |
| ELI-006 | 收入不足 3000 | 同上 | 同上 | income=2999 | 200, eligible=false, reason="收入不足" | P0 | 边界 |
| ELI-007 | 收入刚好 3000 | 同上 | 同上 | income=3000 | 200, eligible=true | P0 | 边界 |
| ELI-008 | 信用分不足 600 | 同上 | 同上 | credit_score=599 | 200, eligible=false, reason="信用评分不足" | P0 | 边界 |
| ELI-009 | 信用分刚好 600 | 同上 | 同上 | credit_score=600 | 200, eligible=true | P0 | 边界 |
| ELI-010 | 缺必填字段 | 同上 | 不传 income | age=22, credit_score=700 | 400 | P1 | 边界 |

---

## 三、贷款创建模块（12 条）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| LOAN-001 | 正常创建 | 客户已注册 | POST /loan | customer_id=1, amount=10000 | 201, 返回 loan_id, status=PENDING | P0 | 功能 |
| LOAN-002 | 客户不存在 | 同上 | 同上 | customer_id=99999 | 404, error="客户不存在" | P0 | 异常 |
| LOAN-003 | 金额为 0 | 同上 | 同上 | amount=0 | 400 | P1 | 边界 |
| LOAN-004 | 金额为负 | 同上 | 同上 | amount=-1 | 400 | P1 | 边界 |
| LOAN-005 | 金额最小值 | 同上 | 同上 | amount=1 | 201 | P1 | 边界 |
| LOAN-006 | 金额超大 | 同上 | 同上 | amount=99999999 | 400 | P1 | 边界 |
| LOAN-007 | customer_id 传字符串 | 同上 | 同上 | customer_id="1" | 400 | P1 | 边界 |
| LOAN-008 | amount 传字符串 | 同上 | 同上 | amount="50000" | 400 | P1 | 边界 |
| LOAN-009 | 缺 customer_id | 同上 | 同上 | 只有 amount | 400 | P1 | 边界 |
| LOAN-010 | 信用分不足 | 客户信用分 500 | 同上 | customer_id=低分客户 | 403, error="信用评分不足" | P0 | 业务规则 |
| LOAN-011 | 收入不足 | 客户收入 3000 | 同上 | customer_id=低收入客户 | 403, error="收入不足" | P0 | 业务规则 |
| LOAN-012 | 月借款超限 | 客户本月已借 5 次 | 同上 | 第 6 次 | 429, error="本月借款次数已达上限" | P1 | 业务规则 |

---

## 四、贷款查询模块（4 条）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| VIEW-001 | 查询存在的贷款 | 贷款已创建 | GET /view-loan/{id} | loan_id=1 | 200, 返回完整字段 | P0 | 功能 |
| VIEW-002 | 查询不存在的贷款 | 服务已启动 | 同上 | loan_id=99999 | 404, error="贷款不存在" | P0 | 异常 |
| VIEW-003 | 查询返回字段契约 | 贷款已创建 | 同上 | loan_id=1 | 字段含 loan_id/customer_id/amount/principal/interest_rate/paid_interest/status | P0 | 契约 |
| VIEW-004 | 接口返回与 DB 一致 | 同上 | 同上 | loan_id=1 | 接口返回 == DB 记录 | P0 | 数据一致性 |

---

## 五、状态流转模块（12 条）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| STM-001 | 初始状态 PENDING | 贷款已创建 | GET /view-loan/{id} | loan_id=1 | status=PENDING | P0 | 功能 |
| STM-002 | PENDING → APPROVED | 同上 | POST /loan/{id}/approve | loan_id=1 | 200, from=PENDING, status=APPROVED, DB 同步 | P0 | 功能 |
| STM-003 | APPROVED → DISBURSED | 已审批 | POST /loan/{id}/disburse | loan_id=1 | 200, status=DISBURSED, DB 同步 | P0 | 功能 |
| STM-004 | DISBURSED → SETTLED | 已放款 | POST /loan/{id}/repay | loan_id=1 | 200, status=SETTLED, DB 同步 | P0 | 功能 |
| STM-005 | PENDING → REJECTED | 贷款 PENDING | POST /loan/{id}/reject | loan_id=1 | 200, status=REJECTED | P0 | 功能 |
| STM-006 | PENDING 不能直接 DISBURSED | 贷款 PENDING | POST /loan/{id}/disburse | loan_id=1 | 409, error="非法状态流转" | P1 | 状态机 |
| STM-007 | PENDING 不能直接 SETTLED | 同上 | POST /loan/{id}/repay | loan_id=1 | 409 | P1 | 状态机 |
| STM-008 | APPROVED 不能回退 REJECTED | 已审批 | POST /loan/{id}/reject | loan_id=1 | 409 | P1 | 状态机 |
| STM-009 | APPROVED 不能重复审批 | 已审批 | POST /loan/{id}/approve | loan_id=1 | 409 | P1 | 状态机 |
| STM-010 | REJECTED 是终态 | 已拒绝 | 调 approve / disburse / repay | loan_id=1 | 全部 409 | P1 | 状态机 |
| STM-011 | SETTLED 是终态 | 已还清 | 同上 | loan_id=1 | 全部 409 | P1 | 状态机 |
| STM-012 | 状态流转不影响其他贷款 | 有两笔贷款 | 只审批 loan1，查 loan2 | — | loan2 仍 PENDING | P1 | 隔离性 |

---

## 六、金融对账模块（6 条）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| RECON-001 | 借款金额 = 本金 + 利息 | 贷款已创建 | 查 DB loan 表 | amount=10000, rate=0.035 | amount == principal + 利息（10350 == 10000 + 350） | P0 | 对账 |
| RECON-002 | 利率按信用分匹配 | 客户信用分 850 | 创建贷款，查 rate | credit_score=850 | interest_rate == 0.02 | P0 | 对账 |
| RECON-003 | 还款流水总额 = 贷款金额 | 已还清 | 查 DB repayment_flow | loan_id=1 | SUM(flow.amount) == loan.amount | P0 | 对账 |
| RECON-004 | 流水拆分 = 本金 + 利息 | 已还清 | 查流水 | flow=1 | principal_part + interest_part == amount | P0 | 对账 |
| RECON-005 | paid_interest 同步更新 | 已还清 | 查 DB loan | loan_id=1 | paid_interest == 利息总额 | P0 | 对账 |
| RECON-006 | 无孤儿流水 | 已还清 | 查所有流水 | — | 每条流水对应的 loan 存在 | P1 | 对账 |

---

## 七、数据库双检模块（6 条）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| DB-001 | 注册数据落库 | 服务已启动 | POST /register，查 DB | name=张三 | DB 记录字段与请求一致 | P0 | 一致性 |
| DB-002 | 连续注册 3 次 | 同上 | 注册 3 个客户 | — | DB customer 表 3 条 | P1 | 一致性 |
| DB-003 | 校验失败不写库 | 同上 | 缺字段注册，查 DB | — | DB 行数不变 | P0 | 一致性 |
| DB-004 | 只读接口不写库 | 同上 | 调 check-eligibility，查 DB | — | customer/loan 行数不变 | P1 | 一致性 |
| DB-005 | 创建贷款落库 | 客户已注册 | POST /loan，查 DB | amount=10000 | DB 记录 status=PENDING | P0 | 一致性 |
| DB-006 | 重置清空所有表 | 有数据 | POST /_reset_db | — | customer/loan 表空 | P0 | 一致性 |

---

## 八、安全模块（3 条，xfail）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| SEC-001 | 水平越权 | 客户 A 有贷款 | 用 A 的 loan_id 直接查（模拟 B） | loan_id=1 | 401/403（当前 200，xfail，BUG-005） | P0 | 安全 |
| SEC-002 | 未授权访问 | 服务已启动 | 不带 token 查贷款 | loan_id=1 | 401（当前 200，xfail，BUG-006） | P0 | 安全 |
| SEC-003 | 幂等性 | 客户已注册 | 相同 payload 提交两次 | 相同请求 | 两次返回同一 loan_id（当前不同，xfail，BUG-004） | P1 | 安全 |

---

## 九、契约模块（8 条）

| 编号 | 标题 | 前置条件 | 测试步骤 | 测试数据 | 预期结果 | 优先级 | 类型 |
|---|---|---|---|---|---|---|---|
| CT-001 | 注册响应契约 | 服务已启动 | POST /register | 正常数据 | 符合 RegisterResponse schema | P0 | 契约 |
| CT-002 | 资格预审通过契约 | 同上 | POST /check-eligibility | 合格数据 | 符合 EligibilityResponse，eligible=true | P0 | 契约 |
| CT-003 | 资格预审拒绝契约 | 同上 | 同上 | age=17 | 符合 EligibilityResponse，eligible=false + reason | P0 | 契约 |
| CT-004 | 创建贷款契约 | 客户已注册 | POST /loan | 正常数据 | 符合 LoanCreateResponse | P0 | 契约 |
| CT-005 | 查询贷款契约 | 贷款已创建 | GET /view-loan/{id} | loan_id=1 | 符合 LoanDetailResponse | P0 | 契约 |
| CT-006 | 注册错误契约 | 服务已启动 | POST /register 缺字段 | — | 符合 ErrorResponse，含 error 字段 | P0 | 契约 |
| CT-007 | 404 错误契约 | 同上 | GET /view-loan/99999 | — | 符合 ErrorResponse | P0 | 契约 |
| CT-008 | 创建贷款错误契约 | 同上 | POST /loan 缺 customer_id | — | 符合 ErrorResponse | P0 | 契约 |

---

## 十、用例统计

| 模块 | 用例数 | P0 | P1 | 类型分布 |
|---|---:|---:|---:|---|
| 注册 | 8 | 3 | 5 | 功能 1 / 边界 6 / 协议 1 |
| 资格预审 | 10 | 6 | 4 | 功能 1 / 边界 9 |
| 贷款创建 | 12 | 4 | 8 | 功能 1 / 边界 7 / 业务规则 3 / 异常 1 |
| 贷款查询 | 4 | 4 | 0 | 功能 1 / 异常 1 / 契约 1 / 一致性 1 |
| 状态流转 | 12 | 5 | 7 | 功能 5 / 状态机 7 |
| 金融对账 | 6 | 5 | 1 | 对账 6 |
| DB 双检 | 6 | 4 | 2 | 一致性 6 |
| 安全 | 3 | 2 | 1 | 安全 3（xfail） |
| 契约 | 8 | 8 | 0 | 契约 8 |
| **合计** | **69** | **41** | **28** | — |

---

## 十一、用例设计方法

### 4 个设计维度

| 维度 | 方法 | 示例 |
|---|---|---|
| **正向流程** | 每个接口的正常路径 | 注册 / 借款 / 审批 / 还款 |
| **边界值** | 0、-1、极大、空、超长、临界点 | age=17/18/60/61；amount=0/1/99999999 |
| **异常路径** | 缺参数、错类型、不存在资源 | 缺 customer_id；loan_id=99999 |
| **业务规则** | 风控、状态机、权限 | 信用分不足 403；非法流转 409 |

### 正交法减少组合爆炸

**原则**：**只测边界点，不测中间值**

例：年龄边界不用测 0~150 全部，只测：
- `17`（未成年上界）
- `18`（刚好成年）
- `60`（刚好上限）
- `61`（超上限）

**4 个点覆盖了 3 类边界**，效率提升 40 倍。

### 优先级判断

| 优先级 | 判断标准 | 例子 |
|---|---|---|
| **P0** | 涉及资金、安全、核心流程 | 越权、对账、状态流转 |
| **P1** | 参数校验、体验优化 | 边界值、异常提示 |
| **P2** | 极少出现的场景 | 特殊字符、超长文本 |

---

## 十二、用例与自动化映射

| 模块 | 自动化文件 | 用例数 |
|---|---|---:|
| 注册 + 冒烟 | `tests/test_credit.py` | 6 |
| 边界参数化 | `tests/test_boundary.py` | 47 |
| 契约 | `tests/test_contract.py` | 8 |
| DB 双检 | `tests/test_db_consistency.py` | 10 |
| 状态机 | `tests/test_loan_state_machine.py` | 16 |
| 数据驱动 | `tests/test_ddt_eligibility.py` | 17 |
| 金融对账 | `tests/test_reconciliation.py` | 8 |
| 业务规则 | `tests/test_business_rules.py` | 7 |

**总计**：101 passed + 3 xfailed = 104 用例

---

## 十三、缺陷关联

| 缺陷 ID | 严重度 | 描述 | 关联用例 |
|---|---|---|---|
| BUG-004 | 🟠 中 | 创建贷款未实现幂等 | SEC-003 |
| BUG-005 | 🔴 高 | 水平越权访问 | SEC-001 |
| BUG-006 | 🔴 高 | 无 token 鉴权 | SEC-002 |

**全部用 `xfail(strict=True)` 守卫**——修复后测试会 FAILED，强制更新文档。