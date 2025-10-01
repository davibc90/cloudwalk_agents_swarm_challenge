"""
    Supabase client initialization module.

    This module is responsible for:
        - Loading environment variables
        - Creating a single Supabase client instance using the service role key.
        - Exposing the client as a reusable singleton across the application.
"""

from supabase import create_client, Client
from config.env_config import env

SUPABASE_URL = str(env.supabase_url)
SUPABASE_KEY = str(env.supabase_service_role_key)

# Instância única do cliente
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
