from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import re
from typing import Any
from urllib.parse import quote_plus


STATUS_BLA_PENDENTE = "pendente / busca pública por data não validada"
PONTO_INICIAL_BLA = "https://www.blablacar.com.br/carpool"

ORIGENS_PADRAO = ["Santo André/SP", "São Paulo/SP"]

CIDADES_PRIORITARIAS = [
    "Extrema/MG",
    "Pouso Alegre/MG",
    "Três Corações/MG",
    "Varginha/MG",
    "São Tomé das Letras/MG",
    "Cambuquira/MG",
    "Campanha/MG",
]

CIDADES_IGNORADAS = ["Caxambu/MG", "Caxambu"]

TERMOS_EVENTO = [
    "agenda cultural",
    "apresentação",
    "atrações",
    "carnaval",
    "encontro",
    "evento",
    "exposição",
    "feira",
    "feriado",
    "festa",
    "festival",
    "ingressos",
    "música",
    "religioso",
    "rodeio",
    "show",
    "turismo",
    "universitário",
]

TERMOS_ALTA_DEMANDA = [
    "alta procura",
    "esgotado",
    "grande público",
    "hotel lotado",
    "ingressos esgotados",
    "lotado",
    "quase lotado",
    "últimos ingressos",
    "vendas encerradas",
]

FONTES_RELEVANTES = [
    "prefeitura",
    ".gov.br",
    "sympla",
    "eventbrite",
    "guicheweb",
    "ticket360",
    "shotgun",
    "instagram",
    "facebook",
    "agenda",
    "turismo",
]


@dataclass(frozen=True)
class FonteEvento:
    cidade: str
    titulo: str
    resumo: str = ""
    link: str = ""
    fonte: str = ""


@dataclass(frozen=True)
class EventoMovimentado:
    acao: str
    conta: str
    origem: str
    destino_final: str
    intermediarias: list[str]
    cidade: str
    data: str
    horario: str
    preco_sugerido: str
    risco_de_conflito: str
    status_validacao: str
    titulo: str
    resumo: str
    fonte: str
    link: str
    score: int
    demanda: str
    motivo: str
    consultas_realizadas: list[str]


