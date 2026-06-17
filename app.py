from __future__ import annotations

import pandas as pd
import streamlit as st

from config.caronas_config import (
    CONTAS,
    DESTINOS,
    DESTINOS_IGNORADOS,
    IDENTIFICADORES_BLOQUEADOS,
    ORIGENS,
    PUBLIC_CARPOOL_ENTRYPOINT,
    STATUS_NAO_VALIDADO,
)
from database.db import init_db
from database.repository import list_recent_scans, save_scan
from rules.agenda import listar_padrao_logistico
from rules.datas_operacionais import gerar_datas_operacionais
from rules.eventos_regionais import normalizar_eventos
from services.public_scan_service import analisar_busca_publica_por_data
from services.scan_service import analisar_arquivo_mhtml

st.set_page_config(page_title="Rota Cheia", page_icon="car", layout="wide")

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


def render_concorrencia(concorrencia: dict) -> None:
    st.subheader("Scanner da concorrência")
    precos = concorrencia.get("precos") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Preço médio", precos.get("preco_medio") or "não detectado")
    c2.metric("Menor preço", precos.get("preco_minimo") or "não detectado")
    c3.metric("Maior preço", precos.get("preco_maximo") or "não detectado")

    horarios = concorrencia.get("horarios_mais_fortes") or []
    destinos = concorrencia.get("destinos_mais_cotados") or []
    cheios = concorrencia.get("motoristas_mais_cheios") or []

    if horarios:
        st.markdown("**Horários mais fortes**")
        st.dataframe(pd.DataFrame(horarios), use_container_width=True)
    else:
        st.warning("Nenhum horário forte detectado ainda.")

    if destinos:
        st.markdown("**Destinos mais cotados**")
        st.dataframe(pd.DataFrame(destinos), use_container_width=True)
    else:
        st.warning("Nenhum destino cotado detectado ainda.")

    if cheios:
        st.markdown("**Motoristas com carros mais cheios**")
        st.dataframe(pd.DataFrame(cheios), use_container_width=True)
    else:
        st.warning("Nenhum carro cheio/quase cheio detectado ainda.")


def render_falha_controlada(exc: Exception) -> None:
    st.error(STATUS_NAO_VALIDADO)
    st.warning(f"Falha técnica controlada: {exc}")
    st.info("Use a aba Fallback Técnico com o arquivo .mht/.mhtml salvo da busca pública por rota + data.")


st.title("Rota Cheia")
st.caption("Inteligência de captação de passageiros para escolher datas, horários e validar concorrência pública.")

with st.sidebar:
    st.header("Regras fixas")
    st.warning(f"Sem validação pública por rota + data: {STATUS_NAO_VALIDADO}")
    st.markdown(f"**Ponto inicial:** [{PUBLIC_CARPOOL_ENTRYPOINT}]({PUBLIC_CARPOOL_ENTRYPOINT})")
    st.markdown("**Contas:** " + ", ".join(CONTAS))
    st.markdown("**Não usar como nome:** " + ", ".join(IDENTIFICADORES_BLOQUEADOS))
    st.markdown("**Ignorar:** " + ", ".join(DESTINOS_IGNORADOS))

aba_cap, aba_scan, aba_fallback, aba_agenda, aba_historico = st.tabs(
    ["Inteligência de Captação", "Scanner da Data Escolhida", "Fallback Técnico", "Agenda", "Histórico"]
)

with aba_cap:
    st.header("Inteligência de Captação")
    st.info("Informe origem e destino. O sistema gera datas futuras e pontua as melhores oportunidades antes da validação pública.")

    col1, col2 = st.columns(2)
    with col1:
        origem_cap = st.selectbox("Origem", list(ORIGENS), key="origem_cap")
        destino_cap = st.selectbox("Destino", list(DESTINOS), key="destino_cap")
        semanas = st.slider("Semanas futuras", min_value=1, max_value=12, value=3)
    with col2:
        incluir_sabado = st.checkbox("Incluir sábado à noite se houver evento/demanda", value=False)
        assentos_cap = st.number_input("Assentos para simular", min_value=1, max_value=4, value=1, step=1, key="assentos_cap")

    st.markdown("**Eventos regionais opcionais**")
    eventos_txt = st.text_area(
        "Um evento por linha: nome | cidade | data | peso",
        placeholder="Festival X | São Tomé das Letras | 2026-07-10 | 40",
    )
    eventos = []
    for linha in eventos_txt.splitlines():
        partes = [p.strip() for p in linha.split("|")]
        if len(partes) >= 3:
            eventos.append(
                {
                    "nome": partes[0],
                    "cidade": partes[1],
                    "data": partes[2],
                    "peso": partes[3] if len(partes) > 3 else 20,
                    "fonte": "entrada do operador",
                }
            )

    datas = gerar_datas_operacionais(
        origem_ida=origem_cap,
        destino_ida=destino_cap,
        semanas=int(semanas),
        incluir_sabado=bool(incluir_sabado),
        assentos=int(assentos_cap),
        eventos_regionais=normalizar_eventos(eventos),
        localidades_eventos=[origem_cap, destino_cap],
    )
    st.dataframe(pd.DataFrame(datas), use_container_width=True)
    st.session_state["datas_sugeridas"] = datas

