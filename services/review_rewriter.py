from __future__ import annotations

import re

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
    "Mais humana",
    "Mais persuasiva",
    "Criativa",
    "Muito recomendável",
)

TIPOS_ALIASES = {
    "Generica": "Genérica",
    "Genérica": "Genérica",
    "Passageiro homem": "Passageiro homem",
    "Passageira mulher": "Passageira mulher",
    "Motorista": "Motorista",
}

ESTILOS_ALIASES = {
    "Curta e natural": "Curta e natural",
    "Mais simpatica": "Mais simpática",
    "Mais simpática": "Mais simpática",
    "Mais profissional": "Mais profissional",
    "Bem direta": "Bem direta",
    "Mais humana": "Mais humana",
    "Mais persuasiva": "Mais persuasiva",
    "Criativa": "Criativa",
    "Muito recomendavel": "Muito recomendável",
    "Muito recomendável": "Muito recomendável",
}

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
    (r"\bparceir\w*", "parceiro"),
    (r"\bconfi[aá]vel\w*", "confiável"),
    (r"\blegal\b", "legal"),
    (r"\borganiza\w*", "organizado"),
    (r"\bboa\s+companhia\b", "boa companhia"),
    (r"\b[óo]tim[ao]\s+companhia\b", "ótima companhia"),
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
    "ótima pessoa",
    "boa pessoa",
)

FEMININO = {
    "educado": "educada",
    "tranquilo": "tranquila",
    "simpático": "simpática",
    "comunicativo": "comunicativa",
    "respeitoso": "respeitosa",
    "seguro": "segura",
    "parceiro": "parceira",
    "organizado": "organizada",
}

MASCULINO = {
    "educada": "educado",
    "tranquila": "tranquilo",
    "simpática": "simpático",
    "comunicativa": "comunicativo",
    "respeitosa": "respeitoso",
    "segura": "seguro",
    "parceira": "parceiro",
    "organizada": "organizado",
}


def normalizar_tipo(tipo: str) -> str:
    return TIPOS_ALIASES.get(str(tipo or "").strip(), "Genérica")


def normalizar_estilo(estilo: str) -> str:
    return ESTILOS_ALIASES.get(str(estilo or "").strip(), "Curta e natural")


def limpar_texto(texto: str) -> str:
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    return texto.strip(" .,!;:")


def _normalizar_para_busca(texto: str) -> str:
    return limpar_texto(texto).casefold()


def _genero(tipo: str) -> str:
    tipo = normalizar_tipo(tipo)
    if tipo == "Passageiro homem":
        return "masculino"
    if tipo in {"Passageira mulher", "Genérica"}:
        return "feminino"
    return "neutro"


def _sujeito(tipo: str) -> str:
    tipo = normalizar_tipo(tipo)
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
    tipo = normalizar_tipo(tipo)
    estilo = normalizar_estilo(estilo)

    if estilo == "Mais profissional":
        return "Recomendo para a comunidade."
    if estilo == "Mais simpática":
        return "Recomendo com certeza!"
    if estilo == "Bem direta":
        return "Recomendo!"
    if estilo == "Mais humana":
        return "Foi uma experiência muito tranquila. Recomendo!"
    if estilo == "Mais persuasiva":
        return "Pode ir sem preocupação. Recomendo muito!"
    if estilo == "Criativa":
        return "Viagem leve, tranquila e muito positiva. Recomendo!"
    if estilo == "Muito recomendável":
        return "Recomendo muito!"

    if tipo == "Passageiro homem":
        return "Recomendo o passageiro!"
    if tipo == "Passageira mulher":
        return "Recomendo a passageira!"
    if tipo == "Motorista":
        return "Recomendo a carona!"
    return "Recomendo!"


def _frase_base(sujeito: str, atributos: list[str], estilo: str) -> str:
    estilo = normalizar_estilo(estilo)
    atributos_txt = _juntar_pt(atributos)
    if not atributos_txt:
        return ""
    if estilo == "Mais humana":
        return f"{sujeito} {atributos_txt}, deixou a viagem mais leve."
    if estilo == "Mais persuasiva":
        return f"{sujeito} {atributos_txt}, excelente companhia para a viagem."
    if estilo == "Criativa":
        return f"{sujeito} nota 10: {atributos_txt} do início ao fim."
    if estilo == "Muito recomendável":
        return f"{sujeito} {atributos_txt}, experiência excelente."
    return f"{sujeito} {atributos_txt}."


def _sentence_case(texto: str) -> str:
    texto = limpar_texto(texto)
    if not texto:
        return ""
    return texto[0].upper() + texto[1:] + "."


def _fallback_reformulado(texto: str, tipo: str) -> str:
    texto = limpar_texto(texto)
    sujeito = _sujeito(tipo)
    if not texto:
        return gerar_avaliacao(tipo)
    if len(texto.split()) <= 3:
        return gerar_avaliacao(tipo)
    return f"{sujeito} deixou uma boa impressão durante a viagem. Recomendo!"


def reformular_avaliacao(
    texto: str,
    tipo: str = "Genérica",
    estilo: str = "Curta e natural",
) -> str:
    texto_limpo = limpar_texto(texto)
    if not texto_limpo:
        return ""

    tipo = normalizar_tipo(tipo)
    estilo = normalizar_estilo(estilo)

    if _tem_negativo(texto_limpo):
        return "Não foi uma boa experiência. Não recomendo."

    sujeito = _sujeito(tipo)
    atributos = _detectar_atributos(texto_limpo, tipo)
    tem_recomendacao = _tem_recomendacao(texto_limpo)

    if atributos:
        frase = _frase_base(sujeito, atributos, estilo)
        if tem_recomendacao:
            return f"{frase} {_frase_recomendacao(tipo, estilo)}"
        return frase

    if tem_recomendacao:
        return f"{sujeito} passou uma boa impressão. {_frase_recomendacao(tipo, estilo)}"

    return _fallback_reformulado(texto_limpo, tipo)


def gerar_avaliacao(tipo: str = "Genérica") -> str:
    tipo = normalizar_tipo(tipo)
    if tipo == "Passageiro homem":
        return "Passageiro educado, tranquilo e pontual. Recomendo com certeza!"
    if tipo == "Passageira mulher":
        return "Passageira educada, tranquila e pontual. Recomendo com certeza!"
    if tipo == "Motorista":
        return "Motorista educado, pontual e seguro. Recomendo a carona!"
    return "Pessoa educada, tranquila e pontual. Recomendo com certeza!"
