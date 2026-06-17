from __future__ import annotations

from utils.normalizador_texto import contem_tres_coracoes


def risco_conflito_tres_coracoes(destino: str | None, motoristas: list[dict], conta_analisada: str | None = None) -> str:
    if not contem_tres_coracoes(destino):
        return "baixo"

    conta = (conta_analisada or "").strip().lower()
    tem_ezequiel = any(m.get("eh_ezequiel") for m in motoristas)
    tem_barbosa = any(m.get("eh_barbosa") for m in motoristas)

    if tem_ezequiel and tem_barbosa:
        return "alto: Ezequiel S e Barbosa aparecem na mesma data para Três Corações"

    if conta == "barbosa" and tem_ezequiel:
        return "alto: Ezequiel S já aparece em Três Corações nesta data; Barbosa não deve publicar/ir para lá"

    if conta == "ezequiel s" and tem_barbosa:
        return "alto: Barbosa já aparece em Três Corações nesta data; Ezequiel S não deve publicar/ir para lá"

    if tem_ezequiel:
        return "atenção: Ezequiel S já aparece em Três Corações nesta data"
    if tem_barbosa:
        return "atenção: Barbosa já aparece em Três Corações nesta data"
    return "baixo"
