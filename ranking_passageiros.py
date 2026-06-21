"""Geração de rankings a partir dos passageiros visíveis e sinais públicos.

A BlaBlaCar nem sempre expõe passageiros na página pública. Quando isso
acontece, o relatório não pode ficar vazio: ele deve usar os sinais públicos da
listagem, como horário, destino, preço, motorista, status cheio e esgotará em
breve.
"""

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


@dataclass
class SinaisPublicosResultado:
    total_caronas: int = 0
    total_com_passageiros_visiveis: int = 0
    total_sem_passageiros_visiveis: int = 0
    cheias: int = 0
    esgotara: int = 0
    horarios_pressao: list[tuple[str, int]] = field(default_factory=list)
    destinos_recorrentes: list[tuple[str, int]] = field(default_factory=list)
    origens_recorrentes: list[tuple[str, int]] = field(default_factory=list)
    motoristas_recorrentes: list[tuple[str, int]] = field(default_factory=list)
    precos_praticados: list[tuple[str, int]] = field(default_factory=list)
    status_publicos: list[tuple[str, int]] = field(default_factory=list)
    linhas_caronas: list[list[str]] = field(default_factory=list)


def _texto(obj: object, attr: str) -> str:
    return str(getattr(obj, attr, "") or "").strip()


def _peso_status(status: str) -> int:
    status_low = (status or "").casefold()
    if "cheio" in status_low:
        return 5
    if "esgot" in status_low:
        return 4
    return 1


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
            if _texto(card, "departure_time"):
                horarios[_texto(card, "departure_time")] += count
            if _texto(card, "driver"):
                motoristas[_texto(card, "driver")] += count
            if _texto(card, "price"):
                precos[_texto(card, "price")] += count
    return RankingResultado(destinos.most_common(), origens.most_common(), horarios.most_common(), motoristas.most_common(), precos.most_common(), total)


def gerar_sinais_publicos(details: Iterable[TripDetail]) -> SinaisPublicosResultado:
    detalhes = list(details)
    horarios: Counter[str] = Counter()
    destinos: Counter[str] = Counter()
    origens: Counter[str] = Counter()
    motoristas: Counter[str] = Counter()
    precos: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    linhas: list[list[str]] = []
    cheias = 0
    esgotara = 0
    com_passageiros = 0

    for detail in detalhes:
        card = detail.card
        status = _texto(card, "status") or "Disponível"
        peso = _peso_status(status)
        if detail.passengers:
            com_passageiros += 1
        if "cheio" in status.casefold():
            cheias += 1
        if "esgot" in status.casefold():
            esgotara += 1

        horario = _texto(card, "departure_time") or "sem horário"
        origem = _texto(card, "origin") or "origem não captada"
        destino = _texto(card, "destination") or "destino não captado"
        motorista = _texto(card, "driver") or "motorista não captado"
        preco = _texto(card, "price") or "preço não captado"

        horarios[horario] += peso
        destinos[destino] += peso
        origens[origem] += peso
        motoristas[motorista] += 1
        precos[preco] += 1
        status_counter[status] += 1
        linhas.append([horario, origem, destino, motorista, preco, status, str(peso), detail.detail_status or "-"])

    return SinaisPublicosResultado(
        total_caronas=len(detalhes),
        total_com_passageiros_visiveis=com_passageiros,
        total_sem_passageiros_visiveis=max(0, len(detalhes) - com_passageiros),
        cheias=cheias,
        esgotara=esgotara,
        horarios_pressao=horarios.most_common(),
        destinos_recorrentes=destinos.most_common(),
        origens_recorrentes=origens.most_common(),
        motoristas_recorrentes=motoristas.most_common(),
        precos_praticados=precos.most_common(),
        status_publicos=status_counter.most_common(),
        linhas_caronas=linhas,
    )


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_Sem dados públicos visíveis._"
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return "\n".join([head, sep, body])


def _rows_counter(counter_rows: list[tuple[str, int]], col1: str, col2: str = "Pontuação") -> str:
    return _table([col1, col2], [[k, str(v)] for k, v in counter_rows])


def gerar_relatorio_markdown(details: list[TripDetail]) -> str:
    ranking = gerar_rankings(details)
    sinais = gerar_sinais_publicos(details)
    linhas: list[str] = ["# SCAN BLA — Ranking público"]
    linhas.append(f"Caronas públicas analisadas: **{sinais.total_caronas}**")
    linhas.append(f"Total estimado de passageiros visíveis: **{ranking.total_passageiros_estimado}**")
    linhas.append(f"Caronas com passageiros visíveis: **{sinais.total_com_passageiros_visiveis}**")
    linhas.append(f"Caronas sem passageiros visíveis: **{sinais.total_sem_passageiros_visiveis}**")
    linhas.append(f"Caronas cheias: **{sinais.cheias}**")
    linhas.append(f"Caronas com 'esgotará em breve': **{sinais.esgotara}**")

    if ranking.total_passageiros_estimado == 0 and sinais.total_caronas:
        linhas.append(
            "\n> A BlaBlaCar não expôs passageiros visíveis nesta execução. "
            "O ranking abaixo usa sinais públicos de demanda: horário, destino, preço, motorista, "
            "status cheio e esgotará em breve."
        )

    linhas.append("\n## Horários com maior pressão pública")
    linhas.append(_rows_counter(sinais.horarios_pressao, "Horário"))
    linhas.append("\n## Destinos mais recorrentes nas caronas públicas")
    linhas.append(_rows_counter(sinais.destinos_recorrentes, "Destino"))
    linhas.append("\n## Origens mais recorrentes nas caronas públicas")
    linhas.append(_rows_counter(sinais.origens_recorrentes, "Origem"))
    linhas.append("\n## Status públicos encontrados")
    linhas.append(_rows_counter(sinais.status_publicos, "Status", "Caronas"))
    linhas.append("\n## Preços praticados")
    linhas.append(_rows_counter(sinais.precos_praticados, "Preço", "Caronas"))
    linhas.append("\n## Motoristas/carros encontrados")
    linhas.append(_rows_counter(sinais.motoristas_recorrentes, "Motorista", "Caronas"))
    linhas.append("\n## Caronas públicas captadas")
    linhas.append(_table(["Horário", "Origem", "Destino", "Motorista", "Preço", "Status", "Peso", "Detalhe"], sinais.linhas_caronas))

    if ranking.total_passageiros_estimado > 0:
        linhas.append("\n## Destinos mais procurados por passageiros visíveis")
        linhas.append(_table(["Destino", "Passageiros"], [[k, str(v)] for k, v in ranking.destinos]))
        linhas.append("\n## Origens mais fortes por passageiros visíveis")
        linhas.append(_table(["Origem", "Passageiros"], [[k, str(v)] for k, v in ranking.origens]))
        linhas.append("\n## Horários com mais passageiros visíveis")
        linhas.append(_table(["Horário", "Passageiros"], [[k, str(v)] for k, v in ranking.horarios]))
        linhas.append("\n## Motoristas com mais passageiros visíveis")
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
