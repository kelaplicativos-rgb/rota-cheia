from __future__ import annotations

import re
import unicodedata


STATUS_NIVEIS_BLOQUEADOS = (
    "4.9",
    "super driver",
    "embaixador",
    "expert",
)


def limpar_espacos(texto: str | None) -> str:
    if not texto:
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()


def sem_acentos(texto: str | None) -> str:
    texto_limpo = limpar_espacos(texto).lower()
    return "".join(
        char for char in unicodedata.normalize("NFD", texto_limpo)
        if unicodedata.category(char) != "Mn"
    )


def contem_ezequiel(texto: str | None) -> bool:
    normalizado = sem_acentos(texto)
    return bool(re.search(r"\bezequiel\s+s\b", normalizado))


def contem_barbosa(texto: str | None) -> bool:
    normalizado = sem_acentos(texto)
    return bool(re.search(r"\bbarbosa\b", normalizado))


def contem_tres_coracoes(texto: str | None) -> bool:
    normalizado = sem_acentos(texto)
    return "tres coracoes" in normalizado or "três corações" in limpar_espacos(texto).lower()


def remover_status_como_nome(nome: str | None) -> str:
    texto = limpar_espacos(nome)
    normalizado = sem_acentos(texto)
    for status in STATUS_NIVEIS_BLOQUEADOS:
        normalizado = normalizado.replace(status, "")
    return limpar_espacos(normalizado)
