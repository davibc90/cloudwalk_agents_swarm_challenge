from datetime import datetime, timedelta
from config.env_config import env
import pytz

MAX_BOOK_AHEAD_DAYS = env.max_book_ahead_days
TZ = pytz.timezone("America/Sao_Paulo")


class ValidationError(Exception):
    """Validation error for appointments!"""
    pass

def to_iso8601(dt: datetime) -> str:
    """
        Serializes datetime aware to ISO-8601 (preserves offset).
        Raises ValueError if naive to avoid ambiguity.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("to_iso8601 requires datetime timezone-aware.")
    return dt.isoformat()


def _normalize_midnight_sp(dt: datetime) -> datetime:
    """
        Returns the same day at 00:00:00 in São Paulo timezone (aware).
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        # naive → interpret as local time in SP
        dt = TZ.localize(dt)
    else:
        # aware → convert to SP
        dt = dt.astimezone(TZ)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def validate_requested_date(date_str: str | None) -> datetime:
    """
        Validates the requested date (format 'MM/DD/YYYY' or None).
        Returns datetime of the start of the day in São Paulo (aware).
    """
    if date_str:
        try:
            target_day = datetime.strptime(date_str, "%m/%d/%Y")  # naive
        except ValueError:
            raise ValidationError("Formato de data inválido. Use MM/DD/YYYY.")
    else:
        target_day = datetime.now(TZ)  # aware

    # Normalizes to 00:00 in São Paulo timezone (without duplicate localize)
    target_day = _normalize_midnight_sp(target_day)

    today = _normalize_midnight_sp(datetime.now(TZ))
    max_day = today + timedelta(days=MAX_BOOK_AHEAD_DAYS)

    if target_day < today:
        raise ValidationError("It is forbidden to consult past dates.")
    if target_day > max_day:
        raise ValidationError(f"Appointments can only be scheduled up to {MAX_BOOK_AHEAD_DAYS} days in advance.")

    return target_day

def to_sp_hhmm(value):
    """
        Converts timestamp (ISO str ou datetime) to HH:MM in São Paulo.
    """
    if isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        dt = value

    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)

    return dt.astimezone(TZ).strftime("%H:%M")