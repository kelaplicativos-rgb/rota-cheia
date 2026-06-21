from __future__ import annotations

from datetime import date
import json
from typing import Any

import streamlit as st

from eventos_movimentados import (
    CIDADES_IGNORADAS,
    CIDADES_PRIORITARIAS,
    ORIGENS_PADRAO,
    STATUS_BLA_PENDENTE,
    descobrir_eventos_movimentados,
    gerar_datas,
    gerar_relatorio_eventos_markdown,
    montar_links_busca_eventos,
    montar_pacote_para_scan_bla,
    parse_fontes_coladas,
)

try:
    from diagnostics import init_diagnostics, log_event, log_exception, render_diagnostics_panel
except Exception:
    def init_diagnostics() -> None:
        return None

    def render_diagnostics_panel() -> None:
        return None

    def log_event(*args: Any, **kwargs: Any) -> None:
        return None

    def log_exception(*args: Any, **kwargs: Any) -> None:
        return None

try:
    st.set_page_config(page_title="Radar de Eventos", page_icon="🎪", layout="wide")
except Exception:
    pass

init_diagnostics()
render_diagnostics_panel()

st.title("🎪 Radar de Eventos Movimentados")
st.caption("Potencial de demanda por eventos antes do SCAN BLA.")
st.warning(
    "Evento forte não libera CRIAR/PUBLICAR. Primeiro valide a busca pública BlaBlaCar por rota + data exata e procure Ezequiel S / Barbosa."
)

with st.form("form_eventos"):
    data_base = st.date_input("Data inicial", value=date.today())
    janela_dias = st.selectbox("Janela de busca", [3, 7, 14, 21, 31], index=1)
    origem = st.selectbox("Origem", ORIGENS_PADRAO, index=0)
    destino_final = st.selectbox(
        "Destino final",
        CIDADES_PRIORITARIAS,
        index=CIDADES_PRIORITARIAS.index("São Tomé das Letras/MG"),
    )
    trechos = st.multiselect(
        "Trechos considerados",
        CIDADES_PRIORITARIAS,
        default=["Extrema/MG", "Pouso Alegre/MG", "Três Corações/MG", "Varginha/MG", "São Tomé das Letras/MG"],
    )
    st.caption(f"Bloqueado: {', '.join(CIDADES_IGNORADAS)}")
    fontes_texto = st.text_area(
        "Cole eventos/fontes encontrados",
        height=180,
        placeholder="cidade | título | resumo | link | fonte",
    )
    analisar = st.form_submit_button("Analisar eventos", type="primary", use_container_width=True)

cidades = list(dict.fromkeys([*trechos, destino_final]))
datas = gerar_datas(data_base, janela_dias)

st.subheader("Consultas sugeridas")
consultas = []
for cidade in cidades:
    if cidade not in CIDADES_IGNORADAS:
        consultas.extend(montar_links_busca_eventos(cidade, datas))
st.dataframe(consultas, width="stretch")

if analisar:
    fontes = parse_fontes_coladas(fontes_texto, cidade_padrao=destino_final)
    pacote_scan = montar_pacote_para_scan_bla(
        origem=origem,
        destino_final=destino_final,
        intermediarias=trechos,
        data=data_base,
    )
    try:
        eventos = descobrir_eventos_movimentados(
            data_base=data_base,
            janela_dias=janela_dias,
            cidades=cidades,
            origem=origem,
            destino_final=destino_final,
            intermediarias=trechos,
            fontes=fontes,
        )
        log_event(
            "Radar de Eventos",
            "Analisar eventos",
            "OK",
            entrada=json.dumps({"fontes": len(fontes)}, ensure_ascii=False),
            resultado=f"Eventos classificados: {len(eventos)} | {STATUS_BLA_PENDENTE}",
        )
    except Exception as exc:
        log_exception("Radar de Eventos", "Analisar eventos", exc)
        st.error("Falha ao analisar eventos. Baixe o diagnóstico.")
        st.stop()

    if not fontes:
        st.warning("Cole pelo menos uma fonte/evento para analisar.")
    elif not eventos:
        st.warning("Nenhum evento forte foi classificado com as fontes coladas.")
    else:
        st.success(f"Eventos analisados: {len(eventos)}")
        st.dataframe(eventos, width="stretch")
        relatorio = gerar_relatorio_eventos_markdown(eventos)
        st.download_button(
            "Baixar relatório .md",
            relatorio,
            file_name="radar_eventos_movimentados.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.subheader("Pacote obrigatório para SCAN BLA")
    st.code(json.dumps(pacote_scan, ensure_ascii=False, indent=2), language="json")
    st.warning(STATUS_BLA_PENDENTE)
