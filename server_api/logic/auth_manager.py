import os
from supabase import create_client, Client
from dotenv import load_dotenv

class AuthManager:
    def __init__(self, url: str, service_key: str):
        self.supabase_admin = create_client(url, service_key) if service_key else None

    def create_user_admin(self, email: str, password: str, metadata: dict):
        if not self.supabase_admin:
            raise Exception("Service Role Key não configurada no servidor.")
        
        try:
            res = self.supabase_admin.auth.admin.create_user({
                "email": email,
                "password": password,
                "user_metadata": metadata,
                "email_confirm": True
            })
            return res
        except Exception as e:
            raise Exception(f"Erro no Supabase Admin: {str(e)}")

    def delete_user_admin(self, user_id: str):
        if not self.supabase_admin:
            raise Exception("Service Role Key não configurada no servidor.")
        return self.supabase_admin.auth.admin.delete_user(user_id)
