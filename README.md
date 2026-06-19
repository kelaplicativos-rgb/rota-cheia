# Rota Cheia

App assistente de caronas para planejar, validar e organizar viagens no corredor Sao Paulo/Santo Andre ↔ Minas Gerais.

## Objetivo

O Rota Cheia ajuda a lotar o carro com antecedencia analisando buscas publicas da BlaBlaCar, arquivos `.mhtml/.mht`, motoristas, horarios, precos, lotacao e possiveis conflitos entre as contas **Ezequiel S** e **Barbosa**.

## Primeiro modulo

O app deve começar por **Mensagens e avaliacoes BlaBlaCar**, porque este e o recurso mais rapido, mais usado e com maior chance de engajar o usuario logo na entrada.

Fluxo do modulo:

1. Entrar no perfil do passageiro.
2. Copiar uma avaliacao interessante.
3. Colar no Rota Cheia.
4. Reformular o texto.
5. Copiar a avaliacao pronta para usar.

## Corredor operacional

- Sao Paulo/SP ou Santo Andre/SP ↔ Extrema/MG
- Sao Paulo/SP ou Santo Andre/SP ↔ Pouso Alegre/MG
- Sao Paulo/SP ou Santo Andre/SP ↔ Tres Coracoes/MG
- Sao Paulo/SP ou Santo Andre/SP ↔ Varginha/MG
- Sao Paulo/SP ou Santo Andre/SP ↔ Sao Tome das Letras/MG
- Cambuquira/MG e Campanha/MG podem ser consideradas como intermediarias quando ajudarem a completar o carro.
- Caxambu deve ser ignorada.

## Regra obrigatoria

Antes de recomendar **CRIAR**, **PUBLICAR**, **MANTER**, **ALTERAR** ou **EXCLUIR**, o app precisa validar a busca publica da BlaBlaCar por **rota + data exata**.

Se a busca publica por data nao estiver validada, a saida deve ser:

```txt
nao confirmado / busca publica por data nao validada
```

## Identificadores validos

Usar apenas:

- Ezequiel S
- Barbosa

Nunca usar como identificador:

- 4.9
- Super Driver
- Embaixador
- Expert
- qualquer nivel ou status da plataforma

## Fluxo atual

1. **Mensagens e avaliacoes BlaBlaCar**: reformulador de avaliacoes e textos rapidos.
2. **Planejar viagem**: origem, destino, conta, assentos, antecedencia e eventos.
3. **Escolher melhor data e horario**: ranking operacional com score.
4. **SCAN BLA**: validacao publica obrigatoria por rota + data.
5. **Decisao final**: acao, conta, origem, destino final, intermediarias, data, horario, preco sugerido, risco de conflito e status de validacao.
6. **Historico e agenda**: scans salvos e agenda operacional padrao.
7. **Fallback**: upload `.mhtml/.mht` quando a leitura publica automatica falhar.

## Decisoes operacionais

- Se Ezequiel S ou Barbosa ja aparecer publicado naquela data/rota, o app nao deve criar duplicado.
- Se ja estiver publicado, a decisao deve tender para **MANTER**, **ALTERAR HORARIO**, **ALTERAR PRECO** ou **ALTERAR DESTINO FINAL**.
- Se houver conflito em Tres Coracoes entre Ezequiel S e Barbosa, o app bloqueia a duplicidade logistica e sugere alterar o destino final.
- Sem validacao publica por data, a decisao fica bloqueada como nao confirmada.

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
