"""Extrai passageiros visíveis de páginas individuais da BlaBlaCar."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Iterable

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from scanner_bla import CHROMIUM_ARGS, TripCard, _launch_chromium


@dataclass
class Passenger:
    name: str
    origin: str = ""
    destination: str = ""
    companions: int = 0
    raw_text: str = ""

    @property
    def estimated_count(self) -> int:
        return 1 + max(0, self.companions)


@dataclass
class TripDetail:
    card: TripCard
    passengers: list[Passenger] = field(default_factory=list)
    raw_text: str = ""
    passenger_block: str = ""
    detail_status: str = "não analisado"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _lines(text: str) -> list[str]:
    return [_clean(line) for line in re.split(r"\n+", text or "") if _clean(line)]


def _companions(name: str) -> int:
    m = re.search(r"\+(\d+)", name)
    return int(m.group(1)) if m else 0


def _looks_like_name(text: str) -> bool:
    if not text or len(text) > 45:
        return False
    low = text.casefold()
    bad = ["origem", "destino", "chegada", "saída", "saida", "r$", "passageiro", "reservar", "motorista"]
    if any(b in low for b in bad):
        return False
    if re.search(r"\d{1,2}:\d{2}", text):
        return False
    return bool(re.match(r"^[A-ZÁÉÍÓÚÃÕÂÊÔÇ][A-Za-zÁÉÍÓÚÃÕÂÊÔÇáéíóúãõâêôç' .+-]+$", text))


def _looks_like_city(text: str) -> bool:
    if not text or len(text) > 70:
        return False
    bad = ["r$", "avalia", "motorista", "reserva", "mensagem", "carona", "passageiro"]
    if any(b in text.casefold() for b in bad):
        return False
    return bool(re.search(r"[A-ZÁÉÍÓÚÃÕÂÊÔÇ][\wÁÉÍÓÚÃÕÂÊÔÇáéíóúãõâêôç' -]{2,}", text))


def extract_passenger_block(text: str) -> str:
    low = text.casefold()
    starts = [low.find(m) for m in ["passageiros", "passageiro", "viajando", "reservas"] if low.find(m) != -1]
    if not starts:
        return ""
    start = min(starts)
    end_candidates = []
    for marker in ["motorista", "sobre", "avaliações", "avaliacoes", "preço", "preco", "mensagem"]:
        pos = low.find(marker, start + 30)
        if pos != -1:
            end_candidates.append(pos)
    end = min(end_candidates) if end_candidates else min(len(text), start + 3500)
    return text[start:end]


def parse_passengers_from_text(text: str) -> list[Passenger]:
    block = extract_passenger_block(text) or text
    lines = _lines(block)
    passengers: list[Passenger] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _looks_like_name(line):
            origin = ""
            destination = ""
            for j in range(i + 1, min(i + 7, len(lines))):
                if _looks_like_city(lines[j]):
                    if not origin:
                        origin = lines[j]
                    elif not destination and lines[j] != origin:
                        destination = lines[j]
                        break
            if origin or destination:
                passengers.append(Passenger(line, origin, destination, _companions(line), " | ".join(lines[i : min(i + 7, len(lines))])))
                i += 4
                continue
        i += 1

    unique: list[Passenger] = []
    seen: set[tuple[str, str, str]] = set()
    for p in passengers:
        key = (p.name.casefold(), p.origin.casefold(), p.destination.casefold())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def parse_trip_detail_from_html(html: str, card: TripCard) -> TripDetail:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    block = extract_passenger_block(text)
    passengers = parse_passengers_from_text(block or text)
    return TripDetail(card, passengers, text, block, "passageiros encontrados" if passengers else "sem passageiros visíveis")


async def scrape_trip_detail(card: TripCard, headless: bool = True, timeout_ms: int = 45000) -> TripDetail:
    async with async_playwright() as p:
        browser = await _launch_chromium(p, headless=headless)
        context = await browser.new_context(locale="pt-BR")
        page = await context.new_page()
        await page.goto(card.url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(2500)
        for _ in range(10):
            await page.evaluate("window.scrollBy(0, 700)")
            await page.wait_for_timeout(600)
        html = await page.content()
        await browser.close()
    return parse_trip_detail_from_html(html, card)


async def scrape_many_trip_details(cards: Iterable[TripCard], headless: bool = True) -> list[TripDetail]:
    details: list[TripDetail] = []
    for card in cards:
        try:
            details.append(await scrape_trip_detail(card, headless=headless))
        except Exception as exc:
            details.append(TripDetail(card=card, detail_status=f"erro ao abrir detalhe: {exc}"))
    return details


def scrape_many_sync(cards: Iterable[TripCard], headless: bool = True) -> list[TripDetail]:
    return asyncio.run(scrape_many_trip_details(cards, headless=headless))
