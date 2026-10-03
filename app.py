import os
from pathlib import Path

# 子进程启动时同步启动覆盖率统计（如果环境变量存在）
if os.getenv("COVERAGE_PROCESS_START"):
    import coverage
    coverage.process_startup()

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)

# ==============================================================================
# 数据库配置
# 优先读 DATABASE_URL（MySQL / 其他数据库）
# 未设置时回退到 SQLite（本地开发 / 单元测试）
# ==============================================================================
def _build_db_uri() -> str:
    # 1. 显式传入完整 URL
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url

    # 2. 兼容旧逻辑：MOCK_DB_PATH 指定 SQLite 文件路径
    db_path = Path(os.getenv("MOCK_DB_PATH", "instance/loan.db")).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"


app.config['SQLALCHEMY_DATABASE_URI'] = _build_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.url_map.strict_slashes = False


# ==============================================================================
# 数据模型
# ==============================================================================
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    income = db.Column(db.Integer, nullable=False)
    credit_score = db.Column(db.Integer, nullable=False)


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="PENDING", nullable=False)


# ==============================================================================
# 贷款状态机
# ==============================================================================
LOAN_STATE_TRANSITIONS = {
    "PENDING": {"APPROVED", "REJECTED"},
    "APPROVED": {"DISBURSED"},
    "DISBURSED": {"SETTLED"},
    "REJECTED": set(),
    "SETTLED": set(),
}


def _can_transition(from_state, to_state):
    return to_state in LOAN_STATE_TRANSITIONS.get(from_state, set())


# ==============================================================================
# 通用校验函数
# ==============================================================================
def _require_json():
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "请求体必须为合法 JSON"}), 400)
    return data, None


def _require_fields(data, fields):
    missing = [f for f in fields if f not in data]
    if missing:
        return jsonify({"error": "缺少必填字段", "missing": missing}), 400
    return None


def _require_int(data, field, min_val=None, max_val=None):
    val = data[field]
    if isinstance(val, bool) or not isinstance(val, int):
        return jsonify({"error": f"{field} 必须为整数"}), 400
    if min_val is not None and val < min_val:
        return jsonify({"error": f"{field} 不能小于 {min_val}"}), 400
    if max_val is not None and val > max_val:
        return jsonify({"error": f"{field} 不能大于 {max_val}"}), 400
    return None


def _require_str(data, field, min_len=1, max_len=32):
    val = data[field]
    if not isinstance(val, str):
        return jsonify({"error": f"{field} 必须为字符串"}), 400
    if len(val) < min_len:
        return jsonify({"error": f"{field} 不能为空"}), 400
    if len(val) > max_len:
        return jsonify({"error": f"{field} 长度不能超过 {max_len}"}), 400
    return None


# ==============================================================================
# 接口：注册
# ==============================================================================
@app.route('/api/v1/register', methods=['POST'])
def register():
    data, err = _require_json()
    if err:
        return err
    err = _require_fields(data, ["name", "age", "income", "credit_score"])
    if err:
        return err
    err = _require_str(data, "name", min_len=1, max_len=32)
    if err:
        return err
    err = _require_int(data, "age", min_val=0, max_val=150)
    if err:
        return err
    err = _require_int(data, "income", min_val=0, max_val=100_000_000)
    if err:
        return err
    err = _require_int(data, "credit_score", min_val=0, max_val=1000)
    if err:
        return err

    try:
        cust = Customer(
            name=data["name"],
            age=data["age"],
            income=data["income"],
            credit_score=data["credit_score"],
        )
        db.session.add(cust)
        db.session.commit()
        return jsonify({"customer_id": cust.id}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "数据库操作失败", "detail": str(e)}), 500


