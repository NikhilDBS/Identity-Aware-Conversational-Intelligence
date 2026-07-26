from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings

COT_SYSTEM = """You are a reasoning system. Given a user message, output a JSON object with these fields:

{
  "needs_memory": true/false,
  "likely_topic": "string or null",
  "memory_worthy": true/false,
  "reasoning": "hidden scratchpad - never shown to user"
}

- needs_memory: whether answering this message meaningfully requires prior context about the user
- likely_topic: the main topic (work, health, relationships, hobbies, etc) for memory retrieval filtering
- memory_worthy: whether the message contains new information worth remembering
- reasoning: your chain-of-thought (internal only)"""


def reason_about_message(message: str) -> dict:
    llm = ChatMistralAI(model=settings.model_name, mistral_api_key=settings.mistral_api_key, temperature=0)
    msgs = [SystemMessage(content=COT_SYSTEM), HumanMessage(content=f"Analyze this user message:\n\n{message}")]
    resp = llm.invoke(msgs)
    import json
    text = resp.content
    if "```" in text:
        import re
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
    try:
        return json.loads(text.strip())
    except Exception:
        return {"needs_memory": True, "likely_topic": None, "memory_worthy": True, "reasoning": "parse error"}
