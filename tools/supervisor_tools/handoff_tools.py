from typing import Annotated
from langgraph.types import Command, Send
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langchain_core.messages import HumanMessage, ToolMessage


def create_task_description_handoff_tool(*, agent_name: str, description: str | None = None):
    """
        Create a handoff tool that transfers the execution flow to a specified agent.
        Args:
            agent_name (str): The name of the agent to transfer the task to.
            description (str | None, optional): A description for the tool. 
                If not provided, defaults to "Transfer to {agent_name}".
        Returns:
            function: A tool function that, when invoked, creates a handoff command 
            to transfer execution to the given agent with the provided task description.
    """

    tool_name = f"transfer_to_{agent_name}"
    description = description or f"Transfer to {agent_name}"

    @tool(tool_name, description=description)
    def handoff_tool(
        task_description: Annotated[str,"Brief description of what the next agent should do"],
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:

        last_active_agent = state.get("last_active_agent", None)

        if last_active_agent == f"{agent_name}":
            return Command(update={
                "messages": [ToolMessage(
                    content="You can't transfer to the same agent twice in a row! Use finish_execution tool to hand back to user or pick another agent!",
                    name=tool_name,
                    tool_call_id=tool_call_id,
                )],
            })

        # Tool message to close execution cycle
        tool_msg = ToolMessage(
            content=f"Transfering to {agent_name} with instructions",
            name=tool_name,
            tool_call_id=tool_call_id,
        )

        # Human message with the task description (maintaining the history!)
        task_msg = HumanMessage(content=task_description, name="supervisor")

        new_state = dict(state)
        new_state["messages"] = state["messages"] + [tool_msg, task_msg]
        new_state["last_active_agent"] = agent_name

        return Command(
            goto=[Send(agent_name, new_state)],
            graph=Command.PARENT,
        )

    return handoff_tool


def supervisor_finishing_tool(*, description: str | None = None):
    """
        Create a finishing tool that completes the agents flow 
        and returns data for the personality node generate the final response.
        Args:
            description (str | None, optional): A description for the tool. 
                If not provided, defaults to "Finish the execution and hand back answer to user".
        Returns:
            function: A tool function that, when invoked, validates execution state 
            and completes the workflow, sending results to the personality node.
    """

    tool_name = f"finish_execution"
    description = description or f"Finish the execution and hand back answer to user"

    @tool(tool_name, description=description)
    def finishing_tool(        
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:

        new_state = dict(state)

        # At least one agent must be assigned in each execution
        last_active_agent = state.get("last_active_agent", None)

        if last_active_agent:
            new_state["last_active_agent"] = None
        else:
            return Command(update={
                "messages": [ToolMessage(
                    content="You must transfer to at least one agent before finishing the execution! Analyze the conversation and transfer to the most suitable agent!",
                    name=tool_name,
                    tool_call_id=tool_call_id,
                )],
            })

        # Toll Message to finish execution
        tool_msg = ToolMessage(
            content=f"Finishing agents work and proceeding to personality node...",
            name=tool_name,
            tool_call_id=tool_call_id,
        )             
        new_state["messages"] = state["messages"] + [tool_msg]

        return Command(
            goto=[Send("personality_node", new_state)],
            graph=Command.PARENT,
        )
    return finishing_tool


def create_supervisor_tools():
    """
        Create and return a list of supervisor tools.
        Includes:
            - Handoff tools for different agents (knowledge, customer service, secretary).
            - A finishing tool to complete execution and return results to the user.
        Returns:
            list: A list of supervisor tool functions.
    """
    tools = []
    tools.append(create_task_description_handoff_tool(agent_name="knowledge_agent"))
    tools.append(create_task_description_handoff_tool(agent_name="customer_service_agent"))
    tools.append(create_task_description_handoff_tool(agent_name="secretary_agent"))
    tools.append(supervisor_finishing_tool())
    return tools

