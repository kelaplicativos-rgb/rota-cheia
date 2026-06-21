from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from message_rewriter import BIO_CURTA, reformular_mensagem
from ranking_passageiros import gerar_relatorio_markdown
from scanner_bla import (
    extrair_data_do_link,
    filtrar_caronas_acessiveis,
    load_html_or_mhtml_with_source,
    parse_trip_cards_from_html,
    scan_sync,
)
from trip_detail_scraper import TripDetail, scrape_many_sync
from validador_conflito import resultado_nao_confirmado, validar_conflitos


APP_TZ = ZoneInfo("America/Sao_Paulo")


def hoje_sp() -> date:
    return datetime.now(APP_TZ).date()


def parse_data_iso(valor: str) -> date | None:
    valor = (valor or "").strip()[:10]
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def validar_data_entrada(data_efetiva: str, *, permite_historico: bool) -> tuple[date | None, bool]:
    data_dt = parse_data_iso(data_efetiva)
    if data_efetiva and data_dt is None:
        st.error(f"Data inválida: {data_efetiva}. Use o formato AAAA-MM-DD, exemplo: 2026-06-26.")
        st.warning(resultado_nao_confirmado().status_validacao)
        st.stop()

    historico = bool(data_dt and data_dt < hoje_sp())
    if historico and not permite_historico:
        st.error(
            f"Data no passado: {data_dt.isoformat()}. "
            "A busca pública da BlaBlaCar normalmente não retorna viagens antigas. "
            f"Use uma data a partir de {hoje_sp().isoformat()}."
        )
        st.warning(resultado_nao_confirmado().status_validacao)
        st.stop()

    return data_dt, historico


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
        detalhes_com_erro = False
        arquivo_historico = False
        fonte_arquivo_url = ""

        data_link = extrair_data_do_link(link or "")
        data_efetiva = (data or "").strip() or data_link

        if data_link:
            st.caption(f"Data detectada no link informado: {data_link}")

        if arquivo is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(arquivo.name).suffix) as tmp:
                tmp.write(arquivo.read())
                tmp_path = tmp.name

            documento = load_html_or_mhtml_with_source(tmp_path)
            fonte_arquivo_url = documento.source_url
            if fonte_arquivo_url:
                data_arquivo = extrair_data_do_link(fonte_arquivo_url)
                st.caption(f"Link detectado no arquivo MHTML: {fonte_arquivo_url}")
                if data_arquivo:
                    st.caption(f"Data detectada no arquivo MHTML: {data_arquivo}")
                if not data_efetiva:
                    data_efetiva = data_arquivo

            _, arquivo_historico = validar_data_entrada(data_efetiva, permite_historico=True)
            if arquivo_historico:
                st.warning(
                    "Arquivo MHTML histórico: vou extrair e mostrar os dados, mas não vou liberar "
                    "CRIAR/PUBLICAR/MANTER/ALTERAR/EXCLUIR sem uma busca pública atual por data."
                )

            base_url = link or fonte_arquivo_url or "https://www.blablacar.com.br"
            cards = parse_trip_cards_from_html(documento.html, base_url=base_url)
            validado = bool(cards)

        elif link:
            validar_data_entrada(data_efetiva, permite_historico=False)
            try:
                cards = scan_sync(link, headless=not navegador_visivel)
                validado = bool(cards)
            except Exception as exc:
                st.error(f"Não consegui abrir a busca pública: {exc}")

        if not validado or not data_efetiva:
            st.warning("Nenhuma carona pública foi encontrada para esta rota/data ou a página não pôde ser validada.")
            st.warning(resultado_nao_confirmado().status_validacao)
            st.stop()

        st.success(f"Busca carregada. Caronas encontradas: {len(cards)}")
        st.caption(f"Data analisada: {data_efetiva}")
        st.dataframe([card.__dict__ for card in cards], width="stretch")

        acessiveis = filtrar_caronas_acessiveis(cards, incluir_cheias=incluir_cheias)
        st.write(f"Caronas para abrir por dentro: {len(acessiveis)}")

        detalhes = []
        if arquivo_historico:
            st.info("Por ser arquivo histórico, não vou abrir detalhes online antigos. Vou gerar ranking pelos sinais públicos salvos no MHTML.")
            detalhes = [
                TripDetail(card=card, detail_status="arquivo histórico / passageiros online não abertos")
                for card in cards
            ]
            relatorio = gerar_relatorio_markdown(detalhes)
            st.markdown(relatorio)
            st.download_button("Baixar relatório .md", relatorio, file_name="scan_bla_ranking.md")
        elif acessiveis:
            with st.spinner("Entrando nas caronas para buscar passageiros visíveis..."):
                detalhes = scrape_many_sync(acessiveis, headless=not navegador_visivel)
            detalhes_com_erro = any(
                (detalhe.detail_status or "").casefold().startswith("erro ao abrir detalhe")
                for detalhe in detalhes
            )
            relatorio = gerar_relatorio_markdown(detalhes)
            st.markdown(relatorio)
            st.download_button("Baixar relatório .md", relatorio, file_name="scan_bla_ranking.md")
        else:
            st.info("Nenhuma carona acessível para abertura interna nesta busca.")

        if arquivo_historico:
            validacao = resultado_nao_confirmado(
                "Arquivo MHTML histórico analisado. Ação operacional exige busca pública atual por rota + data exata."
            )
        else:
            validacao = validar_conflitos(cards, data=data_efetiva)

        if detalhes_com_erro and validacao.acao == "CRIAR":
            validacao = resultado_nao_confirmado()
            st.warning("Abertura interna das caronas falhou. Não vou liberar CRIAR/PUBLICAR sem validação completa.")

        if validacao.acao == "NAO_CONFIRMADO":
            st.warning(validacao.status_validacao)
        elif validacao.acao == "CONFLITO":
            st.error(f"Ação: {validacao.acao} — {validacao.motivo}")
        else:
            st.info(f"Ação: {validacao.acao} — {validacao.motivo}")
