from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlencode

PUBLIC_CARPOOL_ENTRYPOINT = "https://www.blablacar.com.br/carpool"
PUBLIC_SEARCH_BASE = "https://www.blablacar.com.br/search"
PUBLIC_ALLOWED_HOSTS = ("www.blablacar.com.br", "blablacar.com.br")
PUBLIC_ALLOWED_PATHS = ("/carpool", "/search", "/search-car-sharing")

CONTAS = ("Ezequiel S", "Barbosa")
IDENTIFICADORES_BLOQUEADOS = ("4.9", "Super Driver", "Embaixador", "Expert")

ORIGENS = (
    "Santo André, SP, Brasil",
    "São Paulo, SP, Brasil",
)

DESTINOS = (
    "Extrema, MG, Brasil",
    "Pouso Alegre, MG, Brasil",
    "Três Corações, MG, Brasil",
    "Varginha, MG, Brasil",
    "São Tomé das Letras, MG, Brasil",
    "Cambuquira, MG, Brasil",
    "Campanha, MG, Brasil",
)

DESTINOS_IGNORADOS = ("Caxambu, MG, Brasil",)

INTERMEDIARIAS_PADRAO = (
    "Extrema, Pouso Alegre, Três Corações, Cambuquira, Campanha quando fizer sentido"
)

STATUS_NAO_VALIDADO = "não confirmado / busca pública por data não validada"

FLUXO_SEGURO_APK = [
    {
        "etapa": "Busca pública",
        "uso no sistema": "Gerar/abrir link público com origem, destino, data exata e assentos.",
        "regra": "Começar pelo carpool público; sem busca por data não há recomendação operacional.",
    },
    {
        "etapa": "Resultados",
        "uso no sistema": "Ler motoristas, horários, preços, vagas e status cheio/quase cheio.",
        "regra": "Procurar apenas Ezequiel S e Barbosa como identificadores próprios.",
    },
    {
        "etapa": "Detalhe da carona",
        "uso no sistema": "Guardar contexto público de passageiros/localidades quando o arquivo enviado trouxer esse dado.",
        "regra": "Não depender de login, token, pagamento ou API privada do app.",
    },
    {
        "etapa": "Decisão",
        "uso no sistema": "Retornar CRIAR, MANTER, ALTERAR HORÁRIO, ALTERAR PREÇO, ALTERAR DESTINO FINAL ou EXCLUIR.",
        "regra": "Nunca criar duplicado quando Ezequiel S ou Barbosa já aparecerem na rota/data.",
    },
    {
        "etapa": "Conflito",
        "uso no sistema": "Bloquear conflito entre Ezequiel S e Barbosa em Três Corações no mesmo dia.",
        "regra": "Se uma conta estiver em Três Corações, a outra não deve publicar/ir para lá no mesmo dia.",
    },
]

CAMPOS_SCAN_PUBLICO = [
    {"campo": "link_busca", "origem": "URL pública", "obrigatório": "sim"},
    {"campo": "origem", "origem": "query fn / texto público", "obrigatório": "sim"},
    {"campo": "destino", "origem": "query tn / texto público", "obrigatório": "sim"},
    {"campo": "data_viagem", "origem": "query db / texto público", "obrigatório": "sim"},
    {"campo": "motoristas", "origem": "resultado público", "obrigatório": "sim"},
    {"campo": "horários", "origem": "resultado público", "obrigatório": "quando detectado"},
    {"campo": "preços", "origem": "resultado público", "obrigatório": "quando detectado"},
    {"campo": "status cheio/quase cheio", "origem": "resultado público", "obrigatório": "quando detectado"},
    {"campo": "passageiros/localidades", "origem": "detalhe público salvo em MHTML", "obrigatório": "quando disponível"},
]


def formatar_data_busca(valor: str | date | datetime) -> str:
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor or "").strip()


def gerar_link_busca_publica(origem: str, destino: str, data_viagem: str | date | datetime, assentos: int = 1) -> str:
    """Gera o link público que o operador deve abrir antes de qualquer recomendação."""
    data_iso = formatar_data_busca(data_viagem)
    assentos_int = max(1, min(int(assentos or 1), 4))
    query = urlencode(
        {
            "fn": origem,
            "tn": destino,
            "db": data_iso,
            "seats": assentos_int,
            "search_origin": "HOME",
        }
    )
    return f"{PUBLIC_SEARCH_BASE}?{query}"
