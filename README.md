# CloudWalk Agents Swarm Challenge (by Davi Carneiro)

A multi-agent system built as a coding challenge for CloudWalk in Python.  
This application orchestrates several specialized AI agents to handle routing, knowledge retrieval, customer support, and scheduling tasks, all exposed via a FastAPI HTTP interface and containerized for easy deployment.

---

## Frameworks & Libraries

- **FastAPI** – HTTP server and routing  
- **Docker** – Containerization  
- **LangChain / LangGraph** – Agents orchestration 
- **Supabase** – User data, support calls, and appointment scheduling storage
- **Weaviate** – Vector database for RAG queries and document storage  
- **OpenAI API** – LLM back end & Moderation (Guardrails)  
- Others: see [requirements.txt](requirements.txt)

---

## Project Overview

This repository implements an **Agents Swarm**—a coordinated set of AI agents that collaborate to process incoming user messages and fulfill a variety of tasks:

1. **Supervisor (Router) Agent**  
   - Entry point for all messages; routes requests to the appropriate agent or finish the agents work
   - Calls "personality_node" in order to generate a final response
    
2. **Knowledge Agent**  
   - Handles RAG-based retrieval over InfinitePay’s website content ingested to Weaviate vector store  
   - Web search tool for external information retrieval

3. **Customer Support Agent**  
   - Provides user-centric support using Supabase as database
   - Includes tools for retrieving user information and registering support calls for human team assesment

4. **Secretary Agent**  
   - Manages appointment scheduling with human intervention hooks
   - Online meetings are booked for identity checking purposes when fund transfers are blocked for the user  
   - Integrates a simple calendar toolset able to check availability and add new appointments 

---

## Directory Structure

```text
...
├── Dockerfile
├── docker-compose.yaml
├── main.py
├── requirements.txt
├── routes/   -> invoking agents swarm and data ingestion routes
├── services/ -> services for data ingestion and moderation
├── config/   -> configuration files for supabase e weaviate vector database clients
├── graphs/   -> main graph, agents subgraphs, summarization and personality nodes
├── prompts/  -> prompts for each agent
├── tools/    -> tools for each agent
├── utils/    -> utils functions for a variety of purposes
└── README.md
```

---

## Graph Flow and Architecture

```python
        ...
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
        ...  
```
1st node -`Summarization node` (`graphs/other_components/summarization_node.py`) 
- Used to generate summaries of the conversation, preventting the messages list of the chat history from growing too large. 
- The necessity for summarization is checked at runtime, always before calling the supervisor agent to analyze the user's input

2nd node - `Supervisor` (`graphs/general_agent_subgraph.py`) 
- Agents communicate via direct tool calls always within a central workflow graph (`graphs/main_graph.py`).  
- Must await the response of the last transfered agent before transferring control to another agent or calling the personality node.

Agent Nodes - `Agents` (`graphs/general_agent_subgraph.py`) 
- Each agent subgraph is generated in the `graphs/general_agent_subgraph.py` file and composes the main graph as nodes.
- Mandatory to send back a response to the supervisor agent.

Last node - `Personality node` (`graphs/other_components/personality_node.py`) 
- Is used to generate a final response to the user, gathering all data from the conversation history.
- Generates a final response adding personality to the response.

---

## Configuration

- Edit environment variables in the `docker-compose.yaml` file
- The most sensitive variables are related to external services and are displayed bellow:

```yaml
    environment:
      # --- Supabase ---
      SUPABASE_URL: "https://qmcdadefjwjxjylslljt.supabase.co"
      SUPABASE_SERVICE_ROLE_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFtY2RhZGVmandqeGp5bHNsbGp0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTM3NDU0NywiZXhwIjoyMDQwOTUwNTQ3fQ.uSeiiInAsSlzjQiZuwOgdqaZDshMSaSkzFGHPezzDN4"

       # --- Web_Search_Tool ---
      TAVILY_SEARCH_API_KEY: "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"

      # --- LLM / OpenAI ---
      OPENAI_API_KEY: "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"
```

- The other variables are majorly related to the application's runtime configurations, such as business rules, LLM parameters, etc
---

## Building & Running

Navigate to the root directory and run the following command to build and download images and start all services:
`IT IS READY TO RUN! PERMISSION GRANTED FOR USING MY OWN TOKENS AND OTHER PRIVATE KEYS IF WANTED`

```bash
docker-compose up -d
```

---

## API Endpoints and Execution Steps

`WINDOWS POWERSHELL COMMANDS FOR DATA INGESTION AND SWARM INVOKING ARE INSIDE windows_cmd_commands.txt`

### STEP 1: **Ingest URL Data**  
   `/routes/ingest_data_route.py`  
   - Ingests data from a given set of URLs, must be done before invoking the swarm
   - Request body:
```json
{
    "urls": ["url1", "url2","url3", "..."]
}
```
### STEP 2: **Invoke Swarm**  
   `/routes/invoke_route.py`  
   - Request body for regular message flow:
```json
{
    "message": "Your message here",
    "user_id": "client789"
}
```

---

