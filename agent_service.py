"""
Conversation agent service using Swarmauri (Groq + system context).
"""
import logging
from typing import Any, Optional

from config import get_config

logger = logging.getLogger(__name__)

# Lazy swarmauri imports (after config so env is loaded)
_GroqModel = None
_SystemMessage = None
_SimpleConversationAgent = None
_MaxSystemContextConversation = None


def _ensure_swarmauri() -> None:
    global _GroqModel, _SystemMessage, _SimpleConversationAgent, _MaxSystemContextConversation
    if _GroqModel is not None:
        return
    import swarmauri  # noqa: F401
    import importlib

    _mod = importlib.import_module("swarmauri.llms.GroqModel")
    _GroqModel = getattr(_mod, "GroqModel")
    _mod = importlib.import_module("swarmauri.messages.SystemMessage")
    _SystemMessage = getattr(_mod, "SystemMessage")
    _mod = importlib.import_module("swarmauri.agents.SimpleConversationAgent")
    _SimpleConversationAgent = getattr(_mod, "SimpleConversationAgent")
    _mod = importlib.import_module("swarmauri.conversations.MaxSystemContextConversation")
    _MaxSystemContextConversation = getattr(_mod, "MaxSystemContextConversation")


def get_available_models() -> list[str]:
    """Return list of Groq model names for the dropdown."""
    _ensure_swarmauri()
    config = get_config()
    try:
        llm = _GroqModel(api_key=config.groq_api_key)
        return list(llm.allowed_models) if llm.allowed_models else ["default-model"]
    except Exception as e:
        logger.warning("Could not list Groq models: %s", e)
        return ["default-model"]


def run_conversation(
    user_input: str,
    system_context: str,
    model_name: str,
    tone: str,
) -> tuple[str, Optional[str]]:
    """
    Run one turn of conversation. Returns (response_text, error_message).
    If error_message is set, response_text may still contain partial content.
    """
    _ensure_swarmauri()
    config = get_config()

    try:
        llm = _GroqModel(api_key=config.groq_api_key, name=model_name)
    except Exception as e:
        logger.exception("Failed to load model %s", model_name)
        return "", f"Error loading model: {e}"

    conversation = _MaxSystemContextConversation()
    agent = _SimpleConversationAgent(llm=llm, conversation=conversation)
    agent.conversation.system_context = _SystemMessage(
        content=f"{system_context or ''}\nTone: {tone}".strip()
    )

    try:
        result = agent.exec(user_input)
        return result, None
    except Exception as e:
        logger.exception("Conversation execution failed")
        return "", str(e)
