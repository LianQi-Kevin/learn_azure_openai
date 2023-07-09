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
from datetime import timedelta
from uuid import uuid4

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from apis.chat import chat_bp
from utils.logging_utils import log_set
# from apis.account import account_bp
from apis.login import login_bp

# init flask & JWT
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = str(uuid4())
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=10)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=15)

# 跨域
CORS(app)
jwt = JWTManager(app)

# logging
log_set(logging.DEBUG, log_save=True)

# apis - blueprint
app.register_blueprint(login_bp)
# app.register_blueprint(account_bp)    # 暂时禁用账户操作API
app.register_blueprint(chat_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
