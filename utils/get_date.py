
import locale
import pytz
from datetime import datetime

def get_date():
    """
    Get the current date and time in São Paulo formatted in U.S. English style.

    ### Description
    This function retrieves the current local time in the **America/Sao_Paulo** timezone,
    formats it using the U.S. English locale (`en_US.UTF-8`), and returns the result
    wrapped in a custom `<current_date>` tag.

    - The date is formatted as: **Day of the week, MM/DD/YYYY, Time: HH:MM AM/PM**.
    - The locale ensures month/day names appear in English.
    - The time is displayed in 12-hour format with AM/PM.

    ### Returns
    - **str**: A string containing the formatted date and time, wrapped in XML-like tags.
    """
    
    locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
    
    timezone = pytz.timezone("America/Sao_Paulo")
    date_time = datetime.now(timezone)

    # Formato americano: Month/Day/Year e AM/PM
    current_date_time = date_time.strftime("%A, %m/%d/%Y, Time: %I:%M %p")
    return f"<current_date>\n{current_date_time}\n</current_date>"

    
