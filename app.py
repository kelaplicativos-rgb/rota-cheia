from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from message_rewriter import BIO_CURTA, reformular_mensagem
from ranking_passageiros import gerar_relatorio_markdown
from scanner_bla import filtrar_caronas_acessiveis, load_html_or_mhtml, parse_trip_cards_from_html, scan_sync
from trip_detail_scraper import scrape_many_sync
from validador_conflito import resultado_nao_confirmado, validar_conflitos

st.set_page_config(page_title="Rota Cheia", page_icon="🚗", layout="wide")

st.title("🚗 Rota Cheia")
st.caption("Mensagens prontas + SCAN BLA Modo Ouro")

aba_msg, aba_scan = st.tabs(["Mensagens e avaliações", "SCAN BLA Modo Ouro"])

with aba_msg:
    st.subheader("Reformular mensagens e avaliações")
    texto = st.text_area("Cole aqui a mensagem ou avaliação", height=150)
    tom = st.selectbox("Tom", ["curto", "educado", "persuasivo", "avaliacao"], index=1)
    if st.button("Reformular", type="primary"):
        resultado = reformular_mensagem(texto, tom=tom)
        st.text_area("Pronto para copiar", value=resultado.rewritten, height=160)
    st.divider()
    st.write("Bio curta sugerida")
    st.code(BIO_CURTA, language="text")

with aba_scan:
    st.subheader("SCAN BLA Modo Ouro")
    st.write("Cole o link público da busca ou envie um arquivo .mhtml/.mht.")
    link = st.text_input("Link da busca pública BlaBlaCar")
    data = st.text_input("Data da busca", placeholder="2026-06-26")
    arquivo = st.file_uploader("Arquivo .mhtml/.mht da busca", type=["mhtml", "mht", "html"])
    incluir_cheias = st.checkbox("Tentar analisar também caronas cheias", value=False)
    navegador_visivel = st.checkbox("Abrir navegador visível para depuração", value=False)

    if st.button("Rodar SCAN BLA", type="primary"):
        cards = []
        validado = False
        if arquivo is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(arquivo.name).suffix) as tmp:
                tmp.write(arquivo.read())
                tmp_path = tmp.name
            html = load_html_or_mhtml(tmp_path)
            cards = parse_trip_cards_from_html(html, base_url=link or "https://www.blablacar.com.br")
            validado = bool(cards)
        elif link:
            try:
                cards = scan_sync(link, headless=not navegador_visivel)
                validado = bool(cards)
            except Exception as exc:
                st.error(f"Não consegui abrir a busca pública: {exc}")

        if not validado:
            st.warning(resultado_nao_confirmado().status_validacao)
            st.stop()

        st.success(f"Busca validada. Caronas encontradas: {len(cards)}")
        st.dataframe([card.__dict__ for card in cards], use_container_width=True)
        validacao = validar_conflitos(cards, data=data)
        st.info(f"Ação: {validacao.acao} — {validacao.motivo}")
        acessiveis = filtrar_caronas_acessiveis(cards, incluir_cheias=incluir_cheias)
        st.write(f"Caronas para abrir por dentro: {len(acessiveis)}")
        if acessiveis:
            with st.spinner("Entrando nas caronas para buscar passageiros visíveis..."):
                detalhes = scrape_many_sync(acessiveis, headless=not navegador_visivel)
            relatorio = gerar_relatorio_markdown(detalhes)
            st.markdown(relatorio)
            st.download_button("Baixar relatório .md", relatorio, file_name="scan_bla_ranking.md")
