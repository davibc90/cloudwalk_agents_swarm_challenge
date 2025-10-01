from langchain_core.messages import HumanMessage, AIMessage

def cleanup_messages_for_summarization_node(messages):
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
    """
    
    filtered_messages = []
    
    # Iterate through each message in the input list
    for m in messages:
        name = (getattr(m, "name", "") or "").lower()

        # Check if the message is a HumanMessage and not from the "supervisor"
        if isinstance(m, HumanMessage):
            if name != "supervisor":
                filtered_messages.append(HumanMessage(content=m.content))
                
        # Check if the message is an AIMessage and does not contain tool calls
        elif isinstance(m, AIMessage) and not getattr(m, "tool_calls", False):
            if name != "supervisor":
                filtered_messages.append(AIMessage(content=m.content))

    return filtered_messages

