
from datetime import datetime
from langchain_core.tools import tool
from config.supabase_client import supabase
from langgraph.types import interrupt

@tool
def add_appointment(
    user_id: str,
    start_time: datetime,
    end_time: datetime,
) -> str:
    """
    Tool used to add a new online meeting appointment in the calendar
    Args:
        user_id (str): Unique user identifier.
        start_time (datetime): Appointment start time (UTC).
        end_time (datetime): Appointment end time (UTC).
    Returns:
        str: Success message, error details, or rejection notice.
    """
    
    # Human intervention hook
    response = interrupt(  
        f"Trying to call `add_appointment` with args {{'user_id': {user_id}, 'start_time': {start_time}, 'end_time': {end_time}}}. "
        "Do you approve this appointment? \n"
        "Please answer with 'YES' or 'NO'."
    )

    # Human intervention approval
    if response["type"] == "YES":

        try:
            # Inserts appointment in Supabase
            response = supabase.table("appointments").insert({
                "user_id": user_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }).execute()

            if response.data: 
                return "Appointment added successfully!"
            else:
                return "Unknown error: could not add appointment. Please try again!"

        except Exception as e:
            return f"Unknown error: {str(e)}"

    # Human intervention rejection        
    else:
        return (
            "Human intervention rejected the appointment. "
            "Please, tell the user a customer succes specialist will reach out soon in person."
            "When it happens, both will find the best time to schedule the appointment."
        )

