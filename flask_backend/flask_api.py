import logging
from datetime import timedelta, datetime
from uuid import uuid4
from functools import wraps
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager
from flask_jwt_extended import create_refresh_token, create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity

from account_sql import AccountSQL
from utils.exceptions import PasswordError, AccountError, DuplicateValueError, TimeSetError
from utils.logging_utils import log_set
from typing import List

# init flask & JWT
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = str(uuid4())
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=10)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=15)

jwt = JWTManager(app)

sql_account = AccountSQL(sql_name="account.db", admin_username="admin", admin_password="yxAlFXQ&EL6!sxQ")


def info_check(verify_role: bool = True, verify_time: bool = False, role_group: List = None):
    """
    校验装饰器，用来校验是否在可用时间或可用权限组，通过user_id获取数据库内信息并比对
    :param verify_role: 是否校验权限组
    :param verify_time: 是否检验”当前时间是否位于可用时间段“
    :param role_group: 权限组
    """
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kw):
            _, role, start_time, end_time = sql_account.user_id_get_base_info(get_jwt_identity())
            if verify_role and role not in role_group:
                return jsonify(success=False, msg=f"This API only allow {', '.join(role_group)}"), 401
            if verify_time:
                end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                if start_time < datetime.now() < end_time:
                    return jsonify(success=False, msg="Access is prohibited at the current time"), 401
            # 被装饰的函数的实际执行位置
            func(*args, **kw)
        return inner
    return wrapper


@app.route("/login", methods=["POST"])
def user_login():
    """
    用户登录
    """
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    try:
        info = sql_account.verify_account(username, password)
    except AccountError or PasswordError:
        return jsonify(success=False, msg="Username and Password error"), 404

    access_token = create_access_token(identity=str(info[0]))
    # 设置admin用户的refresh_token有效期为3小时，否则使用默认值
    refresh_token = create_refresh_token(identity=str(info[0]), expires_delta=timedelta(hours=3) if info[3] == "admin" else None)
    return jsonify(success=True, access_token=access_token, refresh_token=refresh_token), 200


@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    使用refresh_token获取access_token
    """
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify(success=True, access_token=access_token), 200


@app.route('/account', methods=['PUT'])
@jwt_required(refresh=True)
# @info_check(verify_role=True, role_group=["admin"])
def change_password():
    """
    更改用户密码
    """
    username = request.json.get("username", None)
    old_password = request.json.get("old_password", None)
    new_password = request.json.get("new_password", None)
    # 获取请求的id的权限和用户名
    identity_username, role, _, _ = sql_account.user_id_get_base_info(user_id=get_jwt_identity())
    if role != "admin" and identity_username == username:
        try:
            sql_account.verify_account(username, old_password)
        except AccountError:
            return jsonify(success=False, msg="Account not found"), 401
        except PasswordError:
            return jsonify(success=False, msg="Password error"), 401
    if sql_account.check_username_exits(username):
        sql_account.change_password(username, new_password)
    else:
        return jsonify(success=False, msg=""), 401
    return jsonify(success=True, msg=f"Successful change {username}'s password to {new_password}"), 200


@app.route('/account', methods=['POST'])
@jwt_required(refresh=True)
@info_check(verify_role=True, role_group=["admin"])
def create_account():
    """
    创建新账户
    """
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    role = request.json.get("role", None)
    start_time = request.json.get("start_time", None)
    end_time = request.json.get("end_time", None)
    try:
        sql_account.create_accounts([(username, password, role, start_time, end_time)])
        return jsonify(success=True, msg=f"successful create '{username}'"), 200
    except DuplicateValueError:
        return jsonify(success=False, msg=f"username error, '{username}' already in used"), 409
    except TimeSetError:
        return jsonify(success=False, msg=f"Time set error, '{end_time}' early than '{start_time}'"), 400


@app.route('/account', methods=['DELETE'])
@jwt_required(refresh=True)
@info_check(verify_role=True, role_group=["admin"])
# todo: 未完成，暂存
def delete_account():
    """
    删除账户
    """
    username = request.json.get("delete_username", None)
    return jsonify(success=True, msg=f"Successful delete {username}"), 200


@app.route('/account', methods=['PATCH'])
@jwt_required(refresh=True)
@info_check(verify_role=True, role_group=["admin"])
# todo: 未完成，暂存
def change_allow_time():
    """
    修改用户的可用时间
    """
    pass


@app.route('/account', methods=['PATCH'])
@jwt_required()
# todo: 未完成，暂存
def get_account_info():
    """
    获取账户基本信息
    """
    pass


if __name__ == '__main__':
    log_set(logging.INFO)
    app.run(debug=True, port=5000)
