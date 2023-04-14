from flask import Flask, request
from flask_restful import Resource, Api
# from chat import ChatOpenai

app = Flask(__name__)
api = Api(app)
datas = []


class UserView(Resource):
    """
    通过继承 Resource 来实现调用 GET/POST 等动作方法
    """

    def get(self):
        """
        GET 请求
        :return:
        """
        return {'code': 200, 'msg': 'success', 'data': datas}

    def post(self):
        # 参数数据
        json_data = request.get_json()
        print(json_data)

        # 追加数据到列表中
        new_id = len(datas) + 1
        datas.append({'id': new_id, **json_data})

        # 返回新增的最后一条数据
        return {'code': 200, 'msg': 'ok', 'success': datas}


api.add_resource(UserView, '/User')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