# ==============================================================================
# 接口：资格预审
# ==============================================================================
@app.route('/api/v1/check-eligibility', methods=['POST'])
def check_eligibility():
    data, err = _require_json()
    if err:
        return err
    err = _require_fields(data, ["age", "income", "credit_score"])
    if err:
        return err
    err = _require_int(data, "age", min_val=0, max_val=150)
    if err:
        return err
    err = _require_int(data, "income", min_val=0, max_val=100_000_000)
    if err:
        return err
    err = _require_int(data, "credit_score", min_val=0, max_val=1000)
    if err:
        return err

    age, income, credit_score = data["age"], data["income"], data["credit_score"]
    if age < 18 or age > 60:
        return jsonify({"eligible": False, "reason": "年龄不符合要求"}), 200
    if income < 3000:
        return jsonify({"eligible": False, "reason": "收入不足"}), 200
    if credit_score < 600:
        return jsonify({"eligible": False, "reason": "信用评分不足"}), 200
    return jsonify({"eligible": True, "max_amount": 100000}), 200


# ==============================================================================
# 接口：创建贷款
# ==============================================================================
@app.route('/api/v1/loan', methods=['POST'])
def create_loan():
    data, err = _require_json()
    if err:
        return err
    err = _require_fields(data, ["customer_id", "amount"])
    if err:
        return err
    err = _require_int(data, "customer_id", min_val=1)
    if err:
        return err
    err = _require_int(data, "amount", min_val=1, max_val=10_000_000)
    if err:
        return err

    cust = db.session.get(Customer, data["customer_id"])
    if not cust:
        return jsonify({"error": "客户不存在"}), 404

    try:
        loan = Loan(
            customer_id=data["customer_id"],
            amount=data["amount"],
            status="PENDING",
        )
        db.session.add(loan)
        db.session.commit()
        return jsonify({"loan_id": loan.id, "status": loan.status}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "数据库操作失败", "detail": str(e)}), 500


# ==============================================================================
# 接口：查询贷款
# ==============================================================================
@app.route('/api/v1/view-loan/<int:loan_id>', methods=['GET'])
def view_loan(loan_id):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"error": "贷款不存在"}), 404
    return jsonify({
        "loan_id": loan.id,
        "customer_id": loan.customer_id,
        "amount": loan.amount,
        "status": loan.status,
    }), 200


# ==============================================================================
# 状态流转通用函数
# ==============================================================================
def _transition_loan(loan_id, target_status):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"error": "贷款不存在"}), 404

    from_status = loan.status
    if not _can_transition(from_status, target_status):
        return jsonify({
            "error": f"非法状态流转：{from_status} → {target_status}",
            "current_status": from_status,
            "target_status": target_status,
        }), 409

    loan.status = target_status
    try:
        db.session.commit()
        return jsonify({
            "loan_id": loan.id,
            "from_status": from_status,
            "status": loan.status,
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "数据库操作失败", "detail": str(e)}), 500


@app.route('/api/v1/loan/<int:loan_id>/approve', methods=['POST'])
def approve_loan(loan_id):
    return _transition_loan(loan_id, "APPROVED")


@app.route('/api/v1/loan/<int:loan_id>/reject', methods=['POST'])
def reject_loan(loan_id):
    return _transition_loan(loan_id, "REJECTED")


@app.route('/api/v1/loan/<int:loan_id>/disburse', methods=['POST'])
def disburse_loan(loan_id):
    return _transition_loan(loan_id, "DISBURSED")


@app.route('/api/v1/loan/<int:loan_id>/repay', methods=['POST'])
def repay_loan(loan_id):
    return _transition_loan(loan_id, "SETTLED")


# ==============================================================================
# 接口：重置数据库（仅测试用）
# ==============================================================================
@app.route('/api/v1/_reset_db', methods=['POST'])
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        return jsonify({"msg": "db reset success"}), 200
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# 启动入口
# ==============================================================================
if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
    debug_mode = os.getenv("FLASK_DEBUG", "1") == "1"
    # use_reloader=False 防止 debug 模式启动双进程抢端口
    app.run(host="127.0.0.1", port=5000, debug=debug_mode, use_reloader=False)