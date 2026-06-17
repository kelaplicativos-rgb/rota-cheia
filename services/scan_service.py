from __future__ import annotations

from dataclasses import asdict
from typing import Any

from scanner.blablacar_parser import parse_search_text
from scanner.mhtml_reader import read_mhtml_bytes
from scanner.validator import validar_busca_publica
from rules.motor_decisao import decidir_acao
from utils.datas import hoje_iso


def _aplicar_link_manual_publico(parsed: dict[str, Any], link_publico_manual: str | None) -> dict[str, Any]:
    """Usa o link público informado na tela quando o MHTML não preserva a URL da busca."""
    link_publico_manual = (link_publico_manual or "").strip()
    if not link_publico_manual:
        return parsed

    manual = asdict(parse_search_text(link_publico_manual))
    parsed["link_busca"] = parsed.get("link_busca") or manual.get("link_busca") or link_publico_manual

    for campo in ("origem", "destino", "data_viagem"):
        parsed[campo] = parsed.get(campo) or manual.get(campo)

    return parsed


def analisar_arquivo_mhtml(
    raw_bytes: bytes,
    arquivo_nome: str,
    origem_esperada: str | None,
    destino_esperado: str | None,
    data_esperada: str | None,
    conta: str,
    sentido: str | None = None,
    horario_planejado: str | None = None,
    link_publico_manual: str | None = None,
) -> dict[str, Any]:
    conteudo = read_mhtml_bytes(raw_bytes)
    parsed_obj = parse_search_text(conteudo.html + "\n" + conteudo.text)
    parsed = asdict(parsed_obj)
    parsed["motoristas"] = [m.to_dict() for m in parsed_obj.motoristas]
    parsed = _aplicar_link_manual_publico(parsed, link_publico_manual)

    validacao_obj = validar_busca_publica(parsed, origem_esperada, destino_esperado, data_esperada)
    validacao = asdict(validacao_obj)
    decisao = decidir_acao(parsed, validacao, conta, horario_planejado)

    scan = {
        "created_at": hoje_iso(),
        "arquivo_nome": arquivo_nome,
        "link_busca": parsed.get("link_busca"),
        "origem": parsed.get("origem") or origem_esperada,
        "destino": parsed.get("destino") or destino_esperado,
        "data_viagem": parsed.get("data_viagem") or data_esperada,
        "sentido": sentido,
        "status_validacao": validacao.get("status"),
        "observacoes": "; ".join(validacao.get("motivos", [])),
    }

    return {
        "scan": scan,
        "parsed": parsed,
        "validacao": validacao,
        "decisao": decisao,
        "motoristas": parsed.get("motoristas", []),
    }
