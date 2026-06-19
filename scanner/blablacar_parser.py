from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from urllib.parse import parse_qs, unquote_plus, urlparse

from utils.normalizador_texto import limpar_espacos, sem_acentos


@dataclass
class DriverOffer:
    nome_motorista: str
    horario: str | None = None
    preco: float | None = None
    vagas: str | None = None
    status: str | None = None
    eh_ezequiel: bool = False  # compatibilidade histórica; não usado pelo núcleo multiusuário
    eh_barbosa: bool = False  # compatibilidade histórica; não usado pelo núcleo multiusuário
    eh_conta_ativa: bool = False
    eh_conta_grupo: bool = False
    contexto: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParsedSearch:
    link_busca: str | None
    origem: str | None
    destino: str | None
    data_viagem: str | None
    texto: str
    motoristas: list[DriverOffer]


URL_RE = re.compile(r"https?://[^\s\"'<>]+blablacar\.com\.br[^\s\"'<>]+", re.IGNORECASE)
TIME_RE = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")
ISO_DATE_RE = re.compile(r"\b20\d{2}-[01]\d-[0-3]\d\b")
PRICE_RE = re.compile(r"R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+)")

STATUS_TERMS = [
    "cheio",
    "esgotará em breve",
    "esgotara em breve",
    "quase cheio",
    "últimos lugares",
    "ultimos lugares",
]


def parse_search_text(
    texto: str,
    *,
    contas_interesse: list[str] | tuple[str, ...] | None = None,
    conta_ativa: str | None = None,
) -> ParsedSearch:
    texto_limpo = limpar_espacos(texto)
    link = _extract_link(texto)
    origem, destino, data = _extract_route_from_link(link)
    if not data:
        data = _extract_iso_date(texto)
    motoristas = _extract_driver_offers(texto, contas_interesse=contas_interesse, conta_ativa=conta_ativa)
    return ParsedSearch(
        link_busca=link,
        origem=origem,
        destino=destino,
        data_viagem=data,
        texto=texto_limpo,
        motoristas=motoristas,
    )


def _extract_link(texto: str) -> str | None:
    matches = URL_RE.findall(texto or "")
    if not matches:
        return None
    preferidos = [url for url in matches if "/search" in url or "/carpool" in url]
    return _normalizar_url((preferidos or matches)[0])


def _normalizar_url(link: str | None) -> str | None:
    if not link:
        return None
    link_limpo = str(link).replace("&amp;", "&").replace("\\u0026", "&")
    return unquote_plus(link_limpo)


def _extract_route_from_link(link: str | None) -> tuple[str | None, str | None, str | None]:
    link = _normalizar_url(link)
    if not link:
        return None, None, None
    try:
        parsed = urlparse(link)
        qs = parse_qs(parsed.query)
        origem = _first(qs.get("fn"))
        destino = _first(qs.get("tn"))
        data = _first(qs.get("db")) or _first(qs.get("departure_date"))
        return origem, destino, data
    except Exception:
        return None, None, None


def _extract_iso_date(texto: str) -> str | None:
    match = ISO_DATE_RE.search(texto or "")
    return match.group(0) if match else None


def _first(values: list[str] | None) -> str | None:
    if not values:
        return None
    return limpar_espacos(unquote_plus(values[0]))


def _normalizar_nome(nome: str | None) -> str:
    return re.sub(r"\s+", " ", sem_acentos(nome)).strip().lower()


def _conta_match(nome_detectado: str | None, conta: str | None) -> bool:
    nd = _normalizar_nome(nome_detectado)
    nc = _normalizar_nome(conta)
    if not nd or not nc:
        return False
    return nd == nc or nc in nd or nd in nc


