from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

BUILD_ID = "rota-cheia-main-2026-06-18-1450-b3"
REPO_CORRETO = "kelaplicativos-rgb/rota-cheia"
BRANCH_CORRETA = "main"
APP_URL = "https://rota-cheia.streamlit.app/"

st.set_page_config(page_title="Status do Deploy", page_icon="✅", layout="centered")

st.title("✅ Status do Deploy")
st.success("Esta página foi criada diretamente no repositório correto do Rota Cheia.")

st.markdown(
    f"""
### Confirmação técnica

- **App:** `{APP_URL}`
- **Repositório correto:** `{REPO_CORRETO}`
- **Branch correta:** `{BRANCH_CORRETA}`
- **Build ID:** `{BUILD_ID}`
- **Criado em UTC:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}`

### Como interpretar

Se esta página aparecer no menu lateral do Streamlit, o deploy está puxando o repositório correto.

Se esta página não aparecer, então o Streamlit Cloud ainda está apontando para outro repositório, outro branch, outro arquivo principal, ou está preso em deploy antigo/cache.
"""
)

st.info("Use esta página como prova visual rápida de que o app publicado refletiu o commit mais recente do GitHub.")
