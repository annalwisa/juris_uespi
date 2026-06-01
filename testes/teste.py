import os
from dotenv import load_dotenv
from openai import OpenAI, api_key

load_dotenv(override=True)
api_key = os.getenv('OPEANAI_API_KEY')

openai = OpenAI()

response = openai.chat.completions.create(model = "gpt-5-nano", messages=[{"role":"user", "content": "me fale sobre a UESPI"}])

response.choices[0].message.content