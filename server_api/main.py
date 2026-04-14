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
from server_api.models.schemas import (
    UserLogin,
    UserProfileUpdate,
    AdminUserCreate,
    RegistroCreate,
)
import pandas as pd

# Configurações de Ambiente (Vercel Ready)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mapeamento Flexível de Variáveis (Suporta múltiplos padrões de nomeação)
DB_URL = (
    os.environ.get("DB_URL")
    or os.environ.get("SUPABASE_URL")
    or os.environ.get("API_URL")
)
SERVICE_KEY = (
    os.environ.get("DB_SERVICE_KEY")
    or os.environ.get("SUPABASE_SERVICE_KEY")
    or os.environ.get("service_role_secret")
)
PUBLIC_KEY = (
    os.environ.get("DB_PUBLIC_KEY")
    or os.environ.get("SUPABASE_ANON_KEY")
    or os.environ.get("anon_public")
)

# Fallback para compatibilidade
DB_KEY = SERVICE_KEY or PUBLIC_KEY

if not DB_URL or not DB_KEY:
    logger.error(
        f"ERRO CRÍTICO: Variáveis ausentes. URL: {bool(DB_URL)}, KEY: {bool(DB_KEY)}, SERVICE: {bool(SERVICE_KEY)}"
    )

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


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.1.0"}


@app.get("/api/status")
async def status():
    db_ok = False
    db_url_present = bool(DB_URL)
    service_key_present = bool(SERVICE_KEY)
    public_key_present = bool(PUBLIC_KEY)
    try:
        # Testa conexão real com o banco
        test = db.table("perfis").select("id").limit(1).execute()
        db_ok = True
    except Exception as e:
        db_ok = False
    return {
        "db_connected": db_ok,
        "db_url_present": db_url_present,
        "service_key_present": service_key_present,
        "public_key_present": public_key_present,
        "env_vars_ok": db_url_present and (service_key_present or public_key_present),
    }


# --- CACHE DE DADOS db ---
GLOBAL_DATA_CACHE = {"records": [], "last_sync": None}


