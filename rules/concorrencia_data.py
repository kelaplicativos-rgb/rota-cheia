from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
import re

from config.caronas_config import DESTINOS, STATUS_NAO_VALIDADO
from utils.normalizador_texto import sem_acentos


@dataclass
class LeituraConcorrente:
    motorista: str
    horario: str | None
    preco: float | None
    vagas: str | None
    status: str | None
    lotacao_score: int
    destinos_detectados: list[str]
    contexto: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def _score_lotacao(vagas: str | None, status: str | None, contexto: str | None) -> int:
    texto = sem_acentos(" ".join([str(vagas or ""), str(status or ""), str(contexto or "")]))

    if "cheio" in texto or "sem vaga" in texto:
        return 100
    if "quase cheio" in texto or "ultimos lugares" in texto or "esgotara em breve" in texto:
        return 85

    match = re.search(r"\b(\d+)\s+(?:vaga|vagas|lugar|lugares)\b", texto)
    if match:
        vagas_int = int(match.group(1))
        if vagas_int <= 1:
            return 80
        if vagas_int == 2:
            return 60
        return 35

    return 20


def _destinos_no_contexto(contexto: str | None) -> list[str]:
    texto = sem_acentos(contexto)
    encontrados = []
    for destino in DESTINOS:
        nome = sem_acentos(destino).replace(" brasil", "")
        cidade = nome.split(",")[0].strip()
        if cidade and cidade in texto:
            encontrados.append(destino)
    return encontrados


def analisar_concorrencia_por_data(parsed: dict, origem: str | None, destino: str | None, data: str | None) -> dict:
    motoristas = parsed.get("motoristas", []) or []

    leituras: list[LeituraConcorrente] = []
    horarios = Counter()
    destinos = Counter()
    por_horario: dict[str, list[int]] = defaultdict(list)

    for motorista in motoristas:
        contexto = motorista.get("contexto")
        horario = motorista.get("horario") or "horário não detectado"
        detectados = _destinos_no_contexto(contexto)
        score = _score_lotacao(motorista.get("vagas"), motorista.get("status"), contexto)

        horarios[horario] += 1
        por_horario[horario].append(score)
        for item in detectados:
            destinos[item] += 1

        leituras.append(
            LeituraConcorrente(
                motorista=motorista.get("nome_motorista") or "Concorrente",
                horario=motorista.get("horario"),
                preco=motorista.get("preco"),
                vagas=motorista.get("vagas"),
                status=motorista.get("status"),
                lotacao_score=score,
                destinos_detectados=detectados,
                contexto=contexto,
            )
        )

    ranking_horarios = []
    for horario, quantidade in horarios.items():
        scores = por_horario[horario]
        media_lotacao = round(sum(scores) / len(scores), 1) if scores else 0
        ranking_horarios.append(
            {
                "horario": horario,
                "ofertas_detectadas": quantidade,
                "media_lotacao": media_lotacao,
                "forca_captacao": round((quantidade * 10) + media_lotacao, 1),
            }
        )

    ranking_horarios.sort(key=lambda item: item["forca_captacao"], reverse=True)

    return {
        "acao": "SCANNER CONCORRENCIA",
        "origem": origem,
        "destino_final": destino,
        "data": data,
        "horarios_mais_fortes": ranking_horarios,
        "destinos_mais_cotados": [
            {"destino": nome, "ocorrencias": qtd} for nome, qtd in destinos.most_common()
        ],
        "motoristas": [leitura.to_dict() for leitura in sorted(leituras, key=lambda item: item.lotacao_score, reverse=True)],
        "status_validacao": STATUS_NAO_VALIDADO,
    }
