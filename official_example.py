import openai


openai.api_key = "REPLACE_WITH_YOUR_API_KEY_HERE"
openai.api_base = "REPLACE_WITH_YOUR_ENDPOINT_HERE"
openai.api_type = 'azure'
openai.api_version = '2023-03-15-preview'
deployment_name = 'REPLACE_WITH_YOUR_DEPLOYMENT_NAME'

response = openai.ChatCompletion.create(
    engine=deployment_name,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Does Azure OpenAI support customer managed keys?"},
        {"role": "assistant", "content": "Yes, customer managed keys are supported by Azure OpenAI."},
        {"role": "user", "content": "Do other Azure Cognitive Services support this too?"}
    ]
)

print(response)
print(response['choices'][0]['message']['content'])