def normalizar_texto(texto: str) -> str:
    texto = (texto or "").casefold()
    for origem, destino in {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i", "ó": "o",
        "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }.items():
        texto = texto.replace(origem, destino)
    return re.sub(r"\s+", " ", texto).strip()


def limpar_cidade(cidade: str) -> str:
    cidade = (cidade or "").strip()
    for uf in ("/MG", "/SP", " - MG", " - SP"):
        cidade = cidade.replace(uf, "")
    return cidade.strip()


def cidade_bloqueada(cidade: str) -> bool:
    alvo = normalizar_texto(cidade)
    return any(normalizar_texto(bloqueada) == alvo for bloqueada in CIDADES_IGNORADAS)


def gerar_datas(data_base: str | date, janela_dias: int = 7) -> list[date]:
    inicio = data_base if isinstance(data_base, date) else datetime.strptime(str(data_base)[:10], "%Y-%m-%d").date()
    janela_dias = max(1, min(int(janela_dias or 7), 31))
    return [inicio + timedelta(days=indice) for indice in range(janela_dias)]


def formatar_data_br(data_item: date) -> str:
    return data_item.strftime("%d/%m/%Y")


def tokens_data(datas: list[date]) -> list[str]:
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    tokens: set[str] = set()
    for data_item in datas:
        tokens.add(data_item.isoformat())
        tokens.add(data_item.strftime("%d/%m/%Y"))
        tokens.add(data_item.strftime("%d/%m"))
        tokens.add(f"{data_item.day} de {meses[data_item.month - 1]}")
        tokens.add(f"{data_item.day}/{data_item.month}")
    return sorted(tokens)


def montar_consultas_eventos(cidade: str, datas: list[date]) -> list[str]:
    cidade_limpa = limpar_cidade(cidade)
    inicio = formatar_data_br(datas[0])
    fim = formatar_data_br(datas[-1])
    mes = datas[0].strftime("%m/%Y")
    ano = datas[0].year
    return [
        f"{cidade_limpa} eventos {inicio} {fim}",
        f"{cidade_limpa} agenda cultural {mes}",
        f"{cidade_limpa} show festa festival {ano}",
        f"{cidade_limpa} turismo eventos fim de semana {inicio}",
        f"{cidade_limpa} ingressos show festa evento",
    ]


def montar_links_busca_eventos(cidade: str, datas: list[date]) -> list[dict[str, str]]:
    links = []
    for consulta in montar_consultas_eventos(cidade, datas):
        links.append(
            {
                "consulta": consulta,
                "link_busca": f"https://www.google.com/search?q={quote_plus(consulta)}",
            }
        )
    return links


def calcular_score_evento(
    cidade: str,
    titulo: str,
    resumo: str,
    fonte: str,
    link: str,
    datas: list[date],
) -> tuple[int, str]:
    texto = normalizar_texto(f"{titulo} {resumo} {fonte} {link}")
    score = 0
    motivos: list[str] = []
    if cidade in CIDADES_PRIORITARIAS:
        score += 15
        motivos.append("cidade prioritária do corredor")
    if any(normalizar_texto(token) in texto for token in tokens_data(datas)):
        score += 25
        motivos.append("data compatível com o período informado")
    if any(normalizar_texto(termo) in texto for termo in TERMOS_EVENTO):
        score += 20
        motivos.append("termos de evento encontrados")
    if any(normalizar_texto(termo) in texto for termo in TERMOS_ALTA_DEMANDA):
        score += 25
        motivos.append("sinais de alta demanda")
    if any(normalizar_texto(fonte_ok) in texto for fonte_ok in FONTES_RELEVANTES):
        score += 15
        motivos.append("fonte pública relevante")
    if not motivos:
        motivos.append("baixo sinal público de evento")
    return min(score, 100), ", ".join(motivos)


def classificar_demanda(score: int) -> str:
    if score >= 75:
        return "ALTA"
    if score >= 50:
        return "MÉDIA"
    return "BAIXA"


def parse_fontes_coladas(texto: str, cidade_padrao: str = "") -> list[FonteEvento]:
    """Converte fontes coladas em eventos.

    Formatos aceitos por linha:
    cidade | título | resumo | link | fonte
    título | resumo | link | fonte
    título
    """
    fontes: list[FonteEvento] = []
    for linha in (texto or "").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        partes = [parte.strip() for parte in linha.split("|")]
        if len(partes) >= 5:
            cidade, titulo, resumo, link, fonte = partes[:5]
        elif len(partes) >= 4:
            cidade = cidade_padrao
            titulo, resumo, link, fonte = partes[:4]
        else:
            cidade = cidade_padrao
            titulo = partes[0]
            resumo = partes[1] if len(partes) > 1 else ""
            link = ""
            fonte = ""
        fontes.append(FonteEvento(cidade=cidade, titulo=titulo, resumo=resumo, link=link, fonte=fonte))
    return fontes


def descobrir_eventos_movimentados(
    data_base: str | date,
    janela_dias: int,
    cidades: list[str],
    *,
    origem: str = "Santo André/SP",
    destino_final: str = "",
    intermediarias: list[str] | None = None,
    fontes: list[FonteEvento] | None = None,
) -> list[dict[str, Any]]:
    datas = gerar_datas(data_base, janela_dias)
    intermediarias = intermediarias or []
    destino_final = destino_final or (cidades[-1] if cidades else "")
    fontes = fontes or []
    eventos: list[EventoMovimentado] = []

    cidades_validas: list[str] = []
    for cidade in cidades:
        if not cidade or cidade_bloqueada(cidade):
            continue
        if cidade not in cidades_validas:
            cidades_validas.append(cidade)

    for cidade in cidades_validas:
        consultas = montar_consultas_eventos(cidade, datas)
        fontes_cidade = [fonte for fonte in fontes if not fonte.cidade or fonte.cidade == cidade]
        for item in fontes_cidade:
            score, motivo = calcular_score_evento(cidade, item.titulo, item.resumo, item.fonte, item.link, datas)
            eventos.append(
                EventoMovimentado(
                    acao="ANALISAR DEMANDA",
                    conta="não aplicável",
                    origem=origem,
                    destino_final=destino_final,
                    intermediarias=intermediarias,
                    cidade=cidade,
                    data=datas[0].isoformat(),
                    horario="pendente",
                    preco_sugerido="pendente",
                    risco_de_conflito="pendente",
                    status_validacao=STATUS_BLA_PENDENTE,
                    titulo=item.titulo,
                    resumo=item.resumo,
                    fonte=item.fonte,
                    link=item.link,
                    score=score,
                    demanda=classificar_demanda(score),
                    motivo=motivo,
                    consultas_realizadas=consultas,
                )
            )

    eventos.sort(key=lambda evento: (evento.score, evento.cidade), reverse=True)
    return [asdict(evento) for evento in eventos]


def montar_pacote_para_scan_bla(
    *,
    origem: str,
    destino_final: str,
    intermediarias: list[str],
    data: str | date,
) -> dict[str, Any]:
    data_txt = data.isoformat() if isinstance(data, date) else str(data)[:10]
    return {
        "acao": "VALIDAR_SCAN_BLA",
        "conta": "pendente",
        "origem": origem,
        "destino_final": destino_final,
        "intermediarias": intermediarias,
        "data": data_txt,
        "horario": "pendente",
        "preco_sugerido": "pendente",
        "risco_de_conflito": "pendente",
        "status_validacao": STATUS_BLA_PENDENTE,
        "ponto_inicial_obrigatorio": PONTO_INICIAL_BLA,
        "observacao": (
            "Evento movimentado não libera CRIAR/PUBLICAR. "
            "Validar BlaBlaCar pública por rota + data exata e procurar Ezequiel S / Barbosa."
        ),
    }


def gerar_relatorio_eventos_markdown(eventos: list[dict[str, Any]]) -> str:
    if not eventos:
        return (
            "# Radar de Eventos Movimentados\n\n"
            "Nenhum evento forte foi informado/analisado.\n\n"
            f"Status de validação: {STATUS_BLA_PENDENTE}\n"
        )
    linhas = [
        "# Radar de Eventos Movimentados",
        "",
        "Este relatório indica potencial de demanda por evento.",
        "Não recomenda CRIAR/PUBLICAR sem SCAN BLA público por rota + data exata.",
        "",
    ]
    for indice, evento in enumerate(eventos, start=1):
        linhas.extend(
            [
                f"## {indice}. {evento['cidade']}",
                "",
                f"- ação: {evento['acao']}",
                f"- conta: {evento['conta']}",
                f"- origem: {evento['origem']}",
                f"- destino final: {evento['destino_final']}",
                f"- intermediárias: {', '.join(evento['intermediarias']) or 'pendente'}",
                f"- data: {evento['data']}",
                f"- horário: {evento['horario']}",
                f"- preço sugerido: {evento['preco_sugerido']}",
                f"- risco de conflito: {evento['risco_de_conflito']}",
                f"- status de validação: {evento['status_validacao']}",
                f"- demanda: {evento['demanda']} ({evento['score']}/100)",
                f"- evento/fonte: {evento['titulo']}",
                f"- motivo: {evento['motivo']}",
                f"- link: {evento['link']}",
                "",
            ]
        )
    return "\n".join(linhas)
