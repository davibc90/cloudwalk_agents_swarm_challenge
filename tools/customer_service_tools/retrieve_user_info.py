from typing import Annotated
from langchain_core.messages import ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command
from config.supabase_client import supabase


@tool
def retrieve_user_info(
    config: RunnableConfig,
    tool_call_id: Annotated[str, InjectedToolCallId],
):
    """
    Retrieve user information from the database with this tool
    Args:
        None is required
    """

    # Get user nickname from context set previously to graph execution
    user_nickname = config.get("configurable", {}).get("user_nickname")

    try:
        user_info = (
            supabase.table("user_info")
            .select("*")
            .eq("nickname", user_nickname)
            .execute()
        )

        if user_info.data:
            return Command(update={
                "messages": [
                    ToolMessage(
                        content=f"User info retrieved from database:\n{user_info.data}",
                        tool_call_id=tool_call_id
                    )
                ]
            })

        else:
            return Command(update={
                "messages": [
                    ToolMessage(
                        content="User info not found! Ask the user for the data...",
                        tool_call_id=tool_call_id
                    )
                ]
            })

    except Exception as e:
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"An error occurred while retrieving user info: {str(e)}",
                    tool_call_id=tool_call_id
                )
            ]
        })
