import logging
from datetime import datetime
from functools import wraps
from typing import Tuple, List

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from utils.account_sql import AccountSQL
from utils.exceptions import AccountError

sql_account = AccountSQL(sql_name="./account.db")


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
