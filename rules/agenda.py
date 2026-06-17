from __future__ import annotations

PADRAO_LOGISTICO = [
    {"sentido": "IDA", "dia": "quinta", "horario": "17:30", "observacao": "padrão preferido"},
    {"sentido": "VOLTA", "dia": "sexta", "horario": "manhã", "observacao": "padrão preferido"},
    {"sentido": "IDA", "dia": "sexta", "horario": "20:30", "observacao": "padrão preferido"},
    {"sentido": "VOLTA", "dia": "domingo", "horario": "11:00", "observacao": "padrão preferido"},
    {"sentido": "IDA", "dia": "sábado", "horario": "noite", "observacao": "usar somente com demanda ou evento forte"},
]


def listar_padrao_logistico() -> list[dict]:
    return PADRAO_LOGISTICO.copy()
