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


def validar_conflitos(cards: Iterable[object], data: str) -> ValidacaoResultado:
    encontrados: list[tuple[str, object]] = []
    for card in cards:
        conta = detectar_conta(getattr(card, "driver", None))
        if conta:
            encontrados.append((conta, card))

    if not encontrados:
        return ValidacaoResultado("CRIAR", None, "Nenhuma conta Ezequiel S ou Barbosa localizada na rota/data validada.", "baixo", "validado")

    contas_tc = {
        conta
        for conta, card in encontrados
        if contem_tres_coracoes(getattr(card, "origin", ""), getattr(card, "destination", ""))
    }

    if "Ezequiel S" in contas_tc and "Barbosa" in contas_tc:
        return ValidacaoResultado("CONFLITO", "Ezequiel S / Barbosa", f"As duas contas aparecem envolvendo Três Corações em {data}.", "alto", "validado")

    conta = encontrados[0][0]
    return ValidacaoResultado("MANTER", conta, f"{conta} já aparece publicado(a). Não criar duplicado.", "baixo", "validado")


def resultado_nao_confirmado() -> ValidacaoResultado:
    return ValidacaoResultado("NAO_CONFIRMADO", None, "Busca pública por rota + data exata não validada.", "não avaliado", "não confirmado / busca pública por data não validada")
