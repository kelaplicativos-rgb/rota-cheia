from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser

from bs4 import BeautifulSoup


@dataclass
class MhtmlContent:
    html: str
    text: str


def read_mhtml_bytes(raw_bytes: bytes) -> MhtmlContent:
    """Lê um arquivo .mhtml/.mht salvo pelo navegador e retorna HTML + texto limpo."""
    message = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    html_parts: list[str] = []
    text_parts: list[str] = []

    if message.is_multipart():
        parts = message.walk()
    else:
        parts = [message]

    for part in parts:
        content_type = part.get_content_type()
        try:
            payload = part.get_content()
        except Exception:
            continue

        if not isinstance(payload, str):
            continue

        if content_type == "text/html":
            html_parts.append(payload)
        elif content_type == "text/plain":
            text_parts.append(payload)

    html = "\n".join(html_parts)
    if html:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n")
    else:
        text = "\n".join(text_parts)

    return MhtmlContent(html=html, text=text)
