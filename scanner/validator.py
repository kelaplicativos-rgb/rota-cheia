from __future__ import annotations

from dataclasses import dataclass


MENSAGEM_NAO_VALIDADO = "não confirmado / busca pública por data não validada"


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
    if not origem:
        motivos.append("origem não detectada")
    if not destino:
        motivos.append("destino não detectado")
    if not data:
        motivos.append("data não detectada")
    if origem_esperada and origem and origem_esperada.lower() not in origem.lower():
        motivos.append("origem diferente da informada")
    if destino_esperado and destino and destino_esperado.lower() not in destino.lower():
        motivos.append("destino diferente do informado")
    if data_esperada and data and data_esperada != data:
        motivos.append("data diferente da informada")

    valido = not motivos
    return ValidationResult(
        valido=valido,
        status="busca pública por rota + data validada" if valido else MENSAGEM_NAO_VALIDADO,
        motivos=motivos,
    )
