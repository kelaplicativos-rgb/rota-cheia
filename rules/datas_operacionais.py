from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta

from config.caronas_config import STATUS_NAO_VALIDADO, gerar_link_busca_publica
from rules.eventos_regionais import eventos_relevantes_para_data, score_eventos_regionais

DIAS_PT = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}


@dataclass
class DataOperacional:
    data: str
    dia_semana: str
    sentido: str
    origem: str
    destino_final: str
    horario: str
    prioridade: str
    motivo: str
    score_base: int
    score_eventos: int
    score_total: int
    eventos_relevantes: list[dict]
    link_busca_publica: str
    status_validacao: str = STATUS_NAO_VALIDADO

    def to_dict(self) -> dict:
        return asdict(self)


def _to_date(valor: date | datetime | str | None = None) -> date:
    if valor is None:
        return date.today()
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.fromisoformat(str(valor)).date()


def _proximo_dia(base: date, weekday: int) -> date:
    dias = (weekday - base.weekday()) % 7
    return base + timedelta(days=dias)


def gerar_datas_operacionais(
    origem_ida: str,
    destino_ida: str,
    semanas: int = 3,
    incluir_sabado: bool = False,
    data_base: date | datetime | str | None = None,
    assentos: int = 1,
    eventos_regionais: list[dict] | None = None,
    localidades_eventos: list[str] | None = None,
) -> list[dict]:
    base = _to_date(data_base)
    semanas = max(1, min(int(semanas or 1), 12))
    localidades = localidades_eventos or [origem_ida, destino_ida]

    padroes = [
        {
            "weekday": 3,
            "sentido": "IDA",
            "horario": "17:30",
            "prioridade": "alta",
            "score_base": 75,
            "motivo": "ida quinta no padrão preferido, com antecedência para lotar o carro",
            "origem": origem_ida,
            "destino": destino_ida,
        },
        {
            "weekday": 4,
            "sentido": "VOLTA",
            "horario": "manhã",
            "prioridade": "alta",
            "score_base": 70,
            "motivo": "volta sexta de manhã no padrão preferido",
            "origem": destino_ida,
            "destino": origem_ida,
        },
        {
            "weekday": 4,
            "sentido": "IDA",
            "horario": "20:30",
            "prioridade": "muito alta",
            "score_base": 85,
            "motivo": "ida sexta à noite no padrão preferido para captar passageiros de fim de semana",
            "origem": origem_ida,
            "destino": destino_ida,
        },
        {
            "weekday": 6,
            "sentido": "VOLTA",
            "horario": "11:00",
            "prioridade": "muito alta",
            "score_base": 85,
            "motivo": "volta domingo perto de 11:00 no padrão preferido",
            "origem": destino_ida,
            "destino": origem_ida,
        },
    ]

    if incluir_sabado:
        padroes.append(
            {
                "weekday": 5,
                "sentido": "IDA",
                "horario": "noite",
                "prioridade": "condicional",
                "score_base": 45,
                "motivo": "sábado à noite somente se demanda ou evento justificar",
                "origem": origem_ida,
                "destino": destino_ida,
            }
        )

    datas: list[DataOperacional] = []
    for semana in range(semanas):
        inicio_semana = base + timedelta(days=semana * 7)
        for padrao in padroes:
            data_viagem = _proximo_dia(inicio_semana, int(padrao["weekday"]))
            if data_viagem < base:
                continue

            score_base = int(padrao["score_base"])
            score_eventos = score_eventos_regionais(eventos_regionais, data_viagem, localidades)
            eventos_relevantes = eventos_relevantes_para_data(eventos_regionais, data_viagem, localidades)
            score_total = min(100, score_base + score_eventos)

            motivo = str(padrao["motivo"])
            if eventos_relevantes:
                motivo += " + evento regional relevante na janela da viagem"

            datas.append(
                DataOperacional(
                    data=data_viagem.isoformat(),
                    dia_semana=DIAS_PT[data_viagem.weekday()],
                    sentido=str(padrao["sentido"]),
                    origem=str(padrao["origem"]),
                    destino_final=str(padrao["destino"]),
                    horario=str(padrao["horario"]),
                    prioridade=str(padrao["prioridade"]),
                    motivo=motivo,
                    score_base=score_base,
                    score_eventos=score_eventos,
                    score_total=score_total,
                    eventos_relevantes=eventos_relevantes,
                    link_busca_publica=gerar_link_busca_publica(
                        origem=str(padrao["origem"]),
                        destino=str(padrao["destino"]),
                        data_viagem=data_viagem,
                        assentos=assentos,
                    ),
                )
            )

    return [item.to_dict() for item in sorted(datas, key=lambda item: (-item.score_total, item.data, item.sentido, item.horario))]
