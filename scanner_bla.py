"""Scanner da listagem pública da BlaBlaCar.

Captura rota, data, lista de caronas e links internos. O detalhe dos
passageiros fica no módulo trip_detail_scraper.py.
"""

from __future__ import annotations

import asyncio
from email import policy
from email.parser import BytesParser
import html as html_lib
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BLABLACAR_BASE = "https://www.blablacar.com.br"
CHROMIUM_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]


@dataclass
class TripCard:
    driver: str = ""
    departure_time: str = ""
    arrival_time: str = ""
    origin: str = ""
    destination: str = ""
    price: str = ""
    status: str = "Disponível"
    url: str = ""
    raw_text: str = ""

    @property
    def is_full(self) -> bool:
        return "cheio" in self.status.casefold()


@dataclass(frozen=True)
class MhtmlDocument:
    html: str
    source_url: str = ""


def _ensure_chromium_installed() -> None:
    """Instala o Chromium do Playwright quando o ambiente ainda não tem browser."""
    if os.environ.get("ROTACHEIA_SKIP_PLAYWRIGHT_INSTALL") == "1":
        return
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _launch_chromium(p, headless: bool):
    try:
        return await p.chromium.launch(headless=headless, args=CHROMIUM_ARGS)
    except Exception as exc:
        msg = str(exc).casefold()
        if "executable doesn't exist" not in msg and "browser executable" not in msg:
            raise
        _ensure_chromium_installed()
        return await p.chromium.launch(headless=headless, args=CHROMIUM_ARGS)


def _decode_payload(payload: bytes, charset: str | None = None) -> str:
    for encoding in [charset, "utf-8", "windows-1252", "latin-1"]:
        if not encoding:
            continue
        try:
            return payload.decode(encoding, errors="replace")
        except LookupError:
            continue
    return payload.decode("utf-8", errors="replace")


def load_html_or_mhtml_with_source(path: str | Path) -> MhtmlDocument:
    """Lê HTML comum ou MHTML preservando a URL original da busca.

    O MHTML da BlaBlaCar é multipart/related. Decodificar o arquivo inteiro como
    quoted-printable corrompe cabeçalhos e pode perder link/data. Por isso esta
    função extrai somente a parte text/html e captura Snapshot-Content-Location
    ou Content-Location.
    """
    data = Path(path).read_bytes()
    source_url = ""
    try:
        msg = BytesParser(policy=policy.default).parsebytes(data)
        source_url = str(msg.get("Snapshot-Content-Location") or msg.get("Content-Location") or "").strip()
        parts = list(msg.walk()) if msg.is_multipart() else [msg]
        for part in parts:
            if part.get_content_type() != "text/html":
                continue
            source_url = source_url or str(part.get("Content-Location") or "").strip()
            payload = part.get_payload(decode=True)
            if payload is None:
                text = str(part.get_content())
            else:
                text = _decode_payload(payload, part.get_content_charset())
            if "<html" in text.casefold():
                return MhtmlDocument(text, source_url)
    except Exception:
        source_url = ""

    text = _decode_payload(data, "utf-8")
    return MhtmlDocument(text, source_url)


def load_html_or_mhtml(path: str | Path) -> str:
    return load_html_or_mhtml_with_source(path).html


def extrair_link_do_mhtml(path: str | Path) -> str:
    return load_html_or_mhtml_with_source(path).source_url


