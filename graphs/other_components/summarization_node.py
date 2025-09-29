"""
Factory for a LangGraph node that maintains a rolling conversation summary and
shrinks message history to control context size and cost.

Behavior:
- Skips summarization until the message list reaches 30 items (configurable only
  in code). Below that threshold, returns only {"last_active_agent": None}.
- When summarizing:
  1) Builds a dedicated summarization prompt:
     - If an existing summary is present, uses `existing_summary_prompt(summary)`
       and starts from `STARTING_SUMMARY_INDEX` within the cleaned history.
     - Otherwise, uses `none_summary_prompt` over the full cleaned history.
  2) Calls a lightweight LLM (`SUMMARIZATION_LLM`) to produce `new_summary_text`.
  3) Rewrites the state’s messages by:
     - Emitting a `RemoveMessage(REMOVE_ALL_MESSAGES)` sentinel to clear history.
     - Inserting a single `AIMessage` named `"summary"` with the new summary.
     - Re-appending clones of the last `KEEP_LAST` cleaned messages
       (preserving role/name, generating fresh IDs).

Inputs:
    def summary_node(State, rate_limiter: InMemoryRateLimiter):
        Returns a callable node:

            def _node(state: Annotated[dict, InjectedState]) -> dict

        The node reads:
          - state["messages"] (list of LangChain messages)
          - state.get("summary") (optional prior summary)

        And returns either:
          - {"last_active_agent": None}  # when under threshold
          - {
                "summary": <new_summary_text>,
                "messages": [
                    RemoveMessage(REMOVE_ALL_MESSAGES),
                    AIMessage(name="summary", content=<new_summary_text>, ...),
                    *lastN_clones
                ],
            }

Environment variables:
- SUMMARIZATION_LLM (default: "gpt-4.1-nano"): Model used for summarization.
- SUMMARIZATION_LLM_TEMPERATURE (default: "0.15"): Temperature for the model.
- KEEP_LAST (default: "4"): Number of most recent messages to retain after summary.
- STARTING_SUMMARY_INDEX (default: "5"): Start index in cleaned history when an
  existing summary is present.
- SUMMARY_TOKENS (default: "300"): Max completion tokens for the summary call.
- OPENAI_API_KEY: Required; raises ValueError if missing.

Dependencies & helpers:
- `cleanup_messages_for_summary_team(messages)` filters/normalizes history before
  summarization.
- Prompts: `none_summary_prompt`, `existing_summary_prompt`.
- Uses `ChatOpenAI` with optional `rate_limiter` (InMemoryRateLimiter).
- Logs progress and decisions via `utils.logger_utils.setup_logger`.

Notes:
- The node returns a list of messages as required by LangGraph, combining the
  summary message with the most recent `KEEP_LAST` messages to preserve immediate
  context while keeping the state compact.
- IDs are regenerated for cloned messages to avoid collisions.
"""


import os
from typing import Annotated
from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.prebuilt import InjectedState
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from utils.cleanup_messages_for_team import cleanup_messages_for_summarization_node
from prompts.summarization_prompts import none_summary_prompt, existing_summary_prompt
from uuid import uuid4
from utils.logger_utils import setup_logger

logger = setup_logger(__name__)

from dotenv import load_dotenv
load_dotenv()

# Converta tipos corretamente
SUMMARIZATION_LLM = os.getenv("SUMMARIZATION_LLM", "gpt-4.1-nano")
SUMMARIZATION_LLM_TEMPERATURE = float(os.getenv("SUMMARIZATION_LLM_TEMPERATURE", "0.15"))
KEEP_LAST = int(os.getenv("KEEP_LAST", "4"))
STARTING_SUMMARY_INDEX = int(os.getenv("STARTING_SUMMARY_INDEX", "5"))
SUMMARY_TOKENS = int(os.getenv("SUMMARY_TOKENS", "300"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Verify if the environment variable is defined!")

def summary_node(State, rate_limiter: InMemoryRateLimiter):
    
    def _node(state: Annotated[dict, InjectedState]):
        messages_list = state.get("messages", []) or []
        list_size = len(messages_list)

        logger.info(f"\nMessage list size: {list_size}")

        # Só resume quando há bastante histórico
        if list_size < 30:
            logger.info("Message list size shorter than 30, will not be summarized...")
            # Retorne apenas o que muda; não quebre o estado de mensagens
            return {"last_active_agent": None}

        logger.info("Message list size longer than 30, continue to summarization...")

        model = ChatOpenAI(
            model=SUMMARIZATION_LLM,
            temperature=SUMMARIZATION_LLM_TEMPERATURE,
            max_completion_tokens=SUMMARY_TOKENS,
            openai_api_key=OPENAI_API_KEY,
            rate_limiter=rate_limiter,
        )

        summary = state.get("summary")
        filtered_messages = cleanup_messages_for_summarization_node(messages_list)

        if summary:
            summary_prompt = existing_summary_prompt(summary)
            context_for_llm = filtered_messages[STARTING_SUMMARY_INDEX:] + [HumanMessage(content=summary_prompt)]
        else:
            summary_prompt = none_summary_prompt
            context_for_llm = filtered_messages + [HumanMessage(content=summary_prompt)]

        # Gera o resumo
        response = model.invoke(context_for_llm)
        new_summary_text = getattr(response, "content", "") or ""

        # Remove tudo que existe hoje no state (por id)
        delete_all = [RemoveMessage(REMOVE_ALL_MESSAGES)]

        # Reinsere: primeiro o resumo (AIMessage), depois as últimas N clonadas
        summary_message = AIMessage(
            content=new_summary_text,
            name="summary",
            id=str(uuid4()),
        )

        lastN = filtered_messages[-KEEP_LAST:] if KEEP_LAST > 0 else []
        lastN_clones = []
        for m in lastN:
            if isinstance(m, HumanMessage):
                lastN_clones.append(
                    HumanMessage(content=m.content, name=getattr(m, "name", None), id=str(uuid4()))
                )
            elif isinstance(m, AIMessage):
                lastN_clones.append(
                    AIMessage(content=m.content, name=getattr(m, "name", None), id=str(uuid4()))
                )

        # Use o formatter do logging corretamente
        logger.info("Last N cloned messages: %s", lastN_clones)

        new_messages = delete_all + [summary_message] + lastN_clones

        return {
            "summary": new_summary_text,
            "messages": new_messages,
        }

    return _node