from __future__ import annotations

import streamlit as st

from services.review_rewriter import ESTILOS_AVALIACAO, TIPOS_AVALIACAO, reformular_avaliacao


TEXTOS_RAPIDOS: dict[str, str] = {
    "Confirmar reserva": "Oi! Tudo certo. Sua reserva está confirmada. Vou avisar quando estiver indo para o ponto combinado.",
    "A caminho": "Estou a caminho do ponto combinado. Aviso qualquer atualização importante.",
    "Combinar ponto": "Me confirme o ponto combinado para eu organizar a viagem direitinho.",
}


# Bloco inicial do aplicativo.
def render_mensagens_avaliacoes_inicio() -> None:
    st.markdown("## 1. Mensagens e avaliações BlaBlaCar")
    st.markdown("Cole uma avaliação de passageiro e gere uma versão reformulada pronta para usar.")
    tipo = st.selectbox("Tipo de avaliação", list(TIPOS_AVALIACAO), index=0, key="inicio_avaliacao_tipo")
    estilo = st.selectbox("Tom", list(ESTILOS_AVALIACAO), index=0, key="inicio_avaliacao_estilo")
    texto = st.text_area("Cole aqui a avaliação original", height=120, key="inicio_avaliacao_original")
    if st.button("Reformular avaliação", type="primary", use_container_width=True, key="inicio_reformular_avaliacao"):
        if not texto.strip():
            st.warning("Cole uma avaliação primeiro.")
        else:
            st.session_state["inicio_avaliacao_reformulada"] = reformular_avaliacao(texto, tipo=tipo, estilo=estilo)
    resultado = st.session_state.get("inicio_avaliacao_reformulada", "")
    if resultado:
        st.success("Avaliação reformulada pronta:")
        st.text_area("Resultado", value=resultado, height=95, key="inicio_avaliacao_resultado")

    st.markdown("### Textos rápidos")
    texto_modelo = st.selectbox("Modelo", list(TEXTOS_RAPIDOS), key="inicio_texto_rapido_modelo")
    texto_base = st.text_area("Texto pronto", value=TEXTOS_RAPIDOS[texto_modelo], height=110, key="inicio_texto_rapido_base")
    if texto_base.strip():
        st.text_area("Copiar texto", value=texto_base.strip(), height=100, key="inicio_texto_rapido_pronto")