async def fetch_all_registros_from_db(force_refresh=False):
    global GLOBAL_DATA_CACHE
    now = datetime.now()

    # Cache de 30 segundos para performance no dashboard
    if (
        not force_refresh
        and GLOBAL_DATA_CACHE["last_sync"]
        and (now - GLOBAL_DATA_CACHE["last_sync"]).seconds < 30
    ):
        return GLOBAL_DATA_CACHE["records"]

    try:
        all_registros = []
        offset = 0
        while True:
            # Busca em blocos de 1000 (limite do db)
            chunk = (
                db.table("registros")
                .select("*")
                .order("created_at", desc=True)
                .range(offset, offset + 999)
                .execute()
            )
            if not chunk.data:
                break
            all_registros.extend(chunk.data)
            offset += 1000
            if len(chunk.data) < 1000:
                break

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
        res = db.auth.sign_in_with_password(
            {"email": credentials.email, "password": credentials.password}
        )

        # Buscar profile na tabela profiles (ou view perfis)
        try:
            profile_res = (
                db.table("perfis").select("*").eq("id", res.user.id).single().execute()
            )
            profile = profile_res.data or {}
        except Exception:
            profile = {}

        # Montar objeto user unificado com campos do profile
        # O frontend salva este objeto inteiro no localStorage como 'hm_user'
        user_obj = {
            "id": res.user.id,
            "email": res.user.email,
            # Campos normalizados que o frontend (core.js) espera
            "nome_completo": profile.get("nome_completo")
            or profile.get("full_name")
            or res.user.user_metadata.get("full_name", ""),
            "cargo": profile.get("cargo") or profile.get("role") or "user",
            "acessos": profile.get("acessos") or [],
            "ativo": profile.get("ativo", True),
            # Metadados extras
            "created_at": str(res.user.created_at) if res.user.created_at else None,
        }

        return {"session": res.session, "user": user_obj, "profile": profile}
    except Exception as e:
        logger.error(
            f"Erro no login para {credentials.email}: {str(e)}\n{traceback.format_exc()}"
        )
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
            return {
                "status": "error",
                "message": "Variaveis ADMIN_EMAIL/PASSWORD ausentes na Vercel.",
            }

        try:
            auth_admin.create_user_admin(email, password, {"full_name": "Dev Master"})
        except:
            pass

        prof_data = {
            "nome_completo": "Dev Master",
            "email": email,
            "cargo": "admin",
            "acessos": [
                "dashboard",
                "registro",
                "tabulacao",
                "dinamica",
                "validacoes",
                "configuracoes",
            ],
        }
        profiles = db.table("perfis").select("id").eq("email", email).execute()
        if len(profiles.data) > 0:
            db.table("perfis").update(prof_data).eq(
                "id", profiles.data[0]["id"]
            ).execute()
            return {"status": "success", "message": "Resgate concluido."}
        return {
            "status": "partial",
            "message": "Usuario Auth criado. Logue para ativar perfil.",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/")
async def root():
    """Redireciona o acesso da raiz para a pagina de login"""
    return RedirectResponse(url="/login.html")


import traceback


@app.get("/api/Dados/dashboard")
async def get_dashboard_data(
    unit: str = "TODAS", month: str = "TODOS", year: str = "TODOS"
):
    try:
        data = await fetch_all_registros_from_db()
        if not data:
            return {
                "filters": {"units": [], "months": [], "years": []},
                "moments": [],
                "categories": [],
                "timeline": [],
                "units": [],
            }

        df = pd.DataFrame(data)

        # Filtros Dinâmicos
        all_units = sorted(df["unidade"].unique().tolist())
        all_years = sorted(df["ano"].unique().tolist())
        all_months = [
            "jan",
            "fev",
            "mar",
            "abr",
            "mai",
            "jun",
            "jul",
            "ago",
            "set",
            "out",
            "nov",
            "dez",
        ]

        # Aplicar Filtros selecionados
        temp_df = df.copy()
        if unit != "TODAS":
            temp_df = temp_df[temp_df["unidade"] == unit]
        if month != "TODOS":
            temp_df = temp_df[temp_df["mes"] == month]
        if year != "TODOS":
            temp_df = temp_df[temp_df["ano"] == year]

        # Agregadores para o Dashboard (Volume de Monitoramento)
        def get_chart_data(group_col):
            if temp_df.empty:
                return []
            counts = temp_df.groupby(group_col).size().reset_index(name="total")
            counts.columns = ["label", "total"]
            return counts.sort_values(by="total", ascending=False).to_dict(
                orient="records"
            )

        return {
            "filters": {"units": all_units, "months": all_months, "years": all_years},
            "moments": get_chart_data("momento_auditado"),
            "categories": get_chart_data("profissional_auditado"),
            "timeline": get_chart_data("mes"),
            "units": get_chart_data("unidade"),
        }
    except Exception as e:
        logger.error(f"Erro no dashboard purificado: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="Erro interno ao processar dados vivos do db."
        )


@app.get("/api/Dados/tabulation")
async def get_tabulation():
    try:
        data = await fetch_all_registros_from_db(force_refresh=True)
        return data
    except Exception as e:
        logger.error(f"Erro na tabulação: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="Erro interno ao carregar tabulação de dados."
        )


@app.get("/api/Dados/validations")
async def get_validations():
    """Retorna as listas oficiais diretamente do db (Sync Realtime)"""
    try:
        data = await fetch_all_registros_from_db()
        df = pd.DataFrame(data)

        # Extrai valores únicos existentes no banco como verdade absoluta
        return {
            "unidades": sorted(df["unidade"].unique().tolist())
            if not df.empty
            else ["Enf A", "Enf B", "UTI"],
            "profissionais": sorted(df["profissional_auditado"].unique().tolist())
            if not df.empty
            else ["Médico", "Enfermeiro", "Técnico"],
            "momentos": [
                "1 - Antes de contato com o paciente",
                "2 - Antes de procedimento asséptico",
                "3 - Após risco de exposição a fluidos",
                "4 - Após contato com o paciente",
                "5 - Após contato com áreas próximas",
            ],
            "produtos": sorted(df["produto_utilizado"].unique().tolist())
            if not df.empty
            else ["Álcool Gel", "Sabonete"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao sincronizar listas: {str(e)}"
        )


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
            margins_name="Total Geral",
        ).reset_index()

        # Converter para lista de dicionários para o frontend
        return pivot.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Erro no pivot purificado: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Erro interno ao gerar Tabela Dinâmica do banco."
        )


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
            final_list.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "nome_completo": p.get("nome_completo")
                    or u.user_metadata.get("nome_completo")
                    or "Usuário Pendente",
                    "cargo": p.get("cargo") or "user",
                    "acessos": p.get("acessos") or ["registro"],
                    "sincronizado": u.id in profiles_map,
                }
            )

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
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID obrigatório")

        # 1. Se houver nova senha, atualizar no db Auth
        new_password = data.get("password")
        if new_password:
            auth_admin.db_admin.auth.admin.update_user_by_id(
                user_id, {"password": new_password}
            )

        # 2. Atualizar ou Inserir na tabela de Perfis (Upsert)
        profile_data = {
            "id": user_id,
            "nome_completo": data.get("nome_completo"),
            "cargo": data.get("cargo"),
            "acessos": data.get("acessos", ["dashboard"]),
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
        meses_map = {
            1: "jan",
            2: "fev",
            3: "mar",
            4: "abr",
            5: "mai",
            6: "jun",
            7: "jul",
            8: "ago",
            9: "set",
            10: "out",
            11: "nov",
            12: "dez",
        }
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
            "horario_envio": datetime.now().strftime("%H:%M:%S"),
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
        raise HTTPException(
            status_code=500, detail="Erro ao excluir registro do banco."
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
