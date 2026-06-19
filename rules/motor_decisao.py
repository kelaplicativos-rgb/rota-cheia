from __future__ import annotations

from statistics import median

from scanner.validator import MENSAGEM_NAO_VALIDADO
from rules.anti_duplicidade import (
    existe_publicacao_da_conta,
    horario_publicado_da_conta,
    preco_publicado_da_conta,
)
from rules.conflito_contas import risco_conflito_tres_coracoes
from rules.precos import sugerir_preco
from utils.normalizador_texto import sem_acentos


INTERMEDIARIAS_PADRAO = "Extrema, Pouso Alegre, Três Corações, Cambuquira, Campanha quando fizer sentido"


def _score_lotacao(motorista: dict) -> int:
    texto = sem_acentos(
        " ".join(
            [
                str(motorista.get("vagas") or ""),
                str(motorista.get("status") or ""),
                str(motorista.get("contexto") or ""),
            ]
        )
    )
    if "cheio" in texto or "sem vaga" in texto:
        return 100
    if "quase cheio" in texto or "ultimos lugares" in texto or "esgotara em breve" in texto:
        return 85
    if "1 vaga" in texto or "1 lugar" in texto:
        return 80
    if "2 vagas" in texto or "2 lugares" in texto:
        return 60
    return 20


def _horario_mais_forte(motoristas: list[dict], conta: str) -> str | None:
    pontos: dict[str, int] = {}
    for motorista in motoristas:
        if motorista.get("eh_ezequiel") or motorista.get("eh_barbosa"):
            continue
        horario = motorista.get("horario")
        if not horario:
            continue
        pontos[horario] = pontos.get(horario, 0) + 10 + _score_lotacao(motorista)
    if not pontos:
        return None
    return max(pontos, key=pontos.get)


def _preco_mediano(motoristas: list[dict]) -> float | None:
    precos = [float(m.get("preco")) for m in motoristas if isinstance(m.get("preco"), (int, float))]
    if not precos:
        return None
    return float(median(precos))


def _decidir_ajuste_publicado(
    *,
    motoristas: list[dict],
    conta: str,
    horario_planejado: str | None,
) -> tuple[str, str, str]:
    horario_publicado = horario_publicado_da_conta(motoristas, conta)
    preco_publicado = preco_publicado_da_conta(motoristas, conta)
    horario_forte = _horario_mais_forte(motoristas, conta)
    preco_mediano = _preco_mediano(motoristas)

    horario_final = horario_publicado or horario_planejado or "manter horário detectado"
    ajustes: list[str] = []

    if horario_forte and horario_publicado and horario_forte != horario_publicado:
        ajustes.append(
            f"horário publicado {horario_publicado}; concorrência/lotação mais forte em {horario_forte}"
        )
        return (
            "ALTERAR HORÁRIO",
            horario_forte,
            f"{conta} já aparece publicado; ajustar para o horário com maior força detectada. "
            + "; ".join(ajustes),
        )

    if preco_publicado is not None and preco_mediano is not None and preco_publicado > (preco_mediano + 8):
        return (
            "ALTERAR PREÇO",
            horario_final,
            f"{conta} já aparece publicado; preço detectado acima da mediana da concorrência.",
        )

    return (
        "MANTER",
        horario_final,
        f"{conta} já aparece publicado na busca pública; não criar duplicado.",
    )


def decidir_acao(parsed: dict, validacao: dict, conta: str, horario_planejado: str | None = None) -> dict:
    motoristas = parsed.get("motoristas", []) or []
    origem = parsed.get("origem")
    destino = parsed.get("destino")
    data = parsed.get("data_viagem")

    if not validacao.get("valido"):
        return {
            "acao": "não confirmado",
            "conta": conta,
            "origem": origem,
            "destino_final": destino,
            "intermediarias": INTERMEDIARIAS_PADRAO,
            "data": data,
            "horario": horario_planejado or "não confirmado",
            "preco_sugerido": "não sugerido",
            "risco_conflito": "não confirmado",
            "status_validacao": MENSAGEM_NAO_VALIDADO,
            "motivo": "; ".join(validacao.get("motivos", [])) or MENSAGEM_NAO_VALIDADO,
        }

    publicado = existe_publicacao_da_conta(motoristas, conta)
    risco = risco_conflito_tres_coracoes(destino, motoristas, conta)
    preco = sugerir_preco(motoristas)

    if publicado:
        acao, horario, motivo = _decidir_ajuste_publicado(
            motoristas=motoristas,
            conta=conta,
            horario_planejado=horario_planejado,
        )
    else:
        acao = "CRIAR"
        horario = horario_planejado or _horario_mais_forte(motoristas, conta) or "definir pelo padrão logístico"
        motivo = f"{conta} não aparece publicado na busca pública validada para esta rota/data."

    if risco.startswith("alto"):
        acao = "ALTERAR DESTINO FINAL"
        motivo = f"Conflito logístico detectado em Três Corações. {motivo}"

    return {
        "acao": acao,
        "conta": conta,
        "origem": origem,
        "destino_final": destino,
        "intermediarias": INTERMEDIARIAS_PADRAO,
        "data": data,
        "horario": horario,
        "preco_sugerido": preco,
        "risco_conflito": risco,
        "status_validacao": validacao.get("status"),
        "motivo": motivo,
    }
