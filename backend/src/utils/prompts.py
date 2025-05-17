import os
from dotenv import load_dotenv

load_dotenv()
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "").strip()

if not SYSTEM_PROMPT:
    raise ValueError("SYSTEM_PROMPT is not set in the .env file.")

system_prompt = f"{SYSTEM_PROMPT} CONTEXT: {{context}} LANGUAGE: {{language}}"
