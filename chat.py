import codecs
import json
from typing import Tuple

import openai
import tiktoken


class ChatOpenai:
    def __init__(self, config_path: str = "key.json"):
        # load config
        self.config = self._load_conf(config_path)
        self.max_response_tokens = self.config.get("max_response_tokens", 250)
        self.token_limit = self.config.get("token_limit", 4096)
        self.temperature = self.config.get("temperature", 0.7)
        self.model_name = self.config.get("model_name", "gpt-3.5-turbo")

        # init openai
        self._init_openai()

        # init conversation
        self.conversation = []
        self._init_conversation()
        self.system_msg_num = len(self.conversation)
        self.token_encoding = tiktoken.encoding_for_model(self.model_name)
        self.tokens_per_message, self.token_per_name = self._init_permsg_pername()

    @staticmethod
    def _load_conf(config_path: str) -> dict:
        with codecs.open(config_path, "r", "UTF-8") as conf_f:
            return json.loads("".join(conf_f.readlines()))

    def _init_conversation(self):
        """
        初始化conversation list, 添加预设信息, 可以使用name标签来向对话头添加额外的数据
        https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        """
        self.conversation.append({"role": "system",
                                  "content": self.config.get("system_message", "You are a helpful assistant.")})

    def _init_permsg_pername(self) -> Tuple[int, int]:
        if "gpt-3.5-turbo" in self.model_name:
            return 4, -1
        elif "gpt-4" in self.model_name:
            return 3, 1
        else:
            raise NotImplementedError(
                f"""num_tokens_from_messages() is not implemented for model {self.config["model_name"]}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")

    def _init_openai(self):
        # check necessary data exists
        config_keys = self.config.keys()
        assert "api_key" in config_keys, "api_key is the required, not found in config"
        assert "api_base" in config_keys, "api_base is the required, not found in config"
        assert "deployment_name" in config_keys, "deployment_name is the required, not found in config"

        # init openai
        openai.api_key = self.config["api_key"]
        openai.api_base = self.config["api_base"]
        openai.api_type = self.config.get("api_type", "azure")
        openai.api_version = self.config.get("api_version", "2023-03-15-preview")

    def _token_del_conversation(self):
        """
        todo: 该方案可以保持开头设置的system信息，但是长时间对话，即超过token_limit后，会逐渐舍弃早期对话内容。或额外添加对话总条目限制
        获取对话总token，从头删除超出token的数据(规避system信息)
        """
        conv_history_tokens = self.num_tokens_from_messages()
        while conv_history_tokens + self.max_response_tokens >= self.token_limit:
            del self.conversation[self.system_msg_num]
            conv_history_tokens = self.num_tokens_from_messages()

    def num_tokens_from_messages(self) -> int:
        """
        todo: 每次发送数据之前均需要校验对话总token，或许拖慢了进度，待优化
        from: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        """
        num_tokens = 0
        for message in self.conversation:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(self.token_encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += self.tokens_per_message  # role is always required and always 1 token
        num_tokens += self.token_per_name  # every reply is primed with <im_start>assistant
        return num_tokens

    def get_response(self, message) -> Tuple[str, dict]:
        self.conversation.append({"role": "user", "content": message})
        self._token_del_conversation()  # 删除超过token_limit的数据
        response = openai.ChatCompletion.create(
            engine=self.config["deployment_name"],
            messages=self.conversation,
            temperature=self.temperature,
            max_tokens=self.max_response_tokens,
        )
        response_msg = response['choices'][0]['message']['content']
        self.conversation.append({"role": "assistant", "content": response_msg})
        return response_msg, response


if __name__ == '__main__':
    chat = ChatOpenai(config_path="dev_Ai_key.json")
    while True:
        user_input = input('User: ')
        response, _ = chat.get_response(user_input)
        print(f"Assistant: {response}")
