from supabase import create_client as _create_client, Client
import os

def create_client(url: str, key: str) -> Client:
    """
    Wrapper para o cliente do banco de dados (Data Twin).
    Centraliza a conexão para facilitar a neutralização e troca de provedor se necessário.
    """
    if not url or not key:
        return None
    return _create_client(url, key)
