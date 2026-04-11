import os

target_dir = r"c:\Projetos\Hospital\HM_CONTROL\app-client"

injection = """            <div class="nav-dropdown">
                <a href="javascript:void(0)" class="nav-link"><i class="fas fa-cogs"></i> CONFIGURAÇÕES</a>
                <div class="nav-dropdown-content">
                    <a href="/configuracoes.html#sistema"><i class="fas fa-server"></i> Sistema</a>
                    <a href="/configuracoes.html#usuarios"><i class="fas fa-users-cog"></i> Usuários</a>
                    <a href="/configuracoes.html#logs"><i class="fas fa-clipboard-list"></i> Logs</a>
                </div>
            </div>
        </nav>"""

for f in os.listdir(target_dir):
    if f.endswith(".html"):
        path = os.path.join(target_dir, f)
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
            
        modified = False
        
        if '<div class="nav-dropdown">' not in content:
            # We want to replace the FIRST </nav> inside <nav class="nav-links">
            content = content.replace("        </nav>", injection)
            modified = True
            
        if modified:
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            print(f"Updated {f}")
        else:
            print(f"Skipped {f}")
