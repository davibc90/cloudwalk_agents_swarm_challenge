
from typing import Annotated
from langgraph.prebuilt import InjectedState, ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.graph import StateGraph, START, END
# Knowledge Agent tools
from tools.knowledge_agent.retriever_tool import initialize_retriever_for_rag
from tools.knowledge_agent.web_search_tool import web_search_tool
# Supervisor Agent tools
from tools.supervisor_tools.handoff_tools import create_supervisor_tools
# Customer Service Agent tools
from tools.customer_service_tools.new_support_call import new_support_call
from tools.customer_service_tools.retrieve_user_info import retrieve_user_info
# Secretary Agent tools
from tools.secretary_tools.get_appointments import get_appointments
from tools.secretary_tools.add_appointment import add_appointment   
# Prompts
from prompts.secretary_agent_prompt import secretary_agent_prompt
from prompts.customer_service_agent_prompt import customer_service_agent_prompt
from prompts.knowledge_agent_prompt import knowledge_agent_prompt
from prompts.supervisor_prompt import supervisor_prompt
from config.env_config import env

from utils.logger_utils import setup_logger
logger = setup_logger(__name__)

LLM = env.llm
LLM_TEMPERATURE = env.llm_temperature
MAX_COMPLETION_TOKENS = env.max_completion_tokens
LLM_TIMEOUT = env.llm_timeout
OPENAI_API_KEY = env.openai_api_key

# Tool sets for each agent
knowledge_agent_tools = [initialize_retriever_for_rag(), web_search_tool]
secretary_agent_tools = [get_appointments, add_appointment]
customer_service_agent_tools = [retrieve_user_info, new_support_call]
supervisor_agent_tools = create_supervisor_tools()

# Generates the agent graph
def generate_worker_graph(
    agent_name: str,
    shared_state_schema: Annotated[dict, InjectedState],
    rate_limiter: InMemoryRateLimiter,
    current_date: str
):
    """
        Defines the `generate_worker_graph` function, which builds a specialized LangGraph
        subgraph for a given agent (knowledge, customer service, secretary, or supervisor).
        Each agent is configured with its own toolset, system prompt, and execution flow.

        Main features:
        - Dynamically assigns tool sets and prompts per agent type:
        * knowledge_agent → retrieval (RAG) + web search.
        * customer_service_agent → user info + support call handling.
        * secretary_agent → appointment management (get/add).
        * supervisor → orchestration/handoff tools.
        - Wraps tools in a `ToolNode` for controlled invocation.
        - Configures `ChatOpenAI` with environment-based settings:
        model name, temperature, token limits, timeout, and API key.
        - Applies `InMemoryRateLimiter` to prevent excessive API requests.
        - Uses conditional edges:
        * Redirects to `tool_node` when the model produces tool calls.
        * Terminates immediately unless the agent is the supervisor, which
            can loop for further decisions.

        Public API:
            def generate_worker_graph(
                agent_name: str,
                shared_state_schema: Annotated[dict, InjectedState],
                rate_limiter: InMemoryRateLimiter,
                current_date: str
            ) -> StateGraph:
                Builds and compiles the agent subgraph.

                Args:
                    agent_name: Identifier of the agent type ("knowledge_agent",
                        "customer_service_agent", "secretary_agent", "supervisor").
                    shared_state_schema: Shared state structure across graph nodes.
                    rate_limiter: Configured limiter to control API request bursts.
                    current_date: Current date string, appended to prompts to ground
                        responses in temporal context.

                Returns:
                    A compiled `StateGraph` object representing the agent’s workflow.

        Environment variables:
        - LLM (str, default "gpt-4.1-mini"): Model name.
        - LLM_TEMPERATURE (float, default 0.15): Sampling temperature.
        - MAX_COMPLETION_TOKENS (int, default 200): Max output tokens.
        - LLM_TIMEOUT (int, default 20): Request timeout in seconds.
        - OPENAI_API_KEY (str): Required, raises ValueError if missing.

        Dependencies:
        - langgraph, langchain-openai, langchain-core, dotenv, and
        local tools/prompts from `agent_tools.*` and `prompts.*`.
    """

    # Dynamic tools set and system prompt assignment based on agent type
    if agent_name == "knowledge_agent":
        tools = knowledge_agent_tools
        instructions = current_date + "\n\n" + knowledge_agent_prompt
    elif agent_name == "customer_service_agent":
        tools = customer_service_agent_tools
        instructions = current_date + "\n\n" + customer_service_agent_prompt
    elif agent_name == "secretary_agent":
        tools = secretary_agent_tools
        instructions = current_date + "\n\n" + secretary_agent_prompt
    elif agent_name =="supervisor":
        tools = supervisor_agent_tools
        instructions = current_date + "\n\n" + supervisor_prompt
    
    tool_node = ToolNode(tools)    
  
    def call_worker(state: shared_state_schema):
        logger.info(f"\nStarting agent node of the graph for {agent_name}...")

        # Model configuration
        model = ChatOpenAI(
            model=LLM,
            temperature=LLM_TEMPERATURE,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            timeout=LLM_TIMEOUT,
            openai_api_key=OPENAI_API_KEY,
            rate_limiter=rate_limiter,
        ).bind_tools(
            tools,
            tool_choice="any" if agent_name == "supervisor" else "auto",
            parallel_tool_calls=False
        )

        sys_msg = SystemMessage(content=instructions)
        messages = [sys_msg] + state["messages"]

        # Invoke the model to generate a response
        response = model.invoke(messages)
        response.name = agent_name
        return {"messages": response}
                  
    # Conditional Edge
    def should_continue(state: shared_state_schema):
        messages = state["messages"]
        last_message = messages[-1]
                    
        # If tool call is present, redirect to tool node
        if last_message.tool_calls:
            logger.info(f"Tool call detected. Redirecting to tool node... {last_message.tool_calls}")
            return "tool_node"
        
        if not last_message.tool_calls:
            if agent_name == 'supervisor':
                return 'worker'
            else:
                logger.info(f"Finishing subgraph for {agent_name}...")
                return END

    # Graph builder
    graph_builder = StateGraph(shared_state_schema)
    graph_builder.add_node("worker", call_worker)
    graph_builder.add_node("tool_node", tool_node)

    graph_builder.add_edge(START, "worker")
    graph_builder.add_edge("tool_node", "worker")    
    graph_builder.add_conditional_edges("worker", should_continue)
    graph = graph_builder.compile()   
    return graph