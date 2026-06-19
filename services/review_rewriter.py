from __future__ import annotations

import re
from typing import Literal

TIPOS_AVALIACAO = (
    "Genérica",
    "Passageiro homem",
    "Passageira mulher",
    "Motorista",
)

ESTILOS_AVALIACAO = (
    "Curta e natural",
    "Mais simpática",
    "Mais profissional",
    "Bem direta",
)

TipoAvaliacao = Literal["Genérica", "Passageiro homem", "Passageira mulher", "Motorista"]
EstiloAvaliacao = Literal["Curta e natural", "Mais simpática", "Mais profissional", "Bem direta"]


ATRIBUTOS_BASE = [
    (r"\bpontual\w*", "pontual"),
    (r"\beducad\w*", "educado"),
    (r"\btranquil\w*", "tranquilo"),
    (r"\bagrad[áa]vel\w*", "agradável"),
    (r"\bgente\s+boa\b", "gente boa"),
    (r"\bsimp[aá]tic\w*", "simpático"),
    (r"\bcomunicativ\w*", "comunicativo"),
    (r"\brespeitos\w*", "respeitoso"),
    (r"\brespons[aá]vel\w*", "responsável"),
    (r"\bsegur\w*", "seguro"),
]

NEGATIVOS = (
    "não recomendo",
    "nao recomendo",
    "não gostei",
    "nao gostei",
    "ruim",
    "problema",
    "atrasou",
    "cancelou",
)

RECOMENDACAO = (
    "recomendo",
    "recomendaria",
    "indico",
    "aprovado",
    "aprovada",
)


FEMININO = {
    "educado": "educada",
    "tranquilo": "tranquila",
    "simpático": "simpática",
    "comunicativo": "comunicativa",
    "respeitoso": "respeitosa",
    "seguro": "segura",
}


MASCULINO = {
    "educada": "educado",
    "tranquila": "tranquilo",
    "simpática": "simpático",
    "comunicativa": "comunicativo",
    "respeitosa": "respeitoso",
    "segura": "seguro",
}


def limpar_texto(texto: str) -> str:
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    return texto.strip(" .,!;:")


def _normalizar_para_busca(texto: str) -> str:
    return limpar_texto(texto).casefold()


def _genero(tipo: str) -> str:
    if tipo == "Passageiro homem":
        return "masculino"
    if tipo in {"Passageira mulher", "Genérica"}:
        return "feminino"
    return "neutro"


def _sujeito(tipo: str) -> str:
    if tipo == "Passageiro homem":
        return "Passageiro"
    if tipo == "Passageira mulher":
        return "Passageira"
    if tipo == "Motorista":
        return "Motorista"
    return "Pessoa"


def _ajustar_genero(atributo: str, tipo: str) -> str:
    genero = _genero(tipo)
    if genero == "feminino":
        return FEMININO.get(atributo, atributo)
    if genero == "masculino":
        return MASCULINO.get(atributo, atributo)
    return atributo


def _detectar_atributos(texto: str, tipo: str) -> list[str]:
    normalizado = _normalizar_para_busca(texto)
    atributos: list[str] = []
    for padrao, atributo in ATRIBUTOS_BASE:
        if re.search(padrao, normalizado, flags=re.IGNORECASE):
            ajustado = _ajustar_genero(atributo, tipo)
            if ajustado not in atributos:
                atributos.append(ajustado)
    return atributos


def _tem_recomendacao(texto: str) -> bool:
    normalizado = _normalizar_para_busca(texto)
    return any(palavra in normalizado for palavra in RECOMENDACAO)


def _tem_negativo(texto: str) -> bool:
    normalizado = _normalizar_para_busca(texto)
    return any(palavra in normalizado for palavra in NEGATIVOS)


def _juntar_pt(itens: list[str]) -> str:
    if not itens:
        return ""
    if len(itens) == 1:
        return itens[0]
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def _frase_recomendacao(tipo: str, estilo: str) -> str:
    if estilo == "Mais profissional":
        return "Recomendo à comunidade."
    if estilo == "Mais simpática":
        return "Recomendo com certeza!"
    if estilo == "Bem direta":
        return "Recomendo!"

    if tipo == "Passageiro homem":
        return "Recomendo o passageiro!"
    if tipo == "Passageira mulher":
        return "Recomendo a passageira!"
    if tipo == "Motorista":
        return "Recomendo a carona!"
    return "Recomendo!"


def _sentence_case(texto: str) -> str:
    texto = limpar_texto(texto)
    if not texto:
        return ""
    return texto[0].upper() + texto[1:] + "."


def reformular_avaliacao(
    texto: str,
    tipo: str = "Genérica",
    estilo: str = "Curta e natural",
) -> str:
    """Reformula uma avaliação curta sem inventar fatos novos.

    A função é determinística para funcionar sem chave externa de IA. Ela preserva
    o sentido da avaliação colada pelo usuário e devolve uma frase pronta para
    copiar e colar na BlaBlaCar.
    """
    texto_limpo = limpar_texto(texto)
    if not texto_limpo:
        return ""

    if tipo not in TIPOS_AVALIACAO:
        tipo = "Genérica"
    if estilo not in ESTILOS_AVALIACAO:
        estilo = "Curta e natural"

    if _tem_negativo(texto_limpo):
        return "Não foi uma boa experiência. Não recomendo."

    sujeito = _sujeito(tipo)
    atributos = _detectar_atributos(texto_limpo, tipo)
    tem_recomendacao = _tem_recomendacao(texto_limpo)

    if atributos:
        frase_base = f"{sujeito} {_juntar_pt(atributos)}."
        if tem_recomendacao:
            return f"{frase_base} {_frase_recomendacao(tipo, estilo)}"
        return frase_base

    if tem_recomendacao:
        return _frase_recomendacao(tipo, estilo)

    return _sentence_case(texto_limpo)
