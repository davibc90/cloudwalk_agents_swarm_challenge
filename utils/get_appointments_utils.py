from config.env_config import env
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta, time
import pytz

# =========================
# Timezones
# =========================
TZ_UTC = pytz.utc
TZ_BR = pytz.timezone("America/Sao_Paulo")  # Keep BR tz as business logic is São Paulo time

# =========================
# Configuration (Environment Variables)
# =========================
BOOKING_DURATION_MINUTES = env.booking_duration_minutes
BOOKING_STEP_MINUTES = env.booking_step_minutes
BOOKING_START_TIME = env.booking_starting_time
BOOKING_END_TIME = env.booking_end_time
MAX_BOOK_AHEAD_DAYS = env.max_book_ahead_days
AVAILABLE_WEEKDAYS = env.available_weekdays

# =========================
# Date/Time Helpers
# =========================
def parse_dt(val: Optional[datetime | str]) -> Optional[datetime]:
    """
        Accepts datetime or ISO string (optional trailing 'Z'). Returns timezone-aware datetime preserving original tz.
        Examples of accepted ISO strings: "2025-09-29T09:30:00-03:00", "2025-09-29T12:30:00Z"
    """
    if val is None:
        return None
    if isinstance(val, str):
        s = val.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    return val

def as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
        Ensure datetime has tzinfo; assume UTC if naive, then convert to UTC
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_UTC)
    return dt.astimezone(TZ_UTC)

def floor_min(dt: Optional[datetime]) -> Optional[datetime]:
    """
        Zero-out seconds and microseconds
    """
    if dt is None:
        return None
    return dt.replace(second=0, microsecond=0)

def to_iso(dt: datetime) -> str:
    """
        Return ISO string with timezone offset (e.g., 2025-09-29T09:00:00-03:00)
    """
    return dt.isoformat()

def weekday_name(dt: datetime) -> str:
    """
        Return weekday name in English (lowercase), monday=0..sunday=6
    """
    idx = dt.weekday()  # Monday=0 ... Sunday=6
    if 0 <= idx < len(AVAILABLE_WEEKDAYS):
        return AVAILABLE_WEEKDAYS[idx]
    return ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][idx]

def format_us_date(dt: datetime) -> str:
    """
        Return US-formatted date string MM/DD/YYYY for labels and summaries
    """
    return dt.strftime("%m/%d/%Y")

def utc_window_for_us_date(date_str: Optional[str]) -> Tuple[datetime, datetime]:
    """
        Convert 'MM/DD/YYYY' in São Paulo timezone to a [start_of_day, start_of_next_day) window in UTC.
        If date_str is None, use the current local day in São Paulo.
    """
    if date_str:
        try:
            mm, dd, yyyy = map(int, date_str.split("/"))
            local_start = TZ_BR.localize(datetime(yyyy, mm, dd, 0, 0, 0, 0))
        except Exception:
            raise ValueError("Invalid 'date_str'. Use format MM/DD/YYYY.")
    else:
        now_br = datetime.now(TZ_BR)
        local_start = now_br.replace(hour=0, minute=0, second=0, microsecond=0)

    local_end = local_start + timedelta(days=1)
    start_utc = local_start.astimezone(TZ_UTC)
    end_utc = local_end.astimezone(TZ_UTC)
    return floor_min(start_utc), floor_min(end_utc)

