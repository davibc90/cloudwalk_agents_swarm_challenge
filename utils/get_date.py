import locale
import pytz
from datetime import datetime

def get_date():
    """
        Get the current date and time in São Paulo formatted in U.S. English style.

        ### Description
        Retrieves the current local time in the **America/Sao_Paulo** timezone,
        formats it as: **Month, D, YYYY - HH:MM AM/PM (GMT±X)** 
        (e.g., September, 30, 2025 - 02:15 PM GMT-3),
        and wraps the result in a <current_date> tag
    """
    
    try:
        locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
    except:
        locale.setlocale(locale.LC_TIME, "English_United States.1252")
    
    timezone = pytz.timezone("America/Sao_Paulo")
    date_time = datetime.now(timezone)

    # Format: Month, D, YYYY - HH:MM AM/PM
    current_date = date_time.strftime("%B, %d, %Y - %I:%M %p")
    current_date = current_date.replace(" 0", " ")

    # Get the offset from UTC in the format ±HHMM
    gmt_offset = date_time.strftime("%z")  
    gmt_formatted = f"GMT{gmt_offset[:3]}"  

    return f"<current_date>\n{current_date} {gmt_formatted}\n</current_date>"
