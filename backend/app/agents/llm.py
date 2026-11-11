import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


# Locate backend/.env explicitly
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

# Ensure .env values override previously loaded environment values
load_dotenv(dotenv_path=ENV_FILE, override=True)


def get_llm():

    model_name = os.getenv("GEMINI_MODEL")
    api_key = os.getenv("GOOGLE_API_KEY")

    if not model_name:
        raise ValueError("GEMINI_MODEL is missing from .env")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing from .env")

    print("========== PLANNING LLM DEBUG ==========")
    print("ENV FILE:", ENV_FILE)
    print("SELECTED MODEL:", model_name)
    print("========================================")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
        max_retries=2,
        timeout=120,
    )