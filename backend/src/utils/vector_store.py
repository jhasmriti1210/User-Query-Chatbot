import os
from dotenv import load_dotenv

load_dotenv()

from langchain.chat_models import ChatOpenAI


SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "").strip()
if not SYSTEM_PROMPT:
    raise ValueError("SYSTEM_PROMPT is not set in the .env file.")

system_prompt = f"{SYSTEM_PROMPT} CONTEXT: {{context}} LANGUAGE: {{language}}"

# Use OpenAI or any LLM you prefer
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")  # Or "gpt-4"
