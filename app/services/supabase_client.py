"""
Supabase client — thin wrapper around supabase-py.
Set SUPABASE_URL and SUPABASE_KEY in your .env file.
"""
import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)
