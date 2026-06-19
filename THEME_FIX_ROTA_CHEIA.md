# Correção de tema claro

Esta atualização foi criada porque o app ativo é `rota-cheia.streamlit.app`, ligado ao repositório `kelaplicativos-rgb/rota-cheia`.

O tema claro foi aplicado no arquivo correto:

- `app.py`: CSS claro com `!important` para sobrescrever o tema escuro antigo.
- `.streamlit/config.toml`: tema base light, azul principal e texto azul-marinho.
- `theme_probe.py`: força novo deploy no Streamlit Cloud.

Visual esperado: fundo branco, azul forte, texto azul-marinho, cards brancos arredondados e botões azuis.
