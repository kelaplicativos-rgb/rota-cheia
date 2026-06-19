from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config.caronas_config import (
    CONTAS_SUGERIDAS,
    DESTINOS,
    DESTINOS_IGNORADOS,
    IDENTIFICADORES_BLOQUEADOS,
    ORIGENS,
    PUBLIC_CARPOOL_ENTRYPOINT,
    STATUS_NAO_VALIDADO,
    TERMOS_CONFLITO_SUGERIDOS,
)
from database.db import init_db
from database.repository import list_recent_scans, save_scan
from rules.agenda import listar_padrao_logistico
from rules.datas_operacionais import gerar_datas_operacionais
from rules.eventos_regionais import normalizar_eventos
from services.public_scan_service import analisar_busca_publica_por_data
from services.review_rewriter import ESTILOS_AVALIACAO, TIPOS_AVALIACAO, reformular_avaliacao


st.set_page_config(page_title="Rota Cheia", page_icon="🚗", layout="wide")
init_db()

CSS = """
<style id="rota-cheia-tema-blablacar-v4">
:root {
    --rc-bg: #ffffff;
    --rc-bg-soft: #f5f9ff;
    --rc-blue: #087cf5;
    --rc-blue-strong: #0068d9;
    --rc-blue-soft: #eaf4ff;
    --rc-navy: #031b45;
    --rc-muted: #5f6f86;
    --rc-border: #dce6f3;
    --rc-success: #087c54;
    --rc-success-soft: #ccffcb;
    --rc-warning: #f59e0b;
    --rc-danger: #dc2626;
}
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main, .appview-container, .main {
    background: #ffffff !important;
    color: var(--rc-navy) !important;
}
[data-testid="stHeader"], header[data-testid="stHeader"], [data-testid="stToolbar"] {
    background: rgba(255, 255, 255, .96) !important;
}
.block-container {
    padding-top: .78rem !important;
    padding-bottom: 5rem !important;
    max-width: 860px !important;
}
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--rc-border) !important;
}
[data-testid="stSidebar"] * { color: var(--rc-navy) !important; }
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
    color: var(--rc-navy) !important;
    letter-spacing: -.045em !important;
}
p, span, label, small,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
.stCaptionContainer {
    color: var(--rc-muted) !important;
}
.rc-hero, .rc-card, .rc-scan, .rc-result, .rc-blocked {
    border-radius: 26px !important;
    padding: 1.05rem !important;
    background: #ffffff !important;
    border: 1px solid var(--rc-border) !important;
    box-shadow: 0 10px 24px rgba(3, 27, 69, .07) !important;
}
.rc-hero {
    border: 3px solid var(--rc-blue) !important;
    box-shadow: 0 12px 28px rgba(8, 124, 245, .14) !important;
}
.rc-title {
    font-size: clamp(2.35rem, 8vw, 4.5rem) !important;
    line-height: .96 !important;
    font-weight: 950 !important;
    margin: .45rem 0 .5rem 0 !important;
    color: var(--rc-navy) !important;
    letter-spacing: -.06em !important;
}
.rc-muted {
    color: var(--rc-muted) !important;
    font-size: 1rem !important;
    line-height: 1.42 !important;
    font-weight: 650 !important;
}
.rc-pill-row { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
.rc-pill {
    border: 1px solid rgba(8, 124, 245, .24) !important;
    background: var(--rc-blue-soft) !important;
    color: var(--rc-blue-strong) !important;
    border-radius: 999px !important;
    padding: .38rem .72rem !important;
    font-size: .82rem !important;
    font-weight: 850 !important;
}
.rc-step {
    display: inline-flex;
    padding: .38rem .72rem;
    border-radius: 999px;
    background: var(--rc-blue-soft);
    border: 1px solid rgba(8, 124, 245, .28);
    color: var(--rc-blue-strong) !important;
    font-weight: 900;
    font-size: .78rem;
    text-transform: uppercase;
}
.rc-score { font-size: 2.15rem; font-weight: 950; line-height: 1; }
.rc-good { color: var(--rc-success) !important; }
.rc-warn { color: var(--rc-warning) !important; }
.rc-danger { color: var(--rc-danger) !important; }
.rc-result { border-color: rgba(8, 124, 84, .38) !important; background: #fbfffb !important; }
.rc-blocked { border-color: rgba(220, 38, 38, .25) !important; background: #fffafa !important; }
.rc-mini-table { width: 100%; border-collapse: collapse; }
.rc-mini-table td {
    border-bottom: 1px solid rgba(3, 27, 69, .10) !important;
    padding: .46rem .1rem;
    vertical-align: top;
    color: var(--rc-navy) !important;
}
.rc-mini-table td:first-child {
    color: var(--rc-muted) !important;
    width: 38%;
    font-weight: 800;
}
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid var(--rc-border) !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 18px rgba(3, 27, 69, .055) !important;
}
.stButton > button, .stDownloadButton > button, .stLinkButton > a {
    border-radius: 18px !important;
    min-height: 3rem !important;
    font-weight: 900 !important;
    border: 1px solid var(--rc-border) !important;
    color: var(--rc-navy) !important;
    background: #ffffff !important;
}
.stButton > button[kind="primary"], .stButton > button:has(p), .stDownloadButton > button[kind="primary"] {
    background: var(--rc-blue) !important;
    color: #ffffff !important;
    border-color: var(--rc-blue) !important;
    box-shadow: 0 12px 24px rgba(8, 124, 245, .22) !important;
}
.stButton > button[kind="primary"] *, .stDownloadButton > button[kind="primary"] *, .stButton > button:has(p) * {
    color: #ffffff !important;
}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea, [data-baseweb="select"] > div {
    background: #ffffff !important;
    color: var(--rc-navy) !important;
    border: 1px solid var(--rc-border) !important;
    border-radius: 18px !important;
    min-height: 3rem !important;
}
[data-testid="stExpander"], [data-testid="stDataFrame"] {
    background: #ffffff !important;
    border: 1px solid var(--rc-border) !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 18px rgba(3, 27, 69, .045) !important;
}
hr { border-color: rgba(3, 27, 69, .10) !important; }
@media (max-width: 768px) {
    .block-container {
        max-width: 100vw !important;
        padding-left: .78rem !important;
        padding-right: .78rem !important;
    }
    .rc-title { font-size: clamp(2.1rem, 11vw, 3.2rem) !important; }
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
            <div class="rc-step">Central multiusuário para lotar o carro</div>
            <h1 class="rc-title">Rota Cheia</h1>
            <p class="rc-muted">
                Informe origem, destino e contas públicas do seu grupo. O sistema valida a busca pública
                da BlaBlaCar por rota + data, cruza sinais de eventos e retorna a melhor decisão sem
                depender de nomes fixos ou arquivo enviado pelo usuário.
            </p>
            <div class="rc-pill-row">
                <span class="rc-pill">Multiusuário</span>
                <span class="rc-pill">SCAN BLA público</span>
                <span class="rc-pill">Validação forte</span>
                <span class="rc-pill">Conflitos configuráveis</span>
                <span class="rc-pill">Sem validação: {escape(STATUS_NAO_VALIDADO)}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def parse_linhas(texto: str) -> list[str]:
    saida: list[str] = []
    for linha in (texto or "").splitlines():
        linha = linha.strip()
        if linha and linha not in saida:
            saida.append(linha)
    return saida


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
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Oportunidades", total)
    col2.metric("Muito fortes", muito_fortes)
    col3.metric("Melhor score", melhor.get("score_total", "-") if melhor else "-")
    col4.metric("Status", "validar no SCAN BLA")


def render_concorrencia(concorrencia: dict) -> None:
    st.markdown("### Radar da concorrência e demanda")
    precos = concorrencia.get("precos") or {}
    horarios = concorrencia.get("horarios_mais_fortes") or []
    destinos = concorrencia.get("destinos_mais_cotados") or []
    cheios = concorrencia.get("motoristas_mais_cheios") or []
    motoristas = concorrencia.get("motoristas") or cheios

    total_ofertas = concorrencia.get("total_ofertas_detectadas") or len(motoristas)
    cheios_ou_quase = concorrencia.get("cheios_ou_quase")
    if cheios_ou_quase is None:
        cheios_ou_quase = sum(1 for m in motoristas if int(m.get("lotacao_score") or 0) >= 85)

    melhor_horario = concorrencia.get("melhor_horario_sugerido")
    if not melhor_horario and horarios:
        melhor_horario = horarios[0].get("horario")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ofertas detectadas", total_ofertas)
    c2.metric("Cheios/quase cheios", cheios_ou_quase)
    c3.metric("Melhor horário", melhor_horario or "não detectado")
    c4.metric("Faixa de preço", precos.get("faixa") or "não detectada")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Ranking de horários para publicar**")
        if horarios:
            st.dataframe(pd.DataFrame(horarios), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum horário forte detectado ainda.")
    with col2:
        st.markdown("**Ranking de cidades/destinos**")
        if destinos:
            st.dataframe(pd.DataFrame(destinos), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum destino cotado detectado ainda.")

    if cheios:
        st.markdown("**Carros cheios, quase cheios ou com maior sinal de demanda**")
        df_cheios = pd.DataFrame(cheios)
        colunas = ["motorista", "horario", "preco", "vagas", "status", "lotacao_score", "destinos_detectados"]
        st.dataframe(df_cheios[[c for c in colunas if c in df_cheios.columns]], use_container_width=True, hide_index=True)


def decisao_para_copia(decisao: dict) -> str:
    return "\n".join(
        [
            f"ação: {decisao.get('acao') or 'não confirmado'}",
            f"conta: {decisao.get('conta') or 'não confirmado'}",
            f"origem: {decisao.get('origem') or 'não confirmado'}",
            f"destino final: {decisao.get('destino_final') or 'não confirmado'}",
            f"intermediárias: {decisao.get('intermediarias') or 'não confirmado'}",
            f"data: {decisao.get('data') or 'não confirmado'}",
            f"horário: {decisao.get('horario') or 'não confirmado'}",
            f"preço sugerido: {decisao.get('preco_sugerido') or 'não sugerido'}",
            f"risco de conflito: {decisao.get('risco_conflito') or 'não confirmado'}",
            f"status de validação: {decisao.get('status_validacao') or STATUS_NAO_VALIDADO}",
        ]
    )


def render_decisao(decisao: dict) -> None:
    validado = decisao.get("status_validacao") != STATUS_NAO_VALIDADO and decisao.get("acao") != "não confirmado"
    classe = "rc-result" if validado else "rc-blocked"
    st.markdown(
        f"""
        <div class="{classe}">
            <div class="rc-step">Decisão final</div>
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

    texto = decisao_para_copia(decisao)
    st.markdown("#### Decisão pronta para copiar")
    st.text_area("Copie e cole este resumo", value=texto, height=230, key="decisao_pronta_copia")
    st.download_button(
        "Baixar decisão em TXT",
        data=texto,
        file_name="decisao_rota_cheia.txt",
        mime="text/plain",
        use_container_width=True,
    )


