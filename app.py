from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from diagnostics import init_diagnostics, log_event, log_exception, render_diagnostics_panel
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
        log_event(
            "Validação de data",
            "Validar data informada",
            "ERRO",
            entrada=data_efetiva,
            resultado="Data inválida.",
            sugestao="Usar o formato AAAA-MM-DD, exemplo: 2026-06-26.",
        )
        st.error(f"Data inválida: {data_efetiva}. Use o formato AAAA-MM-DD, exemplo: 2026-06-26.")
        st.warning(resultado_nao_confirmado().status_validacao)
        st.stop()

    historico = bool(data_dt and data_dt < hoje_sp())
    if historico and not permite_historico:
        log_event(
            "Validação de data",
            "Bloquear busca pública em data passada",
            "AVISO",
            entrada=data_dt.isoformat() if data_dt else data_efetiva,
            resultado="A busca pública normalmente não retorna viagens antigas.",
            sugestao=f"Usar uma data a partir de {hoje_sp().isoformat()}.",
        )
        st.error(
            f"Data no passado: {data_dt.isoformat()}. "
            "A busca pública da BlaBlaCar normalmente não retorna viagens antigas. "
            f"Use uma data a partir de {hoje_sp().isoformat()}."
        )
        st.warning(resultado_nao_confirmado().status_validacao)
        st.stop()

    log_event(
        "Validação de data",
        "Validar data informada",
        "OK",
        entrada=data_efetiva,
        resultado=f"Data aceita. Histórico: {historico}.",
    )
    return data_dt, historico


st.set_page_config(page_title="Rota Cheia", page_icon="🚗", layout="wide")
init_diagnostics()

if not st.session_state.get("app_boot_logged"):
    log_event(
        "Inicialização",
        "Abrir app",
        "INFO",
        resultado="Sessão iniciada com diagnóstico ativo.",
    )
    st.session_state.app_boot_logged = True

render_diagnostics_panel()

st.title("🚗 Rota Cheia")
st.caption("Mensagens prontas + SCAN BLA Modo Ouro")

aba_msg, aba_scan = st.tabs(["Mensagens e avaliações", "SCAN BLA Modo Ouro"])

