# Rota Cheia

App assistente de caronas para planejar, validar e organizar viagens no corredor São Paulo/Santo André ↔ Minas Gerais.

## Objetivo

O Rota Cheia ajuda a lotar o carro com antecedência analisando buscas públicas da BlaBlaCar, arquivos `.mhtml/.mht`, motoristas, horários, preços, lotação e possíveis conflitos entre as contas **Ezequiel S** e **Barbosa**.

## Primeiro módulo

O app deve começar por **Mensagens e avaliações BlaBlaCar**, porque este é o recurso mais rápido, mais usado e com maior chance de engajar o usuário logo na entrada.

Fluxo do módulo:

1. Entrar no perfil do passageiro.
2. Copiar uma avaliação interessante.
3. Colar no Rota Cheia.
4. Reformular o texto.
5. Copiar a avaliação pronta para usar.

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

## Fluxo atual

1. **Mensagens e avaliações BlaBlaCar**: reformulador de avaliações e textos rápidos.
2. **Planejar viagem**: origem, destino, conta, assentos, antecedência e eventos.
3. **Escolher melhor data e horário**: ranking operacional com score.
4. **SCAN BLA**: validação pública obrigatória por rota + data.
5. **Decisão final**: ação, conta, origem, destino final, intermediárias, data, horário, preço sugerido, risco de conflito e status de validação.
6. **Histórico e agenda**: scans salvos e agenda operacional padrão.
7. **Fallback**: upload `.mhtml/.mht` quando a leitura pública automática falhar.

## Decisões operacionais

- Se Ezequiel S ou Barbosa já aparecer publicado naquela data/rota, o app não deve criar duplicado.
- Se já estiver publicado, a decisão deve tender para **MANTER**, **ALTERAR HORÁRIO**, **ALTERAR PREÇO** ou **ALTERAR DESTINO FINAL**.
- Se houver conflito em Três Corações entre Ezequiel S e Barbosa, o app bloqueia a duplicidade logística e sugere alterar o destino final.
- Sem validação pública por data, a decisão fica bloqueada como não confirmada.

## Como rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```txt
rota-cheia/
├─ app.py
├─ requirements.txt
├─ components/
├─ database/
├─ scanner/
├─ rules/
├─ services/
├─ utils/
└─ data/
```