def render_falha_controlada(exc: Exception) -> None:
    st.error(STATUS_NAO_VALIDADO)
    st.warning(f"Falha técnica controlada: {exc}")
    st.info("A busca automática pública não validou esta rota/data. Não publique antes de validar a data exata.")


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
        "motivo",
        "status_validacao",
    ]
    return df[[c for c in colunas if c in df.columns]]


def render_mensagens_prontas() -> None:
    st.markdown("### 💬 Mensagens rápidas para passageiros")
    mensagens = {
        "Após reserva": (
            "Oi! Tudo certo 👍\n\n"
            "Vi sua reserva e está tudo confirmado. Assim que eu estiver indo para o ponto de embarque, "
            "te aviso o tempo estimado para chegar e combinamos direitinho."
        ),
        "Bio curta": (
            "Aceito Pix ou dinheiro. Após a reserva, entro em contato para combinar o embarque. "
            "Não entro nas cidades; embarque/desembarque em trevos, postos ou pontos na rodovia."
        ),
        "A caminho": "Estou a caminho do ponto combinado. Te aviso qualquer atualização e chego em breve 👍",
    }

    with st.expander("Abrir mensagens prontas", expanded=False):
        escolha_msg = st.selectbox("Mensagem", list(mensagens), key="mensagem_pronta_tipo")
        st.text_area("Copie a mensagem", value=mensagens[escolha_msg], height=120, key="mensagem_pronta_texto")


