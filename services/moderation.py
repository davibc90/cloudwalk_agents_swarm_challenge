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


def _cats_true(mod_result):
    """
    Extracts the categories from the moderation result that were marked as True.
    Normalizes for different versions of the SDK/pydantic. 
    """
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


def assert_safe_input_or_raise(text: str, model: str = "omni-moderation-latest"):    
    """
    Validates input text against OpenAI's moderation API.
    
    Args:
        text (str): The content to be checked.
        model (str): Moderation model to use. Defaults to 'omni-moderation-latest'.
    Returns:
        result (ModerationResult): The moderation result object from OpenAI.
    Raises:
        ModerationError: If the input is flagged as violating usage policies.
    """
    # Get OpenAI client
    client = _get_client()
    resp = client.moderations.create(model=model, input=text)
    result = resp.results[0]

    # Extract categories from moderation result
    cats_dict = getattr(result, "categories", {})

    if not isinstance(cats_dict, dict):
        if hasattr(cats_dict, "model_dump"):
            cats_dict = cats_dict.model_dump()
        elif hasattr(cats_dict, "dict"):
            cats_dict = cats_dict.dict()
        else:
            cats_dict = getattr(cats_dict, "__dict__", {})

    true_categories = [k for k, v in cats_dict.items() if v]

    # Raise exception if content is flagged
    if result.flagged:
        raise ModerationError(
            "Input rejected! Your message violates our usage policies: "
            f"{', '.join(true_categories) if true_categories else 'content not allowed!'}."
        )

    if true_categories:
        logger.warning(f"Content allowed, but flagged in categories: {', '.join(true_categories)}")

    return result
