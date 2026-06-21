"""Reformulação simples de mensagens e avaliações para BlaBlaCar."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Tom = Literal["curto", "educado", "persuasivo", "avaliacao"]


@dataclass(frozen=True)
class RewriteResult:
    original: str
    rewritten: str
    tom: Tom


BIO_CURTA = (
    "Assim que reservar, chamo para combinar direitinho. "
    "Aviso quando estiver a caminho. Aceito Pix ou dinheiro. "
    "Embarque/desembarque em trevos ou postos na rodovia."
)


def _limpar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def reformular_mensagem(texto: str, tom: Tom = "educado") -> RewriteResult:
    original = _limpar_texto(texto)
    if not original:
        return RewriteResult(original="", rewritten="", tom=tom)

    base = original[0].upper() + original[1:]
    if tom == "curto":
        saida = f"{base} 👍"
    elif tom == "persuasivo":
        saida = (
            f"{base}\n\n"
            "Pode ficar tranquilo(a): assim que eu estiver a caminho, aviso você "
            "e combino certinho o ponto de embarque."
        )
    elif tom == "avaliacao":
        saida = "Pessoa tranquila, educada e pontual. Recomendo para a comunidade BlaBlaCar."
        if len(original) > 25:
            saida = f"{base}. Recomendo com certeza para a comunidade BlaBlaCar."
    else:
        saida = f"{base}\n\nQualquer dúvida pode me chamar. Assim que eu estiver a caminho, aviso por aqui."
    return RewriteResult(original=original, rewritten=saida.strip(), tom=tom)
