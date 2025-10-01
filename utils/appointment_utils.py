# utils/appointments_utils/validation.py
from datetime import datetime, timedelta
from config.env_config import env
import pytz

MAX_BOOK_AHEAD_DAYS = env.max_book_ahead_days
TZ = pytz.timezone("America/Sao_Paulo")


class ValidationError(Exception):
    """Erro de validação de agendamento."""
    pass


def to_iso8601(dt: datetime) -> str:
    """
    Serializa datetime aware para ISO-8601 (preserva offset).
    Levanta ValueError se for naive para evitar ambiguidade.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("to_iso8601 requer datetime timezone-aware.")
    return dt.isoformat()


def _normalize_midnight_sp(dt: datetime) -> datetime:
    """
        Returns the same day at 00:00:00 in São Paulo timezone (aware).
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        # naive → interpretar como hora local de SP
        dt = TZ.localize(dt)
    else:
        # aware → converter para SP
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

    # Normaliza para 00:00 no fuso de SP (sem localize duplicado)
    target_day = _normalize_midnight_sp(target_day)

    today = _normalize_midnight_sp(datetime.now(TZ))
    max_day = today + timedelta(days=MAX_BOOK_AHEAD_DAYS)

    if target_day < today:
        raise ValidationError("Não é permitido consultar horários no passado.")
    if target_day > max_day:
        raise ValidationError(
            f"Agendamentos só podem ser feitos até {MAX_BOOK_AHEAD_DAYS} dias no futuro."
        )

    return target_day
