from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from utils.API_utils import api_return, info_check
from utils.account_sql import AccountSQL
from utils.exceptions import AccountError, PasswordError, DuplicateValueError, TimeSetError

account_bp = Blueprint('account', __name__, url_prefix="/account")
sql_account = AccountSQL(sql_name="./account.db")


@account_bp.route('/', methods=['PUT'])
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


@account_bp.route('/', methods=['POST'])
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
    except DuplicateValueError:
        return api_return(code=409, status="error", message=f"username error, '{username}' already in used")
    except TimeSetError:
        return api_return(code=400, status="error", message=f"'{end_time}' early than '{start_time}'")
    data = {
        "username": username,
        "password": password,
        "role": role,
        "start_time": start_time,
        "end_time": end_time
    }
    return api_return(code=201, status="success", data=data)


@account_bp.route('/', methods=['DELETE'])
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


@account_bp.route('/', methods=['PATCH'])
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


@account_bp.route('/', methods=['GET'])
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
