"""
所有 API 遵循 RESTful API 设计规范
{
    code: int,  # http 状态码
    status: "success" | "error" | "fail",
    message: str,   # 当 status 为 error 或 fail 的时候提供原因
    data: dict  # 实际的数据体，一般为 dict
}
"""

import logging
from datetime import timedelta, datetime
from functools import wraps
from typing import List, Tuple
from uuid import uuid4

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_refresh_token, create_access_token

from account_sql import AccountSQL
from utils.exceptions import PasswordError, AccountError, DuplicateValueError, TimeSetError
from utils.logging_utils import log_set

# init flask & JWT
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = str(uuid4())
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=10)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=15)

jwt = JWTManager(app)

sql_account = AccountSQL(sql_name="account.db", admin_username="admin", admin_password="yxAlFXQ&EL6!sxQ")


def api_return(code: int, status: str, message: str = None, data: dict = None) -> Tuple[jsonify, int]:
    """
    :param code: http status code
    :param status: success | error | fail
    :param message: if status in ["error", "fail"], give the reason
    :param data: if status == "success", data
    :return: jsonify(code, status, message, data), code
    """
    if status not in ["success", "error", "fail"]:
        raise ValueError(f'{status} must in ["success", "error", "fail"]')
    if status != "success" and message is None:
        raise ValueError(f"status not 'success', must give reason")
    return jsonify(code=code, status=status, message=message, data=data), code


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
            user_id = get_jwt_identity()
            try:
                _, role, start_time, end_time = sql_account.user_id_get_base_info(user_id)
            except AccountError:
                return api_return(code=404, status="error", message=f"{user_id} not exits")
            if verify_role and role not in role_group:
                return api_return(code=403, status="error", message=f"This API only allow {', '.join(role_group)}")
            if verify_time:
                end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                if start_time < datetime.now() < end_time:
                    return api_return(code=403, status="error", message="Access is prohibited at the current time")
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
    except (AccountError, PasswordError):
        return api_return(code=404, status="error", message="Username or Password error")

    access_token = create_access_token(identity=str(info[0]))
    # 设置admin用户的refresh_token有效期为3小时，否则使用默认值
    refresh_token = create_refresh_token(identity=str(info[0]),
                                         expires_delta=timedelta(hours=3) if info[3] == "admin" else None)
    return api_return(code=200, status="success", data={"access_token": access_token, "refresh_token": refresh_token})


@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    use refresh_token get access_token
    """
    return api_return(code=201, status="success",
                      data={"access_token": create_access_token(identity=get_jwt_identity())})


@app.route('/account', methods=['PUT'])
@jwt_required(refresh=True)
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
        except (AccountError, PasswordError):
            return api_return(code=403, status="error", message="Username or Password error")
    if sql_account.check_username_exits(username):
        sql_account.change_password(username, new_password)
    else:
        return api_return(code=403, status="error", message="Username or Password error")
    return api_return(code=201, status="success", data={"username": username, "password": new_password})


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
        data = {
            "username": username,
            "password": password,
            "role": role,
            "start_time": start_time,
            "end_time": end_time
        }
        return api_return(code=201, status="success", data=data)
    except DuplicateValueError:
        return api_return(code=409, status="error", message=f"username error, '{username}' already in used")
    except TimeSetError:
        return api_return(code=400, status="error", message=f"'{end_time}' early than '{start_time}'")


@app.route('/account', methods=['DELETE'])
@jwt_required(refresh=True)
@info_check(verify_role=True, role_group=["admin"])
def delete_account():
    """
    删除账户
    """
    username = request.json.get("delete_username", None)
    try:
        sql_account.delete_account(username)
    except AccountError:
        return api_return(code=404, status="error", message=f"{username} not exits")
    return api_return(code=204, status="success")


@app.route('/account', methods=['PATCH'])
@jwt_required(refresh=True)
@info_check(verify_role=True, role_group=["admin"])
def change_allow_time():
    """
    修改用户的可用时间
    """
    username = request.json.get("username", None)
    start_time = request.json.get("start_time", None)
    end_time = request.json.get("end_time", None)
    try:
        sql_account.update_allow_time(username=username, start_time=start_time, end_time=end_time)
    except AccountError:
        return api_return(code=404, status="error", message=f"{username} not exits")
    except TimeSetError:
        return api_return(code=400, status="error", message=f"'{end_time}' early than '{start_time}'")
    return api_return(code=201, status="success",
                      data={"username": username, "start_time": start_time, "end_time": end_time})


@app.route('/account', methods=['GET'])
@jwt_required()
def get_account_info():
    """
    获取账户基本信息
    """
    username, role, start_time, end_time = sql_account.user_id_get_base_info(get_jwt_identity())
    data = {
        "username": username,
        "role": role,
        "start_time": start_time,
        "end_time": end_time
    }
    return api_return(code=200, status="success", data=data)


if __name__ == '__main__':
    log_set(logging.INFO)
    app.run(debug=True, port=5000)
