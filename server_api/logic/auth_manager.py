import os
from db import create_client, Client
from dotenv import load_dotenv


class AuthManager:
    def __init__(self, url: str, service_key: str):
        self.auth_client = create_client(url, service_key) if service_key else None
        self.db_client = create_client(url, service_key) if service_key else None

    def create_auth_user(self, email: str, password: str):
        """Cria usuário via Auth Admin (retorna dict para compatibilidade)"""
        if not self.auth_client:
            return {"error": "Chave de serviço não configurada"}
        try:
            res = self.auth_client.auth.admin.create_user(
                {"email": email, "password": password, "email_confirm": True}
            )
            return {"user_id": res.id}
        except Exception as e:
            return {"error": str(e)}

    def delete_auth_user(self, user_id: str):
        """Deleta usuário via Auth Admin"""
        if not self.auth_client:
            return {"error": "Chave de serviço não configurada"}
        try:
            self.auth_client.auth.admin.delete_user(user_id)
            return {"status": "success"}
        except Exception as e:
            return {"error": str(e)}

    def create_user_admin(self, email: str, password: str, metadata: dict):
        if not self.auth_client:
            raise Exception("Chave de serviço não configurada no servidor.")

        try:
            res = self.auth_client.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "user_metadata": metadata,
                    "email_confirm": True,
                }
            )
            return res
        except Exception as e:
            raise Exception(f"Erro no Cliente de Identidade: {str(e)}")

    def delete_user_admin(self, user_id: str):
        if not self.auth_client:
            raise Exception("Chave de serviço não configurada no servidor.")
        return self.auth_client.auth.admin.delete_user(user_id)

    def list_users_admin(self):
        """Retorna todos os usuários cadastrados no Serviço de Identidade (Admin)"""
        if not self.auth_client:
            raise Exception("Chave de serviço não configurada no servidor.")
        try:
            # A API retorna um objeto com a propriedade 'users'
            res = self.auth_client.auth.admin.list_users()
            return res.users if hasattr(res, "users") else res
        except Exception as e:
            raise Exception(f"Erro ao listar usuários: {str(e)}")

    def update_user_by_id(self, user_id: str, attributes: dict):
        """Atualiza usuário via Auth Admin"""
        if not self.auth_client:
            raise Exception("Chave de serviço não configurada no servidor.")
        try:
            self.auth_client.auth.admin.update_user_by_id(user_id, attributes)
            return {"status": "success"}
        except Exception as e:
            raise Exception(f"Erro ao atualizar usuário: {str(e)}")