with aba_msg:
    st.subheader("Mensagens e avaliações BlaBlaCar")
    st.write(
        "Cole uma mensagem, resposta de passageiro ou avaliação. "
        "O app sempre retorna versões prontas para copiar."
    )

    exemplos = {
        "Resposta para atraso": "Você demorou para responder e eu acabei comprando passagem de ônibus.",
        "Confirmação de reserva": (
            "Vi sua solicitação, está tudo confirmado. Te aviso quando estiver a caminho do local combinado."
        ),
        "Avaliação simples": "Gente boa, educado e pontual. Recomendo a carona.",
        "Aviso de rodovia": "Não entro dentro das cidades, apenas trevos ou postos na rodovia.",
    }

    if "msg_input" not in st.session_state:
        st.session_state.msg_input = ""

    col_exemplo, col_bio, col_limpar = st.columns([2, 1, 1])
    with col_exemplo:
        exemplo = st.selectbox("Exemplo rápido para testar", [""] + list(exemplos.keys()))
    with col_bio:
        st.write("")
        st.write("")
        usar_bio = st.button("Usar bio curta", use_container_width=True)
    with col_limpar:
        st.write("")
        st.write("")
        limpar = st.button("Limpar", use_container_width=True)

    if "ultimo_exemplo_msg" not in st.session_state:
        st.session_state.ultimo_exemplo_msg = ""

    if exemplo and exemplo != st.session_state.ultimo_exemplo_msg:
        st.session_state.msg_input = exemplos[exemplo]
        st.session_state.pop("rewrite_result", None)
        log_event(
            "Mensagens e avaliações",
            "Selecionar exemplo rápido",
            "INFO",
            entrada=exemplo,
            resultado="Campo preenchido com exemplo.",
        )

    st.session_state.ultimo_exemplo_msg = exemplo

    if usar_bio:
        st.session_state.msg_input = BIO_CURTA
        st.session_state.pop("rewrite_result", None)
        log_event(
            "Mensagens e avaliações",
            "Usar bio curta",
            "OK",
            entrada=BIO_CURTA,
            resultado="Bio curta carregada no campo de mensagem.",
        )
        st.rerun()

    if limpar:
        st.session_state.msg_input = ""
        st.session_state.pop("rewrite_result", None)
        log_event(
            "Mensagens e avaliações",
            "Limpar campo",
            "INFO",
            resultado="Campo de mensagem e resultado foram limpos.",
        )
        st.rerun()

    texto = st.text_area(
        "Cole aqui a mensagem ou avaliação",
        key="msg_input",
        height=150,
        placeholder="Ex.: Pontual, educado, gente boa. Recomendo a carona.",
    )

    tom = st.selectbox(
        "Versão principal",
        ["educado", "persuasivo", "curto", "avaliacao"],
        format_func={
            "educado": "Mais educada",
            "persuasivo": "Mais persuasiva",
            "curto": "Mais curta",
            "avaliacao": "Avaliação BlaBlaCar",
        }.get,
        index=0,
    )

    reformular = st.button("Reformular agora", type="primary", use_container_width=True)

    if reformular:
        log_event(
            "Mensagens e avaliações",
            "Clicar em Reformular agora",
            "INFO",
            entrada=f"Tom: {tom} | Tamanho do texto: {len(texto.strip())}",
            resultado="Botão acionado.",
        )
        if not texto.strip():
            st.warning("Cole uma mensagem primeiro.")
            st.session_state.pop("rewrite_result", None)
            log_event(
                "Mensagens e avaliações",
                "Validar campo de mensagem",
                "AVISO",
                resultado="Campo vazio. Nenhuma reformulação gerada.",
                sugestao="Colar uma mensagem ou avaliação antes de clicar em Reformular.",
            )
        else:
            try:
                st.session_state.rewrite_result = reformular_mensagem(texto, tom=tom)
                log_event(
                    "Mensagens e avaliações",
                    "Gerar reformulação",
                    "OK",
                    entrada=texto,
                    resultado=f"Versões geradas: {len(st.session_state.rewrite_result.variants)}.",
                )
            except Exception as exc:
                log_exception(
                    "Mensagens e avaliações",
                    "Gerar reformulação",
                    exc,
                    entrada=texto,
                    sugestao="Verificar message_rewriter.py e testar o mesmo texto informado pelo usuário.",
                )
                st.error("Falha ao reformular. Baixe o diagnóstico na lateral para corrigir o problema.")

    resultado = st.session_state.get("rewrite_result")
    if resultado and resultado.original:
        st.success("Pronto. Escolha uma versão e copie.")
        st.text_area(
            "Versão principal",
            value=resultado.rewritten,
            height=120,
            key="rewrite_principal",
        )

        for indice, versao in enumerate(resultado.variants, start=1):
            st.markdown(f"**{indice}. {versao.titulo}**")
            st.text_area(
                f"Copiar — {versao.titulo}",
                value=versao.texto,
                height=110,
                key=f"rewrite_variant_{indice}",
            )

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

        log_event(
            "SCAN BLA",
            "Iniciar scanner",
            "INFO",
            entrada=(
                f"link={link or ''}\n"
                f"data={data or ''}\n"
                f"arquivo={arquivo.name if arquivo else ''}\n"
                f"incluir_cheias={incluir_cheias}\n"
                f"navegador_visivel={navegador_visivel}"
            ),
            resultado="Scanner iniciado pelo usuário.",
        )

        data_link = extrair_data_do_link(link or "")
        data_efetiva = (data or "").strip() or data_link

        if data_link:
            st.caption(f"Data detectada no link informado: {data_link}")
            log_event(
                "SCAN BLA",
                "Detectar data no link",
                "OK",
                entrada=link,
                resultado=data_link,
            )

        if arquivo is not None:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(arquivo.name).suffix) as tmp:
                    tmp.write(arquivo.read())
                    tmp_path = tmp.name

                log_event(
                    "SCAN BLA",
                    "Receber arquivo MHTML/HTML",
                    "OK",
                    entrada=arquivo.name,
                    resultado=f"Arquivo salvo temporariamente em {tmp_path}.",
                )

                documento = load_html_or_mhtml_with_source(tmp_path)
                fonte_arquivo_url = documento.source_url
                if fonte_arquivo_url:
                    data_arquivo = extrair_data_do_link(fonte_arquivo_url)
                    st.caption(f"Link detectado no arquivo MHTML: {fonte_arquivo_url}")
                    log_event(
                        "SCAN BLA",
                        "Extrair link do MHTML",
                        "OK",
                        entrada=arquivo.name,
                        resultado=fonte_arquivo_url,
                    )
                    if data_arquivo:
                        st.caption(f"Data detectada no arquivo MHTML: {data_arquivo}")
                        log_event(
                            "SCAN BLA",
                            "Detectar data no MHTML",
                            "OK",
                            entrada=fonte_arquivo_url,
                            resultado=data_arquivo,
                        )
                    if not data_efetiva:
                        data_efetiva = data_arquivo

                _, arquivo_historico = validar_data_entrada(data_efetiva, permite_historico=True)
                if arquivo_historico:
                    st.warning(
                        "Arquivo MHTML histórico: vou extrair e mostrar os dados, mas não vou liberar "
                        "CRIAR/PUBLICAR/MANTER/ALTERAR/EXCLUIR sem uma busca pública atual por data."
                    )
                    log_event(
                        "SCAN BLA",
                        "Detectar arquivo histórico",
                        "AVISO",
                        entrada=data_efetiva,
                        resultado="Arquivo histórico analisado apenas para extração/ranking.",
                        sugestao="Para ação operacional, rodar busca pública atual por rota + data exata.",
                    )

                base_url = link or fonte_arquivo_url or "https://www.blablacar.com.br"
                cards = parse_trip_cards_from_html(documento.html, base_url=base_url)
                validado = bool(cards)
                log_event(
                    "SCAN BLA",
                    "Extrair cards do arquivo",
                    "OK" if validado else "AVISO",
                    entrada=base_url,
                    resultado=f"Caronas encontradas: {len(cards)}.",
                    sugestao="Se zerou, conferir se o arquivo foi salvo a partir da listagem pública correta.",
                )
            except Exception as exc:
                log_exception(
                    "SCAN BLA",
                    "Processar arquivo MHTML/HTML",
                    exc,
                    entrada=arquivo.name,
                    sugestao="Enviar o diagnóstico junto com o arquivo usado para reproduzir a falha.",
                )
                st.error("Falha ao processar o arquivo. Baixe o diagnóstico na lateral para corrigir.")

        elif link:
            validar_data_entrada(data_efetiva, permite_historico=False)
            try:
                cards = scan_sync(link, headless=not navegador_visivel)
                validado = bool(cards)
                log_event(
                    "SCAN BLA",
                    "Abrir busca pública online",
                    "OK" if validado else "AVISO",
                    entrada=link,
                    resultado=f"Caronas encontradas: {len(cards)}.",
                    sugestao="Se não encontrou, conferir rota/data e se a página pública carregou resultados.",
                )
            except Exception as exc:
                st.error(f"Não consegui abrir a busca pública: {exc}")
                log_exception(
                    "SCAN BLA",
                    "Abrir busca pública online",
                    exc,
                    entrada=link,
                    sugestao="Testar o mesmo link público e verificar bloqueio, carregamento ou mudança no site.",
                )

        if not validado or not data_efetiva:
            log_event(
                "SCAN BLA",
                "Validar resultado da busca",
                "AVISO",
                entrada=f"data_efetiva={data_efetiva} | validado={validado}",
                resultado="Busca pública por data não validada.",
                sugestao="Informar link público com data ou enviar MHTML correto da busca por rota + data exata.",
            )
            st.warning("Nenhuma carona pública foi encontrada para esta rota/data ou a página não pôde ser validada.")
            st.warning(resultado_nao_confirmado().status_validacao)
            st.stop()

        st.success(f"Busca carregada. Caronas encontradas: {len(cards)}")
        st.caption(f"Data analisada: {data_efetiva}")
        st.dataframe([card.__dict__ for card in cards], width="stretch")
        log_event(
            "SCAN BLA",
            "Exibir cards extraídos",
            "OK",
            resultado=f"Caronas exibidas na tabela: {len(cards)}.",
        )

        acessiveis = filtrar_caronas_acessiveis(cards, incluir_cheias=incluir_cheias)
        st.write(f"Caronas para abrir por dentro: {len(acessiveis)}")
        log_event(
            "SCAN BLA",
            "Filtrar caronas acessíveis",
            "OK",
            entrada=f"incluir_cheias={incluir_cheias}",
            resultado=f"Acessíveis: {len(acessiveis)} de {len(cards)}.",
        )

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
            log_event(
                "SCAN BLA",
                "Gerar ranking por arquivo histórico",
                "OK",
                resultado=f"Relatório gerado com {len(detalhes)} detalhes simulados por arquivo histórico.",
            )
        elif acessiveis:
            try:
                with st.spinner("Entrando nas caronas para buscar passageiros visíveis..."):
                    detalhes = scrape_many_sync(acessiveis, headless=not navegador_visivel)
                detalhes_com_erro = any(
                    (detalhe.detail_status or "").casefold().startswith("erro ao abrir detalhe")
                    for detalhe in detalhes
                )
                relatorio = gerar_relatorio_markdown(detalhes)
                st.markdown(relatorio)
                st.download_button("Baixar relatório .md", relatorio, file_name="scan_bla_ranking.md")
                log_event(
                    "SCAN BLA",
                    "Abrir caronas por dentro e gerar ranking",
                    "AVISO" if detalhes_com_erro else "OK",
                    resultado=(
                        f"Detalhes analisados: {len(detalhes)}. "
                        f"Houve erro em detalhe: {detalhes_com_erro}."
                    ),
                    sugestao="Se houve erro, baixar o diagnóstico e verificar quais detalhes não abriram.",
                )
            except Exception as exc:
                detalhes_com_erro = True
                log_exception(
                    "SCAN BLA",
                    "Abrir caronas por dentro e gerar ranking",
                    exc,
                    entrada=f"Acessíveis: {len(acessiveis)}",
                    sugestao="Verificar trip_detail_scraper.py e possível mudança na página da BlaBlaCar.",
                )
                st.error("Falha ao abrir caronas por dentro. Baixe o diagnóstico na lateral.")
        else:
            st.info("Nenhuma carona acessível para abertura interna nesta busca.")
            log_event(
                "SCAN BLA",
                "Abrir caronas por dentro",
                "AVISO",
                resultado="Nenhuma carona acessível para abertura interna.",
            )

        if arquivo_historico:
            validacao = resultado_nao_confirmado(
                "Arquivo MHTML histórico analisado. Ação operacional exige busca pública atual por rota + data exata."
            )
            log_event(
                "Validação operacional",
                "Bloquear ação por arquivo histórico",
                "AVISO",
                resultado=validacao.status_validacao,
                sugestao="Rodar busca pública atual antes de recomendar CRIAR/PUBLICAR/MANTER/ALTERAR/EXCLUIR.",
            )
        else:
            try:
                validacao = validar_conflitos(cards, data=data_efetiva)
                log_event(
                    "Validação operacional",
                    "Validar duplicidade e conflito",
                    "OK" if validacao.acao not in {"NAO_CONFIRMADO", "CONFLITO"} else "AVISO",
                    entrada=f"data={data_efetiva} | cards={len(cards)}",
                    resultado=f"Ação={validacao.acao} | Motivo={validacao.motivo}",
                )
            except Exception as exc:
                validacao = resultado_nao_confirmado()
                log_exception(
                    "Validação operacional",
                    "Validar duplicidade e conflito",
                    exc,
                    entrada=f"data={data_efetiva} | cards={len(cards)}",
                    sugestao="Verificar validador_conflito.py e os nomes Ezequiel S / Barbosa nos cards extraídos.",
                )

        if detalhes_com_erro and validacao.acao == "CRIAR":
            validacao = resultado_nao_confirmado()
            st.warning("Abertura interna das caronas falhou. Não vou liberar CRIAR/PUBLICAR sem validação completa.")
            log_event(
                "Validação operacional",
                "Bloquear CRIAR por erro em detalhes",
                "AVISO",
                resultado="Ação alterada para não confirmado.",
                sugestao="Corrigir falha na abertura interna antes de liberar ação operacional.",
            )

        if validacao.acao == "NAO_CONFIRMADO":
            st.warning(validacao.status_validacao)
        elif validacao.acao == "CONFLITO":
            st.error(f"Ação: {validacao.acao} — {validacao.motivo}")
        else:
            st.info(f"Ação: {validacao.acao} — {validacao.motivo}")

        log_event(
            "Resultado final",
            "Exibir ação operacional",
            "OK" if validacao.acao not in {"NAO_CONFIRMADO", "CONFLITO"} else "AVISO",
            resultado=f"Ação: {validacao.acao} — {validacao.motivo}",
        )
