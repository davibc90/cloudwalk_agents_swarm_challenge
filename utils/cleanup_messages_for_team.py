"""
    Clean up and filter a list of LangChain messages for the summarization node.

    ### Description
    This function processes a list of LangChain messages (`HumanMessage`, `AIMessage`, 
    and optionally `ToolMessage`) and returns a filtered version suitable for use by 
    the summarization node. It removes unnecessary metadata, excludes supervisor messages, 
    and ignores AI messages that only contain tool calls.

    ### Filtering Rules
    - **HumanMessage**:
      - Included only if the sender is not `"supervisor"`.
      - Only the `content` field is preserved.
    - **AIMessage**:
      - Included only if it does not contain tool calls (`tool_calls` is False or missing).
      - Excluded if the sender is `"supervisor"`.
      - Only the `content` field is preserved.
    - **Other message types** (e.g., `ToolMessage`):
      - Ignored and excluded from the result.

    ### Parameters
    - **messages** (*list*): A list of LangChain message objects (`HumanMessage`, `AIMessage`, `ToolMessage`).

    ### Returns
    - **list**: A new list containing only the cleaned and filtered `HumanMessage` 
      and `AIMessage` objects.

    ### Example
    ```python
    from langchain_core.messages import HumanMessage, AIMessage

    msgs = [
        HumanMessage(content="Hello!", name="user"),
        AIMessage(content="Hi there!", name="assistant"),
        HumanMessage(content="Ignore me", name="supervisor"),
    ]

    filtered = cleanup_messages_for_summary_team(msgs)
    # Result: [HumanMessage(content="Hello!"), AIMessage(content="Hi there!")]
    ```
"""

from langchain_core.messages import HumanMessage, AIMessage

def cleanup_messages_for_summarization_node(messages):
    filtered_messages = []
    for m in messages:
        name = (getattr(m, "name", "") or "").lower()

        if isinstance(m, HumanMessage):
            if name != "supervisor":
                filtered_messages.append(
                    HumanMessage(
                        content=m.content,
                    )
                )
        elif isinstance(m, AIMessage) and not getattr(m, "tool_calls", False):
            if name != "supervisor":
                filtered_messages.append(
                    AIMessage(
                        content=m.content,
                    )
                )
    return filtered_messages

