"""Validação de duplicidade e conflito entre contas BlaBlaCar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

Acao = Literal["MANTER", "ALTERAR", "CRIAR", "NAO_CONFIRMADO", "CONFLITO"]


@dataclass(frozen=True)
class ValidacaoResultado:
    acao: Acao
    conta: str | None
    motivo: str
    risco_conflito: str
    status_validacao: str


def normalizar(texto: str | None) -> str:
    return (texto or "").strip().casefold()


def contem_tres_coracoes(*partes: str | None) -> bool:
    texto = " ".join(p or "" for p in partes).casefold()
    return "três corações" in texto or "tres coracoes" in texto


def detectar_conta(nome_motorista: str | None) -> str | None:
    nome = normalizar(nome_motorista)
    if "ezequiel s" in nome:
        return "Ezequiel S"
    if "barbosa" in nome:
        return "Barbosa"
    return None


def resultado_nao_confirmado(motivo: str | None = None) -> ValidacaoResultado:
    return ValidacaoResultado(
        "NAO_CONFIRMADO",
        None,
        motivo or "Busca pública por rota + data exata não validada.",
        "não avaliado",
        "não confirmado / busca pública por data não validada",
    )


def validar_conflitos(cards: Iterable[object], data: str) -> ValidacaoResultado:
    cards_lista = list(cards)
    if not data or not cards_lista:
        return resultado_nao_confirmado()

    motoristas_vazios = [card for card in cards_lista if not normalizar(getattr(card, "driver", None))]
    if motoristas_vazios:
        return resultado_nao_confirmado(
            "Motorista não foi captado em uma ou mais caronas. Não liberar CRIAR/PUBLICAR."
        )

    encontrados: list[tuple[str, object]] = []
    for card in cards_lista:
        conta = detectar_conta(getattr(card, "driver", None))
        if conta:
            encontrados.append((conta, card))

    if not encontrados:
        return ValidacaoResultado(
            "CRIAR",
            None,
            "Nenhuma conta Ezequiel S ou Barbosa localizada na rota/data validada.",
            "baixo",
            "validado",
        )

    contas_tc = {
        conta
        for conta, card in encontrados
        if contem_tres_coracoes(getattr(card, "origin", ""), getattr(card, "destination", ""))
    }

    if "Ezequiel S" in contas_tc and "Barbosa" in contas_tc:
        return ValidacaoResultado(
            "CONFLITO",
            "Ezequiel S / Barbosa",
            f"As duas contas aparecem envolvendo Três Corações em {data}.",
            "alto",
            "validado",
        )

    conta = encontrados[0][0]
    return ValidacaoResultado(
        "MANTER",
        conta,
        f"{conta} já aparece publicado(a). Não criar duplicado.",
        "baixo",
        "validado",
    )
