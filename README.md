# 🏥 HM CONTROL 2.0 — Portal de Auditoria Hospitalar

**HM CONTROL** é uma solução SaaS premium para gestão e auditoria de Higiene de Mãos (HM), projetada para substituir fluxos manuais por uma interface moderna, rápida e orientada a dados.

![Versão](https://img.shields.io/badge/Vers%C3%A3o-2.1.0--Propriet%C3%A1ria-blue)
![Status](https://img.shields.io/badge/Status-Est%C3%A1vel-success)

---

## 🚀 Visão Geral
O sistema oferece uma experiência integrada onde toda a inteligência e cálculos complexos de auditoria são processados no backend, enquanto o frontend oferece uma interface extremamente ágil e visual.

### Principais Destaques:
- **Dashboard de Alta Performance**: Gráficos dinâmicos que refletem os indicadores hospitalares instantaneamente.
- **Registro Estilo Mobile App**: Uma interface otimizada para tablets e celulares, facilitando a coleta de dados à beira do leito.
- **Centro de Controle Administrativo**: Painel central para gestão de usuários, auditoria de logs e sincronização de dados.
- **Segurança Enterprise**: Camada de proteção avançada com autenticação segura e isolamento de dados por perfil (RLS).

---

## 🏗️ Arquitetura do Sistema

O projeto é dividido em dois grandes pilares:

1.  **`public/`**: Frontend estático (HTML5/Vanilla CSS/JavaScript) focado em performance e design "Hospitalar Premium".
2.  **`server_api/`**: Backend em Python (FastAPI) que atua como o motor lógico e integrador de dados.

---

## 🛠️ Como Iniciar

### 1. Pré-requisitos
- Python 3.10+
- Acesso às credenciais do Servidor de Dados.

### 2. Rodar o Backend
```bash
cd server_api
pip install -r requirements.txt
python main.py
```
O servidor iniciará em `http://localhost:8010`.

### 3. Acessar o Frontend
Basta abrir o arquivo `public/login.html` no navegador ou, se estiver rodando o backend, acesse diretamente `http://localhost:8010/`.

---

**Desenvolvido por Gestão de Qualidade Hospitalar — 2026**
