"""
    Invoke the AI agents team to process a user message.

    ### Description
    This endpoint receives a request containing a message and a user identifier, 
    validates the input, applies moderation guardrails on both input and output, 
    and delegates the processing to the AI agents team.  
    If successful, it returns a structured response from the agents.

    ### Request Body (JSON)
    - **message** (*str*): The user’s input message to be processed.
    - **user** (*str*): The identifier of the requesting user.
    - **human_intervention_response** (*bool, optional*): Flag indicating whether the 
      response involves human intervention (default: `False`).

    ### Response
    - **201 Created**
        - Returns a JSON object in the following format:
        ```json
        {
            "response": {
                "ai_response": "...",
                "metadata": {...}
            }
        }
        ```

    ### Error Responses
    - **400 Bad Request**
        - Missing required fields (`message` or `user`).
        - Input blocked by moderation.
    - **500 Internal Server Error**
        - Failed to obtain a response from the agents team.
        - Output blocked by moderation.
        - Unexpected internal errors during processing.

    ### Logging
    - Logs the reception of the request.
    - Records results of moderation checks (input and output).
    - Issues warnings for blocked inputs or outputs.
    - Reports errors when agent calls fail.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from graphs.main_graph import call_agents_team
from utils.logger_utils import setup_logger
from utils.moderation import assert_safe_input_or_raise, ModerationError
logger = setup_logger(__name__)

# Initialize router
router = APIRouter()

# Request schema
class QueryRequest(BaseModel):
    message: str
    user: str
    human_intervention_response: Optional[bool] = False

# Response schema
class QueryResponse(BaseModel):
    response: dict

# Helper function to get categories in the JSON response from moderation API
def _cats_true(mod_result):
    cats = getattr(mod_result, "categories", {})
    if isinstance(cats, dict):
        d = cats
    elif hasattr(cats, "model_dump"):
        d = cats.model_dump()
    elif hasattr(cats, "dict"):
        d = cats.dict()
    else:
        d = getattr(cats, "__dict__", {})
    return [k for k, v in d.items() if v]


# Define the route to invoke the agent
@router.post("/langgraph/invoke", response_model=QueryResponse, status_code=status.HTTP_201_CREATED)
async def invoke_agent(request: QueryRequest):
    
    try:
        logger.info("Receiving request to invoke the agents team...")

        # Request Validation
        message = request.message
        user = request.user
        human_intervention_response = request.human_intervention_response

        missing_fields = []
        if not message:
            missing_fields.append("message")
        if not user:
            missing_fields.append("user")
       
        if missing_fields:
            detail_message = f"Missing fields in request. Missing: {', '.join(missing_fields)}."
            logger.warning(detail_message)
            raise HTTPException(status_code=400, detail=detail_message)

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

        # Invoking AI Team and response validation
        response = call_agents_team(message, user, human_intervention_response)
        if not response:
            logger.error("Failed to obtain response from AI team...")
            raise HTTPException(status_code=500, detail = "Failed to obtain response from AI team...")

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

        return {"response": response}
    
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))