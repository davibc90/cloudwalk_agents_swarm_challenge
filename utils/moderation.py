import os
from openai import OpenAI
from utils.logger_utils import setup_logger

logger = setup_logger(__name__)

class ModerationError(Exception):
    """Custom exception raised when content violates moderation rules."""
    pass

_client = None
def _get_client():
    """
    Lazily initialize and cache the OpenAI client.
    Ensures we only create one instance throughout the application lifecycle.
    """
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def assert_safe_input_or_raise(text: str, user_id: str = None, model: str = "omni-moderation-latest"):    
    """
    Validates input text against OpenAI's moderation API.
    
    Args:
        text (str): The content to be checked.
        user_id (str, optional): Identifier of the user who submitted the text.
        model (str): Moderation model to use. Defaults to 'omni-moderation-latest'.
    
    Returns:
        result (ModerationResult): The moderation result object from OpenAI.
    
    Raises:
        ModerationError: If the input is flagged as violating usage policies.
    """
    client = _get_client()
    resp = client.moderations.create(model=model, input=text)
    result = resp.results[0]

    # --- NOVO: normaliza categories para dict
    cats = result.categories
    if isinstance(cats, dict):
        cats_dict = cats
    elif hasattr(cats, "model_dump"):          # Pydantic v2 (SDKs recentes)
        cats_dict = cats.model_dump()
    elif hasattr(cats, "dict"):                # Pydantic v1 (fallback)
        cats_dict = cats.dict()
    else:                                      # fallback final
        cats_dict = getattr(cats, "__dict__", {})

    true_categories = [k for k, v in cats_dict.items() if v]

    if result.flagged:
        raise ModerationError(
            "Input rejected! Your message violates our usage policies: "
            f"{', '.join(true_categories) if true_categories else 'content not allowed!'}."
        )

    if true_categories:
        logger.warning(f"Content allowed, but flagged in categories: {', '.join(true_categories)}")

    return result