## RAG Pipeline Description

1. URL data ingestion in the vector db through the ingest_data route, described in STEP 1 of the previous section (`routes/ingest_data_route.py`), shown bellow:

```python 
...
@router.post("/ingest_url_content", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    logger.info(f"Received ingestion request with {len(req.urls)} URLs")

    # Urls validation
    if not req.urls:
        raise HTTPException(status_code=400, detail="Please, send at least one URL...")

    # Ingestion
    raw_results = ingest_urls_to_weaviate(
        urls=[str(u) for u in req.urls],
        index_name=INDEX_NAME,
        openai_api_key=OPENAI_API_KEY,
        embeddings_model=EMBEDDINGS_MODEL,
    )

    # Results
    results = [IngestResult(**r) for r in raw_results]
    total_chunks = sum(r.chunks for r in results if r.ok)

    return IngestResponse(collection=INDEX_NAME, results=results, total_chunks=total_chunks)
```

2. Loop execution for data fetching and processing, each url at a time, always using Langchain components, implemented in `services/ingest_data.py`:
    - *WebBaseLoader* is used to fetch the data from the url
    - *RecursiveCharacterTextSplitter* is used to split the data into chunks
    - *OpenAIEmbeddings* is used to generate embeddings for the data
    - *WeaviateVectorStore* interface is used to store the data in the vector db

```python
...
        for url in urls:
            # Fetch HTML
            logger.debug(f"Processing URL: {url}")
            status, html, meta = fetch_html(url)
...
            # Load documents
            try:
                docs = WebBaseLoader(url).load()
                logger.info(f"Loaded {len(docs)} documents from {url}")
...
            # Split documents and add metadata
            for d in docs:
                d.metadata = {**(d.metadata or {}), "source": url}
            splits = splitter.split_documents(docs)
...
            # Add docments to vectorstore
            texts = [doc.page_content for doc in splits]
            metadatas = [doc.metadata for doc in splits]
            vectorstore.add_texts(texts=texts, metadatas=metadatas)
```

3. Retrieval querys are performed using the WeaviateVectorStore interface as retriever tool, implemented in `tools/knowledge_agent/retriever_tool.py`:
```python
...
def initialize_retriever_for_rag():

    # Defines the embeddings model
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model=EMBEDDINGS_MODEL)
    weaviate_client = create_weaviate_client()

    # Initializes the WeaviateVectorStore
    db = WeaviateVectorStore(
        embedding=embeddings,
        client=weaviate_client,
        index_name=INDEX_NAME,
        text_key="content",
        use_multi_tenancy=False
    )

    # Returns the configured retriever based on the interface with the vector store
    retriever = db.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "score_threshold": float(RETRIEVER_SCORE_THRESHOLD),
            "k": int(RETRIEVER_K),
            "alpha": float(RETRIEVER_ALPHA),
        }
    )

    # Returns the configured retriever tool ready for use by the agent
    retriever_tool = create_retriever_tool(
        retriever, 
        name="retriever_tool",
        description="Use this tool to retrieve relevant documents from the knowledge base based on the user's query"
    )
    return retriever_tool
```

---

## Bonus Features

- **Fourth Agent**
    - The secretary agent has been additionaly implemented with the objective of checking availability for booking new appointments and create new appointments registers in the table 'appointments' in the database.
    - Every time the user has fund transfers blocked, the only way to unlock them is to book an appointment with a costumer success specialist, wich is arrenged by the secretary agent.

- **Guardrails** for input/output parsing  
    - Guardrails are implemented in `utils/moderation.py` and invoked before/after LLM calls inside `routes/invoke_route.py`.
    - The OpenAI Moderation API assess the content of the messages to ensure they do not contain inappropriate content,
        analyzing both the input and output messages, evaluating them against a set of categories, including: hate speech, sexual content, violence, harassment, etc.

```python
        ...
        # =========================
        # Input guardrail (pretty much the same for output)
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
```

---

- **Human Intervention** 
    - Every single call to the add_appointment tool (secretary agent) requires human intervention. 
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

- In ther request schema in the `routes/invoke_route.py` file, there is a field called "human_intervention_response" which flags if the current request is a response to address a human intervention interruption or a regular message coming from the user.
```python
        # Request schema
        class QueryRequest(BaseModel):
            message: str
            user: str
            human_intervention_response: Optional[bool] = False

```

- Inside the `main_graph.py` file, in the very end of the code, there are two different invoking patterns:
```python
        ...
            if not human_intervention_response:
            # Regular message flow
            output = compiled_graph.invoke({"messages": [input_message]}, config)
        ...
            else:
            # Human intervention response
            output = compiled_graph.invoke(Command(resume={"type": f"{user_message}"}), config)
        ...
```

- Request body for human intervention response:
```json
     {
       "message": "requested response by human intervention goes here",
       "user_id": "client789",
       "human_intervention_response": true
     }
```

---

## Testing 

**Once all services are running, it is possible to test the agents swarm by using the commands inside `windows_cmd_commands.txt`, in the root directory of this repository**

**The following unit and integration tests have been performed so far:**

