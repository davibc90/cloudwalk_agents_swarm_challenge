from typing import Optional
from pydantic import BaseModel

# -------------------------------------------------
# Schemas for request and response models
# of the LangGraph agent invocation endpoint
# -------------------------------------------------

class QueryRequest(BaseModel):
    """
    Represents the request body for invoking the AI agents team.

    Attributes:
        message (str): The user's input message to be processed.
        user (str): Identifier of the requesting user.
        human_intervention_response (Optional[bool]): 
            Indicates whether human intervention should be considered.
            Defaults to False.
    """
    message: str
    user: str
    human_intervention_response: Optional[bool] = False


class QueryResponse(BaseModel):
    """
    Represents the structured response returned by the AI agents team.

    Attributes:
        response (dict): The AI agents' response, 
                         typically containing the generated output
                         and optional metadata.
    """
    response: dict
