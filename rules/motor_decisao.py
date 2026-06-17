from __future__ import annotations

from scanner.validator import MENSAGEM_NAO_VALIDADO
from rules.anti_duplicidade import existe_publicacao_da_conta, horario_publicado_da_conta
from rules.conflito_contas import risco_conflito_tres_coracoes
from rules.precos import sugerir_preco


def decidir_acao(parsed: dict, validacao: dict, conta: str, horario_planejado: str | None = None) -> dict:
    motoristas = parsed.get("motoristas", [])
    origem = parsed.get("origem")
    destino = parsed.get("destino")
    data = parsed.get("data_viagem")

    if not validacao.get("valido"):
        return {
            "acao": "não confirmado",
            "conta": conta,
            "origem": origem,
            "destino_final": destino,
            "intermediarias": "Extrema, Pouso Alegre, Três Corações, Cambuquira, Campanha quando fizer sentido",
            "data": data,
            "horario": horario_planejado or "não confirmado",
            "preco_sugerido": "não sugerido",
            "risco_conflito": "não confirmado",
            "status_validacao": MENSAGEM_NAO_VALIDADO,
            "motivo": "; ".join(validacao.get("motivos", [])) or MENSAGEM_NAO_VALIDADO,
        }

    publicado = existe_publicacao_da_conta(motoristas, conta)
    horario_publicado = horario_publicado_da_conta(motoristas, conta)
    risco = risco_conflito_tres_coracoes(destino, motoristas)
    preco = sugerir_preco(motoristas)

    if publicado:
        acao = "MANTER"
        motivo = f"{conta} já aparece publicado na busca pública; não criar duplicado."
        horario = horario_publicado or horario_planejado or "manter horário detectado"
    else:
        acao = "CRIAR"
        motivo = f"{conta} não aparece publicado na busca pública validada para esta rota/data."
        horario = horario_planejado or "definir pelo padrão logístico"

    if risco.startswith("alto"):
        acao = "ALTERAR DESTINO FINAL"
        motivo = f"Conflito logístico detectado. {motivo}"

    return {
        "acao": acao,
        "conta": conta,
        "origem": origem,
        "destino_final": destino,
        "intermediarias": "Extrema, Pouso Alegre, Três Corações, Cambuquira, Campanha quando fizer sentido",
        "data": data,
        "horario": horario,
        "preco_sugerido": preco,
        "risco_conflito": risco,
        "status_validacao": validacao.get("status"),
        "motivo": motivo,
    }
