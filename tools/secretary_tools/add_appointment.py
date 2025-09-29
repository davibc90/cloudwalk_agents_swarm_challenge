
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
    Tool used to add a new appointment with identity checking purposes
        Args:
            user_id (str): User ID retrieved by customer_service_agent
            start_time (datetime): Start date and time of the appointment (UTC timezone timestamp format)
            end_time (datetime): End date and time of the appointment (UTC timezone timestamp format)
    """
    response = interrupt(  
        f"Trying to call `add_appointment` with args {{'user_id': {user_id}, 'start_time': {start_time}, 'end_time': {end_time}}}. "
        "Do you approve this appointment? \n"
        "Please answer with 'YES' or 'NO'."
    )

    if response["type"] == "YES":
        try:
            # Inserindo dados no Supabase
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
    else:
        return (
            "Human intervention rejected the appointment. "
            "Please, tell the user a customer succes specialist will reach out soon in person."
            "When it happens, both will find the best time to schedule the appointment."
        )

