from __future__ import annotations

from utils.normalizador_texto import contem_tres_coracoes


def risco_conflito_tres_coracoes(destino: str | None, motoristas: list[dict]) -> str:
    if not contem_tres_coracoes(destino):
        return "baixo"

    tem_ezequiel = any(m.get("eh_ezequiel") for m in motoristas)
    tem_barbosa = any(m.get("eh_barbosa") for m in motoristas)

    if tem_ezequiel and tem_barbosa:
        return "alto: Ezequiel S e Barbosa aparecem na mesma data para Três Corações"
    if tem_ezequiel:
        return "atenção: Ezequiel S já aparece em Três Corações nesta data"
    if tem_barbosa:
        return "atenção: Barbosa já aparece em Três Corações nesta data"
    return "baixo"
