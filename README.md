# Learn Azure OpenAI

* 学习 Azure 的 OpenAI 课程的笔记和示例代码

* 使用gradio构建基础页面，计划变更为vue3+Django

---

### Official examples

#### 1. build env

```shell
pip install openai tiktoken>=0.3.0
```

#### 2. examples

```python
import openai

openai.api_key = "REPLACE_WITH_YOUR_API_KEY_HERE"
openai.api_base = "REPLACE_WITH_YOUR_ENDPOINT_HERE"
deployment_name = 'REPLACE_WITH_YOUR_DEPLOYMENT_NAME'

openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'

response = openai.ChatCompletion.create(
    engine=deployment_name,
    messages=[
        {"role": "system", "content": "You are a helpful, pattern-following assistant that translates corporate jargon into plain English."},
        {"role": "system", "name": "example_user", "content": "New synergies will help drive top-line growth."},
        {"role": "system", "name": "example_assistant", "content": "Things working well together will increase revenue."},
        {"role": "system", "name": "example_user", "content": "Let's circle back when we have more bandwidth to touch base on opportunities for increased leverage."},
        {"role": "system", "name": "example_assistant", "content": "Let's talk later when we're less busy about how to do better."},
        {"role": "user", "content": "This late pivot means we don't have time to boil the ocean for the client deliverable."},
    ],
)

print(response)
print(response['choices'][0]['message']['content'])
```

---

### key.json

```json
{
  "api_key": "REPLACE_WITH_YOUR_API_KEY_HERE",
  "api_base": "REPLACE_WITH_YOUR_ENDPOINT_HERE",
  "deployment_name": "REPLACE_WITH_YOUR_DEPLOYMENT_NAME",
  "api_type": "azure",
  "api_version": "2023-03-15-preview",
  "model_name": "gpt-3.5-turbo",
  "max_response_tokens": 250,
  "token_limit": 4096,
  "temperature": 0.7,
  "system_message": "You are a helpful assistant."
}
```

* 必填字段: `api_key`、`api_base`、`deployment_name`
* 可选字段: `api_type`、`api_version`、`model_name`、`max_response_tokens`、`token_limit`、`temperature`、`system_message`
> 除必填字段外，其余字段如不在`key.json`中声明则自动使用上方示例的结果
> 
> 必填字段的三个项请访问 [OpenAI_access](https://aka.ms/oai/access) 申请获取

---

### 相关资料

* https://aka.ms/cn/LearnOpenAI
* https://learn.microsoft.com/zh-cn/azure/cognitive-services/openai/