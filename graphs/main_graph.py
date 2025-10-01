from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph, START, MessagesState
from langgraph.types import Command
from graphs.general_agent_subgraph import generate_worker_graph
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.rate_limiters import InMemoryRateLimiter
from graphs.other_components.summarization_node import summary_node
from graphs.other_components.personality_node import respond_to_user
from utils.get_date import get_date
from pprint import pprint
from config.env_config import env

from utils.logger_utils import setup_logger
logger = setup_logger(__name__)

# Environment variables
REQUESTS_PER_SEC = env.requests_per_sec
CHECKING_SEC_INTERVAL = env.checking_sec_interval
MAX_BUCKET_SIZE = env.max_bucket_size
BOOKING_START_TIME = env.booking_starting_time
BOOKING_END_TIME = env.booking_end_time
BOOKING_DURATION_MINUTES = env.booking_duration_minutes
DB_URI = env.db_uri

# Current date and time for context (GMT -3 AMERICA/SÃO PAULO Timezone)
current_date = get_date()

def call_agents_team(
    user_message: str, 
    contact: str, 
    human_intervention_response: bool
):
    """
    Orchestrates a team of LangGraph agents to handle a user message with persistent
    state, rate limiting, summarization, and a final user-facing response.

    This module compiles and executes a LangGraph `StateGraph` composed of:
    - `summarization_node`: builds/updates a running summary of the conversation.
    - `supervisor`: routes work to worker agents based on the summarized context.
    - `knowledge_agent`: retrieves/produces knowledge-grounded answers.
    - `customer_service_agent`: handles customer-support style interactions.
    - `secretary_agent`: manages booking/scheduling intents (uses BOOKING_* envs).
    - `personality_node`: produces the final response aligned with a chosen persona.

    Persistence & rate limiting:
    - Conversation state and message history are checkpointed with
    `langgraph.checkpoint.postgres.PostgresSaver` (PostgreSQL).
    - OpenAI request bursts are controlled via `InMemoryRateLimiter` to avoid tier
    limits or throttling.

    Timezone & date:
    - Current date/time is resolved by `utils.get_date.get_date()` assuming
    America/São_Paulo (GMT-3) context and is passed to the agents to keep replies
    temporally coherent.

    Environment variables:
    - REQUESTS_PER_SEC (float, default "1"): Leaky-bucket allowed requests per second.
    - CHECKING_SEC_INTERVAL (float, default "1"): Rate-limiter check interval.
    - MAX_BUCKET_SIZE (int, default "1"): Max accumulated burst in the bucket.
    - BOOKING_START_TIME (str, default "09:00"): Window start for secretary bookings.
    - BOOKING_END_TIME (str, default "18:00"): Window end for secretary bookings.
    - BOOKING_DURATION_MINUTES (int, default "30"): Default booking slot length.
    - DB_URI (str): PostgreSQL DSN for `PostgresSaver`.

    Public API:
        def call_agents_team(
            user_message: str,
            contact: str,
            human_intervention_response: bool,
        ) -> dict:
            Compile (if needed) and run the main agents graph for a single turn.

            Args:
                user_message: The user input (or a resume "type" when resuming).
                contact: An identifier used for naming the thread and message author.
                human_intervention_response: If False, runs the normal flow.
                    If True, resumes a previously interrupted run with:
                    `Command(resume={"type": user_message})`.
            Returns:
                A dict with:
                - "user_input": The message that was processed.
                - "ai_response": The final assistant message (or an interrupt payload
                when human intervention is required).
            Side effects:
                - Prints chat history to stdout for debugging/inspection.
                - Logs lifecycle events using `utils.logger_utils.setup_logger`.
                - Persists conversation state to PostgreSQL via `PostgresSaver`.
    """
    logger.info("Starting main graph for agents team...")

    # Graph state schema shared between agents and the main graph
    class TeamState(MessagesState):
        summary: str
        last_active_agent: str

    # Rate Limiter setup to avoid cuts on repeated requests to OpenAI API as a result of user tier limitations
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=REQUESTS_PER_SEC,  
        check_every_n_seconds=CHECKING_SEC_INTERVAL, 
        max_bucket_size=MAX_BUCKET_SIZE,  
    )

    # Checkpointer setup for persistance of the graph state and chat history
    with (PostgresSaver.from_conn_string(DB_URI) as checkpointer):
        checkpointer.setup()

        logger.info("Checkpointing setup successfully!")

        # Agents Subgraphs
        supervisor_agent = generate_worker_graph("supervisor", TeamState, rate_limiter, current_date)
        knowledge_agent = generate_worker_graph("knowledge_agent", TeamState, rate_limiter, current_date)
        customer_service_agent = generate_worker_graph("customer_service_agent", TeamState, rate_limiter, current_date)
        secretary_agent = generate_worker_graph("secretary_agent", TeamState, rate_limiter, current_date)

        # Main Graph Nodes
        summarization_node = summary_node(TeamState, rate_limiter)
        personality_node = respond_to_user(TeamState, rate_limiter, user_message, current_date)
        logger.info("Main graph nodes generated successfully!")

        graph = StateGraph(TeamState)

        # Main Graph Nodes
        graph.add_node("supervisor", supervisor_agent)
        graph.add_node("knowledge_agent", knowledge_agent)
        graph.add_node("customer_service_agent", customer_service_agent)
        graph.add_node("secretary_agent", secretary_agent)
        graph.add_node("summarization_node", summarization_node)
        graph.add_node("personality_node", personality_node)

        # Main Graph Edges
        graph.add_edge(START, "summarization_node")
        graph.add_edge("summarization_node", "supervisor")
        graph.add_edge("knowledge_agent", "supervisor")
        graph.add_edge("customer_service_agent", "supervisor")
        graph.add_edge("secretary_agent", "supervisor")
        graph.add_edge("personality_node", END)    

        compiled_graph = graph.compile(checkpointer=checkpointer)
        logger.info("Main graph compiled successfully!")

    #---------------------------------------------------------------------------------------------------

        # Main Graph execution context configuration
        config = {
            "recursion_limit":25,
            "configurable": {
                "thread_id": f"chat_history_{contact}",
                "user_nickname": contact,
            }
        }

        input_message = HumanMessage(content=user_message, name=f"{contact}")

        if not human_intervention_response:
            # Regular message flow
            output = compiled_graph.invoke({"messages": [input_message]}, config)
            messages_list = output["messages"]
            last_message = messages_list[-1]

            if last_message.content == input_message.content:
                print("\n\n=================================================")
                print("WAITING FOR HUMAN INTERVENTION RESPONSE...")
                print("=================================================")
                print(output["__interrupt__"][0])
                return {"user_input": input_message.content, "ai_response": output["__interrupt__"][0]}

            else:
                print("\n\nCHAT HISTORY")
                for message_item in messages_list:
                    pprint({
                        "name": message_item.name,
                        "content": message_item.content
                    })
                    print("=================================================")
                return {"user_input": input_message.content, "ai_response": last_message.content}

        else:
            # Human intervention response
            output = compiled_graph.invoke(Command(resume={"type": f"{user_message}"}), config)
            messages_list = output["messages"]
            last_message = messages_list[-1]

            print("\n\nCHAT HISTORY")
            for message_item in messages_list:
                pprint({
                    "name": message_item.name,
                    "content": message_item.content
                })
                print("=================================================")

            return {"user_input": input_message.content, "ai_response": last_message.content}