from __future__ import annotations


def existe_publicacao_da_conta(motoristas: list[dict], conta: str) -> bool:
    conta_normalizada = (conta or "").strip().lower()
    for motorista in motoristas:
        if conta_normalizada == "ezequiel s" and motorista.get("eh_ezequiel"):
            return True
        if conta_normalizada == "barbosa" and motorista.get("eh_barbosa"):
            return True
    return False


def horario_publicado_da_conta(motoristas: list[dict], conta: str) -> str | None:
    conta_normalizada = (conta or "").strip().lower()
    for motorista in motoristas:
        if conta_normalizada == "ezequiel s" and motorista.get("eh_ezequiel"):
            return motorista.get("horario")
        if conta_normalizada == "barbosa" and motorista.get("eh_barbosa"):
            return motorista.get("horario")
    return None
