from fastapi import FastAPI, HTTPException, Depends, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from typing import List, Optional
from pydantic import BaseModel
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Importações Modulares
from .logic.audit_logger import logger
from .logic.auth_manager import AuthManager
from .models.schemas import UserLogin, UserProfileUpdate, AdminUserCreate, RegistroCreate
import pandas as pd

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

# --- CACHE DE DADOS SUPABASE ---
GLOBAL_DATA_CACHE = {"records": [], "last_sync": None}

async def fetch_all_registros_from_supabase(force_refresh=False):
    global GLOBAL_DATA_CACHE
    now = datetime.now()
    
    # Cache de 30 segundos para performance no dashboard
    if not force_refresh and GLOBAL_DATA_CACHE["last_sync"] and (now - GLOBAL_DATA_CACHE["last_sync"]).seconds < 30:
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
            return {"status": "error", "message": "Variaveis ADMIN_EMAIL/PASSWORD ausentes na Vercel."}
        
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
            return {"status": "success", "message": "Resgate concluido."}
        return {"status": "partial", "message": "Usuario Auth criado. Logue para ativar perfil."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    """Redireciona o acesso da raiz para a pagina inicial do frontend"""
    return RedirectResponse(url="/index.html")

import traceback

@app.get("/api/excel/dashboard")
async def get_dashboard_data(unit: str = "TODAS", month: str = "TODOS", year: str = "TODOS"):
    try:
        data = await fetch_all_registros_from_supabase()
        if not data:
            return {"filters": {"units": [], "months": [], "years": []}, "moments": [], "categories": [], "timeline": [], "units_data": []}
            
        df = pd.DataFrame(data)
        
        # Filtros Dinâmicos
        all_units = sorted(df["unidade"].unique().tolist())
        all_years = sorted(df["ano"].unique().tolist())
        all_months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
        
        # Aplicar Filtros selecionados
        temp_df = df.copy()
        if unit != "TODAS": temp_df = temp_df[temp_df["unidade"] == unit]
        if month != "TODOS": temp_df = temp_df[temp_df["mes"] == month]
        if year != "TODOS": temp_df = temp_df[temp_df["ano"] == year]

        # Agregadores para o Dashboard (Volume de Monitoramento)
        def get_chart_data(group_col):
            if temp_df.empty: return []
            counts = temp_df.groupby(group_col).size().reset_index(name="total")
            counts.columns = ["label", "total"]
            return counts.sort_values(by="total", ascending=False).to_dict(orient="records")

        return {
            "filters": {
                "units": all_units,
                "months": all_months,
                "years": all_years
            },
            "moments": get_chart_data("momento_auditado"),
            "categories": get_chart_data("profissional_auditado"),
            "timeline": get_chart_data("mes"),
            "units": get_chart_data("unidade")
        }
    except Exception as e:
        logger.error(f"Erro no dashboard purificado: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar dados vivos do Supabase.")

@app.get("/api/excel/tabulation")
async def get_tabulation():
    try:
        data = await fetch_all_registros_from_supabase(force_refresh=True)
        return data
    except Exception as e:
        logger.error(f"Erro na tabulação: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro interno ao carregar tabulação de dados.")

@app.get("/api/excel/validations")
async def get_validations():
    """Retorna as listas oficiais diretamente do Supabase (Sync Realtime)"""
    try:
        data = await fetch_all_registros_from_supabase()
        df = pd.DataFrame(data)
        
        # Extrai valores únicos existentes no banco como verdade absoluta
        return {
            "unidades": sorted(df["unidade"].unique().tolist()) if not df.empty else ["Enf A", "Enf B", "UTI"],
            "profissionais": sorted(df["profissional_auditado"].unique().tolist()) if not df.empty else ["Médico", "Enfermeiro", "Técnico"],
            "momentos": [
                "1 - Antes de contato com o paciente",
                "2 - Antes de procedimento asséptico",
                "3 - Após risco de exposição a fluidos",
                "4 - Após contato com o paciente",
                "5 - Após contato com áreas próximas"
            ],
            "produtos": sorted(df["produto_utilizado"].unique().tolist()) if not df.empty else ["Álcool Gel", "Sabonete"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar listas: {str(e)}")

@app.post("/api/admin/cache/clear")
async def clear_cache():
    """Reseta o cache global de registros"""
    global GLOBAL_DATA_CACHE
    GLOBAL_DATA_CACHE = {"records": [], "last_sync": None}
    return {"status": "success", "message": "Cache limpo."}

@app.post("/api/admin/sync")
async def sync_database():
    """Força sincronização total com Supabase"""
    try:
        await fetch_all_registros_from_supabase(force_refresh=True)
        return {"status": "success", "message": "Sincronização concluída."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/excel/pivot")
async def get_pivot():
    try:
        data = await fetch_all_registros_from_supabase()
        if not data:
            return []
            
        df = pd.DataFrame(data)
        
        # Gerar Pivot Table: Unidade vs Momento Auditado (Volume)
        # Bate com a lógica da Tabela Dinâmica do Excel original
        pivot = pd.crosstab(
            df["unidade"], 
            df["momento_auditado"], 
            margins=True, 
            margins_name="Total Geral"
        ).reset_index()
        
        # Converter para lista de dicionários para o frontend
        return pivot.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Erro no pivot purificado: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar Tabela Dinâmica do banco.")

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
async def get_profile(user_id: str = None):
    if not user_id:
        raise HTTPException(status_code=400, detail="ID de usuário não fornecido.")
    profile = supabase.table("perfis").select("*").eq("id", user_id).single().execute()
    return profile.data

# --- SALVAR REGISTRO ---
@app.post("/api/registros")
async def save_registro(reg: RegistroCreate):
    try:
        data_ref = reg.data_auditoria or str(datetime.now().date())
        meses_map = {1:"jan",2:"fev",3:"mar",4:"abr",5:"mai",6:"jun",7:"jul",8:"ago",9:"set",10:"out",11:"nov",12:"dez"}
        dt = datetime.strptime(data_ref, "%Y-%m-%d")
        mes_nome = meses_map.get(dt.month, "jan")
        
        payload = {
            "observador": reg.observador, 
            "auditor": reg.observador,
            "profissional_auditado": reg.profissional_auditado, 
            "unidade": reg.unidade, 
            "momento_auditado": reg.momento_auditado, 
            "produto_utilizado": reg.produto_utilizado,
            "usuario_login": reg.usuario_login or "aplicativo",
            "data_auditoria": data_ref,
            "mes": mes_nome,
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
