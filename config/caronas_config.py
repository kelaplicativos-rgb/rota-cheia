from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlencode

PUBLIC_CARPOOL_ENTRYPOINT = "https://www.blablacar.com.br/carpool"
PUBLIC_SEARCH_BASE = "https://www.blablacar.com.br/search"
PUBLIC_ALLOWED_HOSTS = ("www.blablacar.com.br", "blablacar.com.br")
PUBLIC_ALLOWED_PATHS = ("/carpool", "/search", "/search-car-sharing")

# Sugestões de demonstração. O núcleo não depende destes nomes.
CONTAS_SUGERIDAS = ("Ezequiel S", "Barbosa")
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
TERMOS_CONFLITO_SUGERIDOS = ("Três Corações",)

INTERMEDIARIAS_PADRAO = (
    "Extrema, Pouso Alegre, Três Corações, Cambuquira, Campanha quando fizer sentido"
)

STATUS_NAO_VALIDADO = "não confirmado / busca pública por data não validada"

FLUXO_SEGURO_APK = [
    {
        "etapa": "Inteligência de captação",
        "uso no sistema": "Usuário informa origem e destino; o sistema gera ranking de datas futuras.",
        "regra": "Não recomendar ação operacional antes da validação pública por rota e data.",
    },
    {
        "etapa": "Eventos regionais",
        "uso no sistema": "Eventos aumentam a pontuação das datas próximas à região definida.",
        "regra": "Sábado à noite só ganha força quando houver demanda ou evento relevante.",
    },
    {
        "etapa": "Scanner da data escolhida",
        "uso no sistema": "Executar busca pública interna para ler motoristas, horários, preços e lotação.",
        "regra": "O fluxo principal não depende de link digitado nem arquivo manual.",
    },
    {
        "etapa": "Ranking da concorrência",
        "uso no sistema": "Mostrar horários fortes, destinos cotados, motoristas mais cheios e faixa de preço.",
        "regra": "A decisão usa apenas dados validados na busca pública da data.",
    },
    {
        "etapa": "Fallback técnico",
        "uso no sistema": "Importação manual somente para diagnóstico interno, fora do fluxo do usuário.",
        "regra": "O usuário final não precisa fornecer .mhtml/.mht.",
    },
]

CAMPOS_SCAN_PUBLICO = [
    {"campo": "origem", "origem": "usuário", "obrigatório": "sim"},
    {"campo": "destino", "origem": "usuário", "obrigatório": "sim"},
    {"campo": "datas futuras", "origem": "inteligência de captação", "obrigatório": "sim"},
    {"campo": "eventos regionais", "origem": "camada de eventos", "obrigatório": "opcional"},
    {"campo": "horários fortes", "origem": "scanner público por data", "obrigatório": "após validação"},
    {"campo": "destinos cotados", "origem": "scanner público por data", "obrigatório": "após validação"},
    {"campo": "motoristas mais cheios", "origem": "scanner público por data", "obrigatório": "após validação"},
    {"campo": "preço médio/faixa", "origem": "scanner público por data", "obrigatório": "quando detectado"},
]


def normalizar_lista_texto(valores: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if valores is None:
        return []
    if isinstance(valores, str):
        bruto = valores.replace(",", "\n").splitlines()
    else:
        bruto = list(valores)
    saida: list[str] = []
    for valor in bruto:
        item = str(valor or "").strip()
        if item and item not in saida:
            saida.append(item)
    return saida


def formatar_data_busca(valor: str | date | datetime) -> str:
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor or "").strip()


def gerar_link_busca_publica(origem: str, destino: str, data_viagem: str | date | datetime, assentos: int = 1) -> str:
    """Gera link público de auditoria.

    Importante: este link não é usado como evidência de validação. A validação forte
    só considera rota/data encontradas no HTML/JSON público retornado pela BlaBlaCar.
    """
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
