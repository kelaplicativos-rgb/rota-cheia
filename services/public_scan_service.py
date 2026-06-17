from __future__ import annotations

from dataclasses import asdict
from typing import Any
from urllib.request import Request, urlopen

from config.caronas_config import gerar_link_busca_publica
from scanner.blablacar_parser import parse_search_text
from scanner.validator import validar_busca_publica
from rules.concorrencia_data import analisar_concorrencia_por_data
from rules.motor_decisao import decidir_acao
from utils.datas import hoje_iso


USER_AGENT = "Mozilla/5.0 RotaCheia/1.0"


def baixar_busca_publica(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read()
    return raw.decode(charset, errors="replace")


def analisar_busca_publica_por_data(
    origem: str,
    destino: str,
    data_viagem: str,
    conta: str,
    sentido: str | None = None,
    horario_planejado: str | None = None,
    assentos: int = 1,
) -> dict[str, Any]:
    link_busca = gerar_link_busca_publica(origem, destino, data_viagem, assentos)
    html = baixar_busca_publica(link_busca)

    parsed_obj = parse_search_text(link_busca + "\n" + html)
    parsed = asdict(parsed_obj)
    parsed["motoristas"] = [m.to_dict() for m in parsed_obj.motoristas]
    parsed["link_busca"] = parsed.get("link_busca") or link_busca
    parsed["origem"] = parsed.get("origem") or origem
    parsed["destino"] = parsed.get("destino") or destino
    parsed["data_viagem"] = parsed.get("data_viagem") or data_viagem

    validacao = asdict(validar_busca_publica(parsed, origem, destino, data_viagem))
    decisao = decidir_acao(parsed, validacao, conta, horario_planejado)
    concorrencia = analisar_concorrencia_por_data(parsed, origem, destino, data_viagem)
    if validacao.get("valido"):
        concorrencia["status_validacao"] = validacao.get("status")

    scan = {
        "created_at": hoje_iso(),
        "arquivo_nome": "scanner-publico",
        "link_busca": link_busca,
        "origem": origem,
        "destino": destino,
        "data_viagem": data_viagem,
        "sentido": sentido,
        "status_validacao": validacao.get("status"),
        "observacoes": "; ".join(validacao.get("motivos", [])),
    }

    return {
        "scan": scan,
        "parsed": parsed,
        "validacao": validacao,
        "decisao": decisao,
        "concorrencia": concorrencia,
        "motoristas": parsed.get("motoristas", []),
    }
