"""Motor local para reformular mensagens e avaliações da BlaBlaCar.

Este módulo não depende de API externa. A regra principal é nunca deixar a tela
sem resposta quando o usuário cola um texto válido.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Tom = Literal["curto", "educado", "persuasivo", "avaliacao"]


@dataclass(frozen=True)
class RewriteVariant:
    titulo: str
    texto: str


@dataclass(frozen=True)
class RewriteResult:
    original: str
    rewritten: str
    tom: Tom
    variants: tuple[RewriteVariant, ...] = ()


BIO_CURTA = (
    "Assim que reservar, chamo para combinar direitinho. "
    "Aviso quando estiver a caminho. Aceito Pix ou dinheiro. "
    "Embarque/desembarque em trevos ou postos na rodovia."
)


def _limpar_texto(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto or "").strip()
    return texto.strip(" -–—")


def _frase(texto: str) -> str:
    texto = _limpar_texto(texto)
    if not texto:
        return ""
    texto = texto[0].upper() + texto[1:]
    if texto[-1] not in ".!?":
        texto += "."
    return texto


def _tem(texto: str, *palavras: str) -> bool:
    base = texto.casefold()
    return any(p.casefold() in base for p in palavras)


def _compactar_avaliacao(original: str) -> str:
    base = original.casefold()
    elogios: list[str] = []

    if _tem(base, "pontual", "horário", "horario"):
        elogios.append("pontual")
    if _tem(base, "educad", "respeitos", "gente boa", "tranquil"):
        elogios.append("educada")
    if _tem(base, "agrad", "divertid", "conversa", "boa companhia"):
        elogios.append("boa companhia")
    if _tem(base, "recomendo", "recomend"):
        elogios.append("recomendada")

    if not elogios:
        elogios = ["tranquila", "educada", "recomendada"]

    elogios_unicos = []
    for item in elogios:
        if item not in elogios_unicos:
            elogios_unicos.append(item)

    if len(elogios_unicos) == 1:
        resumo = elogios_unicos[0]
    elif len(elogios_unicos) == 2:
        resumo = " e ".join(elogios_unicos)
    else:
        resumo = ", ".join(elogios_unicos[:-1]) + " e " + elogios_unicos[-1]

    return f"Pessoa {resumo}. Recomendo com certeza para a comunidade BlaBlaCar."


def _mensagem_por_contexto(original: str) -> tuple[str, str, str]:
    base = _frase(original)
    lower = original.casefold()

    if _tem(lower, "demor", "passagem", "ônibus", "onibus", "desesperad"):
        curta = (
            "Entendo perfeitamente. Nem sempre consigo responder na hora, mas retorno assim que possível "
            "para alinhar tudo certinho."
        )
        educada = (
            "Entendo sim, sem problema. Às vezes estou dirigindo ou resolvendo outra etapa da viagem e não consigo "
            "responder imediatamente, mas sempre retorno para combinar tudo com segurança."
        )
        persuasiva = (
            "Entendo perfeitamente. Para as próximas reservas, pode ficar tranquilo(a): assim que eu estiver a caminho, "
            "aviso por aqui, confirmo o ponto de embarque e combino tudo direitinho."
        )
        return curta, educada, persuasiva

    if _tem(lower, "pix", "dinheiro", "pagar", "pagamento"):
        curta = "Pode pagar por Pix ou dinheiro, como for melhor para você."
        educada = (
            "Tudo certo. Aceito Pix ou dinheiro, e a gente combina o pagamento com tranquilidade no momento da viagem."
        )
        persuasiva = (
            "Pode reservar com tranquilidade. Aceito Pix ou dinheiro e, assim que a reserva entrar, chamo você para "
            "alinhar embarque, horário e qualquer detalhe da viagem."
        )
        return curta, educada, persuasiva

    if _tem(lower, "trevo", "posto", "rodovia", "cidade", "entro"):
        curta = "Combinado. Faço embarque e desembarque em trevos ou postos na rodovia."
        educada = (
            "Só reforçando: para manter a viagem no horário, faço embarque e desembarque em trevos ou postos na rodovia, "
            "sem entrar dentro das cidades."
        )
        persuasiva = (
            "Para a viagem fluir melhor e todos chegarem no horário, combino o embarque em trevos ou postos na rodovia. "
            "Assim que eu estiver a caminho, aviso o tempo estimado de chegada."
        )
        return curta, educada, persuasiva

    if _tem(lower, "confirm", "reserva", "reservou", "solicitação", "solicitacao", "embarque"):
        curta = "Tudo certo, sua reserva está confirmada. Te aviso quando estiver a caminho."
        educada = (
            "Tudo certo, sua reserva está confirmada. Assim que eu estiver a caminho do ponto combinado, aviso por aqui "
            "e informo a previsão de chegada."
        )
        persuasiva = (
            "Reserva confirmada. Pode ficar tranquilo(a): antes do embarque eu te aviso quando estiver saindo, confirmo "
            "o ponto combinado e passo a previsão de chegada."
        )
        return curta, educada, persuasiva

    curta = base
    educada = (
        f"{base}\n\n"
        "Qualquer dúvida pode me chamar. Assim que eu estiver a caminho, aviso por aqui e combino tudo certinho."
    )
    persuasiva = (
        f"{base}\n\n"
        "Pode ficar tranquilo(a): eu aviso quando estiver a caminho, confirmo o ponto de embarque e acompanho tudo "
        "até a viagem ficar bem alinhada."
    )
    return curta, educada, persuasiva


def reformular_mensagem(texto: str, tom: Tom = "educado") -> RewriteResult:
    original = _limpar_texto(texto)
    if not original:
        return RewriteResult(original="", rewritten="", tom=tom, variants=())

    avaliacao = _compactar_avaliacao(original)
    curta, educada, persuasiva = _mensagem_por_contexto(original)

    variants = (
        RewriteVariant("Mais curta para copiar", curta),
        RewriteVariant("Mais educada", educada),
        RewriteVariant("Mais persuasiva", persuasiva),
        RewriteVariant("Avaliação BlaBlaCar", avaliacao),
    )

    por_tom = {
        "curto": curta,
        "educado": educada,
        "persuasivo": persuasiva,
        "avaliacao": avaliacao,
    }
    return RewriteResult(
        original=original,
        rewritten=por_tom.get(tom, educada).strip(),
        tom=tom,
        variants=variants,
    )
