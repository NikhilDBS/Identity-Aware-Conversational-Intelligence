import json
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.config import settings

RESPONSE_SYSTEM = """You are a helpful, warm conversational agent with access to the user's memory context.

Guidelines:
- Use the provided memory context naturally in your response. Never mention that you have access to memory systems.
- Never output raw Cypher queries, node IDs, or internal reasoning.
- Calibrate your tone based on known emotional patterns — if the user has expressed frustration or exhaustion recently, be empathetic.
- Be concise and conversational, not clinical or robotic.
- If no memory context is provided, respond naturally based on the message alone."""


def compose_response(message: str, context: dict, history: list[dict] | None = None) -> str:
    llm = ChatMistralAI(model=settings.model_name, mistral_api_key=settings.mistral_api_key, temperature=0.7)
    context_str = json.dumps(context, indent=2, default=str) if context else "No memory context available."
    system_msg = SystemMessage(content=RESPONSE_SYSTEM + f"\n\nMemory context:\n{context_str}")
    msgs = [system_msg]
    if history:
        for h in history:
            if h["role"] == "user":
                msgs.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                msgs.append(AIMessage(content=h["content"]))
    msgs.append(HumanMessage(content=message))
    resp = llm.invoke(msgs)
    return resp.content
