import os
from dotenv import load_dotenv
from db import create_client, Client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "config", ".env"))

DB_URL = os.getenv("DB_URL")
DB_KEY = os.getenv("DB_SERVICE_KEY")

db = create_client(DB_URL, DB_KEY)

accounts = [
    {
        "email": "dev_master@serialaudit.com",
        "password": "HM_Control_2026!#",
        "cargo": "admin",
        "nome_completo": "Dev Master"
    },
    {
        "email": "julia.bsilva@ibcc.org.br",
        "password": "Juliabsilva123",
        "cargo": "admin",
        "nome_completo": "Julia B Silva"
    }
]

for acc in accounts:
    try:
        # get user id by email (requires list users or creating if not exists)
        # we can use admin API
        users_res = db.auth.admin.list_users()
        target_user = None
        for u in users_res:
            if u.email == acc["email"]:
                target_user = u
                break
        
        if not target_user:
            print(f"User {acc['email']} not found, attempting to create...")
            new_user = db.auth.admin.create_user({
                "email": acc["email"],
                "password": acc["password"],
                "email_confirm": True
            })
            target_user = new_user.user
            print(f"Created user {acc['email']} with ID: {target_user.id}")
        else:
            print(f"Updating user {acc['email']} (ID: {target_user.id}) password...")
            db.auth.admin.update_user_by_id(target_user.id, {"password": acc["password"]})
        
        # Now update profile table
        prof_data = {
            "id": target_user.id,
            "cargo": acc["cargo"],
            "acessos": ["dashboard", "registro", "tabulacao", "dinamica", "validacoes", "configuracoes"] # all access
        }
        
        # Check if profile exists
        prof_res = db.table("perfis").select("*").eq("id", target_user.id).execute()
        if len(prof_res.data) > 0:
            db.table("perfis").update(prof_data).eq("id", target_user.id).execute()
            print(f"Updated profile for {acc['email']}")
        else:
            prof_data["nome_completo"] = acc["nome_completo"]
            prof_data["email"] = acc["email"]
            db.table("perfis").insert(prof_data).execute()
            print(f"Created profile for {acc['email']}")
            
    except Exception as e:
        print(f"Error processing {acc['email']}: {e}")

print("Done.")
