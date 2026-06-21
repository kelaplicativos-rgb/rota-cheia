# Rota Cheia — RotaClean

Aplicação enxuta para duas funções:

1. **Mensagens e avaliações** — reformula mensagens curtas para BlaBlaCar.
2. **SCAN BLA Modo Ouro** — valida a busca pública, abre caronas acessíveis e monta ranking por passageiros visíveis.

## Rodar

```bash
pip install -r requirements.txt
python -m playwright install chromium
streamlit run app.py
```

## Regra principal

Antes de recomendar criar, publicar, manter, alterar ou excluir, validar rota + data exata na busca pública da BlaBlaCar.

Se a busca pública por data não for validada:

```text
não confirmado / busca pública por data não validada
```

## Foco do scanner

O destino do motorista é só a rota-base. O dado principal é:

```text
passageiro → origem → destino → horário → motorista → preço
```

Nesta versão não há banco de dados. O relatório é gerado na execução e pode ser baixado em Markdown.
