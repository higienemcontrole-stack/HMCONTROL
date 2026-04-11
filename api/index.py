import sys
import os

# Adiciona a raiz do projeto ao path para encontrar o pacote server_api
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importa o app usando o nome completo do pacote
from server_api.main import app
