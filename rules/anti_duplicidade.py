from __future__ import annotations


def _conta_match(motorista: dict, conta: str) -> bool:
    conta_normalizada = (conta or "").strip().lower()
    if conta_normalizada == "ezequiel s":
        return bool(motorista.get("eh_ezequiel"))
    if conta_normalizada == "barbosa":
        return bool(motorista.get("eh_barbosa"))
    return False


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
