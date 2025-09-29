
from langchain_core.messages import ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command
from typing import Annotated
from config.supabase_client import supabase

@tool
def new_support_call(
    user_id: str,
    issue_description: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    config: RunnableConfig    
):
    """
        Register a new customer service call for human team assessment
        Args:
            user_id (str): ID of the user (uuid retrieved from database)
            issue_description (str): Description of the issue
    """

    user_nickname = config.get("configurable", {}).get("user_nickname")
    
    try:
        response = supabase.table("support_calls").insert({
            "user_id": user_id,
            "issue_description": issue_description,
            "nickname": user_nickname
        }).execute()

        print("\nDados retornados pelo Supabase ao abrir chamado:\n", response)

        if response.data:
            return Command(update={
                "messages": [
                    ToolMessage(
                        content=f"Successfully opened support call! Tell the user to wait for responsible team to get back to them...",
                        tool_call_id=tool_call_id
                    )
                ]
            })
        else:
            return Command(update={
                "messages": [
                    ToolMessage(
                        content="An unknown error occurred while opening the call... Try again!",
                        tool_call_id=tool_call_id
                    )
                ]
            })

    except Exception as e:
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"An error occurred while opening the call: {str(e)}",
                    tool_call_id=tool_call_id
                )
            ]
        })