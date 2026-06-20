from __future__ import annotations

import streamlit as st

from services.review_rewriter import TIPOS_AVALIACAO, gerar_avaliacao, reformular_avaliacao


TEXTOS_RAPIDOS: dict[str, str] = {
    "Confirmar reserva": "Oi! Tudo certo. Sua reserva está confirmada. Vou avisar quando estiver indo para o ponto combinado.",
    "A caminho": "Estou a caminho do ponto combinado. Aviso qualquer atualização importante.",
    "Combinar ponto": "Me confirme o ponto combinado para eu organizar a viagem direitinho.",
}


def limpar_resultado_avaliacao() -> None:
    st.session_state["inicio_avaliacao_resultado"] = ""


def render_mensagens_avaliacoes_inicio() -> None:
    st.markdown("## 1. Mensagens e avaliações BlaBlaCar")
    st.markdown("Cole, digite para corrigir ou gere uma avaliação pronta.")

    modo = st.radio(
        "O que deseja fazer?",
        ["Corrigir ou reformular", "Gerar do zero"],
        horizontal=True,
        key="inicio_avaliacao_modo",
    )
    tipo = st.selectbox("Para quem?", list(TIPOS_AVALIACAO), index=0, key="inicio_avaliacao_tipo")

    texto = ""
    if modo == "Corrigir ou reformular":
        texto = st.text_area("Cole ou digite a avaliação", height=120, key="inicio_avaliacao_original")

    col_gerar, col_limpar = st.columns([2, 1])
    with col_gerar:
        gerar = st.button("Gerar avaliação", type="primary", use_container_width=True, key="inicio_gerar_avaliacao")
    with col_limpar:
        st.button("Limpar", use_container_width=True, key="inicio_limpar_avaliacao", on_click=limpar_resultado_avaliacao)

    if gerar:
        if modo == "Gerar do zero":
            indice = int(st.session_state.get("inicio_avaliacao_indice", 0))
            st.session_state["inicio_avaliacao_indice"] = indice + 1
            st.session_state["inicio_avaliacao_resultado"] = gerar_avaliacao(tipo, indice)
        elif not texto.strip():
            st.warning("Cole ou digite uma avaliação primeiro.")
        else:
            st.session_state["inicio_avaliacao_resultado"] = reformular_avaliacao(texto, tipo=tipo, estilo="Mais persuasiva")

    resultado = st.session_state.get("inicio_avaliacao_resultado", "")
    if resultado:
        st.success("Avaliação pronta para copiar:")
        st.text_area("Resultado", value=resultado, height=95, key="inicio_avaliacao_resultado_box")

    with st.expander("Textos rápidos", expanded=False):
        texto_modelo = st.selectbox("Modelo", list(TEXTOS_RAPIDOS), key="inicio_texto_rapido_modelo")
        texto_base = st.text_area("Texto pronto", value=TEXTOS_RAPIDOS[texto_modelo], height=110, key="inicio_texto_rapido_base")
        if texto_base.strip():
            st.text_area("Copiar texto", value=texto_base.strip(), height=100, key="inicio_texto_rapido_pronto")
