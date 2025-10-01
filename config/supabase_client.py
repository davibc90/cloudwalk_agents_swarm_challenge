"""
    Supabase client initialization module.

    This module is responsible for:
        - Loading environment variables from the .env file.
        - Creating a single Supabase client instance using the service role key.
        - Exposing the client as a reusable singleton across the application.
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Create a single Supabase client instance
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
