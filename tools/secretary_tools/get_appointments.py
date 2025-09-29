"""
    Query the bookings database and return a normalized, single-day availability map
    (and occupied time slots) for São Paulo time, encoded as a JSON string.

    This tool validates the requested date (not in the past, no more than
    `MAX_BOOK_AHEAD_DAYS` days ahead), converts the day’s local window to UTC, fetches
    existing appointments from Supabase, computes busy intervals, and discretizes them
    based on the booking duration/step. It never suggests times outside business
    hours or in the past.

    Args:
        date_str (str, optional):
            Target date in the format "MM/DD/YYYY" interpreted in America/Sao_Paulo.
            If omitted, the current day in São Paulo is used.

    Returns:
        str: A JSON string with the following structure:

            Success payload:
            {
              "busy": {
                "duration_minutes": <int>,          # slot length used by the system
                "step_minutes": <int>,              # step between candidate times
                "queried_days": ["MM/DD/YYYY"],     # day(s) covered (always 1 for this tool)
                "busy_times_by_day": {
                  "MM/DD/YYYY": ["HH:MM", "HH:MM", ...]  # discretized busy start times
                }
              },
              "context": {
                "workday_start": "HH:MM",           # local business start (São Paulo)
                "workday_end": "HH:MM",             # local business end (São Paulo)
                "book_ahead_limit_days": <int>,     # max days in advance allowed
                "date_requested": "MM/DD/YYYY"      # normalized requested day (local)
              },
              "rules": [
                "Business hours: <start> - <end> (São Paulo time).",
                "Appointments/simulations only up to <N> days in advance.",
                "Interval between options: <step> minutes.",
                "Respect already busy times.",
                "It is FORBIDDEN to suggest any option in the past, even if it is not listed as busy.",
                "Always check the current time before suggesting an option!"
              ]
            }

    Notes:
        - All validations and computations use São Paulo local time for day boundaries,
          but queries against Supabase are performed in UTC using the day's UTC window.
        - This tool returns only one day per call, but `queried_days`/grouping are
          preserved for extensibility.
"""

from langchain_core.tools import tool
from config.supabase_client import supabase
from utils.get_appointments_utils import *
import json

# =========================
# TOOL: get_appointments 
# =========================
@tool
def get_appointments(
    date_str: str = None,
) -> str:
    """
    Query appointments and return a structured JSON with availabilities/unavailabilities of the specified day.
    Args:
        date_str: date in the format 'MM/DD/YYYY' (São Paulo timezone). 
    """
    workday_start = BOOKING_START_TIME
    workday_end = BOOKING_END_TIME
    duration_minutes = BOOKING_DURATION_MINUTES
    step_minutes = BOOKING_STEP_MINUTES

    try:
        # =========================
        # Date range validation (up to 15 days ahead, not in the past)
        # =========================
        now_br_dt = datetime.now(TZ_BR)
        today_br = now_br_dt.date()
        max_day = today_br + timedelta(days=MAX_BOOK_AHEAD_DAYS)

        # Safe parse of the date provided (or today)
        if date_str:
            try:
                mm, dd, yyyy = map(int, date_str.split("/"))
                target_local_start = TZ_BR.localize(datetime(yyyy, mm, dd, 0, 0, 0, 0))
            except Exception:
                return json.dumps({
                    "error": "INVALID_DATE",
                    "message": "Use o formato MM/DD/YYYY. Ex: 09/29/2025.",
                    "rules": [
                        f"Só é permitido consultar/agendar entre {today_br.strftime('%m/%d/%Y')} e {max_day.strftime('%m/%d/%Y')} (zona São Paulo)."
                    ]
                }, ensure_ascii=False, indent=2)
        else:
            # Sem parâmetro => usa o dia corrente em São Paulo
            target_local_start = now_br_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        target_day = target_local_start.date()

        if target_day < today_br:
            return json.dumps({
                "error": "DATE_IN_PAST",
                "message": "A data informada está no passado.",
                "today": today_br.strftime("%m/%d/%Y"),
            }, ensure_ascii=False, indent=2)

        if target_day > max_day:
            return json.dumps({
                "error": "DATE_OUT_OF_RANGE",
                "message": f"A data está fora do limite permitido de {MAX_BOOK_AHEAD_DAYS} dias à frente.",
                "allowed_until": max_day.strftime("%m/%d/%Y"),
            }, ensure_ascii=False, indent=2)

        # =========================
        # UTC window for the day provided
        # =========================
        day_start_utc, day_end_utc = utc_window_for_us_date(date_str)

        # Normalize with existing rules (do not suggest past, etc.)
        start_utc, end_utc, err = normalize_future_window(day_start_utc, day_end_utc)
        if err:
            return json.dumps({
                "error": err["code"],
                "message": err["message"],
                "now": err["now"],
                "rules": [
                    "Do not suggest times outside available intervals.",
                    "Do not suggest times in the past.",
                    "It is PROHIBITED to suggest times outside business hours.",
                    "Suggestions must respect: start + duration <= end of the available interval.",
                ],
            }, ensure_ascii=False, indent=2)

        # =========================
        # Supabase query 
        # =========================
        q = (
            supabase
            .table("appointments")
            .select("id, start_time, end_time")
        ).lt("start_time", to_iso(end_utc)).gt("end_time", to_iso(start_utc))

        resp = q.order("start_time", desc=False).execute()
        appointments = resp.data

        # =========================
        # Base availability
        # =========================
        base = compute_availability(appointments, start_utc, end_utc)
        busy = base["busy_intervals"]

        # Discretized busy slots (for UI to show “already unavailable”)
        busy_slots = generate_discrete_busy_slots(
            busy,
            duration_minutes=duration_minutes,
            step_minutes=step_minutes,
        )

        # Queried days (always 1 day, but we keep the structure)
        queried_days = list_queried_days(busy_slots)
        if not queried_days:
            queried_days = list_days_in_window(start_utc, end_utc)

        # Occupations grouped by day ("HH:MM")
        busy_times_grouped = group_times_by_day(
            busy_slots,
            time_only=True,
        )
        return json.dumps(
            {
                "busy": {
                    "duration_minutes": duration_minutes,
                    "step_minutes": step_minutes or duration_minutes,
                    "queried_days": queried_days,
                    "busy_times_by_day": busy_times_grouped,
                },
                "context": {
                    "workday_start": workday_start,
                    "workday_end": workday_end,
                    "book_ahead_limit_days": MAX_BOOK_AHEAD_DAYS,
                    "date_requested": target_day.strftime("%m/%d/%Y"),
                },
                "rules": [
                    f"Business hours: {workday_start} - {workday_end} (São Paulo time).",
                    f"Appointments/simulations only up to {MAX_BOOK_AHEAD_DAYS} days in advance.",
                    f"Interval between options: {step_minutes or duration_minutes} minutes.",
                    "Respect already busy times.",
                    "It is FORBIDDEN to suggest any option in the past, even if it is not listed as busy.",
                    "Always check the current time before suggesting an option!",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)