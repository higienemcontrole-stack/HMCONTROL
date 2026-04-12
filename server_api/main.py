from fastapi import FastAPI, HTTPException, Depends, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Importações Modulares
from .logic.excel_processor import ExcelProcessor
from .logic.audit_logger import logger
from .logic.auth_manager import AuthManager
from .models.schemas import UserLogin, UserProfileUpdate, AdminUserCreate, RegistroCreate

# Configurações de Ambiente (Vercel Ready)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Prioriza variáveis do sistema (Dashboard Vercel) over arquivos locais
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error(f"ERRO CRÍTICO: Variáveis do Supabase ausentes.")

# --- INICIALIZAÇÃO ÚNICA DO APP ---
app = FastAPI(title="HM CONTROL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Componentes
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
auth_admin = AuthManager(SUPABASE_URL, SUPABASE_KEY)

# Caminho absoluto para garantir consistência no Vercel
EXCEL_PATH = os.path.join(BASE_DIR, "logic", "Planilha NOVA de higiene de Mãos.xlsx")
excel = ExcelProcessor(EXCEL_PATH)

# --- CACHE DE DADOS SUPABASE ---
GLOBAL_DATA_CACHE = {"records": [], "last_sync": None}

async def fetch_all_registros_from_supabase(force_refresh=False):
    global GLOBAL_DATA_CACHE
    now = datetime.now()
    
    # Cache de 60 segundos para performance no dashboard
    if not force_refresh and GLOBAL_DATA_CACHE["last_sync"] and (now - GLOBAL_DATA_CACHE["last_sync"]).seconds < 60:
        return GLOBAL_DATA_CACHE["records"]
        
    try:
        all_registros = []
        offset = 0
        while True:
            # Busca em blocos de 1000 (limite do Supabase)
            chunk = supabase.table("registros").select("*").order("created_at", desc=True).range(offset, offset + 999).execute()
            if not chunk.data: break
            all_registros.extend(chunk.data)
            offset += 1000
            if len(chunk.data) < 1000: break
        
        # Filtra registros válidos (com observador)
        real_records = [r for r in all_registros if r.get("observador")]
        GLOBAL_DATA_CACHE = {"records": real_records, "last_sync": now}
        return real_records
    except Exception as e:
        logger.error(f"Erro ao buscar no Supabase: {str(e)}")
        return GLOBAL_DATA_CACHE["records"] if GLOBAL_DATA_CACHE["records"] else []

# --- ROTAS DE AUTENTICAÇÃO ---
@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    try:
        res = supabase.auth.sign_in_with_password({"email": credentials.email, "password": credentials.password})
        profile = supabase.table("perfis").select("*").eq("id", res.user.id).single().execute()
        return {"session": res.session, "user": res.user, "profile": profile.data}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Credenciais Inválidas")

@app.get("/api/admin/bootstrap")
async def bootstrap_admin(token: str):
    expected_token = os.environ.get("ADMIN_BOOTSTRAP_TOKEN")
    if not expected_token or token != expected_token:
        raise HTTPException(status_code=403, detail="Token Inválido")

    try:
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        if not email or not password:
            return {"status": "error", "message": "Variáveis ADMIN_EMAIL/PASSWORD ausentes na Vercel."}
        
        try:
            auth_admin.create_user_admin(email, password, {"full_name": "Dev Master"})
        except: pass

        prof_data = {
            "nome_completo": "Dev Master",
            "email": email,
            "cargo": "admin",
            "acessos": ["dashboard", "registro", "tabulacao", "dinamica", "validacoes", "configuracoes"]
        }
        profiles = supabase.table("perfis").select("id").eq("email", email).execute()
        if len(profiles.data) > 0:
            supabase.table("perfis").update(prof_data).eq("id", profiles.data[0]["id"]).execute()
            return {"status": "success", "message": "Resgate concluído."}
        return {"status": "partial", "message": "Usuário Auth criado. Logue para ativar perfil."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

import traceback

@app.get("/api/excel/dashboard")
async def get_dashboard_data(unit: str = "TODAS", month: str = "TODOS", year: str = "TODOS"):
    try:
        data = await fetch_all_registros_from_supabase()
        excel_ready = []
        for r in data:
            prod = r.get("produto_utilizado", "")
            hm_status = "Não" if "Não Realizou" in str(prod) else "Sim"
            
            excel_ready.append({
                "Mês (automático)": r.get("mes"),
                "Ano (automático)": r.get("ano"),
                "Observador": r.get("observador"),
                "Unidade": r.get("unidade"),
                "Profissional Auditado": r.get("profissional_auditado"),
                "Momento Auditado": r.get("momento_auditado"),
                "Produto utilizado": prod,
                "HM realizada?": hm_status,
                "Login": r.get("usuario_login"),
                "Horário": r.get("horario_envio")
            })
            
        excel.update_from_external_data(excel_ready)
        return excel.get_dashboard_data(unit, month, year)
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Erro no dashboard: {error_details}")
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": error_details})

@app.get("/api/excel/tabulation")
async def get_tabulation():
    try:
        # Busca com force_refresh para garantir dados novos na tabela
        data = await fetch_all_registros_from_supabase(force_refresh=True)
        mapped = []
        for r in data:
            prod = r.get("produto_utilizado", "")
            hm_status = "Não" if "Não Realizou" in str(prod) else "Sim"
            
            mapped.append({
                "Mês (automático)": r.get("mes"),
                "Ano (automático)": r.get("ano"),
                "Observador": r.get("observador"),
                "Unidade": r.get("unidade"),
                "Profissional Auditado": r.get("profissional_auditado"),
                "Momento Auditado": r.get("momento_auditado"),
                "Produto utilizado": prod,
                "HM realizada?": hm_status,
                "Login": r.get("usuario_login"),
                "Horário": r.get("horario_envio")
            })
        return mapped
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Erro na tabulação: {error_details}")
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": error_details})

# --- GESTÃO DE USUÁRIOS ---
@app.get("/api/admin/users")
async def list_users():
    profiles = supabase.table("perfis").select("*").order("nome_completo").execute()
    return profiles.data

@app.post("/api/admin/users")
async def create_user(user: AdminUserCreate):
    auth_res = auth_admin.create_auth_user(user.email, user.password)
    if "error" in auth_res: raise HTTPException(status_code=400, detail=auth_res["error"])
    
    profile_data = {
        "id": auth_res["user_id"],
        "email": user.email,
        "nome_completo": user.nome_completo,
        "cargo": user.cargo,
        "acessos": user.acessos
    }
    supabase.table("perfis").insert(profile_data).execute()
    return {"status": "success"}

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str):
    supabase.table("perfis").delete().eq("id", user_id).execute()
    auth_admin.delete_auth_user(user_id)
    return {"status": "success"}

@app.get("/api/user/profile")
async def get_profile(user_id: str = Header(...)):
    profile = supabase.table("perfis").select("*").eq("id", user_id).single().execute()
    return profile.data

# --- SALVAR REGISTRO ---
@app.post("/api/registros")
async def save_registro(reg: RegistroCreate):
    try:
        data_ref = reg.data_auditoria or str(datetime.now().date())
        dt = datetime.strptime(data_ref, "%Y-%m-%d")
        
        payload = {
            "observador": reg.observador, 
            "auditor": reg.observador,
            "profissional_auditado": reg.profissional_auditado, 
            "unidade": reg.unidade, 
            "momento_auditado": reg.momento_auditado, 
            "produto_utilizado": reg.produto_utilizado,
            "usuario_login": reg.usuario_login or "aplicativo",
            "data_auditoria": data_ref,
            "mes": dt.month,
            "ano": str(dt.year),
            "data_envio": str(datetime.now().date()),
            "horario_envio": datetime.now().strftime("%H:%M:%S")
        }
        
        supabase.table("registros").insert(payload).execute()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Erro ao salvar registro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
