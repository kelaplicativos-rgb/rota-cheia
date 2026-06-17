from __future__ import annotations

import pandas as pd
import streamlit as st

from config.caronas_config import (
    CAMPOS_SCAN_PUBLICO,
    CONTAS,
    DESTINOS,
    DESTINOS_IGNORADOS,
    FLUXO_SEGURO_APK,
    IDENTIFICADORES_BLOQUEADOS,
    ORIGENS,
    PUBLIC_CARPOOL_ENTRYPOINT,
    STATUS_NAO_VALIDADO,
    gerar_link_busca_publica,
)
from database.db import init_db
from database.repository import list_recent_scans, save_scan
from rules.agenda import listar_padrao_logistico
from services.scan_service import analisar_arquivo_mhtml

st.set_page_config(page_title="Rota Cheia", page_icon="🚗", layout="wide")

init_db()

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
    st.warning(f"Sem busca pública por rota + data validada, o app retorna: {STATUS_NAO_VALIDADO}.")
    st.markdown(f"**Ponto inicial fixo:** [{PUBLIC_CARPOOL_ENTRYPOINT}]({PUBLIC_CARPOOL_ENTRYPOINT})")
    st.markdown("**Identificadores válidos:** " + ", ".join(CONTAS))
    st.markdown("**Nunca usar:** " + ", ".join(IDENTIFICADORES_BLOQUEADOS))
    st.markdown("**Ignorar:** " + ", ".join(DESTINOS_IGNORADOS))

aba_scan, aba_config, aba_agenda, aba_historico = st.tabs(["Nova análise", "Configuração", "Agenda", "Histórico"])

with aba_scan:
    st.header("Nova análise BlaBlaCar")
    st.info("Fluxo seguro: abra a busca pública gerada, valide rota + data exata, salve a página em .mhtml/.mht e envie aqui.")

    col1, col2 = st.columns(2)

    with col1:
        origem = st.selectbox("Origem esperada", list(ORIGENS))
        destino = st.selectbox("Destino final esperado", list(DESTINOS))
        data_viagem = st.date_input("Data exata da viagem")
        sentido = st.selectbox("Sentido", SENTIDOS)

    with col2:
        conta = st.selectbox("Conta analisada", list(CONTAS))
        horario_planejado = st.text_input("Horário planejado", placeholder="Ex.: 17:30, 20:30 ou 11:00")
        assentos = st.number_input("Assentos na busca pública", min_value=1, max_value=4, value=1, step=1)
        salvar_historico = st.checkbox("Salvar no histórico", value=True)

    link_gerado = gerar_link_busca_publica(origem, destino, data_viagem, int(assentos))
    st.subheader("Busca pública obrigatória")
    st.markdown(f"1. Abra o ponto inicial: [{PUBLIC_CARPOOL_ENTRYPOINT}]({PUBLIC_CARPOOL_ENTRYPOINT})")
    st.markdown(f"2. Use esta busca por rota + data exata: [abrir busca pública gerada]({link_gerado})")
    st.code(link_gerado, language="text")

    link_manual = st.text_input(
        "Link público validado da busca",
        value=link_gerado,
        placeholder="https://www.blablacar.com.br/search?...",
        help="Use o link público da busca por rota + data. Ele ajuda quando o arquivo MHTML não preserva a URL.",
    )

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
                link_publico_manual=link_manual or None,
            )

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

with aba_config:
    st.header("Configuração segura baseada no aplicativo")
    st.info(
        "O APK serve como referência de telas e campos do fluxo. O Rota Cheia não usa token, login, pagamento ou API privada; a validação continua sendo pela busca pública."
    )

    st.subheader("Fluxo aplicado no sistema")
    st.dataframe(pd.DataFrame(FLUXO_SEGURO_APK), use_container_width=True)

    st.subheader("Campos que o scanner deve capturar")
    st.dataframe(pd.DataFrame(CAMPOS_SCAN_PUBLICO), use_container_width=True)

    st.subheader("Rotas operacionais")
    st.dataframe(
        pd.DataFrame(
            {
                "origens": list(ORIGENS) + ["" for _ in range(max(0, len(DESTINOS) - len(ORIGENS)))],
                "destinos": list(DESTINOS),
            }
        ),
        use_container_width=True,
    )

    st.subheader("Bloqueios fixos")
    st.code(
        "\n".join(
            [
                f"status sem validação: {STATUS_NAO_VALIDADO}",
                "identificadores válidos: " + ", ".join(CONTAS),
                "identificadores proibidos: " + ", ".join(IDENTIFICADORES_BLOQUEADOS),
                "destinos ignorados: " + ", ".join(DESTINOS_IGNORADOS),
            ]
        ),
        language="text",
    )

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