def _fold(text: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()


def _clean(text: str) -> str:
    text = html_lib.unescape(text or "")
    text = text.replace("\xa0", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", text).strip()


def _lines(text: str) -> list[str]:
    return [_clean(line) for line in re.split(r"\n+", text or "") if _clean(line)]


def _is_time(text: str) -> bool:
    return bool(re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d", _clean(text)))


def _times(text: str) -> list[str]:
    return re.findall(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", text)


def _is_duration(text: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}h(?:[0-5]\d)?", _clean(text)))


def _price_from_lines(lines: list[str]) -> str:
    for i, line in enumerate(lines):
        if re.search(r"R\$\s*\d+", line):
            m = re.search(r"R\$\s*\d+(?:[,.]\d{2})?", line)
            if m:
                return m.group(0).replace("R$", "R$ ")
        if line == "R$" and i + 1 < len(lines):
            inteiro = re.sub(r"\D", "", lines[i + 1])
            centavos = ""
            if i + 2 < len(lines) and re.fullmatch(r"[,.]\d{2}", lines[i + 2]):
                centavos = lines[i + 2].replace(",", ",")
            if inteiro:
                return f"R$ {inteiro}{centavos or ',00'}"
    return ""


def _price(text: str) -> str:
    return _price_from_lines(_lines(text))


def _status(text: str) -> str:
    low = _fold(text)
    if "cheio" in low:
        return "Cheio"
    if "esgotara" in low or "esgotar" in low or "esgot" in low:
        return "Esgotará em breve"
    return "Disponível"


def _is_rating(text: str) -> bool:
    text = _clean(text)
    if not re.fullmatch(r"\d(?:[,.]\d)?", text):
        return False
    try:
        return 0 <= float(text.replace(",", ".")) <= 5
    except ValueError:
        return False


def _is_price_piece(text: str) -> bool:
    text = _clean(text)
    return bool(
        text == "R$"
        or re.fullmatch(r"\d{1,3}", text)
        or re.fullmatch(r"[,.]\d{2}", text)
        or re.fullmatch(r"R\$\s*\d+(?:[,.]\d{2})?", text)
    )


def _is_day_marker(text: str) -> bool:
    return bool(re.fullmatch(r"\+\d+", _clean(text)))


def _looks_like_driver(text: str) -> bool:
    text = _clean(text)
    low = _fold(text)
    if not text or len(text) > 55:
        return False
    bad = {
        "cheio",
        "disponivel",
        "esgotara em breve",
        "super driver",
        "embaixador",
        "expert",
        "carona",
        "onibus",
        "tudo",
        "sem filtros disponiveis",
        "hoje",
        "amanha",
    }
    if low in bad or any(token in low for token in ["r$", "passageiro", "viagens disponiveis"]):
        return False
    if _is_time(text) or _is_duration(text) or _is_rating(text) or _is_price_piece(text):
        return False
    return bool(re.search(r"[A-Za-zÁÉÍÓÚÃÕÂÊÔÇáéíóúãõâêôç]", text))


def _driver_from_tail(lines: list[str]) -> str:
    skip_price_parts = 0
    for line in lines:
        low = _fold(line)
        if line == "R$":
            skip_price_parts = 2
            continue
        if skip_price_parts:
            skip_price_parts -= 1
            continue
        if "cheio" in low or "esgot" in low:
            continue
        if _looks_like_driver(line):
            return line
    return ""


def _guess_driver(text: str, html: str = "") -> str:
    for candidate in re.findall(r'alt="([^"]+)"', html):
        candidate = _clean(candidate)
        if _looks_like_driver(candidate):
            return candidate
    return _driver_from_tail(_lines(text))


def _guess_route(text: str) -> tuple[str, str]:
    cidades = [
        "São Paulo",
        "Santo André",
        "Três Corações",
        "Tres Coracoes",
        "Varginha",
        "Pouso Alegre",
        "Extrema",
        "Cambuí",
        "Campanha",
        "Cambuquira",
        "São Thomé das Letras",
        "São Tomé das Letras",
        "Lambari",
        "Atibaia",
        "Guarulhos",
        "São Bernardo do Campo",
        "Mogi das Cruzes",
        "Minas Gerais",
        "Carmo da Cachoeira",
        "Baependi",
        "Caxambu",
    ]
    found: list[tuple[int, str]] = []
    folded_text = _fold(text)
    for cidade in cidades:
        pos = folded_text.find(_fold(cidade))
        if pos != -1:
            canon = "Três Corações" if cidade == "Tres Coracoes" else cidade
            found.append((pos, canon))
    ordered: list[str] = []
    for _, cidade in sorted(found):
        if cidade not in ordered:
            ordered.append(cidade)
    if len(ordered) >= 2:
        return ordered[0], ordered[-1]
    return "", ""


def _next_card_start(lines: list[str], start: int) -> int:
    for i in range(start, len(lines) - 1):
        if _is_time(lines[i]) and any(_is_duration(lines[j]) for j in range(i + 1, min(i + 3, len(lines)))):
            return i
    return len(lines)


def _parse_card_at(lines: list[str], start: int, url: str = "") -> tuple[TripCard | None, int]:
    if not _is_time(lines[start]):
        return None, start + 1

    duration_idx = -1
    for j in range(start + 1, min(start + 4, len(lines))):
        if _is_duration(lines[j]):
            duration_idx = j
            break
    if duration_idx == -1:
        return None, start + 1

    arrival_idx = -1
    for j in range(duration_idx + 1, min(duration_idx + 5, len(lines))):
        if _is_time(lines[j]):
            arrival_idx = j
            break
    if arrival_idx == -1:
        return None, start + 1

    origin_candidates = [
        line for line in lines[duration_idx + 1 : arrival_idx] if not _is_time(line) and not _is_duration(line)
    ]
    origin = origin_candidates[-1] if origin_candidates else ""

    destination = ""
    destination_idx = -1
    for j in range(arrival_idx + 1, min(arrival_idx + 6, len(lines))):
        line = lines[j]
        if _is_time(line) or _is_duration(line) or _is_price_piece(line) or _is_day_marker(line):
            continue
        destination = line
        destination_idx = j
        break

    if not origin and not destination:
        return None, start + 1

    end = _next_card_start(lines, max(destination_idx + 1, arrival_idx + 1))
    block = lines[start:end]
    tail = lines[destination_idx + 1 : end] if destination_idx != -1 else lines[arrival_idx + 1 : end]
    card = TripCard(
        driver=_driver_from_tail(tail),
        departure_time=lines[start],
        arrival_time=lines[arrival_idx],
        origin=origin,
        destination=destination,
        price=_price_from_lines(block),
        status=_status(" ".join(block)),
        url=url,
        raw_text="\n".join(block),
    )
    return card, max(end, start + 1)


def _parse_trip_cards_from_text(text: str, url: str = "") -> list[TripCard]:
    lines = _lines(text)
    cards: list[TripCard] = []
    i = 0
    while i < len(lines):
        card, next_i = _parse_card_at(lines, i, url=url)
        if card:
            cards.append(card)
        i = next_i
    return cards


def _card_key(card: TripCard) -> tuple[str, str, str, str, str, str]:
    return (
        _fold(card.departure_time),
        _fold(card.arrival_time),
        _fold(card.origin),
        _fold(card.destination),
        _fold(card.driver),
        _fold(card.price),
    )


def _trip_container_text(anchor) -> str:
    for name in ["li", "article"]:
        container = anchor.find_parent(name)
        if container:
            return container.get_text("\n", strip=True)
    container = anchor
    for _ in range(4):
        if container.parent:
            container = container.parent
            text = container.get_text("\n", strip=True)
            if "R$" in text or _status(text) != "Disponível":
                return text
    return anchor.get_text("\n", strip=True)


def parse_trip_cards_from_html(html: str, base_url: str = BLABLACAR_BASE) -> list[TripCard]:
    soup = BeautifulSoup(html, "html.parser")
    cards: list[TripCard] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()

    def add(card: TripCard) -> None:
        key = _card_key(card)
        if key in seen:
            return
        seen.add(key)
        cards.append(card)

    anchors = soup.find_all("a", href=re.compile(r"/trip\?|/trip\b|blablacar\.com\.br/trip"))
    for anchor in anchors:
        href = (anchor.get("href") or "").replace("&amp;", "&")
        if not href:
            continue
        url = urljoin(base_url, href)
        raw_text = _trip_container_text(anchor)
        parsed_cards = _parse_trip_cards_from_text(raw_text, url=url)
        if parsed_cards:
            add(parsed_cards[0])
        else:
            anchor_text = _clean(anchor.get_text("\n", strip=True))
            times = _times(anchor_text)
            origin, destination = _guess_route(anchor_text)
            add(
                TripCard(
                    driver=_guess_driver(raw_text, str(anchor)),
                    departure_time=times[0] if times else "",
                    arrival_time=times[1] if len(times) > 1 else "",
                    origin=origin,
                    destination=destination,
                    price=_price(raw_text),
                    status=_status(raw_text),
                    url=url,
                    raw_text=raw_text,
                )
            )

    for card in _parse_trip_cards_from_text(soup.get_text("\n", strip=True)):
        add(card)
    return cards


async def _auto_scroll(page, max_scrolls: int = 18) -> None:
    previous_height = 0
    for _ in range(max_scrolls):
        height = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(900)
        if height == previous_height:
            break
        previous_height = height


async def scan_search_page(search_url: str, headless: bool = True, timeout_ms: int = 45000) -> list[TripCard]:
    async with async_playwright() as p:
        browser = await _launch_chromium(p, headless=headless)
        context = await browser.new_context(locale="pt-BR")
        page = await context.new_page()
        await page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(2500)
        await _auto_scroll(page)
        html = await page.content()
        await browser.close()
    return parse_trip_cards_from_html(html, base_url=search_url)


def scan_sync(search_url: str, headless: bool = True) -> list[TripCard]:
    return asyncio.run(scan_search_page(search_url, headless=headless))


def filtrar_caronas_acessiveis(cards: Iterable[TripCard], incluir_cheias: bool = False) -> list[TripCard]:
    if incluir_cheias:
        return list(cards)
    return [card for card in cards if not card.is_full]


def extrair_data_do_link(url: str) -> str:
    return (parse_qs(urlparse(url).query).get("db") or [""])[0]
