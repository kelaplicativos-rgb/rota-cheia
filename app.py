from __future__ import annotations

from html import escape

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

st.set_page_config(page_title="Rota Cheia", page_icon="🚗", layout="wide")

init_db()

SENTIDOS = ["IDA", "VOLTA"]


CSS = """
<style>
:root {
    --rc-bg-0: #050816;
    --rc-bg-1: #0b1020;
    --rc-card: rgba(15, 23, 42, .78);
    --rc-card-2: rgba(30, 41, 59, .72);
    --rc-border: rgba(148, 163, 184, .22);
    --rc-text: #e5e7eb;
    --rc-muted: #94a3b8;
    --rc-accent: #22d3ee;
    --rc-accent-2: #a78bfa;
    --rc-ok: #34d399;
    --rc-warn: #f59e0b;
    --rc-danger: #fb7185;
}
.stApp {
    background:
        radial-gradient(circle at top left, rgba(34, 211, 238, .18), transparent 34rem),
        radial-gradient(circle at top right, rgba(167, 139, 250, .16), transparent 30rem),
        linear-gradient(135deg, var(--rc-bg-0), var(--rc-bg-1) 52%, #111827);
    color: var(--rc-text);
}
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(2, 6, 23, .98), rgba(15, 23, 42, .96));
    border-right: 1px solid var(--rc-border);
}
.rc-hero {
    position: relative;
    padding: 1.2rem 1.25rem;
    border: 1px solid rgba(34, 211, 238, .28);
    border-radius: 26px;
    background:
        linear-gradient(135deg, rgba(34, 211, 238, .14), rgba(167, 139, 250, .10)),
        rgba(15, 23, 42, .76);
    box-shadow: 0 20px 70px rgba(0, 0, 0, .28);
    overflow: hidden;
}
.rc-hero::after {
    content: "";
    position: absolute;
    inset: auto -20% -45% 35%;
    height: 9rem;
    background: radial-gradient(circle, rgba(34, 211, 238, .22), transparent 70%);
}
.rc-title {
    font-size: clamp(2.0rem, 6vw, 4.1rem);
    line-height: .95;
    font-weight: 900;
    letter-spacing: -.07em;
    margin: 0;
}
.rc-subtitle {
    color: var(--rc-muted);
    font-size: 1rem;
    max-width: 800px;
    margin-top: .75rem;
}
.rc-pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: .55rem;
    margin-top: 1rem;
}
.rc-pill {
    border: 1px solid rgba(34, 211, 238, .22);
    background: rgba(8, 47, 73, .46);
    color: #cffafe;
    border-radius: 999px;
    padding: .38rem .7rem;
    font-size: .82rem;
    font-weight: 700;
}
.rc-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .8rem;
    margin: 1rem 0;
}
.rc-card {
    border: 1px solid var(--rc-border);
    border-radius: 22px;
    padding: 1rem;
    background: var(--rc-card);
    box-shadow: 0 16px 45px rgba(0, 0, 0, .20);
}
.rc-card h3, .rc-card h4 {
    margin: 0 0 .45rem 0;
}
.rc-card small, .rc-muted {
    color: var(--rc-muted);
}
.rc-step {
    display: inline-flex;
    align-items: center;
    gap: .45rem;
    padding: .35rem .65rem;
    border-radius: 999px;
    background: rgba(34, 211, 238, .12);
    border: 1px solid rgba(34, 211, 238, .24);
    color: #cffafe;
    font-weight: 800;
    font-size: .78rem;
    letter-spacing: .02em;
    text-transform: uppercase;
}
.rc-score {
    font-size: 2.15rem;
    font-weight: 900;
    line-height: 1;
}
.rc-good { color: var(--rc-ok); }
.rc-warn { color: var(--rc-warn); }
.rc-danger { color: var(--rc-danger); }
.rc-mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.rc-result {
    border: 1px solid rgba(52, 211, 153, .35);
    border-radius: 22px;
    padding: 1rem;
    background: linear-gradient(135deg, rgba(5, 150, 105, .12), rgba(15, 23, 42, .72));
}
.rc-blocked {
    border: 1px solid rgba(251, 113, 133, .35);
    border-radius: 22px;
    padding: 1rem;
    background: linear-gradient(135deg, rgba(190, 18, 60, .12), rgba(15, 23, 42, .72));
}
.rc-mini-table {
    width: 100%;
    border-collapse: collapse;
}
.rc-mini-table td {
    border-bottom: 1px solid rgba(148, 163, 184, .12);
    padding: .42rem .1rem;
    vertical-align: top;
}
.rc-mini-table td:first-child {
    color: var(--rc-muted);
    width: 38%;
}
div[data-testid="stMetric"] {
    border: 1px solid var(--rc-border);
    border-radius: 18px;
    padding: .75rem .85rem;
    background: rgba(15, 23, 42, .58);
}
.stButton > button {
    border-radius: 999px;
    min-height: 2.75rem;
    font-weight: 800;
    border: 1px solid rgba(34, 211, 238, .30);
    box-shadow: 0 10px 30px rgba(34, 211, 238, .10);
}
.stDownloadButton > button {
    border-radius: 999px;
}
@media (max-width: 760px) {
    .rc-grid { grid-template-columns: 1fr; }
    .rc-hero { padding: 1rem; border-radius: 20px; }
    .rc-card { border-radius: 18px; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def html_table(rows: list[tuple[str, object]]) -> str:
    trs = []
    for label, value in rows:
        value_txt = "não confirmado" if value in (None, "") else str(value)
        trs.append(f"<tr><td>{escape(str(label))}</td><td>{escape(value_txt)}</td></tr>")
    return "<table class='rc-mini-table'>" + "".join(trs) + "</table>"


def render_hero() -> None:
    st.markdown(
        f"""
        <section class="rc-hero">
            <div class="rc-step">Central tecnológica de lotação</div>
            <h1 class="rc-title">Rota Cheia</h1>
            <p class="rc-subtitle">
                Um fluxo único para escolher oportunidade, validar a busca pública da BlaBlaCar
                e evitar duplicidade entre Ezequiel S e Barbosa antes de qualquer ação.
            </p>
            <div class="rc-pill-row">
                <span class="rc-pill">Origem → destino</span>
                <span class="rc-pill">Ranking de datas</span>
                <span class="rc-pill">Scanner público</span>
                <span class="rc-pill">Fallback .mht</span>
                <span class="rc-pill">Sem validação: {escape(STATUS_NAO_VALIDADO)}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def parse_eventos(eventos_txt: str) -> list[dict]:
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
    return eventos


