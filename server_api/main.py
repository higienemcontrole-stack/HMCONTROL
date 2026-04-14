from fastapi import FastAPI, HTTPException, Depends, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from typing import List, Optional
from pydantic import BaseModel
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from db import create_client, Client

# Ajuste de path para encontrar o config/.env corretamente
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "config", ".env"))

# Importações Modulares (Absolute Path for Vercel)
from server_api.logic.audit_logger import logger
from server_api.logic.auth_manager import AuthManager
from server_api.models.schemas import UserLogin, UserProfileUpdate, AdminUserCreate, RegistroCreate
import pandas as pd

# Configurações de Ambiente (Vercel Ready)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mapeamento Flexível de Variáveis (Suporta múltiplos padrões de nomeação)
DB_URL = os.environ.get("DB_URL") or os.environ.get("SUPABASE_URL") or os.environ.get("API_URL")
SERVICE_KEY = os.environ.get("DB_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("service_role_secret")
PUBLIC_KEY = os.environ.get("DB_PUBLIC_KEY") or os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("anon_public")

# Fallback para compatibilidade
DB_KEY = SERVICE_KEY or PUBLIC_KEY

if not DB_URL or not DB_KEY:
    logger.error(f"ERRO CRÍTICO: Variáveis ausentes. URL: {bool(DB_URL)}, KEY: {bool(DB_KEY)}, SERVICE: {bool(SERVICE_KEY)}")

# Inicializar Componentes
db = create_client(DB_URL, PUBLIC_KEY or SERVICE_KEY or DB_KEY)
auth_admin = AuthManager(DB_URL, SERVICE_KEY or DB_KEY)

# --- INICIALIZAÇÃO DO APP ---
app = FastAPI(title="HM CONTROL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CACHE DE DADOS db ---
GLOBAL_DATA_CACHE = {"records": [], "last_sync": None}

async def fetch_all_registros_from_db(force_refresh=False):
    global GLOBAL_DATA_CACHE
    now = datetime.now()
    
    # Cache de 30 segundos para performance no dashboard
    if not force_refresh and GLOBAL_DATA_CACHE["last_sync"] and (now - GLOBAL_DATA_CACHE["last_sync"]).seconds < 30:
        return GLOBAL_DATA_CACHE["records"]
        
    try:
        all_registros = []
        offset = 0
        while True:
            # Busca em blocos de 1000 (limite do db)
            chunk = db.table("registros").select("*").order("created_at", desc=True).range(offset, offset + 999).execute()
            if not chunk.data: break
            all_registros.extend(chunk.data)
            offset += 1000
            if len(chunk.data) < 1000: break
        
        # Filtra registros válidos (com observador)
        real_records = [r for r in all_registros if r.get("observador")]
        GLOBAL_DATA_CACHE = {"records": real_records, "last_sync": now}
        return real_records
    except Exception as e:
        logger.error(f"Erro ao buscar no db: {str(e)}")
        return GLOBAL_DATA_CACHE["records"] if GLOBAL_DATA_CACHE["records"] else []

# --- ROTAS DE AUTENTICAÇÃO ---
@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    try:
        res = db.auth.sign_in_with_password({"email": credentials.email, "password": credentials.password})

        # Buscar profile na tabela profiles (ou view perfis)
        try:
            profile_res = db.table("perfis").select("*").eq("id", res.user.id).single().execute()
            profile = profile_res.data or {}
        except Exception:
            profile = {}

        # Montar objeto user unificado com campos do profile
        # O frontend salva este objeto inteiro no localStorage como 'hm_user'
        user_obj = {
            "id": res.user.id,
            "email": res.user.email,
            # Campos normalizados que o frontend (core.js) espera
            "nome_completo": profile.get("nome_completo") or profile.get("full_name") or res.user.user_metadata.get("full_name", ""),
            "cargo": profile.get("cargo") or profile.get("role") or "user",
            "acessos": profile.get("acessos") or [],
            "ativo": profile.get("ativo", True),
            # Metadados extras
            "created_at": str(res.user.created_at) if res.user.created_at else None,
        }

        return {
            "session": res.session,
            "user": user_obj,
            "profile": profile
        }
    except Exception as e:
        logger.error(f"Erro no login para {credentials.email}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=401, detail=f"Erro na autenticação: {str(e)}")


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
        profiles = db.table("perfis").select("id").eq("email", email).execute()
        if len(profiles.data) > 0:
            db.table("perfis").update(prof_data).eq("id", profiles.data[0]["id"]).execute()
            return {"status": "success", "message": "Resgate concluido."}
        return {"status": "partial", "message": "Usuario Auth criado. Logue para ativar perfil."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- GESTÃO DE USUÁRIOS (ADMIN) ---

@app.get("/api/users")
async def list_users():
    """Lista unificada de usuários: Auth + Tabela de Perfis"""
    try:
        # 1. Buscar todos os usuários do db Auth (Admin)
        auth_users = auth_admin.list_users_admin()
        # Garante que temos uma lista de objetos do tipo User
        users_list = auth_users if isinstance(auth_users, list) else (auth_users.users if hasattr(auth_users, 'users') else [])
        
        # 2. Buscar todos os registros da tabela perfis
        profiles_res = db.table("perfis").select("*").execute()
        profiles_map = {p['id']: p for p in profiles_res.data}
        
        # 3. Mesclar dados
        unified = []
        for u in users_list:
            profile = profiles_map.get(u.id, {})
            unified.append({
                "id": u.id,
                "email": u.email,
                "nome_completo": profile.get("nome_completo") or u.user_metadata.get("full_name") or "",
                "cargo": profile.get("cargo") or "user",
                "acessos": profile.get("acessos") or [],
                "ativo": profile.get("ativo", True),
                "hospital": profile.get("hospital") or "",
                "unidade": profile.get("unidade") or "",
                "registro_profissional": profile.get("registro_profissional") or "",
                "celular": profile.get("celular") or "",
                "created_at": str(u.created_at) if hasattr(u, "created_at") else None,
                "updated_at": profile.get("updated_at") or (str(u.updated_at) if hasattr(u, "updated_at") else None),
                # Flag para indicar se o perfil ainda não foi configurado no banco
                "no_profile": u.id not in profiles_map
            })
            
        # Ordenar por nome (ou email se sem nome)
        unified.sort(key=lambda x: (x["nome_completo"] or x["email"]).lower())
        
        return unified
    except Exception as e:
        logger.error(f"Erro ao unificar lista de usuários: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao sincronizar contas do db.")

@app.post("/api/users")
async def create_user(user: AdminUserCreate):
    """Cria um usuário no Auth e o respectivo perfil na tabela perfis"""
    try:
        # 1. Criar no db Auth (Admin)
        auth_res = auth_admin.create_user_admin(
            email=user.email,
            password=user.password,
            metadata={"full_name": user.nome_completo}
        )
        
        new_uid = auth_res.user.id
        
        # 2. Criar perfil
        if new_uid:
            payload = {
                "id": new_uid,
                "email": user.email,
                "nome_completo": user.nome_completo,
                "cargo": user.cargo,
                "acessos": user.acessos,
                "hospital": user.hospital,
                "unidade": user.unidade,
                "registro_profissional": user.registro_profissional,
                "celular": user.celular,
                "updated_at": datetime.now().isoformat()
            }
            db.table("perfis").insert(payload).execute()
            
            # Sincronizar nome e celular com Auth metadata
            try:
                auth_admin.session.auth.admin.update_user_by_id(
                    new_uid, 
                    attributes={"user_metadata": {
                        "full_name": user.nome_completo,
                        "display_name": user.nome_completo,
                        "celular": user.celular
                    }}
                )
            except Exception as e:
                logger.warning(f"Usuário criado, mas falha ao sincronizar metadata: {str(e)}")
            
            return {"status": "success", "user_id": new_uid}
    except Exception as e:
        logger.error(f"Erro ao criar usuário admin: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/users/{user_id}")
async def update_user(user_id: str, data: dict):
    """Atualiza ou cria (upsert) dados do perfil de um usuário"""
    try:
        # Permitir apenas campos específicos
        safe_fields = ["nome_completo", "cargo", "acessos", "ativo", "email", "hospital", "unidade", "registro_profissional", "celular"]
        payload = {k: v for k, v in data.items() if k in safe_fields}
        
        if not payload:
            return {"status": "ignored", "message": "Nenhum campo válido."}
        
        # Garante o ID no payload para o upsert funcionar como esperado
        payload["id"] = user_id
        payload["updated_at"] = datetime.now().isoformat()
            
        res = db.table("perfis").upsert(payload).execute()
        
        # Sincronizar nome e celular com Auth metadata se fornecidos
        meta = {}
        if "nome_completo" in payload:
            meta["full_name"] = payload["nome_completo"]
            meta["display_name"] = payload["nome_completo"]
        if "celular" in payload:
            meta["celular"] = payload["celular"]
            
        if meta:
            try:
                auth_admin.session.auth.admin.update_user_by_id(
                    user_id, 
                    attributes={"user_metadata": meta}
                )
            except Exception as e:
                logger.warning(f"Perfil atualizado, mas erro ao sincronizar Auth: {str(e)}")
                
        return {"status": "success", "data": res.data}
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil (upsert): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    """Remove o usuário da tabela perfis e do db Auth"""
    try:
        # 1. Remover da tabela perfis
        db.table("perfis").delete().eq("id", user_id).execute()
        
        # 2. Remover do db Auth (Admin)
        try:
            auth_admin.delete_user_admin(user_id)
        except Exception as auth_err:
            logger.warning(f"Usuário removido da tabela, mas erro ao apagar do Auth: {str(auth_err)}")
        
        return {"status": "success", "message": "Usuário excluído com sucesso."}
    except Exception as e:
        logger.error(f"Erro ao deletar usuário: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Redireciona o acesso da raiz para a pagina de login"""
    return RedirectResponse(url="/login.html")

import traceback

@app.get("/api/Dados/dashboard")
async def get_dashboard_data(unit: str = "TODAS", month: str = "TODOS", year: str = "TODOS"):
    try:
        data = await fetch_all_registros_from_db()
        if not data:
            return {
                "filters": {"units": [], "months": [], "years": []}, 
                "moments": [], 
                "categories": [], 
                "timeline": [], 
                "units": []
            }
            
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
        raise HTTPException(status_code=500, detail="Erro interno ao processar dados vivos do db.")

@app.get("/api/Dados/tabulation")
async def get_tabulation():
    try:
        data = await fetch_all_registros_from_db(force_refresh=True)
        return data
    except Exception as e:
        logger.error(f"Erro na tabulação: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro interno ao carregar tabulação de dados.")

@app.get("/api/Dados/validations")
async def get_validations():
    """Retorna as listas oficiais diretamente do db (Sync Realtime)"""
    try:
        data = await fetch_all_registros_from_db()
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
    """Força sincronização total com db"""
    try:
        await fetch_all_registros_from_db(force_refresh=True)
        return {"status": "success", "message": "Sincronização concluída."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/Dados/pivot")
async def get_pivot():
    try:
        data = await fetch_all_registros_from_db()
        if not data:
            return []
            
        df = pd.DataFrame(data)
        
        # Gerar Pivot Table: Unidade vs Momento Auditado (Volume)
        # Bate com a lógica da Tabela Dinâmica do sistema original
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
    try:
        # 1. Busca todos os usuários reais do db Auth
        auth_users = auth_admin.list_users_admin()
        
        # 2. Busca todos os perfis configurados na tabela
        profiles_res = db.table("perfis").select("*").execute()
        profiles_map = {p["id"]: p for p in profiles_res.data}
        
        # 3. Faz o Merge e Filtro
        final_list = []
        for u in auth_users:
            # FILTRO DE SEGURANÇA: Omitir conta Dev Master conforme solicitado
            if u.email == "dev_master@serialaudit.com":
                continue
                
            p = profiles_map.get(u.id, {})
            final_list.append({
                "id": u.id,
                "email": u.email,
                "nome_completo": p.get("nome_completo") or u.user_metadata.get("nome_completo") or "Usuário Pendente",
                "cargo": p.get("cargo") or "user",
                "acessos": p.get("acessos") or ["registro"],
                "sincronizado": u.id in profiles_map
            })
            
        return sorted(final_list, key=lambda x: x["nome_completo"])
    except Exception as e:
        logger.error(f"Erro ao listar usuários sincronizados: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro de Identidade: {str(e)}")

# --- LISTAR REGISTROS (GET /api/registros) ---
@app.get("/api/registros")
async def list_registros():
    """Retorna todos os registros em formato bruto para a tabulação"""
    try:
        data = await fetch_all_registros_from_db()
        return data
    except Exception as e:
        logger.error(f"Erro ao listar registros: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar dados do banco.")

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
    db.table("perfis").insert(profile_data).execute()
    return {"status": "success"}

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str):
    db.table("perfis").delete().eq("id", user_id).execute()
    auth_admin.delete_auth_user(user_id)
    return {"status": "success"}

@app.get("/api/user/profile")
async def get_profile(user_id: str = None):
    if not user_id:
        raise HTTPException(status_code=400, detail="ID de usuário não fornecido.")
    profile = db.table("perfis").select("*").eq("id", user_id).single().execute()
    return profile.data

@app.post("/api/user/update")
async def update_user_profile(data: dict):
    """Atualiza perfil e senha (se fornecido) de forma sincronizada"""
    try:
        user_id = data.get("user_id")
        if not user_id: raise HTTPException(status_code=400, detail="User ID obrigatório")
        
        # 1. Se houver nova senha, atualizar no db Auth
        new_password = data.get("password")
        if new_password:
            auth_admin.db_admin.auth.admin.update_user_by_id(
                user_id, 
                {"password": new_password}
            )
            
        # 2. Atualizar ou Inserir na tabela de Perfis (Upsert)
        profile_data = {
            "id": user_id,
            "nome_completo": data.get("nome_completo"),
            "cargo": data.get("cargo"),
            "acessos": data.get("acessos", ["dashboard"])
        }
        
        # Tenta atualizar
        res = db.table("perfis").update(profile_data).eq("id", user_id).execute()
        
        # Se não existia o perfil (Pending), insere agora
        if not res.data:
            db.table("perfis").insert(profile_data).execute()
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil sincronizado: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        db.table("registros").insert(payload).execute()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Erro ao salvar registro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/registros/{reg_id}")
async def delete_registro(reg_id: str):
    """Exclui uma auditoria específica pelo ID único"""
    try:
        db.table("registros").delete().eq("id", reg_id).execute()
        return {"status": "success", "message": "Registro excluído com sucesso."}
    except Exception as e:
        logger.error(f"Erro ao excluir registro: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao excluir registro do banco.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
