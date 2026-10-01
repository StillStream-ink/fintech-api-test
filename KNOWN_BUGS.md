# 已知 BUG 清单

本文件记录 Mock 信贷项目中**已通过测试发现、但尚未修复**的缺陷。
每个 BUG 都对应一个 `@pytest.mark.xfail(strict=True)` 的测试用例。

> **重要**：当某个 BUG 修复后，`strict=True` 会让对应测试从 `xfailed` 变成 `failed`。
> 此时必须：
> 1. 移除测试上的 `@pytest.mark.xfail` 标记
> 2. 把本文档中该 BUG 的状态改为 `✅ 已修复`
> 3. 重新跑测试，确保用例变为 `passed`

---

## BUG 总览

| ID | 严重程度 | 模块 | 描述 | 对应测试 | 状态 |
|---|---|---|---|---|---|
| BUG-004 | 🟠 中 | 贷款 | 创建贷款接口未实现幂等，重复提交生成多条记录 | `tests/test_db_consistency.py::TestDatabaseConsistency::test_create_loan_idempotent_db` | 🔴 待修复 |
| BUG-005 | 🔴 高 | 安全 | 缺少权限控制，存在水平越权漏洞 | `tests/test_credit.py::TestSecurityKnownBugs::test_loan_horizontal_privilege` | 🔴 待修复 |
| BUG-006 | 🔴 高 | 安全 | 无 token 鉴权，未授权可以直接访问接口 | `tests/test_credit.py::TestSecurityKnownBugs::test_loan_unauthorized` | 🔴 待修复 |

---

## BUG-004：创建贷款未实现幂等

**严重程度**：🟠 中

**现象**：同一客户对同一笔贷款重复提交，接口生成多条 `Loan` 记录。

**复现步骤**：
1. 注册一个客户，得到 `customer_id`
2. 调用 `POST /api/v1/loan` 两次，payload 完全相同
3. 观察两次返回的 `loan_id`，以及 DB 里 `loan` 表的记录数

**期望**：两次返回同一个 `loan_id`，DB 里只有 1 条记录

**实际**：两次返回不同的 `loan_id`，DB 里有 2 条记录

**影响**：重复点击"借款"按钮可能导致重复放款，产生资金风险。

**修复建议**：
- 方案 A：客户端生成幂等键（idempotency key），服务端据此去重
- 方案 B：服务端限制"同一客户 + 同一金额 + 未结清状态"不能重复创建
- 方案 C：提交后进入 PENDING 状态，禁止客户再创建新贷款，直到当前贷款结清

**关联测试**：`tests/test_db_consistency.py::TestDatabaseConsistency::test_create_loan_idempotent_db`

---

## BUG-005：水平越权访问

**严重程度**：🔴 高

**现象**：任何客户端都可以通过 `GET /api/v1/view-loan/{loan_id}` 查询任意客户的贷款详情。

**复现步骤**：
1. 客户 A 创建贷款，得到 `loan_id`
2. 客户 B（或匿名客户端）直接访问 `GET /api/v1/view-loan/{loan_id}`
3. 观察返回结果

**期望**：返回 `401 Unauthorized` 或 `403 Forbidden`

**实际**：返回 `200 OK`，包含 loan 的完整信息（客户 ID、金额、状态）

**影响**：客户可任意查询他人贷款信息，泄露 PII（个人身份信息）和财务数据，属于合规红线问题。

**修复建议**：
- 在接口层加入身份校验（从 token 或 session 中解析当前用户）
- 查询前判断 `loan.customer_id == current_user.customer_id`
- 不匹配时返回 `403`，不泄露资源是否存在

**关联测试**：`tests/test_credit.py::TestSecurityKnownBugs::test_loan_horizontal_privilege`

---

## BUG-006：缺少 token 鉴权

**严重程度**：🔴 高

**现象**：贷款查询接口未做鉴权，不携带任何身份凭证也能访问。

**复现步骤**：
1. 不带任何 `Authorization` header 或 Cookie
2. 直接调用 `GET /api/v1/view-loan/{loan_id}`
3. 观察返回结果

**期望**：返回 `401 Unauthorized`

**实际**：返回 `200 OK`

**影响**：所有信贷接口对匿名开放，任何人都能操作他人账户，属于严重安全缺陷。

**修复建议**：
- 引入统一鉴权中间件（如 JWT / OAuth2）
- 所有 `/api/v1/**` 除注册/登录外，强制校验身份
- 未携带合法凭证一律返回 `401`

**关联测试**：`tests/test_credit.py::TestSecurityKnownBugs::test_loan_unauthorized`

---

## 维护指南

### 何时更新本文档

- **发现新 BUG**：加一条记录，写清现象、复现步骤、影响、修复建议
- **BUG 修复**：改状态为 `✅ 已修复`，并在测试中移除 `xfail` 标记
- **BUG 关闭**：从总览表移出，归档到文末「已修复历史」

### 修复流程

```powershell
# 1. 确认 BUG 已修复（xfail strict 会让测试 FAILED）
py -m pytest tests/test_credit.py -v

# 2. 移除对应的 @pytest.mark.xfail 装饰器
# 3. 重新跑，确认 PASSED
py -m pytest tests/test_credit.py -v

# 4. 更新本文档状态
# 5. 提交
git add KNOWN_BUGS.md tests/test_credit.py
git commit -m "fix: 修复 BUG-005 水平越权访问"