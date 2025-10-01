# services/get_appointments.py
from datetime import timedelta
from typing import Optional
from langchain_core.tools import tool
from config.supabase_client import supabase
from config.env_config import env
from utils.appointment_utils import to_iso8601, validate_requested_date, ValidationError
import json
import pytz

BOOKING_START_TIME = env.booking_starting_time
BOOKING_END_TIME = env.booking_end_time
MAX_BOOK_AHEAD_DAYS = env.max_book_ahead_days


@tool
def get_appointments(date_str: Optional[str]) -> str:
    """
    Checks occupied time slots for a given date.
    Args:
        date_str (str): Date in MM/DD/YYYY format
    Returns:
        str: JSON string with occupied time slots and context
    """
    try:
        # Validates/normalizes the date (returns 00:00 in São Paulo timezone, aware)
        target_day = validate_requested_date(date_str)

        # UTC Window for checking overlaps on the day
        start_utc = target_day.astimezone(pytz.UTC)
        end_utc = (target_day + timedelta(days=1)).astimezone(pytz.UTC)

        availability_checking = (
            supabase.table("appointments")
            .select("id, start_time, end_time")
            .lt("start_time", to_iso8601(end_utc))
            .gt("end_time", to_iso8601(start_utc))
            .order("start_time", desc=False)
            .execute()
        )
        appointments = availability_checking.data or []

        # Returns JSON with occupied time slots and context
        return json.dumps(
            {
                "ok": True,
                "appointments": appointments,
                "context": {
                    "date_requested": target_day.strftime("%m/%d/%Y"),
                },
                "rules": [
                    f"Business hours: {BOOKING_START_TIME} - {BOOKING_END_TIME} (São Paulo).",
                    f"Booking allowed only up to {MAX_BOOK_AHEAD_DAYS} days in advance.",
                    "Respect already occupied times.",
                    "It is FORBIDDEN to suggest times in the past.",
                    "Always consider the current time before suggesting.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    except ValidationError as ve:
        return json.dumps(
            {"ok": False, "error": "validation_error", "message": str(ve)},
            ensure_ascii=False,
        )
    except Exception as e:
        # Opcional: log interno antes de responder
        return json.dumps(
            {"ok": False, "error": "internal_error", "message": str(e)},
            ensure_ascii=False,
        )
