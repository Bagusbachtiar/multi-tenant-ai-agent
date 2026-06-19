import re

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from app.config import settings

_llm = ChatOllama(
    model=settings.llm_model,
    base_url=settings.ollama_base_url,
    num_ctx=4096,
)


def _strip_thinking(text: str) -> str:
    # Qwen3 wraps chain-of-thought in <think> blocks — remove before returning
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()


async def generate(prompt: str) -> str:
    response = await _llm.ainvoke([HumanMessage(content=prompt)])
    return _strip_thinking(response.content)
