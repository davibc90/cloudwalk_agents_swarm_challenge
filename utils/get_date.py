import locale
import pytz
from datetime import datetime

def get_date():
    """
    Get the current date and time in São Paulo formatted in U.S. English style.

    ### Description
    Retrieves the current local time in the **America/Sao_Paulo** timezone,
    formats it as: **Month, D, YYYY - HH:MM AM/PM**
    (e.g., September, 30, 2025 - 02:15 PM),
    and wraps the result in a <current_date> tag.
    """
    
    try:
        locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
    except:
        locale.setlocale(locale.LC_TIME, "English_United States.1252")
    
    timezone = pytz.timezone("America/Sao_Paulo")
    date_time = datetime.now(timezone)

    # Format: Month, D, YYYY - HH:MM AM/PM
    # %B → month in full, %d → day, %Y → year, %I:%M %p → 12h time AM/PM
    current_date = date_time.strftime("%B, %d, %Y - %I:%M %p")
    current_date = current_date.replace(" 0", " ")

    return f"<current_date>\n{current_date}\n</current_date>"
