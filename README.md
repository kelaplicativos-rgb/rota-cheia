# Rota Cheia

App assistente de caronas para planejar, validar e organizar viagens no corredor São Paulo/Santo André ↔ Minas Gerais.

## Objetivo

O Rota Cheia ajuda a lotar o carro com antecedência analisando buscas públicas da BlaBlaCar, arquivos `.mhtml/.mht`, motoristas, horários, preços e possíveis conflitos entre as contas **Ezequiel S** e **Barbosa**.

## Corredor operacional

- São Paulo/SP ou Santo André/SP ↔ Extrema/MG
- São Paulo/SP ou Santo André/SP ↔ Pouso Alegre/MG
- São Paulo/SP ou Santo André/SP ↔ Três Corações/MG
- São Paulo/SP ou Santo André/SP ↔ Varginha/MG
- São Paulo/SP ou Santo André/SP ↔ São Tomé das Letras/MG
- Cambuquira/MG e Campanha/MG podem ser consideradas como intermediárias quando ajudarem a completar o carro.
- Caxambu deve ser ignorada.

## Regra obrigatória

Antes de recomendar **CRIAR**, **PUBLICAR**, **MANTER**, **ALTERAR** ou **EXCLUIR**, o app precisa validar a busca pública da BlaBlaCar por **rota + data exata**.

Se a busca pública por data não estiver validada, a saída deve ser:

```txt
não confirmado / busca pública por data não validada
```

## Identificadores válidos

Usar apenas:

- Ezequiel S
- Barbosa

Nunca usar como identificador:

- 4.9
- Super Driver
- Embaixador
- Expert
- qualquer nível ou status da plataforma

## MVP v0.1

Primeira versão com foco em:

1. Upload manual de arquivos `.mhtml/.mht` da BlaBlaCar.
2. Extração de link, origem, destino, data, motoristas, horários, preços e status.
3. Detecção de Ezequiel S e Barbosa.
4. Regra anti-duplicidade.
5. Regra de conflito em Três Corações.
6. Sugestão de ação somente após validação.
7. Histórico em SQLite.

## Como rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```txt
rota-cheia/
├─ app.py
├─ requirements.txt
├─ database/
├─ scanner/
├─ rules/
├─ services/
├─ utils/
└─ data/
```
