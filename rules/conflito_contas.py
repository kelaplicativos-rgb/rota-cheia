from __future__ import annotations

import re

from utils.normalizador_texto import sem_acentos


def _norm(texto: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", sem_acentos(texto)).strip().lower()


def _texto_contem_termo(texto: str | None, termo: str | None) -> bool:
    texto_norm = _norm(texto)
    termo_norm = _norm(termo)
    return bool(texto_norm and termo_norm and termo_norm in texto_norm)


def risco_conflito_contas(
    destino: str | None,
    motoristas: list[dict],
    conta_analisada: str | None = None,
    contas_grupo: list[str] | tuple[str, ...] | None = None,
    termos_conflito: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Avalia conflito logistico de forma generica e multiusuario."""
    termos = [str(t).strip() for t in (termos_conflito or []) if str(t).strip()]
    if termos and not any(_texto_contem_termo(destino, termo) for termo in termos):
        return "baixo"

    conta_atual = _norm(conta_analisada)
    contas = [_norm(c) for c in (contas_grupo or []) if _norm(c)]
    contas_outras = [c for c in contas if c != conta_atual]

    if not contas_outras:
        return "baixo"

    publicadas: list[str] = []
    for motorista in motoristas:
        nome = _norm(motorista.get("nome_motorista"))
        if not nome:
            continue
        if any(conta and (conta == nome or conta in nome or nome in conta) for conta in contas_outras):
            publicadas.append(str(motorista.get("nome_motorista") or "conta do grupo"))

    if publicadas:
        termo_txt = ", ".join(termos) if termos else "termo/cidade configurado"
        nomes = ", ".join(dict.fromkeys(publicadas))
        return f"alto: outra conta do grupo ja aparece nesta data para {termo_txt}: {nomes}"

    return "baixo"


def risco_conflito_tres_coracoes(destino: str | None, motoristas: list[dict], conta_analisada: str | None = None) -> str:
    """Compatibilidade com versoes antigas."""
    return risco_conflito_contas(
        destino=destino,
        motoristas=motoristas,
        conta_analisada=conta_analisada,
        contas_grupo=[conta_analisada] if conta_analisada else [],
        termos_conflito=["Três Corações"],
    )
