import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_CLOUD_BASE_URL = "https://ollama.com/v1"


def _ollama_model(model_env: str, default: str):
    raw = os.getenv(model_env, default)
    return raw.split("/", 1)[1] if raw.startswith("ollama/") else raw


def _build_ollama_llm(model_env: str, default: str):
    model = _ollama_model(model_env, default)
    api_key = os.getenv("OLLAMA_API_KEY", "").strip()
    if api_key:
        from crewai import LLM

        return LLM(model=f"openai/{model}", base_url=OLLAMA_CLOUD_BASE_URL, api_key=api_key)
    return f"ollama/{model}"


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
    if provider == "ollama":
        return _build_ollama_llm("CREWAI_LLM", "ollama/gemma4:31b-cloud")
    if provider == "openrouter":
        model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
        return f"openrouter/{model}"
    if provider == "google":
        model = os.getenv("GOOGLE_MODEL", "gemini/gemini-1.5-flash")
        return model if model.startswith("gemini/") else f"gemini/{model}"
    raise ValueError("LLM_PROVIDER must be one of: ollama, openrouter, google")


def get_tool_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
    if provider == "ollama":
        return _build_ollama_llm("CREWAI_TOOL_LLM", "ollama/gpt-oss:20b")
    return get_llm()


llm = get_llm()
tool_llm = get_tool_llm()