def prioridade_label(score: int) -> str:
    if score >= 85:
        return "muito forte"
    if score >= 70:
        return "forte"
    if score >= 50:
        return "médio"
    return "baixo"


def render_oportunidade(item: dict, idx: int) -> None:
    score = int(item.get("score_total") or 0)
    classe = "rc-good" if score >= 80 else "rc-warn" if score >= 55 else "rc-danger"
    st.markdown(
        f"""
        <div class="rc-card">
            <div class="rc-step">#{idx + 1} · {escape(str(item.get('sentido', '')))}</div>
            <h3>{escape(str(item.get('data', '')))} · {escape(str(item.get('horario', '')))}</h3>
            <div class="rc-score {classe}">{score}</div>
            <small>força da oportunidade: {escape(prioridade_label(score))}</small>
            {html_table([
                ('origem', item.get('origem')),
                ('destino final', item.get('destino_final')),
                ('dia', item.get('dia_semana')),
                ('prioridade', item.get('prioridade')),
                ('validação', item.get('status_validacao')),
            ])}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_resumo_datas(datas: list[dict]) -> None:
    total = len(datas)
    melhor = datas[0] if datas else {}
    muito_fortes = sum(1 for d in datas if int(d.get("score_total") or 0) >= 85)
    col1, col2, col3 = st.columns(3)
    col1.metric("Oportunidades", total)
    col2.metric("Muito fortes", muito_fortes)
    col3.metric("Melhor score", melhor.get("score_total", "-") if melhor else "-")


def render_concorrencia(concorrencia: dict) -> None:
    st.markdown("### Radar da concorrência")
    precos = concorrencia.get("precos") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Preço médio", precos.get("preco_medio") or "não detectado")
    c2.metric("Menor preço", precos.get("preco_minimo") or "não detectado")
    c3.metric("Maior preço", precos.get("preco_maximo") or "não detectado")

    horarios = concorrencia.get("horarios_mais_fortes") or []
    destinos = concorrencia.get("destinos_mais_cotados") or []
    cheios = concorrencia.get("motoristas_mais_cheios") or []

    col1, col2 = st.columns(2)
    with col1:
        if horarios:
            st.markdown("**Horários mais fortes**")
            st.dataframe(pd.DataFrame(horarios), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum horário forte detectado ainda.")
    with col2:
        if destinos:
            st.markdown("**Destinos mais cotados**")
            st.dataframe(pd.DataFrame(destinos), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum destino cotado detectado ainda.")

    if cheios:
        st.markdown("**Motoristas com carros mais cheios**")
        st.dataframe(pd.DataFrame(cheios), use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum carro cheio/quase cheio detectado ainda.")


def render_decisao(decisao: dict) -> None:
    validado = decisao.get("status_validacao") != STATUS_NAO_VALIDADO and decisao.get("acao") != "não confirmado"
    classe = "rc-result" if validado else "rc-blocked"
    st.markdown(
        f"""
        <div class="{classe}">
            <div class="rc-step">Resultado operacional</div>
            <h3>Ação: {escape(str(decisao.get('acao') or 'não confirmado'))}</h3>
            {html_table([
                ('conta', decisao.get('conta')),
                ('origem', decisao.get('origem')),
                ('destino final', decisao.get('destino_final')),
                ('intermediárias', decisao.get('intermediarias')),
                ('data', decisao.get('data')),
                ('horário', decisao.get('horario')),
                ('preço sugerido', decisao.get('preco_sugerido')),
                ('risco de conflito', decisao.get('risco_conflito')),
                ('status de validação', decisao.get('status_validacao')),
            ])}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if decisao.get("motivo"):
        st.info(decisao.get("motivo"))


def render_falha_controlada(exc: Exception) -> None:
    st.error(STATUS_NAO_VALIDADO)
    st.warning(f"Falha técnica controlada: {exc}")
    st.info("Use o Fallback Técnico abaixo com o arquivo .mht/.mhtml salvo da busca pública por rota + data.")


def gerar_opcoes(datas: list[dict]) -> list[str]:
    return [
        f"{i + 1}. {d['data']} · {d['sentido']} · {d['horario']} · {d['origem']} → {d['destino_final']} · score {d.get('score_total')}"
        for i, d in enumerate(datas)
    ]


def dataframe_resumido(datas: list[dict]) -> pd.DataFrame:
    if not datas:
        return pd.DataFrame()
    df = pd.DataFrame(datas)
    colunas = [
        "score_total",
        "data",
        "dia_semana",
        "sentido",
        "horario",
        "origem",
        "destino_final",
        "prioridade",
        "status_validacao",
    ]
    return df[[c for c in colunas if c in df.columns]]


inject_css()
render_hero()

with st.sidebar:
    st.header("Comando rápido")
    st.caption("Fluxo seguro: planejar → escolher → validar → decidir.")
    st.warning(f"Sem validação: {STATUS_NAO_VALIDADO}")
    st.markdown(f"**Entrada pública:** [{PUBLIC_CARPOOL_ENTRYPOINT}]({PUBLIC_CARPOOL_ENTRYPOINT})")
    st.markdown("**Contas:** " + ", ".join(CONTAS))
    st.markdown("**Não usar como nome:** " + ", ".join(IDENTIFICADORES_BLOQUEADOS))
    st.markdown("**Ignorar:** " + ", ".join(DESTINOS_IGNORADOS))

st.markdown("## 1. Configure a rota")
st.markdown("Escolha o corredor. O ranking aparece automaticamente sem precisar navegar por abas.")

col1, col2, col3 = st.columns([1.2, 1.2, .8])
with col1:
    origem_cap = st.selectbox("Origem", list(ORIGENS), key="origem_cap")
    destino_cap = st.selectbox("Destino final", list(DESTINOS), key="destino_cap")
with col2:
    conta_scan = st.selectbox("Conta analisada", list(CONTAS), key="conta_scan")
    semanas = st.slider("Antecedência em semanas", min_value=1, max_value=12, value=3)
with col3:
    assentos_cap = st.number_input("Assentos", min_value=1, max_value=4, value=1, step=1, key="assentos_cap")
    incluir_sabado = st.checkbox("Sábado à noite", value=False, help="Use somente quando demanda ou evento justificar.")

with st.expander("Adicionar eventos regionais que aumentam a pontuação", expanded=False):
    eventos_txt = st.text_area(
        "Formato: nome | cidade | data | peso",
        placeholder="Festival X | São Tomé das Letras | 2026-07-10 | 40",
    )

eventos = parse_eventos(eventos_txt)
datas = gerar_datas_operacionais(
    origem_ida=origem_cap,
    destino_ida=destino_cap,
    semanas=int(semanas),
    incluir_sabado=bool(incluir_sabado),
    assentos=int(assentos_cap),
    eventos_regionais=normalizar_eventos(eventos),
    localidades_eventos=[origem_cap, destino_cap],
)
st.session_state["datas_sugeridas"] = datas

st.markdown("## 2. Escolha a melhor oportunidade")
render_resumo_datas(datas)

if datas:
    top = datas[:3]
    cols = st.columns(len(top))
    for i, item in enumerate(top):
        with cols[i]:
            render_oportunidade(item, i)

    opcoes = gerar_opcoes(datas)
    escolha = st.selectbox("Oportunidade para validar", opcoes, key="escolha_oportunidade")
    idx = int(escolha.split(".", 1)[0]) - 1
    item = datas[idx]

    with st.expander("Ver ranking completo", expanded=False):
        st.dataframe(dataframe_resumido(datas), use_container_width=True, hide_index=True)

    st.markdown("## 3. Validar na busca pública")
    st.markdown(
        "A decisão operacional só aparece depois de tentar validar a rota + data. "
        "Se a BlaBlaCar bloquear a leitura automática, use o fallback na mesma tela."
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        executar_scan = st.button("🚀 Executar scanner público", type="primary", use_container_width=True)
    with col_b:
        salvar_scan = st.checkbox("Salvar resultado no histórico", value=True)

    if executar_scan:
        with st.spinner("Validando busca pública por rota + data..."):
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

    st.markdown("## 4. Fallback técnico, se necessário")
    with st.expander("Abrir fallback .mht/.mhtml", expanded=False):
        st.caption("Use quando a busca automática retornar bloqueio/403. Salve a página pública da BlaBlaCar e envie aqui.")
        col_fb1, col_fb2 = st.columns(2)
        with col_fb1:
            origem_fb = st.selectbox("Origem esperada", list(ORIGENS), index=list(ORIGENS).index(item["origem"]) if item.get("origem") in ORIGENS else 0, key="origem_fb")
            destino_fb = st.selectbox("Destino final esperado", list(DESTINOS), index=list(DESTINOS).index(item["destino_final"]) if item.get("destino_final") in DESTINOS else 0, key="destino_fb")
            data_fb = st.date_input("Data exata", value=pd.to_datetime(item["data"]).date(), key="data_fb")
        with col_fb2:
            conta_fb = st.selectbox("Conta", list(CONTAS), index=list(CONTAS).index(conta_scan), key="conta_fb")
            sentido_fb = st.selectbox("Sentido", SENTIDOS, index=SENTIDOS.index(item["sentido"]) if item.get("sentido") in SENTIDOS else 0, key="sentido_fb")
            horario_fb = st.text_input("Horário planejado", value=str(item.get("horario") or ""), key="horario_fb")

        arquivo_fb = st.file_uploader("Arquivo técnico salvo da busca pública", type=["mhtml", "mht"])
        if st.button("Analisar fallback técnico", disabled=arquivo_fb is None, use_container_width=True):
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
else:
    st.warning("Nenhuma oportunidade gerada para esta configuração.")

st.markdown("---")
col_hist, col_agenda = st.columns(2)
with col_hist:
    with st.expander("Histórico de scans", expanded=False):
        linhas = list_recent_scans()
        if linhas:
            st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum scan salvo ainda.")

with col_agenda:
    with st.expander("Agenda operacional padrão", expanded=False):
        st.dataframe(pd.DataFrame(listar_padrao_logistico()), use_container_width=True, hide_index=True)
