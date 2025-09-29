# CloudWalk Agent Swarm

A multi-agent system built as a coding challenge for CloudWalk.  
This application orchestrates several specialized AI agents to handle routing, knowledge retrieval, customer support, and scheduling tasks, all exposed via a FastAPI HTTP interface and Dockerized for easy deployment.

---

## Table of Contents

- [Project Overview](#project-overview)  
- [Architecture](#architecture)  
- [Frameworks & Libraries](#frameworks--libraries)  
- [Directory Structure](#directory-structure)  
- [Prerequisites](#prerequisites)  
- [Configuration](#configuration)  
- [Building & Running](#building--running)  
- [API Endpoints](#api-endpoints)  
- [Agents & Tools](#agents--tools)  
- [Bonus Features](#bonus-features)  
- [Testing & Debugging](#testing--debugging)  
- [Contributing](#contributing)  

---

## Project Overview

This repository implements an **Agent Swarm**—a coordinated set of AI agents that collaborate to process incoming user messages and fulfill a variety of tasks:

1. **Supervisor (Router) Agent**  
   - Entry point for all messages; routes requests to the appropriate sub-agent.
   - One agent trasferring at a time
   - Uses handoff tools to route messages to appropriate agents or finish working step 

2. **Knowledge Agent**  
   - Handles RAG-based retrieval over InfinitePay’s website content.  
   - Uses LangChain and Weaviate vector store for context-rich responses.
   - Web search tool for external information retrieval

3. **Customer Support Agent**  
   - Provides user-centric support using Supabase for user data and support calls  
   - Includes tools for retrieving user information and registering support calls for human team assesment

4. **Secretary Agent**  
   - Manages appointment scheduling with human intervention hooks
   - Online meetings are booked for identity checking purposes when fund transfers are blocked for the user  
   - Integrates a simple calendar toolset able to check availability and add new appointments 

---

## Architecture

Agents communicate via direct function calls within a central workflow graph (`graphs/main_graph.py`).  
Subgraphs (`graphs/other_components`) define specialized processing nodes (e.g., summarization, personality).

Prompts for each agent are defined under `prompts/` and loaded at runtime to guide LLM behavior.
Tools live in `tools/` and are assigned to agents at runtime based on the agent's role.

---

## Frameworks & Libraries

- **FastAPI** – HTTP server and routing  
- **Docker & Docker Compose** – Containerization  
- **LangChain / LangGraph** – Agent orchestration & RAG  
- **Supabase** – User data storage  
- **Weaviate** – Vector database for embeddings  
- **OpenAI API** – LLM back end & Moderation (GuardRails)  
- Others: see [requirements.txt](requirements.txt)

---

## Directory Structure

```text
.
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yaml
├── main.py
├── requirements.txt
├── routes/
│   ├── ingest_data_route.py
│   └── invoke_route.py
├── config/
│   ├── supabase_client.py
│   └── weaviate_client.py
├── graphs/
│   ├── main_graph.py
│   ├── general_agent_subgraph.py
│   └── other_components/
│       ├── personality_node.py
│       └── summarization_node.py
├── prompts/
│   ├── customer_service_agent_prompt.py
│   ├── knowledge_agent_prompt.py
│   ├── personality_prompt.py
│   ├── secretary_agent_prompt.py
│   ├── summarization_prompts.py
│   └── supervisor_prompt.py
├── tools/
│   ├── customer_service_tools/
│   │   ├── new_support_call.py
│   │   └── retrieve_user_info.py
│   ├── knowledge_agent/
│   │   ├── retriever_tool.py
│   │   └── web_search_tool.py
│   ├── supervisor_tools/
│   │   └── handoff_tools.py
│   └── secretary_tools/
│       ├── add_appointment.py
│       └── get_appointments.py
├── utils/
│   ├── cleanup_messages_for_team.py
│   ├── cmd_commands.txt
│   ├── get_appointments_utils.py
│   ├── get_date.py
│   ├── logger_utils.py
│   ├── moderation.py
│   └── test_scenarios.txt
└── README.md
```

---

## Prerequisites

- Docker & Docker Compose  
- Python 3.9+  
- An OpenAI API key (export as `OPENAI_API_KEY`)  
- Supabase project URL & anon key (`SUPABASE_URL`, `SUPABASE_KEY`)  
- Weaviate URL & API key (`WEAVIATE_URL`, `WEAVIATE_KEY`)

---

## Configuration

Edit environment variables in the `docker-compose.yaml` or provide a `.env` file:

```yaml
services:
  app:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - WEAVIATE_URL=${WEAVIATE_URL}
      - WEAVIATE_KEY=${WEAVIATE_KEY}
```

---

## Building & Running

Navigate to the root directory and run the following command to build or download images and start all services:

```bash
docker-compose up -d
```

---

## API Endpoints

1. **Ingest URL Data**  
   `POST /routes/ingest_data`  
   - Ingests data from a given set of URLs, sent in the request body:
   - Windows PowerShell command:
```powershell
curl -X POST http://127.0.0.1:10000/ingest_url_content `
        -H "Content-Type: application/json" `
        -d "{
        \"urls\": [
            \"https://www.infinitePay.io\",
            \"https://www.infinitePay.io/maquininha\",
            \"https://www.infinitePay.io/maquininha-celular\",
            \"https://www.infinitePay.io/tap-to-pay\",
            \"https://www.infinitePay.io/pdv\",
            \"https://www.infinitePay.io/receba-na-hora\",
            \"https://www.infinitePay.io/gestao-de-cobranca-2\",
            \"https://www.infinitePay.io/gestao-de-cobranca\",
            \"https://www.infinitePay.io/link-de-pagamento\",
            \"https://www.infinitePay.io/loja-online\",
            \"https://www.infinitePay.io/boleto\",
            \"https://www.infinitePay.io/conta-digital\",
            \"https://www.infinitePay.io/conta-pj\",
            \"https://www.infinitePay.io/pix\",
            \"https://www.infinitePay.io/pix-parcelado\",
            \"https://www.infinitePay.io/emprestimo\",
            \"https://www.infinitePay.io/cartao\",
            \"https://www.infinitePay.io/rendimento\"
        ]
        }"
     ```

2. **Invoke Swarm**  
   `POST /routes/invoke`  
   - Request body for regular message flow:
     ```json
     {
       "message": "Your message here",
       "user_id": "user_123"
     }
     ```

   - Request body for human intervention response:
     ```json
     {
       "message": "requested message when human intervention was triggered",
       "user_id": "user_123",
       "human_intervention_response": true
     }
     ```

---

## Agents & Tools

- **Supervisor Agent** (`tools/supervisor_tools/handoff_tools.py`)  
- **Knowledge Agent Tools** (`tools/knowledge_agent/retriever_tool.py`, `tools/knowledge_agent/web_search_tool.py`)  
- **Customer Support Tools** (`tools/customer_service_tools/retrieve_user_info.py`, `new_support_call.py`)  
- **Secretary Tools** (`tools/secretary_tools/add_appointment.py`, `get_appointments.py`)

---

## Bonus Features

- **Fourth Agent**
    - The secretary agent has been additionaly implemented with the objective of checking availability for booking new appointments and create new appointments registers in the table 'appointments' in the database.
    - Every time the user has fund transfers blocked, the only way to unlock them is to book an appointment with a costumer success specialist, wich is arrenged by the secretary agent.
    - Availability check is done using the get_appointments tool and the new appointment are created using the add_appointment tool.

- **GuardRails** for input/output parsing  
    - GuardRails are implemented in `utils/moderation.py` and invoked before/after LLM calls inside `routes/invoke_route.py`.

```python
        ...
        # =========================
        # Input guardrail 
        # =========================
        try:
            mod_result = assert_safe_input_or_raise(message, user_id="system")
            logger.info(
                "Moderation approved | flagged=%s | categories_true=%s",
                mod_result.flagged,
                _cats_true(mod_result),
            )
        except ModerationError as me:
            logger.warning("Input blocked by moderation: %s", me)
            raise HTTPException(status_code=400, detail=str(me))

        ...
        # =========================
        # Output guardrail 
        # =========================
        try:
            response_text = str(response['ai_response'])  
            mod_result_out = assert_safe_input_or_raise(response_text, user_id="system")
            logger.info(
                "Output approved | flagged=%s | categories_true=%s",
                mod_result_out.flagged,
                _cats_true(mod_result_out),
            )
        except ModerationError as me:
            logger.warning("Output blocked by moderation: %s", me)
            raise HTTPException(status_code=500, detail="Agent response blocked by moderation!")

```

- The OpenAI Moderation API assess the content of the messages to ensure they do not contain inappropriate content,
    analyzing both the input and output messages, evaluating them against a set of categories.
- Evaluated categories include: hate speech, sexual content, violence, harassment, etc.

---

-  **Human Intervention** 
    - Every single call to the secretary agent's add_appointment tool requires human intervention. 
    - It iss necessary to approve the appointment before it is created.
    - If not approved, the user will be instructed to await for human contact.

    - Inside the add_appointment tool, there is a call to the interrupt function.
```python
    response = interrupt(  
        f"Trying to call `add_appointment` with args {{'user_id': {user_id}, 'start_time': {start_time}, 'end_time': {end_time}}}. "
        "Do you approve this appointment? \n"
        "Please answer with 'YES' or 'NO'."
    )
```

* In ther request schema in the `routes/invoke_route.py` file, there is a field called "human_intervention" which flags if the current request is a response to address a human intervention interruption or a regular message coming from the user.
```python
        # Request schema
        class QueryRequest(BaseModel):
            message: str
            user: str
            human_intervention_response: Optional[bool] = False

```

* Inside the `main_graph.py` file, in the very end of the code, there are two different invoking patterns:
```python
        ...
            if not human_intervention_response:
            # Regular message flow
            output = compiled_graph.invoke({"messages": [input_message]}, config)
            messages_list = output["messages"]
            last_message = messages_list[-1]
        ...
            else:
            # Human intervention response
            output = compiled_graph.invoke(Command(resume={"type": f"{user_message}"}), config)
            messages_list = output["messages"]
            last_message = messages_list[-1]
        ...
```

---
