"""Diagnóstico por ação/etapa para o app Rota Cheia.

Objetivo:
- registrar cada ação importante do usuário;
- guardar entradas, resultados, erros e sugestões;
- permitir baixar um log TXT para correção rápida.

O módulo usa st.session_state para funcionar no Streamlit sem banco de dados.
"""

from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

import streamlit as st

Status = Literal["INFO", "OK", "AVISO", "ERRO"]
APP_TZ = ZoneInfo("America/Sao_Paulo")
SESSION_KEY = "diagnostic_events"


@dataclass(frozen=True)
class DiagnosticEvent:
    timestamp: str
    etapa: str
    acao: str
    status: Status
    entrada: str = ""
    resultado: str = ""
    detalhe: str = ""
    sugestao: str = ""


def _now() -> str:
    return datetime.now(APP_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _safe_text(value: Any, *, limit: int = 1400) -> str:
    if value is None:
        return ""
    try:
        text = str(value)
    except Exception:
        text = repr(value)
    text = text.replace("\r", " ").strip()
    if len(text) > limit:
        return text[:limit] + "... [cortado]"
    return text


def init_diagnostics() -> None:
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = []


def log_event(
    etapa: str,
    acao: str,
    status: Status = "INFO",
    *,
    entrada: Any = "",
    resultado: Any = "",
    detalhe: Any = "",
    sugestao: str = "",
) -> DiagnosticEvent:
    init_diagnostics()
    event = DiagnosticEvent(
        timestamp=_now(),
        etapa=_safe_text(etapa, limit=160),
        acao=_safe_text(acao, limit=220),
        status=status,
        entrada=_safe_text(entrada),
        resultado=_safe_text(resultado),
        detalhe=_safe_text(detalhe, limit=2400),
        sugestao=_safe_text(sugestao, limit=700),
    )
    st.session_state[SESSION_KEY].append(asdict(event))
    return event


def log_exception(
    etapa: str,
    acao: str,
    exc: BaseException,
    *,
    entrada: Any = "",
    sugestao: str = "Verificar a etapa indicada no log e reproduzir o fluxo com o mesmo texto/link/arquivo.",
) -> DiagnosticEvent:
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return log_event(
        etapa,
        acao,
        "ERRO",
        entrada=entrada,
        resultado=f"{type(exc).__name__}: {exc}",
        detalhe=detail,
        sugestao=sugestao,
    )


def get_events() -> list[dict[str, str]]:
    init_diagnostics()
    return list(st.session_state[SESSION_KEY])


def clear_events() -> None:
    st.session_state[SESSION_KEY] = []
    log_event(
        "Diagnóstico",
        "Limpar log",
        "INFO",
        resultado="Log anterior limpo e novo diagnóstico iniciado.",
    )


def build_report() -> str:
    events = get_events()
    lines: list[str] = []
    lines.append("DIAGNÓSTICO ROTA CHEIA")
    lines.append(f"Gerado em: {_now()}")
    lines.append(f"Total de eventos: {len(events)}")
    lines.append("=" * 72)

    if not events:
        lines.append("Nenhum evento registrado nesta sessão.")
        return "\n".join(lines)

    for idx, item in enumerate(events, start=1):
        lines.append(f"\n#{idx} [{item.get('status', '')}] {item.get('timestamp', '')}")
        lines.append(f"Etapa: {item.get('etapa', '')}")
        lines.append(f"Ação: {item.get('acao', '')}")
        if item.get("entrada"):
            lines.append("Entrada:")
            lines.append(item["entrada"])
        if item.get("resultado"):
            lines.append("Resultado:")
            lines.append(item["resultado"])
        if item.get("detalhe"):
            lines.append("Detalhe técnico:")
            lines.append(item["detalhe"])
        if item.get("sugestao"):
            lines.append("Sugestão de correção:")
            lines.append(item["sugestao"])
        lines.append("-" * 72)

    return "\n".join(lines)


def render_diagnostics_panel() -> None:
    init_diagnostics()
    events = get_events()
    error_count = sum(1 for item in events if item.get("status") == "ERRO")
    warning_count = sum(1 for item in events if item.get("status") == "AVISO")

    with st.sidebar.expander("🧪 Diagnóstico da sessão", expanded=False):
        st.caption(f"Eventos: {len(events)} | Erros: {error_count} | Avisos: {warning_count}")
        if events:
            ultimo = events[-1]
            st.write(f"Última etapa: **{ultimo.get('etapa', '')}**")
            st.write(f"Status: **{ultimo.get('status', '')}**")
            if ultimo.get("resultado"):
                st.caption(ultimo["resultado"][:280])

        st.download_button(
            "Baixar diagnóstico .txt",
            build_report(),
            file_name="diagnostico_rota_cheia.txt",
            mime="text/plain",
            width="stretch",
        )

        if st.button("Limpar diagnóstico", width="stretch"):
            clear_events()
            st.rerun()
