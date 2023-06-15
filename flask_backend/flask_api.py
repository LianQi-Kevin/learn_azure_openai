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
import os
from datetime import timedelta, datetime
from functools import wraps
from typing import List, Tuple
from uuid import uuid4

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_refresh_token, create_access_token
from flask_cors import CORS

from utils.account_sql import AccountSQL
from utils.exceptions import PasswordError, AccountError, DuplicateValueError, TimeSetError
from utils.chat_for_flask import TokenEncoding, get_response, token_del_conversation, config_load, verify_conversation, create_request_url
from utils.logging_utils import log_set

# init flask & JWT
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = str(uuid4())
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=10)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=15)

# 跨域
CORS(app)

jwt = JWTManager(app)

# sql link
sql_account = AccountSQL(sql_name="account.db", admin_username="admin", admin_password="yxAlFXQ&EL6!sxQ")

# chat configs
CHAT_CONFIGS_PATH = "../keys"
assert os.path.exists(CHAT_CONFIGS_PATH), "ChatGPT config path not found"
CHAT_CONFIGS = config_load(CHAT_CONFIGS_PATH)


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
    logging.debug(f"code: {code}, status: {status}, message: {message}, data: {data}")
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


@app.route('/chat/refresh', methods=['GET'])
def refresh_chat_config():
    """刷新ChatGPT配置信息"""
    global CHAT_CONFIGS
    CHAT_CONFIGS = config_load(CHAT_CONFIGS_PATH)
    return api_return(code=200, status="success", data={"support_list": list(CHAT_CONFIGS.keys())})


@app.route('/chat/azure', methods=['POST'])
@jwt_required()
def azure_chatGPT():
    """请求azure API端点并获取数据"""
    # verify request data
    request_keys = request.json.keys()
    if "model_name" not in request_keys or "messages" not in request_keys:
        return api_return(code=400, status="error", message="'messages' and 'model_name' is required, but not got")

    # info with default
    model_name = request.json.get("model_name")
    if model_name not in CHAT_CONFIGS.keys():
        return api_return(code=400, status="error",
                          message=f"{model_name} not supported, Please contact your administrator")

    # verify conversation format
    conversation = request.json.get("messages")
    try:
        verify_conversation(conversation)
    except KeyError:
        return api_return(code=400, status="error",
                          message="Conversation formal error, 'role' and 'content' required in every conversation items")

    # get default info
    configs = CHAT_CONFIGS[model_name]
    info_dict = {
        "model_name": request.json.get("model_name"),
        "messages": conversation,
        "temperature": request.json.get("temperature", configs.get("temperature", 1)),
        "top_p": request.json.get("top_p", configs.get("top_p", 1)),
        "max_tokens": request.json.get("max_tokens", configs.get("max_response_tokens", 2000)),
        "num_result": request.json.get("num_result", configs.get("num_result", 1)),
        "presence_penalty": request.json.get("presence_penalty", configs.get("presence_penalty", 0)),
        "frequency_penalty": request.json.get("frequency_penalty", configs.get("frequency_penalty", 0)),
    }

    # delete more than token limit's conversation
    info_dict["messages"] = token_del_conversation(
        conversation=info_dict["messages"],
        token_encoding=TokenEncoding,
        token_limit=configs.get("token_limit", 4096 if "gpt-3" in model_name else 8192),
        model_name=model_name,
        max_response_tokens=info_dict["max_tokens"]
    )

    # get response
    try:
        url = create_request_url(api_base=configs["api_base"], api_version=configs["api_version"],
                                 deployment_name=configs["deployment_name"])
        response = get_response(
            conversation=info_dict["messages"],
            request_url=url,
            api_key=configs["api_key"],
            temperature=info_dict["temperature"],
            top_p=info_dict["top_p"],
            max_tokens=info_dict["max_tokens"],
            num_result=info_dict["num_result"],
            presence_penalty=info_dict["presence_penalty"],
            frequency_penalty=info_dict["frequency_penalty"]
        )
        if response.status_code != 200:
            return api_return(code=response.status_code, status="error", message="Request error, please check log",
                              data=response.json())
        else:
            return api_return(code=200, status="success", data={"token_usage": response.json()["usage"]["total_tokens"],
                                                                "messages": response.json()["choices"]})
    except ValueError:
        return api_return(code=400, status="error", message="Request parameter error, Please check your parameter")


if __name__ == '__main__':
    log_set(logging.DEBUG)
    app.run(debug=True, port=5000)
