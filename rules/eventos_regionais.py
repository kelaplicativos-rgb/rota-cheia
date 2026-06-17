from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from utils.normalizador_texto import sem_acentos


@dataclass
class EventoRegional:
    nome: str
    cidade: str
    data_inicio: str
    data_fim: str | None = None
    peso: int = 20
    fonte: str = "manual"

    def to_dict(self) -> dict:
        return asdict(self)


def _to_date(valor: str | date | datetime | None) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.fromisoformat(str(valor)).date()


def _normalizar_evento(evento: dict) -> EventoRegional | None:
    nome = str(evento.get("nome") or evento.get("evento") or "").strip()
    cidade = str(evento.get("cidade") or evento.get("localidade") or "").strip()
    data_inicio = str(evento.get("data_inicio") or evento.get("data") or "").strip()
    if not nome or not cidade or not data_inicio:
        return None
    data_fim = evento.get("data_fim") or data_inicio
    try:
        peso = int(evento.get("peso") or 20)
    except Exception:
        peso = 20
    return EventoRegional(
        nome=nome,
        cidade=cidade,
        data_inicio=data_inicio,
        data_fim=str(data_fim) if data_fim else data_inicio,
        peso=max(1, min(peso, 100)),
        fonte=str(evento.get("fonte") or "manual"),
    )


def normalizar_eventos(eventos: list[dict] | None) -> list[dict]:
    saida = []
    for evento in eventos or []:
        normalizado = _normalizar_evento(evento)
        if normalizado:
            saida.append(normalizado.to_dict())
    return saida


def eventos_relevantes_para_data(
    eventos: list[dict] | None,
    data_viagem: str | date | datetime,
    localidades: list[str] | None = None,
    janela_dias: int = 2,
) -> list[dict]:
    alvo = _to_date(data_viagem)
    if not alvo:
        return []

    localidades_norm = [sem_acentos(item) for item in localidades or [] if item]
    relevantes = []
    for evento in normalizar_eventos(eventos):
        inicio = _to_date(evento.get("data_inicio"))
        fim = _to_date(evento.get("data_fim")) or inicio
        if not inicio or not fim:
            continue

        dentro_janela = inicio - timedelta(days=janela_dias) <= alvo <= fim + timedelta(days=janela_dias)
        if not dentro_janela:
            continue

        cidade_norm = sem_acentos(evento.get("cidade"))
        if localidades_norm and not any(loc in cidade_norm or cidade_norm in loc for loc in localidades_norm):
            continue

        relevantes.append(evento)

    return relevantes


def score_eventos_regionais(
    eventos: list[dict] | None,
    data_viagem: str | date | datetime,
    localidades: list[str] | None = None,
) -> int:
    relevantes = eventos_relevantes_para_data(eventos, data_viagem, localidades)
    return min(100, sum(int(evento.get("peso") or 0) for evento in relevantes))
