from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from config.caronas_config import (
    DESTINOS_IGNORADOS,
    PUBLIC_ALLOWED_HOSTS,
    PUBLIC_ALLOWED_PATHS,
    STATUS_NAO_VALIDADO,
)
from utils.normalizador_texto import sem_acentos

MENSAGEM_NAO_VALIDADO = STATUS_NAO_VALIDADO


@dataclass
class ValidationResult:
    valido: bool
    status: str
    motivos: list[str]


def validar_busca_publica(parsed: dict, origem_esperada: str | None, destino_esperado: str | None, data_esperada: str | None) -> ValidationResult:
    motivos: list[str] = []
    link = parsed.get("link_busca")
    origem = parsed.get("origem")
    destino = parsed.get("destino")
    data = parsed.get("data_viagem")

    if not link:
        motivos.append("link não detectado")
    elif not _link_publico_blablacar_valido(link):
        motivos.append("link público da BlaBlaCar inválido")

    if not origem:
        motivos.append("origem não detectada")
    if not destino:
        motivos.append("destino não detectado")
    if not data:
        motivos.append("data não detectada")

    if _destino_ignorado(destino) or _destino_ignorado(destino_esperado):
        motivos.append("destino ignorado: Caxambu")

    if origem_esperada and origem and not _lugares_compativeis(origem_esperada, origem):
        motivos.append("origem diferente da informada")
    if destino_esperado and destino and not _lugares_compativeis(destino_esperado, destino):
        motivos.append("destino diferente do informado")
    if data_esperada and data and data_esperada != data:
        motivos.append("data diferente da informada")

    valido = not motivos
    return ValidationResult(
        valido=valido,
        status="busca pública por rota + data validada" if valido else MENSAGEM_NAO_VALIDADO,
        motivos=motivos,
    )


def _link_publico_blablacar_valido(link: str | None) -> bool:
    if not link:
        return False
    try:
        parsed = urlparse(str(link).replace("&amp;", "&"))
    except Exception:
        return False

    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"

    if host not in PUBLIC_ALLOWED_HOSTS:
        return False

    return any(path == allowed or path.startswith(f"{allowed}/") for allowed in PUBLIC_ALLOWED_PATHS)


def _normalizar_lugar(texto: str | None) -> str:
    normalizado = sem_acentos(texto)
    normalizado = normalizado.replace("sao thome", "sao tome")
    normalizado = re.sub(r"[^a-z0-9]+", " ", normalizado)
    tokens = [token for token in normalizado.split() if token not in {"brasil"}]
    return " ".join(tokens)


def _lugares_compativeis(esperado: str | None, detectado: str | None) -> bool:
    esperado_norm = _normalizar_lugar(esperado)
    detectado_norm = _normalizar_lugar(detectado)
    if not esperado_norm or not detectado_norm:
        return False
    if esperado_norm in detectado_norm or detectado_norm in esperado_norm:
        return True

    esperado_tokens = set(esperado_norm.split())
    detectado_tokens = set(detectado_norm.split())
    return esperado_tokens.issubset(detectado_tokens) or detectado_tokens.issubset(esperado_tokens)


def _destino_ignorado(texto: str | None) -> bool:
    texto_norm = _normalizar_lugar(texto)
    return any(_normalizar_lugar(destino) in texto_norm for destino in DESTINOS_IGNORADOS)
