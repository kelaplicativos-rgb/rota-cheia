from __future__ import annotations

from dataclasses import asdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.caronas_config import STATUS_NAO_VALIDADO, gerar_link_busca_publica, normalizar_lista_texto
from scanner.blablacar_parser import parse_search_text
from scanner.validator import validar_busca_publica
from rules.concorrencia_data import analisar_concorrencia_por_data
from rules.motor_decisao import decidir_acao
from utils.datas import hoje_iso


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)


class BuscaPublicaIndisponivel(RuntimeError):
    """Erro controlado quando a busca pública não pode ser baixada automaticamente."""


def baixar_busca_publica(url: str, timeout: int = 20) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read()
    except HTTPError as exc:
        raise BuscaPublicaIndisponivel(
            f"busca pública automática indisponível: HTTP {exc.code} {exc.reason}. "
            "Ação operacional bloqueada até validar rota + data pública."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise BuscaPublicaIndisponivel(
            "busca pública automática indisponível por falha de conexão/timeout. "
            "Ação operacional bloqueada até validar rota + data pública."
        ) from exc
    return raw.decode(charset, errors="replace")


def _montar_resultado(
    *,
    link_busca: str,
    origem: str,
    destino: str,
    data_viagem: str,
    conta: str,
    sentido: str | None,
    horario_planejado: str | None,
    html: str = "",
    motivo_bloqueio: str | None = None,
    contas_grupo: list[str] | tuple[str, ...] | None = None,
    termos_conflito: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    contas = normalizar_lista_texto([conta] + list(contas_grupo or []))

    # Validação forte: o HTML/JSON público é analisado sozinho.
    # A URL gerada pelo app só entra como link de auditoria, nunca como evidência de rota/data.
    parsed_obj = parse_search_text(
        html or "",
        contas_interesse=contas,
        conta_ativa=conta,
    )
    parsed = asdict(parsed_obj)
    parsed["motoristas"] = [m.to_dict() for m in parsed_obj.motoristas]
    parsed["link_busca"] = link_busca
    parsed["origem_solicitada"] = origem
    parsed["destino_solicitado"] = destino
    parsed["data_solicitada"] = data_viagem

    if motivo_bloqueio:
        validacao = {
            "valido": False,
            "status": STATUS_NAO_VALIDADO,
            "motivos": [motivo_bloqueio],
        }
    else:
        validacao = asdict(validar_busca_publica(parsed, origem, destino, data_viagem))

    decisao = decidir_acao(
        parsed,
        validacao,
        conta,
        horario_planejado,
        contas_grupo=contas,
        termos_conflito=termos_conflito,
    )
    concorrencia = analisar_concorrencia_por_data(parsed, origem, destino, data_viagem)
    if validacao.get("valido"):
        concorrencia["status_validacao"] = validacao.get("status")
    else:
        concorrencia["status_validacao"] = STATUS_NAO_VALIDADO

    scan = {
        "created_at": hoje_iso(),
        "arquivo_nome": "scanner-publico-automatico",
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


def analisar_busca_publica_por_data(
    origem: str,
    destino: str,
    data_viagem: str,
    conta: str,
    sentido: str | None = None,
    horario_planejado: str | None = None,
    assentos: int = 1,
    *,
    contas_grupo: list[str] | tuple[str, ...] | None = None,
    termos_conflito: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    link_busca = gerar_link_busca_publica(origem, destino, data_viagem, assentos)
    try:
        html = baixar_busca_publica(link_busca)
    except BuscaPublicaIndisponivel as exc:
        return _montar_resultado(
            link_busca=link_busca,
            origem=origem,
            destino=destino,
            data_viagem=data_viagem,
            conta=conta,
            sentido=sentido,
            horario_planejado=horario_planejado,
            motivo_bloqueio=str(exc),
            contas_grupo=contas_grupo,
            termos_conflito=termos_conflito,
        )

    return _montar_resultado(
        link_busca=link_busca,
        origem=origem,
        destino=destino,
        data_viagem=data_viagem,
        conta=conta,
        sentido=sentido,
        horario_planejado=horario_planejado,
        html=html,
        contas_grupo=contas_grupo,
        termos_conflito=termos_conflito,
    )