with aba_scan:
    st.header("Scanner da Data Escolhida")
    st.info("Escolha uma data sugerida e execute o scanner público. A ação operacional só aparece após validação por rota + data.")

    sugestoes = st.session_state.get("datas_sugeridas") or []
    opcoes = [f"{i + 1}. {d['data']} | {d['sentido']} | {d['horario']} | {d['origem']} -> {d['destino_final']}" for i, d in enumerate(sugestoes)]
    escolha = st.selectbox("Data sugerida", opcoes) if opcoes else None
    conta_scan = st.selectbox("Conta analisada", list(CONTAS), key="conta_scan")
    salvar_scan = st.checkbox("Salvar scanner no histórico", value=True)

    if escolha and st.button("Executar scanner público", type="primary"):
        idx = int(escolha.split(".", 1)[0]) - 1
        item = sugestoes[idx]
        try:
            resultado = analisar_busca_publica_por_data(
                origem=item["origem"],
                destino=item["destino_final"],
                data_viagem=item["data"],
                conta=conta_scan,
                sentido=item["sentido"],
                horario_planejado=item["horario"],
                assentos=int(assentos_cap),
            )
            validacao = resultado["validacao"]
            if validacao.get("valido"):
                st.success(validacao.get("status"))
            else:
                st.error(validacao.get("status"))
                if validacao.get("motivos"):
                    st.write("Motivos:", ", ".join(validacao.get("motivos")))

            render_concorrencia(resultado["concorrencia"])
            render_decisao(resultado["decisao"])

            if salvar_scan:
                scan_id = save_scan(resultado["scan"], resultado["motoristas"], resultado["decisao"])
                st.success(f"Scanner salvo no histórico com ID {scan_id}.")
        except Exception as exc:
            render_falha_controlada(exc)
    elif not escolha:
        st.warning("Gere as datas na aba Inteligência de Captação primeiro.")

with aba_fallback:
    st.header("Fallback Técnico")
    st.info("Use esta aba somente quando o scanner público automático não conseguir ler a página. Não faz parte do fluxo principal.")

    col1, col2 = st.columns(2)
    with col1:
        origem_fb = st.selectbox("Origem esperada", list(ORIGENS), key="origem_fb")
        destino_fb = st.selectbox("Destino final esperado", list(DESTINOS), key="destino_fb")
        data_fb = st.date_input("Data exata", key="data_fb")
    with col2:
        conta_fb = st.selectbox("Conta", list(CONTAS), key="conta_fb")
        sentido_fb = st.selectbox("Sentido", SENTIDOS, key="sentido_fb")
        horario_fb = st.text_input("Horário planejado", key="horario_fb")

    arquivo_fb = st.file_uploader("Arquivo técnico salvo da busca pública", type=["mhtml", "mht"])
    if st.button("Analisar fallback técnico", disabled=arquivo_fb is None):
        try:
            resultado = analisar_arquivo_mhtml(
                raw_bytes=arquivo_fb.getvalue(),
                arquivo_nome=arquivo_fb.name,
                origem_esperada=origem_fb,
                destino_esperado=destino_fb,
                data_esperada=data_fb.isoformat(),
                conta=conta_fb,
                sentido=sentido_fb,
                horario_planejado=horario_fb or None,
                link_publico_manual=None,
            )
            render_concorrencia(resultado["concorrencia"])
            render_decisao(resultado["decisao"])
        except Exception as exc:
            render_falha_controlada(exc)

with aba_agenda:
    st.header("Agenda operacional padrão")
    st.dataframe(pd.DataFrame(listar_padrao_logistico()), use_container_width=True)

with aba_historico:
    st.header("Histórico de scans")
    linhas = list_recent_scans()
    if linhas:
        st.dataframe(pd.DataFrame(linhas), use_container_width=True)
    else:
        st.warning("Nenhum scan salvo ainda.")
