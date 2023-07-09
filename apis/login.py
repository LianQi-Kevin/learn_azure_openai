import logging
from datetime import timedelta

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, create_refresh_token

from utils.API_utils import api_return
from utils.account_sql import AccountSQL
from utils.exceptions import PasswordError, AccountError

login_bp = Blueprint('login', __name__)
sql_account = AccountSQL(sql_name="./account.db")


@login_bp.route("/login", methods=["POST"])
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
    logging.info(f"{username} already login")
    access_token = create_access_token(identity=str(info[0]))
    # 设置admin用户的refresh_token有效期为3小时，否则使用默认值
    refresh_token = create_refresh_token(identity=str(info[0]),
                                         expires_delta=timedelta(hours=3) if info[3] == "admin" else None)
    return api_return(code=200, status="success", data={"access_token": access_token, "refresh_token": refresh_token})


@login_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    use refresh_token get access_token
    """
    return api_return(code=201, status="success",
                      data={"access_token": create_access_token(identity=get_jwt_identity())})
