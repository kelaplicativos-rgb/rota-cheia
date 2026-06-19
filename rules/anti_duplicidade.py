from __future__ import annotations

import re

from utils.normalizador_texto import sem_acentos


def _normalizar_nome(nome: str | None) -> str:
    return re.sub(r"\s+", " ", sem_acentos(nome)).strip().lower()


def _conta_match(motorista: dict, conta: str) -> bool:
    conta_normalizada = _normalizar_nome(conta)
    if not conta_normalizada:
        return False
    if motorista.get("eh_conta_ativa"):
        return True
    nome = _normalizar_nome(motorista.get("nome_motorista"))
    if not nome:
        return False
    return nome == conta_normalizada or conta_normalizada in nome or nome in conta_normalizada


def publicacao_da_conta(motoristas: list[dict], conta: str) -> dict | None:
    for motorista in motoristas:
        if _conta_match(motorista, conta):
            return motorista
    return None


def existe_publicacao_da_conta(motoristas: list[dict], conta: str) -> bool:
    return publicacao_da_conta(motoristas, conta) is not None


def horario_publicado_da_conta(motoristas: list[dict], conta: str) -> str | None:
    motorista = publicacao_da_conta(motoristas, conta)
    return motorista.get("horario") if motorista else None


def preco_publicado_da_conta(motoristas: list[dict], conta: str) -> float | None:
    motorista = publicacao_da_conta(motoristas, conta)
    preco = motorista.get("preco") if motorista else None
    return float(preco) if isinstance(preco, (int, float)) else None
