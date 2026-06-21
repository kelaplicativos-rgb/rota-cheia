# Rota Cheia

App enxuto para duas funções:

1. **Mensagens e avaliações** — reformula textos curtos para BlaBlaCar.
2. **SCAN BLA Modo Ouro** — valida a busca pública, abre caronas acessíveis e gera ranking por origem, destino, horário, motorista e preço.

## Estrutura

- `app.py` — interface Streamlit.
- `message_rewriter.py` — reformulação de mensagens e avaliações.
- `scanner_bla.py` — captura rota, data, lista de caronas e links.
- `trip_detail_scraper.py` — abre detalhes das caronas acessíveis.
- `ranking_passageiros.py` — monta ranking por origem, destino, horário, motorista e preço.
- `validador_conflito.py` — verifica Ezequiel S, Barbosa, duplicidade e conflito.

## Instalação

```bash
pip install -r requirements.txt
python -m playwright install chromium
streamlit run app.py
```

## Regra de operação

Antes de recomendar criar, publicar, manter, alterar ou excluir, o app deve validar a busca pública por rota + data exata.

Se a busca pública por data não for validada, o resultado deve ser:

```text
não confirmado / busca pública por data não validada
```
