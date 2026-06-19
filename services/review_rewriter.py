from __future__ import annotations

import re

TIPOS_AVALIACAO = (
    "Generica",
    "Passageiro homem",
    "Passageira mulher",
    "Motorista",
)

ESTILOS_AVALIACAO = (
    "Curta e natural",
    "Mais simpatica",
    "Mais profissional",
    "Bem direta",
    "Mais humana",
    "Mais persuasiva",
    "Criativa",
    "Muito recomendavel",
)


ATRIBUTOS_BASE = [
    (r"\bpontual\w*", "pontual"),
    (r"\beducad\w*", "educado"),
    (r"\btranquil\w*", "tranquilo"),
    (r"\bagrad[áa]vel\w*", "agradavel"),
    (r"\bgente\s+boa\b", "gente boa"),
    (r"\bsimp[aá]tic\w*", "simpatico"),
    (r"\bcomunicativ\w*", "comunicativo"),
    (r"\brespeitos\w*", "respeitoso"),
    (r"\brespons[aá]vel\w*", "responsavel"),
    (r"\bsegur\w*", "seguro"),
    (r"\bparceir\w*", "parceiro"),
    (r"\bconfi[aá]vel\w*", "confiavel"),
    (r"\blegal\b", "legal"),
    (r"\borganiza\w*", "organizado"),
    (r"\bboa\s+companhia\b", "boa companhia"),
    (r"\botim[ao]\s+companhia\b", "otima companhia"),
    (r"\bexcelente\b", "excelente"),
]

NEGATIVOS = (
    "nao recomendo",
    "não recomendo",
    "nao gostei",
    "não gostei",
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
    "otima pessoa",
    "boa pessoa",
)

FEMININO = {
    "educado": "educada",
    "tranquilo": "tranquila",
    "simpatico": "simpatica",
    "comunicativo": "comunicativa",
    "respeitoso": "respeitosa",
    "seguro": "segura",
    "parceiro": "parceira",
    "organizado": "organizada",
}

MASCULINO = {
    "educada": "educado",
    "tranquila": "tranquilo",
    "simpatica": "simpatico",
    "comunicativa": "comunicativo",
    "respeitosa": "respeitoso",
    "segura": "seguro",
    "parceira": "parceiro",
    "organizada": "organizado",
}


def limpar_texto(texto: str) -> str:
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    return texto.strip(" .,!;:")


def _normalizar_para_busca(texto: str) -> str:
    return limpar_texto(texto).casefold()


def _genero(tipo: str) -> str:
    if tipo == "Passageiro homem":
        return "masculino"
    if tipo in {"Passageira mulher", "Generica"}:
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
        return "Recomendo para a comunidade."
    if estilo == "Mais simpatica":
        return "Recomendo com certeza!"
    if estilo == "Bem direta":
        return "Recomendo!"
    if estilo == "Mais humana":
        return "Foi uma experiencia muito tranquila. Recomendo!"
    if estilo == "Mais persuasiva":
        return "Pode ir sem preocupacao. Recomendo muito!"
    if estilo == "Criativa":
        return "Viagem leve, tranquila e muito positiva. Recomendo!"
    if estilo == "Muito recomendavel":
        return "Recomendo muito!"

    if tipo == "Passageiro homem":
        return "Recomendo o passageiro!"
    if tipo == "Passageira mulher":
        return "Recomendo a passageira!"
    if tipo == "Motorista":
        return "Recomendo a carona!"
    return "Recomendo!"


def _frase_base(sujeito: str, atributos: list[str], estilo: str) -> str:
    atributos_txt = _juntar_pt(atributos)
    if not atributos_txt:
        return ""
    if estilo == "Mais humana":
        return f"{sujeito} {atributos_txt}, deixou a viagem mais leve."
    if estilo == "Mais persuasiva":
        return f"{sujeito} {atributos_txt}, excelente companhia para a viagem."
    if estilo == "Criativa":
        return f"{sujeito} nota 10: {atributos_txt} do inicio ao fim."
    if estilo == "Muito recomendavel":
        return f"{sujeito} {atributos_txt}, experiencia excelente."
    return f"{sujeito} {atributos_txt}."


def _sentence_case(texto: str) -> str:
    texto = limpar_texto(texto)
    if not texto:
        return ""
    return texto[0].upper() + texto[1:] + "."


def reformular_avaliacao(
    texto: str,
    tipo: str = "Generica",
    estilo: str = "Curta e natural",
) -> str:
    """Reformula uma avaliacao curta sem inventar fatos novos.

    A funcao e deterministica para funcionar sem chave externa de IA. Ela preserva
    o sentido da avaliacao colada pelo usuario e devolve uma frase pronta para
    copiar e colar na BlaBlaCar.
    """
    texto_limpo = limpar_texto(texto)
    if not texto_limpo:
        return ""

    if tipo not in TIPOS_AVALIACAO:
        tipo = "Generica"
    if estilo not in ESTILOS_AVALIACAO:
        estilo = "Curta e natural"

    if _tem_negativo(texto_limpo):
        return "Nao foi uma boa experiencia. Nao recomendo."

    sujeito = _sujeito(tipo)
    atributos = _detectar_atributos(texto_limpo, tipo)
    tem_recomendacao = _tem_recomendacao(texto_limpo)

    if atributos:
        frase = _frase_base(sujeito, atributos, estilo)
        if tem_recomendacao:
            return f"{frase} {_frase_recomendacao(tipo, estilo)}"
        return frase

    if tem_recomendacao:
        return _frase_recomendacao(tipo, estilo)

    return _sentence_case(texto_limpo)
