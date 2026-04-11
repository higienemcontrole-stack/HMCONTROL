# 🏥 HM CONTROL 2.0 — Portal de Auditoria Hospitalar

**HM CONTROL** é uma solução SaaS premium para gestão e auditoria de Higiene de Mãos (HM), projetada para substituir fluxos manuais de Excel por uma interface moderna, rápida e orientada a dados.

![Versão](https://img.shields.io/badge/Vers%C3%A3o-2.1.0--Hardened-blue)
![Status](https://img.shields.io/badge/Status-Est%C3%A1vel-success)

---

## 🚀 Visão Geral
O sistema foi reconstruído em 2026 para oferecer uma experiência "Excel Twin", onde toda a inteligência e cálculos complexos de auditoria são processados no backend, enquanto o frontend oferece uma interface extremamente ágil e visual.

### Principais Destaques:
- **Dashboard de Alta Performance**: Gráficos dinâmicos que refletem os indicadores hospitalares instantaneamente.
- **Registro Estilo Mobile App**: Uma interface otimizada para tablets e celulares, facilitando a coleta de dados à beira do leito.
- **Centro de Controle Administrativo**: Painel central para gestão de usuários, auditoria de logs e sincronização de dados.
- **Segurança Enterprise**: Integração com Supabase Auth e RLS (Row Level Security).

---

## 🏗️ Arquitetura do Sistema

O projeto é dividido em dois grandes pilares:

1.  **`app-client/`**: Frontend estático (HTML5/Vanilla CSS/JavaScript) focado em performance e design "Hospitalar Premium".
2.  **`server_api/`**: Backend em Python (FastAPI) que atua como o motor lógico, integrando dados do Excel com o banco de dados Supabase.

---

## 🛠️ Como Iniciar

### 1. Pré-requisitos
- Python 3.10+
- Acesso ao projeto no Supabase (URL e chaves API).

### 2. Rodar o Backend
```bash
cd server_api
pip install -r requirements.txt
python main.py
```
O servidor iniciará em `http://localhost:8005`.

### 3. Acessar o Frontend
Basta abrir o arquivo `app-client/login.html` no navegador ou, se estiver rodando o backend, acesse diretamente `http://localhost:8005/`.

---

**Desenvolvido por Paulo Ramiro — 2026**
