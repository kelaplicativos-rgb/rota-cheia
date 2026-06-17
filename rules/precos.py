from __future__ import annotations

from statistics import median


def sugerir_preco(motoristas: list[dict]) -> str:
    precos = [m.get("preco") for m in motoristas if isinstance(m.get("preco"), (int, float))]
    if not precos:
        return "não sugerido: preços não detectados"

    valor = round(float(median(precos)))
    menor = round(float(min(precos)))
    maior = round(float(max(precos)))

    if len(precos) == 1:
        return f"R$ {valor},00 baseado no único preço detectado"
    return f"R$ {valor},00 baseado na mediana da concorrência; faixa detectada R$ {menor},00 a R$ {maior},00"