def render_review_rewriter() -> None:
    st.markdown("### ⭐ Reformular avaliações")
    with st.expander("Abrir reformulador de avaliações", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo de avaliação", list(TIPOS_AVALIACAO), index=0, key="home_avaliacao_tipo")
        with col2:
            estilo = st.selectbox("Estilo", list(ESTILOS_AVALIACAO), index=0, key="home_avaliacao_estilo")
        avaliacao_original = st.text_area(
            "Cole aqui a avaliação original",
            placeholder="Ex.: Gente boa recomendo a carona educado",
            height=110,
            key="home_avaliacao_original",
        )
        if st.button("Reformular avaliação", type="primary", use_container_width=True, key="home_reformular_avaliacao"):
            if not avaliacao_original.strip():
                st.warning("Cole uma avaliação primeiro.")
            else:
                st.session_state["home_avaliacao_reformulada"] = reformular_avaliacao(
                    avaliacao_original,
                    tipo=tipo,
                    estilo=estilo,
                )
        resultado = st.session_state.get("home_avaliacao_reformulada", "")
        if resultado:
            st.success("Avaliação reformulada pronta para copiar:")
            st.text_area("Copie a avaliação abaixo", value=resultado, height=90, key="home_avaliacao_resultado")


inject_css()
render_hero()

with st.sidebar:
    st.header("SCAN BLA")
    st.caption("Fluxo seguro: planejar → validar rota + data → decidir.")
    st.warning(f"Sem validação: {STATUS_NAO_VALIDADO}")
    st.markdown(f"**Entrada pública:** [{PUBLIC_CARPOOL_ENTRYPOINT}]({PUBLIC_CARPOOL_ENTRYPOINT})")
    st.markdown("**Não usar como nome:** " + ", ".join(IDENTIFICADORES_BLOQUEADOS))
    st.markdown("**Ignorar:** " + ", ".join(DESTINOS_IGNORADOS))
    st.markdown("---")
    st.markdown("**Regra:** não existe conta fixa. Cada usuário informa a própria conta pública e contas do mesmo grupo logístico.")

st.markdown("## 1. Planejar viagem")
st.markdown("Informe a origem, o destino e o período para o sistema encontrar as melhores datas com antecedência.")

col1, col2 = st.columns(2)
with col1:
    origem_base = st.selectbox("Origem sugerida", list(ORIGENS), key="origem_base")
    origem_custom = st.text_input("Ou digite outra origem", value=origem_base, key="origem_custom")
with col2:
    destino_base = st.selectbox("Destino sugerido", list(DESTINOS), key="destino_base")
    destino_custom = st.text_input("Ou digite outro destino final", value=destino_base, key="destino_custom")

origem_cap = origem_custom.strip() or origem_base
destino_cap = destino_custom.strip() or destino_base

col3, col4, col5 = st.columns([1.3, 1, .8])
with col3:
    conta_scan = st.text_input("Nome público da conta ativa", value=CONTAS_SUGERIDAS[0], key="conta_scan")
with col4:
    semanas = st.slider("Antecedência em semanas", min_value=1, max_value=12, value=3)
with col5:
    assentos_cap = st.number_input("Assentos", min_value=1, max_value=4, value=1, step=1, key="assentos_cap")

with st.expander("Contas do mesmo grupo e conflitos logísticos", expanded=False):
    st.caption("Use uma conta por linha. O sistema é multiusuário: estes nomes são configurados pelo motorista/empresa.")
    contas_grupo_txt = st.text_area(
        "Outras contas públicas do mesmo grupo logístico",
        value="\n".join(CONTAS_SUGERIDAS[1:]),
        placeholder="Ex.: Nome da segunda conta\nMotorista reserva\nConta da empresa",
        height=110,
        key="contas_grupo_txt",
    )
    st.caption("Termos/cidades onde duas contas do mesmo grupo não devem publicar/ir no mesmo dia.")
    termos_conflito_txt = st.text_area(
        "Termos de conflito",
        value="\n".join(TERMOS_CONFLITO_SUGERIDOS),
        placeholder="Ex.: Três Corações\nSão Tomé das Letras\nAeroporto",
        height=110,
        key="termos_conflito_txt",
    )

contas_grupo = [conta_scan.strip()] + parse_linhas(contas_grupo_txt)
contas_grupo = [c for i, c in enumerate(contas_grupo) if c and c not in contas_grupo[:i]]
termos_conflito = parse_linhas(termos_conflito_txt)

with st.expander("Eventos e alta demanda", expanded=False):
    st.caption("Formato: nome | cidade | data | peso. Exemplo: Festival X | São Tomé das Letras | 2026-07-10 | 40")
    eventos_txt = st.text_area(
        "Eventos regionais que aumentam a pontuação",
        placeholder="Festival X | São Tomé das Letras | 2026-07-10 | 40",
    )
    st.info("A busca ampla de eventos deve entrar como coletor automático; por enquanto este campo permite alimentar eventos conhecidos sem bloquear o SCAN BLA.")

eventos = parse_eventos(eventos_txt)
incluir_sabado = any("sab" in (e.get("nome", "") + e.get("cidade", "")).lower() for e in eventos)

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

st.markdown("## 2. Escolher melhor data e horário")
render_resumo_datas(datas)

if datas:
    top = datas[:3]
    cols = st.columns(len(top))
    for i, item_top in enumerate(top):
        with cols[i]:
            render_oportunidade(item_top, i)

    opcoes = gerar_opcoes(datas)
    escolha = st.selectbox("Oportunidade para validar", opcoes, key="escolha_oportunidade")
    idx = int(escolha.split(".", 1)[0]) - 1
    item = datas[idx]

    with st.expander("Ver ranking completo", expanded=False):
        st.dataframe(dataframe_resumido(datas), use_container_width=True, hide_index=True)

    st.markdown("## 3. SCAN BLA — validar rota + data")
    st.markdown(
        "A decisão operacional só é liberada depois da validação pública por rota + data. "
        "O app não pede arquivo .mhtml/.mht no fluxo do usuário."
    )
    st.markdown(
        f"""
        <div class="rc-scan">
            <div class="rc-step">Busca pública obrigatória</div>
            {html_table([
                ('conta ativa', conta_scan),
                ('contas do grupo', ', '.join(contas_grupo)),
                ('rota', f"{item.get('origem')} → {item.get('destino_final')}"),
                ('data', item.get('data')),
                ('horário planejado', item.get('horario')),
                ('ação antes do scan', STATUS_NAO_VALIDADO),
            ])}
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        executar_scan = st.button("🚀 SCAN BLA — validar agora", type="primary", use_container_width=True)
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
                    contas_grupo=contas_grupo,
                    termos_conflito=termos_conflito,
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

st.markdown("---")
st.markdown("## 4. Mensagens e avaliações BlaBlaCar")
render_mensagens_prontas()
render_review_rewriter()
