"""Scanner da listagem pública da BlaBlaCar.

Captura rota, data, lista de caronas e links internos. O detalhe dos
passageiros fica no módulo trip_detail_scraper.py.
"""

from __future__ import annotations

import asyncio
import os
import quopri
import re
import subprocess
import sys
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


def _ensure_chromium_installed() -> None:
    """Instala o Chromium do Playwright quando o ambiente ainda não tem browser.

    No Streamlit Cloud o pacote Python pode ser instalado sem o binário do
    navegador. Esta rotina tenta baixar o Chromium na primeira execução real do
    scanner, evitando falha do tipo "Executable doesn't exist".
    """
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


def decode_mhtml_bytes(data: bytes) -> str:
    decoded = quopri.decodestring(data)
    return decoded.decode("utf-8", errors="ignore")


def load_html_or_mhtml(path: str | Path) -> str:
    data = Path(path).read_bytes()
    text = decode_mhtml_bytes(data)
    if "<html" not in text.lower():
        text = data.decode("utf-8", errors="ignore")
    return text


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _times(text: str) -> list[str]:
    return re.findall(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", text)


def _price(text: str) -> str:
    m = re.search(r"R\$\s*\d+(?:[,.]\d{2})?", text)
    return m.group(0) if m else ""


def _status(text: str) -> str:
    low = text.casefold()
    if "cheio" in low:
        return "Cheio"
    if "esgotará" in low or "esgotara" in low or "esgot" in low:
        return "Esgotará em breve"
    return "Disponível"


def _guess_driver(text: str, html: str = "") -> str:
    for candidate in re.findall(r'alt="([^"]+)"', html):
        candidate = _clean(candidate)
        if candidate and not candidate.lower().startswith("http"):
            return candidate
    chunks = [c.strip() for c in re.split(r"\n+| {2,}", text or "") if c.strip()]
    for chunk in reversed(chunks):
        low = chunk.casefold()
        if "r$" in low or re.search(r"\d", chunk):
            continue
        if low in {"cheio", "esgotará em breve", "disponível"}:
            continue
        if 2 <= len(chunk) <= 45:
            return chunk
    return ""


def _guess_route(text: str) -> tuple[str, str]:
    cidades = [
        "São Paulo", "Santo André", "Três Corações", "Tres Coracoes", "Varginha",
        "Pouso Alegre", "Extrema", "Cambuí", "Campanha", "Cambuquira",
        "São Thomé das Letras", "São Tomé das Letras", "Lambari", "Atibaia",
        "Guarulhos", "São Bernardo do Campo", "Mogi das Cruzes", "Minas Gerais",
    ]
    found: list[str] = []
    for cidade in cidades:
        if re.search(re.escape(cidade), text, flags=re.I):
            canon = "Três Corações" if cidade == "Tres Coracoes" else cidade
            if canon not in found:
                found.append(canon)
    if len(found) >= 2:
        return found[0], found[-1]
    return "", ""


def parse_trip_cards_from_html(html: str, base_url: str = BLABLACAR_BASE) -> list[TripCard]:
    soup = BeautifulSoup(html, "html.parser")
    cards: list[TripCard] = []
    seen: set[str] = set()
    anchors = soup.find_all("a", href=re.compile(r"/trip\?|/trip\b|blablacar\.com\.br/trip"))
    for anchor in anchors:
        href = (anchor.get("href") or "").replace("&amp;", "&")
        if not href:
            continue
        url = urljoin(base_url, href)
        if "/trip" not in url or url in seen:
            continue
        seen.add(url)
        raw_text = _clean(anchor.get_text("\n", strip=True))
        raw_html = str(anchor)
        times = _times(raw_text)
        origin, destination = _guess_route(raw_text)
        cards.append(
            TripCard(
                driver=_guess_driver(raw_text, raw_html),
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
