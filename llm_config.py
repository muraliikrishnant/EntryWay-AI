import os

from dotenv import load_dotenv

load_dotenv()


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
    if provider == "ollama":
        return os.getenv("CREWAI_LLM", "ollama/gemma4:31b-cloud")
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
        return os.getenv("CREWAI_TOOL_LLM", "ollama/gpt-oss:20b")
    return get_llm()


llm = get_llm()
tool_llm = get_tool_llm()
