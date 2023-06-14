"""重新封装功能性函数, 用来支持flask封装调用"""
import glob
import json
import os
from typing import Tuple, List

import requests
import tiktoken
from requests.exceptions import RequestException

# token解码器, 耗时较长, 固使用全局变量
TokenEncoding = tiktoken.get_encoding('cl100k_base')


def config_load(config_path: str = "../keys") -> dict:
    """解析文件夹内配置文件并创建配置dict"""
    assert os.path.exists(config_path), f"{config_path} not found, config load ERROR"
    configs = {}
    for config in glob.glob(os.path.join(config_path, "*.json")):
        with open(config, 'r') as f:
            info_dict = json.loads("".join(f.readlines()))
        configs[info_dict['model_name']] = info_dict
    return configs


def get_token_permsg_pername(model_name: str) -> Tuple[int, int]:
    """获取模型的每一条对话的格式消耗固定token值"""
    if "gpt-3.5" in model_name:
        return 4, -1
    else:
        return 3, 1


def verify_conversation(conversation: List[dict]) -> bool:
    """校验对话列表内每一条对话是否均包含role和content项"""
    try:
        _ = [(msg["role"], msg["content"]) for msg in conversation]
        return True
    except KeyError:
        return False


def num_tokens_from_messages(conversation: List[dict], token_encoding: tiktoken.core.Encoding,
                             model_name: str = "gpt-3.5-turbo") -> int:
    """获取对话的总token数"""
    token_per_message, token_per_name = get_token_permsg_pername(model_name=model_name)
    num_tokens = 0
    for message in conversation:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(token_encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += token_per_message  # role is always required and always 1 token
    num_tokens += token_per_name  # every reply is primed with <im_start>assistant
    return num_tokens


def token_del_conversation(conversation: List[dict], token_encoding: tiktoken.core.Encoding,
                           model_name: str = "gpt-3.5-turbo", max_response_tokens: int = 250, token_limit: int = 4096):
    """获取对话总token，从头删除超出token的数据(规避system信息)"""
    system_msg_num = len([msg for msg in verify_msg if msg['role'] == 'system'])
    conv_history_tokens = num_tokens_from_messages(conversation, token_encoding, model_name)
    while conv_history_tokens + max_response_tokens >= token_limit:
        del conversation[system_msg_num]
        conv_history_tokens = num_tokens_from_messages(conversation, token_encoding, model_name)


def get_response(conversation: List[dict], request_url: str, api_key: str,
                 temperature: float = 1, top_p: float = 1, max_tokens: int = 2048,
                 num_result: int = 1, presence_penalty: float = 0, frequency_penalty: float = 0) -> dict:
    """请求端点获取数据"""
    # parameter verify
    assert verify_conversation(conversation), ValueError("conversation wrong")
    assert 0 <= temperature <= 2, ValueError(f"temperature value wrong, min: 0, max: 2, wrong value: {temperature}")
    assert 0 <= top_p <= 2, ValueError(f"top_p value wrong, min: 0, max: 2, wrong value: {top_p}")
    assert 1 <= max_tokens <= 5000, ValueError(f"max_tokens value wrong, min: 1, max: 5000, wrong value: {max_tokens}")
    assert 1 <= num_result <= 20, ValueError(f"num_result value wrong, min: 1, max: 20, wrong value: {num_result}")
    assert -2 <= presence_penalty <= 2, ValueError(
        f"presence_penalty value wrong, min: -2, max: 2, wrong value: {presence_penalty}")
    assert -2 <= frequency_penalty <= 2, ValueError(
        f"frequency_penalty value wrong, min: -2, max: 2, wrong value: {frequency_penalty}")

    # get response
    headers = {'api-key': api_key, 'Content-Type': 'application/json'}
    # https://platform.openai.com/docs/api-reference/chat/create
    request_body = {"messages": conversation, "temperature": temperature, "top_p": top_p, "max_tokens": max_tokens,
                    "n": num_result, "presence_penalty": presence_penalty, "frequency_penalty": frequency_penalty}
    response = requests.request(method="POST", url=request_url, headers=headers, json=request_body)
    if response.status_code != 200:
        raise RequestException("Request error, Please verify parameter")
    else:
        return json.loads(response.text)



def chatGPT_request():



if __name__ == '__main__':
    import time

    verify_msg = [{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": "Does Azure OpenAI support customer managed keys?"},
                  {"role": "assistant", "content": "Yes, customer managed keys are supported by Azure OpenAI."},
                  {"role": "user", "content": "Do other Azure Cognitive Services support this too?"}]

    st_time = time.time()
    # info = config_load("../keys")
    # token_encoding = tiktoken.get_encoding('cl100k_base')
    print(time.time() - st_time)
