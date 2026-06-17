from __future__ import annotations

from datetime import date, datetime
from dateutil import parser as date_parser


def parse_data(valor: str | None) -> str | None:
    if not valor:
        return None
    try:
        return date_parser.parse(valor, dayfirst=True).date().isoformat()
    except Exception:
        return None


def hoje_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def nome_dia_semana(data_iso: str | None) -> str:
    if not data_iso:
        return ""
    nomes = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    try:
        return nomes[date.fromisoformat(data_iso).weekday()]
    except Exception:
        return ""
