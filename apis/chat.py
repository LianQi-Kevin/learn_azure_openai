import os

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from utils.API_utils import api_return
from utils.chat_for_flask import config_load, verify_conversation, create_request_url, get_response, TokenEncoding, \
    token_del_conversation

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# chat configs
CHAT_CONFIGS_PATH = "./keys"
assert os.path.exists(CHAT_CONFIGS_PATH), "ChatGPT config path not found"
CHAT_CONFIGS = config_load(CHAT_CONFIGS_PATH)


@chat_bp.route('/refresh', methods=['GET'])
def refresh_chat_config():
    """刷新ChatGPT配置信息"""
    global CHAT_CONFIGS
    CHAT_CONFIGS = config_load(CHAT_CONFIGS_PATH)
    return api_return(code=200, status="success", data={"support_list": list(CHAT_CONFIGS.keys())})


@chat_bp.route('/azure', methods=['POST'])
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
        print(response.json())
        if response.status_code != 200:
            return api_return(code=response.status_code, status="error",
                              message="Request error, please check response data",
                              data=response.json())
        else:
            return api_return(code=200, status="success", data={"token_usage": response.json()["usage"]["total_tokens"],
                                                                "messages": response.json()["choices"]})
    except ValueError:
        return api_return(code=400, status="error", message="Request parameter error, Please check your parameter")