def ensure_min_24h(start: Optional[datetime], end: Optional[datetime]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
        Guarantee a minimum 24-hour window, inferring missing bounds when needed
    """
    if start and not end:
        end = start + timedelta(hours=24)
    elif end and not start:
        start = end - timedelta(hours=24)
    elif start and end and (end - start) < timedelta(hours=24):
        end = start + timedelta(hours=24)
    return start, end

def normalize_future_window(start_utc: Optional[datetime], end_utc: Optional[datetime]):
    """
        Normalization rules (UTC):
        - if end <= now: error WINDOW_IN_PAST
        - clamp start to now if start < now
        - if only end is provided and it's in the future: set start = now
        - guarantee 24h window after clamping
        Returns: (start_utc, end_utc, error_dict | None)
    """
    now_utc = floor_min(datetime.now(TZ_UTC))

    if end_utc and end_utc <= now_utc:
        return None, None, {
            "code": "WINDOW_IN_PAST",
            "message": "The requested window is entirely in the past. Please query a future window.",
            "now": to_iso(now_utc),
        }

    if start_utc and start_utc < now_utc:
        start_utc = now_utc
    if not start_utc and end_utc:
        start_utc = now_utc

    start_utc, end_utc = ensure_min_24h(start_utc, end_utc)
    return start_utc, end_utc, None

# =========================
# Labeling & Bucketing Helpers
# =========================
def group_times_by_day(
    iso_times: List[str],
    tz=pytz.timezone("America/Sao_Paulo"),
    time_only: bool = True,  # True -> "HH:MM"; False -> full local ISO
) -> List[Dict[str, List[str]]]:
    """
        Group a list of local ISO times by US-formatted day label 'MM/DD/YYYY - weekday'
    """
    buckets: Dict[str, List[str]] = {}
    for s in iso_times:
        local_dt = parse_dt(s).astimezone(tz)
        label = f"{format_us_date(local_dt)} - {weekday_name(local_dt)}"
        value = local_dt.strftime("%H:%M") if time_only else to_iso(local_dt)
        buckets.setdefault(label, []).append(value)

    keys_sorted = sorted(
        buckets.keys(),
        key=lambda k: datetime.strptime(k.split(" - ")[0], "%m/%d/%Y")
    )
    return [{k: buckets[k]} for k in keys_sorted]

def list_queried_days(iso_times: List[str], tz=pytz.timezone("America/Sao_Paulo")) -> List[str]:
    """
        List unique local days present in the given ISO times, labeled as 'MM/DD/YYYY - weekday'
    """
    seen = set()
    out: List[str] = []
    for s in iso_times:
        local_dt = parse_dt(s).astimezone(tz)
        key = format_us_date(local_dt)
        if key not in seen:
            seen.add(key)
            out.append(f"{key} - {weekday_name(local_dt)}")
    return out

def list_days_in_window(start_utc: datetime, end_utc: datetime, tz=pytz.timezone("America/Sao_Paulo")) -> List[str]:
    """
        List local days covered by the [start_utc, end_utc) window, labeled as 'MM/DD/YYYY - weekday'
    """
    start_local = start_utc.astimezone(tz)
    end_local = end_utc.astimezone(tz)
    day = start_local.date()
    last = end_local.date()
    out: List[str] = []
    while day <= last:
        dt0 = tz.localize(datetime.combine(day, time(0, 0)))
        out.append(f"{format_us_date(dt0)} - {weekday_name(dt0)}")
        day += timedelta(days=1)
    return out

# =========================
# Availability Computation
# =========================
def merge_intervals(pairs: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    if not pairs:
        return []
    pairs = sorted(pairs, key=lambda x: x[0])
    merged = [pairs[0]]
    for s, e in pairs[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged

def compute_availability(appointments: List[Dict], start_utc: datetime, end_utc: datetime):
    """
        Build "busy" (preserving id/nickname/subject) and "free" lists in São Paulo local time (minute precision).
        Returns a dict with busy intervals, free intervals, and the local window in ISO
    """
    # local window
    start_local = floor_min(start_utc.astimezone(TZ_BR))
    end_local = floor_min(end_utc.astimezone(TZ_BR))

    # normalize/parse inputs
    appts = sorted(appointments, key=lambda x: x["start_time"]) if appointments else []

    busy_pairs: List[Tuple[datetime, datetime]] = []
    busy_meta: List[Dict] = []

    for a in appts:
        s = floor_min(parse_dt(a["start_time"]).astimezone(TZ_BR))
        e = floor_min(parse_dt(a["end_time"]).astimezone(TZ_BR))
        busy_pairs.append((s, e))
        busy_meta.append({
            "id": a.get("id"),
            "nickname": a.get("nickname"),
            **({"subject": a.get("subject")} if "subject" in a else {}),
            "start": to_iso(s),
            "end": to_iso(e),
        })

    free_pairs: List[Tuple[datetime, datetime]] = []

    if not busy_pairs:
        free_pairs.append((start_local, end_local))
    else:
        # before first
        if start_local < busy_pairs[0][0]:
            free_pairs.append((start_local, busy_pairs[0][0]))
        # between
        for (s0, e0), (s1, _) in zip(busy_pairs, busy_pairs[1:]):
            if e0 < s1:
                free_pairs.append((e0, s1))
        # after last
        if end_local > busy_pairs[-1][1]:
            free_pairs.append((busy_pairs[-1][1], end_local))

    free_iso = [{"start": to_iso(s), "end": to_iso(e)} for s, e in free_pairs]

    return {
        "busy_intervals": busy_meta,
        "free_intervals": free_iso,
        "window_local": {"start": to_iso(start_local), "end": to_iso(end_local)},
    }

# =========================
# Slot Generation
# =========================
def generate_discrete_slots(
    free_intervals: List[Dict],
    duration_minutes: int = 60,
    step_minutes: Optional[int] = None,
) -> List[str]:
    """
        Suggest start-times (São Paulo tz) fully contained in free intervals and never in the past
    """
    now_br = floor_min(datetime.now(TZ_UTC).astimezone(TZ_BR))
    step = timedelta(minutes=(step_minutes or duration_minutes))
    dur = timedelta(minutes=duration_minutes)

    out: List[str] = []
    for iv in free_intervals:
        s = floor_min(parse_dt(iv["start"]).astimezone(TZ_BR))
        e = floor_min(parse_dt(iv["end"]).astimezone(TZ_BR))
        cur = max(s, now_br)
        while cur + dur <= e:
            out.append(to_iso(cur))
            cur += step
    return out

def generate_discrete_busy_slots(
    busy_intervals: List[Dict],
    duration_minutes: int = 60,
    step_minutes: Optional[int] = None,
) -> List[str]:

    """
        Generate start-times (São Paulo tz) fully contained in busy intervals, 
        never in the past, discretized by step (default = duration)
    """

    now_br = floor_min(datetime.now(TZ_UTC).astimezone(TZ_BR))
    step = timedelta(minutes=(step_minutes or duration_minutes))
    dur = timedelta(minutes=duration_minutes)

    pairs = [
        (floor_min(parse_dt(iv["start"]).astimezone(TZ_BR)),
         floor_min(parse_dt(iv["end"]).astimezone(TZ_BR)))
        for iv in busy_intervals
    ]
    pairs = merge_intervals(pairs)

    out: List[str] = []
    for s, e in pairs:
        cur = max(s, now_br)
        while cur + dur <= e:
            out.append(to_iso(cur))
            cur += step
    return out

def filter_by_working_hours(
    iso_times: List[str],
    duration_minutes: int,
    workday_start: str,
    workday_end: str,
    tzname: str = "America/Sao_Paulo",
) -> List[str]:
    """
        Keep only slots whose start and end fall within [workday_start, workday_end) on the same local day
    """
    tz = pytz.timezone(tzname)
    hh_i, mm_i = map(int, workday_start.split(":"))
    hh_f, mm_f = map(int, workday_end.split(":"))
    if (hh_f, mm_f) <= (hh_i, mm_i):
        return []

    start_min = hh_i * 60 + mm_i
    end_min = hh_f * 60 + mm_f
    dur = timedelta(minutes=duration_minutes)

    kept: List[str] = []
    for s in iso_times:
        start_dt = parse_dt(s).astimezone(tz)
        end_dt = start_dt + dur
        if end_dt.date() != start_dt.date():
            continue
        mi = start_dt.hour * 60 + start_dt.minute
        mf = end_dt.hour * 60 + end_dt.minute
        if start_min <= mi and mf <= end_min:
            kept.append(to_iso(start_dt))
    return kept