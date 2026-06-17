from __future__ import annotations

import pandas as pd
import streamlit as st

from database.db import init_db
from database.repository import list_recent_scans, save_scan
from rules.agenda import listar_padrao_logistico
from services.scan_service import analisar_arquivo_mhtml

st.set_page_config(page_title="Rota Cheia", page_icon="🚗", layout="wide")

init_db()

ORIGENS = [
    "Santo André, SP, Brasil",
    "São Paulo, SP, Brasil",
]

DESTINOS = [
    "Extrema, MG, Brasil",
    "Pouso Alegre, MG, Brasil",
    "Três Corações, MG, Brasil",
    "Varginha, MG, Brasil",
    "São Tomé das Letras, MG, Brasil",
    "Cambuquira, MG, Brasil",
    "Campanha, MG, Brasil",
]

CONTAS = ["Ezequiel S", "Barbosa"]
SENTIDOS = ["IDA", "VOLTA"]


def render_decisao(decisao: dict) -> None:
    st.subheader("Resultado operacional")
    st.code(
        "\n".join(
            [
                f"ação: {decisao.get('acao')}",
                f"conta: {decisao.get('conta')}",
                f"origem: {decisao.get('origem')}",
                f"destino final: {decisao.get('destino_final')}",
                f"intermediárias: {decisao.get('intermediarias')}",
                f"data: {decisao.get('data')}",
                f"horário: {decisao.get('horario')}",
                f"preço sugerido: {decisao.get('preco_sugerido')}",
                f"risco de conflito: {decisao.get('risco_conflito')}",
                f"status de validação: {decisao.get('status_validacao')}",
            ]
        ),
        language="text",
    )
    if decisao.get("motivo"):
        st.info(decisao.get("motivo"))


st.title("🚗 Rota Cheia")
st.caption("Assistente de caronas para validar, organizar e evitar duplicidade antes de publicar.")

with st.sidebar:
    st.header("Regra obrigatória")
    st.warning("Sem busca pública por rota + data validada, o app retorna: não confirmado / busca pública por data não validada.")
    st.markdown("**Identificadores válidos:** Ezequiel S e Barbosa")
    st.markdown("**Ignorar:** Caxambu")

aba_scan, aba_agenda, aba_historico = st.tabs(["Nova análise", "Agenda", "Histórico"])

with aba_scan:
    st.header("Nova análise BlaBlaCar")
    col1, col2 = st.columns(2)

    with col1:
        origem = st.selectbox("Origem esperada", ORIGENS)
        destino = st.selectbox("Destino final esperado", DESTINOS)
        data_viagem = st.date_input("Data exata da viagem")
        sentido = st.selectbox("Sentido", SENTIDOS)

    with col2:
        conta = st.selectbox("Conta analisada", CONTAS)
        horario_planejado = st.text_input("Horário planejado", placeholder="Ex.: 17:30, 20:30 ou 11:00")
        link_manual = st.text_input("Link público da busca, se quiser registrar", placeholder="https://www.blablacar.com.br/search?...")
        salvar_historico = st.checkbox("Salvar no histórico", value=True)

    arquivo = st.file_uploader("Enviar arquivo .mhtml/.mht salvo da busca pública", type=["mhtml", "mht"])

    if st.button("Analisar arquivo", type="primary", disabled=arquivo is None):
        try:
            resultado = analisar_arquivo_mhtml(
                raw_bytes=arquivo.getvalue(),
                arquivo_nome=arquivo.name,
                origem_esperada=origem,
                destino_esperado=destino,
                data_esperada=data_viagem.isoformat(),
                conta=conta,
                sentido=sentido,
                horario_planejado=horario_planejado or None,
            )

            if link_manual and not resultado["scan"].get("link_busca"):
                resultado["scan"]["link_busca"] = link_manual

            validacao = resultado["validacao"]
            if validacao.get("valido"):
                st.success(validacao.get("status"))
            else:
                st.error(validacao.get("status"))
                if validacao.get("motivos"):
                    st.write("Motivos:", ", ".join(validacao.get("motivos")))

            st.subheader("Dados detectados")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Origem", resultado["parsed"].get("origem") or "não detectada")
            col_b.metric("Destino", resultado["parsed"].get("destino") or "não detectado")
            col_c.metric("Data", resultado["parsed"].get("data_viagem") or "não detectada")

            motoristas = resultado.get("motoristas", [])
            st.subheader("Motoristas detectados")
            if motoristas:
                st.dataframe(pd.DataFrame(motoristas), use_container_width=True)
            else:
                st.warning("Nenhum motorista detectado pelo parser inicial.")

            render_decisao(resultado["decisao"])

            if salvar_historico:
                scan_id = save_scan(resultado["scan"], resultado["motoristas"], resultado["decisao"])
                st.success(f"Scan salvo no histórico com ID {scan_id}.")

        except Exception as exc:
            st.exception(exc)

with aba_agenda:
    st.header("Agenda operacional padrão")
    st.dataframe(pd.DataFrame(listar_padrao_logistico()), use_container_width=True)
    st.info("Sábado à noite deve ser usado somente quando a demanda ou evento justificar.")

with aba_historico:
    st.header("Histórico de scans")
    linhas = list_recent_scans()
    if linhas:
        st.dataframe(pd.DataFrame(linhas), use_container_width=True)
    else:
        st.warning("Nenhum scan salvo ainda.")
