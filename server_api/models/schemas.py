from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfileUpdate(BaseModel):
    nome_completo: str
    current_password: str
    new_password: Optional[str] = None

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    nome_completo: str
    cargo: str
    acessos: List[str]

class RegistroCreate(BaseModel):
    observador: str
    profissional_auditado: str
    unidade: str
    momento_auditado: str
    produto_utilizado: str
    data_auditoria: Optional[str] = None # Formato YYYY-MM-DD
    usuario_login: Optional[str] = None
