from __future__ import annotations

import streamlit as st

from services.review_rewriter import ESTILOS_AVALIACAO, TIPOS_AVALIACAO, reformular_avaliacao

st.set_page_config(page_title="Reformular avaliações", page_icon="⭐", layout="centered")

st.title("⭐ Reformular avaliações")
st.caption("Cole uma avaliação simples e receba uma versão curta, natural e pronta para copiar e colar na BlaBlaCar.")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo de avaliação", list(TIPOS_AVALIACAO), index=0)
    with col2:
        estilo = st.selectbox("Estilo", list(ESTILOS_AVALIACAO), index=0)

    avaliacao_original = st.text_area(
        "Cole aqui a avaliação original",
        placeholder="Ex.: Gente boa recomendo a carona educado",
        height=130,
    )

    reformular = st.button("Reformular avaliação", type="primary", use_container_width=True)

    if reformular:
        if not avaliacao_original.strip():
            st.warning("Cole uma avaliação primeiro.")
        else:
            st.session_state["avaliacao_reformulada"] = reformular_avaliacao(
                avaliacao_original,
                tipo=tipo,
                estilo=estilo,
            )

resultado = st.session_state.get("avaliacao_reformulada", "")

if resultado:
    st.success("Avaliação reformulada pronta para copiar:")
    st.text_area(
        "Copie a avaliação abaixo",
        value=resultado,
        height=110,
        key="avaliacao_reformulada_preview",
    )
    st.caption("No celular, toque e segure no texto acima para copiar.")

with st.expander("Exemplos rápidos", expanded=False):
    st.markdown(
        """
        **Original:** Gente boa recomendo a carona educado  
        **Reformulada:** Pessoa gente boa e educada. Recomendo!

        **Original:** Pontual agradável recomendo  
        **Reformulada:** Pessoa pontual e agradável. Recomendo!
        """
    )
