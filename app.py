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
from services.review_rewriter import ESTILOS_AVALIACAO, TIPOS_AVALIACAO, reformular_avaliacao


st.set_page_config(page_title="Rota Cheia", page_icon="🚗", layout="wide")
init_db()

SENTIDOS = ["IDA", "VOLTA"]

CSS = """
<style>
.stApp {
    background:
        radial-gradient(circle at top left, rgba(34, 211, 238, .18), transparent 34rem),
        linear-gradient(135deg, #050816, #0b1020 55%, #111827);
    color: #e5e7eb;
}
.block-container { padding-top: 1.3rem; max-width: 1180px; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(2, 6, 23, .98), rgba(15, 23, 42, .96));
    border-right: 1px solid rgba(148, 163, 184, .22);
}
.rc-hero, .rc-card, .rc-scan, .rc-result, .rc-blocked {
    border-radius: 24px;
    padding: 1rem;
    background: rgba(15, 23, 42, .78);
    border: 1px solid rgba(148, 163, 184, .22);
    box-shadow: 0 16px 45px rgba(0, 0, 0, .20);
}
.rc-hero { border-color: rgba(34, 211, 238, .32); }
.rc-title { font-size: clamp(2.1rem, 6vw, 4.1rem); line-height: .95; font-weight: 900; margin: 0; }
.rc-muted { color: #94a3b8; }
.rc-pill-row { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
.rc-pill {
    border: 1px solid rgba(34, 211, 238, .22);
    background: rgba(8, 47, 73, .46);
    color: #cffafe;
    border-radius: 999px;
    padding: .38rem .7rem;
    font-size: .82rem;
    font-weight: 700;
}
.rc-step {
    display: inline-flex;
    padding: .35rem .65rem;
    border-radius: 999px;
    background: rgba(34, 211, 238, .12);
    border: 1px solid rgba(34, 211, 238, .24);
    color: #cffafe;
    font-weight: 800;
    font-size: .78rem;
    text-transform: uppercase;
}
.rc-score { font-size: 2.15rem; font-weight: 900; line-height: 1; }
.rc-good { color: #34d399; }
.rc-warn { color: #f59e0b; }
.rc-danger { color: #fb7185; }
.rc-result { border-color: rgba(52, 211, 153, .38); }
.rc-blocked { border-color: rgba(251, 113, 133, .38); }
.rc-mini-table { width: 100%; border-collapse: collapse; }
.rc-mini-table td { border-bottom: 1px solid rgba(148, 163, 184, .12); padding: .42rem .1rem; vertical-align: top; }
.rc-mini-table td:first-child { color: #94a3b8; width: 38%; }
.stButton > button, .stDownloadButton > button { border-radius: 999px; min-height: 2.7rem; font-weight: 800; }
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
            <div class="rc-step">Central de decisão para lotar o carro</div>
            <h1 class="rc-title">Rota Cheia</h1>
            <p class="rc-muted">
                Escolha a rota, valide a busca pública da BlaBlaCar e receba uma decisão segura
                para lotar o carro sem duplicar anúncio e sem conflito entre Ezequiel S e Barbosa.
            </p>
            <div class="rc-pill-row">
                <span class="rc-pill">SCAN BLA obrigatório</span>
                <span class="rc-pill">Ranking de horários</span>
                <span class="rc-pill">Ranking de cidades</span>
                <span class="rc-pill">Decisão pronta para copiar</span>
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
    st.info("Use o fallback com o arquivo .mht/.mhtml salvo da busca pública por rota + data.")


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
    st.markdown("**Contas:** " + ", ".join(CONTAS))
    st.markdown("**Não usar como nome:** " + ", ".join(IDENTIFICADORES_BLOQUEADOS))
    st.markdown("**Ignorar:** " + ", ".join(DESTINOS_IGNORADOS))
    st.markdown("---")
    st.markdown("**Regra:** se Ezequiel S ou Barbosa já aparecer na rota/data, não criar duplicado.")

st.markdown("## 1. Planejar viagem")
st.markdown("Escolha o corredor e gere oportunidades futuras com antecedência para encher o carro.")

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

with st.expander("Eventos e alta demanda", expanded=False):
    st.caption("Formato: nome | cidade | data | peso. Exemplo: Festival X | São Tomé das Letras | 2026-07-10 | 40")
    eventos_txt = st.text_area(
        "Eventos regionais que aumentam a pontuação",
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
        "Se a leitura automática for bloqueada, use o fallback `.mht/.mhtml` abaixo."
    )
    st.markdown(
        f"""
        <div class="rc-scan">
            <div class="rc-step">Busca pública obrigatória</div>
            {html_table([
                ('conta', conta_scan),
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

    st.markdown("## 4. Fallback, se necessário")
    with st.expander("Enviar busca salva da BlaBlaCar (.mht/.mhtml)", expanded=False):
        st.caption("Use quando o scanner público retornar bloqueio/403. Salve a página pública da BlaBlaCar e envie aqui.")
        col_fb1, col_fb2 = st.columns(2)
        with col_fb1:
            origem_fb = st.selectbox(
                "Origem esperada",
                list(ORIGENS),
                index=list(ORIGENS).index(item["origem"]) if item.get("origem") in ORIGENS else 0,
                key="origem_fb",
            )
            destino_fb = st.selectbox(
                "Destino final esperado",
                list(DESTINOS),
                index=list(DESTINOS).index(item["destino_final"]) if item.get("destino_final") in DESTINOS else 0,
                key="destino_fb",
            )
            data_fb = st.date_input("Data exata", value=pd.to_datetime(item["data"]).date(), key="data_fb")
        with col_fb2:
            conta_fb = st.selectbox("Conta", list(CONTAS), index=list(CONTAS).index(conta_scan), key="conta_fb")
            sentido_fb = st.selectbox(
                "Sentido",
                SENTIDOS,
                index=SENTIDOS.index(item["sentido"]) if item.get("sentido") in SENTIDOS else 0,
                key="sentido_fb",
            )
            horario_fb = st.text_input("Horário planejado", value=str(item.get("horario") or ""), key="horario_fb")
            salvar_fb = st.checkbox("Salvar fallback no histórico", value=False, key="salvar_fallback")

        arquivo_fb = st.file_uploader("Arquivo salvo da busca pública", type=["mhtml", "mht"])
        if st.button("Analisar fallback", disabled=arquivo_fb is None, use_container_width=True):
            try:
                resultado_fb = analisar_arquivo_mhtml(
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
                render_concorrencia(resultado_fb["concorrencia"])
                render_decisao(resultado_fb["decisao"])
                if salvar_fb:
                    scan_id = save_scan(resultado_fb["scan"], resultado_fb["motoristas"], resultado_fb["decisao"])
                    st.success(f"Fallback salvo no histórico com ID {scan_id}.")
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
st.markdown("## 5. Mensagens e avaliações BlaBlaCar")
render_mensagens_prontas()
render_review_rewriter()
