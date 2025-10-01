from typing import Annotated
from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.prebuilt import InjectedState
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from utils.cleanup_messages_for_summarization import cleanup_messages_for_summarization_node
from prompts.summarization_prompts import none_summary_prompt, existing_summary_prompt
from uuid import uuid4
from utils.logger_utils import setup_logger
from config.env_config import env

logger = setup_logger(__name__)

# Environment variables
SUMMARIZATION_LLM = env.summarization_llm
SUMMARIZATION_LLM_TEMPERATURE = env.summarization_llm_temperature
KEEP_LAST = env.keep_last
STARTING_SUMMARY_INDEX = env.starting_summary_index
SUMMARY_TOKENS = env.summary_tokens
OPENAI_API_KEY = env.openai_api_key


def summary_node(State, rate_limiter: InMemoryRateLimiter):
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
    3) Rewrites the state's messages by:
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
    """
    
    def _node(state: Annotated[dict, InjectedState]):
        
        messages_list = state.get("messages", []) or []
        list_size = len(messages_list)

        logger.info(f"\nMessage list size: {list_size}")

        # Only summarize when there is enough history
        if list_size < 30:
            logger.info("Message list size shorter than 30, will not be summarized...")
            return {"last_active_agent": None}
        logger.info("Message list size longer than 30, continue to summarization...")

        model = ChatOpenAI(
            model=SUMMARIZATION_LLM,
            temperature=SUMMARIZATION_LLM_TEMPERATURE,
            max_completion_tokens=SUMMARY_TOKENS,
            openai_api_key=OPENAI_API_KEY,
            rate_limiter=rate_limiter,
        )

        # Clean up messages for summarization
        summary = state.get("summary")
        filtered_messages = cleanup_messages_for_summarization_node(messages_list)

        # Define context for LLM
        if summary:
            summary_prompt = existing_summary_prompt(summary)
            context_for_llm = filtered_messages[STARTING_SUMMARY_INDEX:] + [HumanMessage(content=summary_prompt)]
        else:
            summary_prompt = none_summary_prompt
            context_for_llm = filtered_messages + [HumanMessage(content=summary_prompt)]

        # Generate the summary
        response = model.invoke(context_for_llm)
        new_summary_text = getattr(response, "content", "") or ""

        # ==================
        # NEW CHAT HISTORY
        # ==================

        # 1. Remove everything that exists in the state (by id)
        delete_all = [RemoveMessage(REMOVE_ALL_MESSAGES)]

        # 2. Builds summary message to be inserted in the first position of the chat history
        summary_message = AIMessage(
            content=new_summary_text,
            name="summary",
            id=str(uuid4()),
        )

        # 3. Reinsert: builds last N cloned messages to be inserted in the last positions of the chat history
        lastN_clones = []
        lastN = filtered_messages[-KEEP_LAST:] if KEEP_LAST > 0 else []

        for m in lastN:
            if isinstance(m, HumanMessage):
                lastN_clones.append(
                    HumanMessage(content=m.content, name=getattr(m, "name", None), id=str(uuid4()))
                )
            elif isinstance(m, AIMessage):
                lastN_clones.append(
                    AIMessage(content=m.content, name=getattr(m, "name", None), id=str(uuid4()))
                )
        logger.info("Last N cloned messages: %s", lastN_clones)

        # 4. New chat history
        new_messages = delete_all + [summary_message] + lastN_clones

        return {
            "summary": new_summary_text,
            "messages": new_messages,
            "last_active_agent": None
        }

    return _node