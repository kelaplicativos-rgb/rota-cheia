"""Geração de rankings a partir dos passageiros visíveis."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

from trip_detail_scraper import TripDetail


@dataclass
class RankingResultado:
    destinos: list[tuple[str, int]] = field(default_factory=list)
    origens: list[tuple[str, int]] = field(default_factory=list)
    horarios: list[tuple[str, int]] = field(default_factory=list)
    motoristas: list[tuple[str, int]] = field(default_factory=list)
    precos: list[tuple[str, int]] = field(default_factory=list)
    total_passageiros_estimado: int = 0


def gerar_rankings(details: Iterable[TripDetail]) -> RankingResultado:
    destinos: Counter[str] = Counter()
    origens: Counter[str] = Counter()
    horarios: Counter[str] = Counter()
    motoristas: Counter[str] = Counter()
    precos: Counter[str] = Counter()
    total = 0
    for detail in details:
        card = detail.card
        for passenger in detail.passengers:
            count = passenger.estimated_count
            total += count
            if passenger.destination:
                destinos[passenger.destination] += count
            if passenger.origin:
                origens[passenger.origin] += count
            if card.departure_time:
                horarios[card.departure_time] += count
            if card.driver:
                motoristas[card.driver] += count
            if card.price:
                precos[card.price] += count
    return RankingResultado(destinos.most_common(), origens.most_common(), horarios.most_common(), motoristas.most_common(), precos.most_common(), total)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_Sem dados públicos visíveis._"
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return "\n".join([head, sep, body])


def gerar_relatorio_markdown(details: list[TripDetail]) -> str:
    ranking = gerar_rankings(details)
    linhas: list[str] = ["# SCAN BLA — Ranking por passageiros"]
    linhas.append(f"Total estimado de passageiros visíveis: **{ranking.total_passageiros_estimado}**")
    linhas.append("\n## Destinos mais procurados")
    linhas.append(_table(["Destino", "Passageiros"], [[k, str(v)] for k, v in ranking.destinos]))
    linhas.append("\n## Origens mais fortes")
    linhas.append(_table(["Origem", "Passageiros"], [[k, str(v)] for k, v in ranking.origens]))
    linhas.append("\n## Horários com mais passageiros")
    linhas.append(_table(["Horário", "Passageiros"], [[k, str(v)] for k, v in ranking.horarios]))
    linhas.append("\n## Motoristas com mais passageiros")
    linhas.append(_table(["Motorista", "Passageiros"], [[k, str(v)] for k, v in ranking.motoristas]))
    linhas.append("\n## Passageiros visíveis por carona")
    rows: list[list[str]] = []
    for detail in details:
        for p in detail.passengers:
            rows.append([detail.card.driver, detail.card.departure_time, p.name, p.origin, p.destination, str(p.estimated_count), detail.card.price])
    linhas.append(_table(["Motorista", "Horário", "Passageiro", "Origem", "Destino", "Qtd", "Preço"], rows))
    erros = [d for d in details if not d.passengers]
    if erros:
        linhas.append("\n## Caronas sem passageiros visíveis ou com erro")
        linhas.append(_table(["Motorista", "Horário", "Status"], [[d.card.driver, d.card.departure_time, d.detail_status] for d in erros]))
    return "\n".join(linhas)
