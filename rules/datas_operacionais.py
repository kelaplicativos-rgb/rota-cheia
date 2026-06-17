from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta

from config.caronas_config import STATUS_NAO_VALIDADO, gerar_link_busca_publica

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
) -> list[dict]:
    """Gera datas futuras candidatas para abrir busca pública depois.

    Esta função não recomenda CRIAR/PUBLICAR/MANTER/ALTERAR/EXCLUIR. Ela apenas monta
    o calendário de validação pública por rota + data exata.
    """
    base = _to_date(data_base)
    semanas = max(1, min(int(semanas or 1), 12))

    padroes = [
        {
            "weekday": 3,
            "sentido": "IDA",
            "horario": "17:30",
            "prioridade": "alta",
            "motivo": "ida quinta no padrão preferido, com antecedência para lotar o carro",
            "origem": origem_ida,
            "destino": destino_ida,
        },
        {
            "weekday": 4,
            "sentido": "VOLTA",
            "horario": "manhã",
            "prioridade": "alta",
            "motivo": "volta sexta de manhã no padrão preferido",
            "origem": destino_ida,
            "destino": origem_ida,
        },
        {
            "weekday": 4,
            "sentido": "IDA",
            "horario": "20:30",
            "prioridade": "alta",
            "motivo": "ida sexta à noite no padrão preferido",
            "origem": origem_ida,
            "destino": destino_ida,
        },
        {
            "weekday": 6,
            "sentido": "VOLTA",
            "horario": "11:00",
            "prioridade": "alta",
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
            datas.append(
                DataOperacional(
                    data=data_viagem.isoformat(),
                    dia_semana=DIAS_PT[data_viagem.weekday()],
                    sentido=str(padrao["sentido"]),
                    origem=str(padrao["origem"]),
                    destino_final=str(padrao["destino"]),
                    horario=str(padrao["horario"]),
                    prioridade=str(padrao["prioridade"]),
                    motivo=str(padrao["motivo"]),
                    link_busca_publica=gerar_link_busca_publica(
                        origem=str(padrao["origem"]),
                        destino=str(padrao["destino"]),
                        data_viagem=data_viagem,
                        assentos=assentos,
                    ),
                )
            )

    return [item.to_dict() for item in sorted(datas, key=lambda item: (item.data, item.sentido, item.horario))]