**Reasoning Test**
- Evaluate the quality of the agents' reasoning (planning, task decomposition, tool selection, consistency checking, and self-correction) without requiring explicit chains of thought; evaluate via observable behavior, logs, and results

**Multi-Agent Coordination Test**
- Validates the communication and delegations across the agents, focusing on simulating scenarios where the agents need to coordinate their actions and share information in order to achieve a common goal

**Knowledge Agent**
- Retriever Tool test, after ingesting the urls, try to ask the agent about the InfinitePay's website content.
- Web Search Tool test, asking for news and events, always after confirming the information is not inside the knowledge base

**Customer Service Agent**
- Retrieve User Info Tool test, in order to evaluate if the user's info is being properly retrieved and parsed
- New Support Call Tool test, in order to evaluate if the agent registers a new support call when the situation requires it

**Secretary Agent Tools Test**
- Get Appointments Tool test, in order to evaluate if the agent retrieves the occupied time slots for a given date
    * Checks if the occupied time slots are being properly retrieved and respected, as well as the context and businees rules
- Add Appointment Tool test, in order to evaluate if the agent registers a new appointment when the situation requires it
    * Checks if the appointment is being properly registered and the human intervention is being properly triggered and evaluated

**Guardrails Test**
- Guardrails test, performed using inputs that certainly should be blocked by the moderations API

**Human Intervention Test**
- Consists in responding to a human intervention interruption> In this case, every time the add_appointment tool is called

**Summarization Test**
- Consists in testing the summarization functionality, observing the conversation history and the summary after a certain number of messages. The old chat history should be deleted after the summarization process and the summary should be added to the conversation history, preserving the conversation context and keeping the very last messages (default last 4 messages).

**Date/Time Context Awareness Test**
- Consists in testing if the agents swarm knows the current date and time

**Further Tests**
- Tracing & Observability
    * Objective: Ensure full end-to-end traceability and monitoring.
    * Approach:
        * Use LangSmith, LangFuse, or equivalent tools to trace inputs/outputs.
        * Measure latency at every stage (agent, tool, database).
        * Collect structured logs for scenario reproducibility and auditing.
        * Track cost metrics (tokens, execution time, external API calls).

- Adversarial & Stress Testing
    * Objective: Evaluate the robustness and security of agents, ensuring that both individual reasoning and multi-agent collaboration can withstand adversarial conditions.
    * Approach:
        * Conduct prompt injection attacks specifically targeting single agents and the message-passing mechanisms between them, testing their ability to detect, filter, and resist malicious inputs.
        * Explore attack vectors such as hidden instructions, role manipulation, and data poisoning to validate safeguards against unauthorized actions.
        * Simulate scenarios with conflicting or adversarial goals (e.g., a secretary agent blocking an appointment while a customer agent insists) to examine how agents handle negotiation, maintain trust boundaries, and prevent escalation of vulnerabilities.

- Automated Testing & CI/CD Integration
    * Objective: Ensure reproducible and automated validation of agentic workflows when there is a new update in the codebase
    * Approach:
        * CI pipelines (GitHub Actions, GitLab CI, Jenkins) to run:
            * Unit tests for individual agents and tools.
            * Integration tests for multi-agent coordination.
            * Reasoning tests validating chain-of-thought execution consistency.
        * Automatic reports on coverage per agent type and cross-agent interactions.
        * Notifications on failures with links to traces/logs for quick debugging.

- A/B Prompt Testing
    * Objective: Validate the effectiveness of different prompt formulations and strategies to optimize accuracy, efficiency, and user experience.
    * Approach:
        * Run controlled experiments where multiple prompt variants are tested against the same scenarios.
        * Measure and compare outcomes in terms of:
            * Accuracy (task completion success rate).
            * Efficiency (token usage, execution time).
            * Robustness (resistance to edge cases and adversarial prompts).
            * User experience metrics (clarity, consistency, perceived helpfulness).
        * Use statistical methods (e.g., significance testing) to validate improvements.
        * Integrate A/B results into continuous improvement cycles for prompt engineering.
---

## Supabase 
- Web User Interface URL: https://supabase.com/dashboard/project/qmcdadefjwjxjylslljt
- Tables:
  - **appointments**: appointments records, queried and registered by secretary agent
  - **user_info**: user info records, retrieved by customer service agent, before any other action
  - **support_calls**: support calls registered by customer service agent, in the restricted cases described in the prompt

- Credentials
```text
- Email: davibc.16@gmail.com  ----> pay attention to the dot after 'c'
- Password: CloudWalk@2025
```

---

## Other LLM Tools

1. **WindSurf**: IDE used for coding with strong auto-completion feature
2. **Cline**: integrated to WindSurf, it is a software development assistant 
3. **ChatGPT**

A big set of tasks were accomplished using the tools above, such as:
  - Building algorithms sketches
  - Problem-solving strategies 
  - Code Modularization and Refactoring
  - Debugging and Error Correction
  - Docstrings generation
  - Prompt refinement
  - Suggestion design patterns and best practices
  - Log analysis to identify failures