def _extract_driver_offers(
    texto: str,
    *,
    contas_interesse: list[str] | tuple[str, ...] | None = None,
    conta_ativa: str | None = None,
) -> list[DriverOffer]:
    linhas = [limpar_espacos(l) for l in (texto or "").splitlines() if limpar_espacos(l)]
    joined = "\n".join(linhas)
    contas = []
    for conta in list(contas_interesse or []):
        conta = str(conta or "").strip()
        if conta and conta not in contas:
            contas.append(conta)

    offers: list[DriverOffer] = []
    for nome_alvo in contas:
        for contexto in _contexts_around(joined, nome_alvo):
            offers.append(_offer_from_context(nome_alvo, contexto, conta_ativa=conta_ativa, contas_grupo=contas))

    blocos = re.split(r"(?=\b(?:[01]?\d|2[0-3]):[0-5]\d\b)", joined)
    for bloco in blocos:
        if "R$" not in bloco:
            continue
        if any(_normalizar_nome(conta) and _normalizar_nome(conta) in _normalizar_nome(bloco) for conta in contas):
            continue
        horario = _extract_time(bloco)
        preco = _extract_price(bloco)
        if horario or preco is not None:
            nome = _guess_driver_name(bloco) or "Concorrente"
            offers.append(
                DriverOffer(
                    nome_motorista=nome,
                    horario=horario,
                    preco=preco,
                    vagas=_extract_vagas(bloco),
                    status=_extract_status(bloco),
                    eh_conta_ativa=_conta_match(nome, conta_ativa),
                    eh_conta_grupo=any(_conta_match(nome, conta) for conta in contas),
                    contexto=limpar_espacos(bloco)[:500],
                )
            )

    return _dedupe_offers(offers)


def _contexts_around(texto: str, termo: str) -> list[str]:
    contexts = []
    pattern = re.compile(re.escape(termo), re.IGNORECASE)
    for match in pattern.finditer(texto or ""):
        start = max(0, match.start() - 300)
        end = min(len(texto), match.end() + 300)
        contexts.append(texto[start:end])
    return contexts


def _offer_from_context(nome: str, contexto: str, *, conta_ativa: str | None, contas_grupo: list[str]) -> DriverOffer:
    return DriverOffer(
        nome_motorista=nome,
        horario=_extract_time(contexto),
        preco=_extract_price(contexto),
        vagas=_extract_vagas(contexto),
        status=_extract_status(contexto),
        eh_conta_ativa=_conta_match(nome, conta_ativa),
        eh_conta_grupo=any(_conta_match(nome, conta) for conta in contas_grupo),
        contexto=limpar_espacos(contexto)[:500],
    )


def _extract_time(texto: str) -> str | None:
    match = TIME_RE.search(texto or "")
    return match.group(0) if match else None


def _extract_price(texto: str) -> float | None:
    match = PRICE_RE.search(texto or "")
    if not match:
        return None
    bruto = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(bruto)
    except ValueError:
        return None


def _extract_vagas(texto: str) -> str | None:
    match = re.search(r"\b(\d+)\s+(?:vaga|vagas|lugar|lugares)\b", texto or "", re.IGNORECASE)
    return match.group(0) if match else None


def _extract_status(texto: str) -> str | None:
    baixo = (texto or "").lower()
    for termo in STATUS_TERMS:
        if termo in baixo:
            return termo
    return None


def _guess_driver_name(bloco: str) -> str | None:
    linhas = [l for l in bloco.split("\n") if l and "R$" not in l and not TIME_RE.search(l)]
    for linha in linhas[:4]:
        if 2 <= len(linha) <= 40 and not any(ch.isdigit() for ch in linha):
            return linha.strip()
    return None


def _dedupe_offers(offers: list[DriverOffer]) -> list[DriverOffer]:
    vistos: set[tuple] = set()
    saida: list[DriverOffer] = []
    for offer in offers:
        key = (
            _normalizar_nome(offer.nome_motorista),
            offer.horario,
            offer.preco,
            offer.eh_conta_ativa,
            offer.eh_conta_grupo,
        )
        if key in vistos:
            continue
        vistos.add(key)
        saida.append(offer)
    return saida
