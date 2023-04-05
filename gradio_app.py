import logging
from copy import deepcopy
from typing import Tuple

import gradio as gr
import openai

from chat import ChatOpenai
from logging_utils import log_set


class GrChat(ChatOpenai):
    """
    重写ChatOpenai的get_response相关方法, 不再更新self.conversation
    """

    def gr_get_response(self, messages: list, temperature: float) -> Tuple[str, dict, list]:
        self._gr_token_del_conversation(messages)
        logging.info(f"Request message: {messages[-1]}")
        response = openai.ChatCompletion.create(
            engine=self.config["deployment_name"],
            messages=messages,
            temperature=temperature,
            max_tokens=self.max_response_tokens,
        )
        response_msg = response['choices'][0]['message']['content']
        messages.append({"role": "assistant", "content": response_msg})
        logging.info(f"Response message: {messages[-1]}")
        return response_msg, response, messages

    def _gr_token_del_conversation(self, messages: list):
        conv_history_tokens = self.gr_num_tokens_from_messages(messages)
        while conv_history_tokens + self.max_response_tokens >= self.token_limit:
            del messages[self.system_msg_num]
            conv_history_tokens = self.gr_num_tokens_from_messages(messages)

    def gr_num_tokens_from_messages(self, messages: list) -> int:
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(self.token_encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += self.tokens_per_message  # role is always required and always 1 token
        num_tokens += self.token_per_name  # every reply is primed with <im_start>assistant
        return num_tokens


def bot(chat_history: list, conversation_history: list, temperature: float) -> Tuple[list, list]:
    text = chat_history[-1][0]
    conversation_history.append({"role": "user", "content": text})
    response_msg, _, messages = chat.gr_get_response(conversation_history, temperature)
    chat_history[-1][1] = response_msg
    print(response_msg)
    return chat_history, conversation_history


def user(text: str, chat_history: list) -> Tuple[str, list]:
    chat_history.append([text, None])
    return "", chat_history


def main():
    global chat
    with gr.Blocks() as demo:
        chatbot = gr.Chatbot().style(height=550)
        text = gr.Textbox(placeholder="Enter text and press enter", show_label=False)
        upload_button = gr.Button("Push")
        gr.Markdown("Advanced Option: \n")
        temperature = gr.Slider(maximum=1, minimum=0, step=0.1, value=0.7, label="temperature")
        conversations = gr.State(value=deepcopy(chat.conversation))

        text.submit(user, inputs=[text, chatbot], outputs=[text, chatbot]).then(
            bot, [chatbot, conversations, temperature], [chatbot, conversations]
        )
        upload_button.click(user, inputs=[text, chatbot], outputs=[text, chatbot]).then(
            bot, [chatbot, conversations, temperature], [chatbot, conversations]
        )

    return demo


if __name__ == '__main__':
    # init logging
    log_set(log_level=logging.INFO, log_save=True, save_path="gradio_chat.log")

    # init openai
    chat = GrChat("dev_Ai_key.json")
    logging.info("Successful init GrChat class")
    logging.info(f"Class config: {chat.config}")

    app = main()
    app.launch(share=False, server_port=6006, server_name="0.0.0.0")
