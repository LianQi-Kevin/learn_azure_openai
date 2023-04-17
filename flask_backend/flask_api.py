from flask import Flask, request, jsonify
# from flask_restful import Resource, Api
from flask_jwt_extended import JWTManager
from flask_jwt_extended import create_refresh_token, create_access_token
from flask_jwt_extended import get_jwt_identity, get_jwt
from flask_jwt_extended import jwt_required
from datetime import timedelta
from uuid import uuid4

# init flask & JWT
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = uuid4()
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)

jwt = JWTManager(app)

Test_User = [
    {
        "id": "0",
        "username": "admin",
        "password": "admin_password",
        "role": "admin",
        "start_time": "2023-04-15 12:00:00",
        "end_time": "2023-06-16 12:00:00"
    },
    {
        "id": "1",
        "username": "teacher1",
        "password": "teacher1",
        "role": "teacher",
        "start_time": "2023-04-15 12:00:00",
        "end_time": "2023-06-16 12:00:00"
    }
]


@app.route("/login", methods=["POST"])
def user_login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    # 仅测试，后期更换到数据库操作
    UserInfo = None
    for dictionary in Test_User:
        if dictionary.get("username") == username and dictionary.get("password") == password:
            UserInfo = dictionary
            break
    if UserInfo is None:
        return jsonify(msg="Account not found"), 401

    additional_claims = {
        "role": UserInfo.get("role"),
        "start_time": UserInfo.get("start_time"),
        "end_time": UserInfo.get("end_time")
    }
    access_token = create_access_token(identity=UserInfo['id'], additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=UserInfo['id'], additional_claims=additional_claims)
    return jsonify(access_token=access_token, refresh_token=refresh_token), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
