# RotaAi Avaliações — Android

Aplicativo Android com navegador interno para preparar, revisar e publicar avaliações de passageiros na BlaBlaCar.

## Fluxo rápido

1. Fazer login na página oficial da BlaBlaCar.
2. Tocar no botão nativo **Revisar pendentes**.
3. O app abre a área de viagens ou o resumo necessário, identifica somente os convites individuais ainda pendentes e abre a primeira pessoa.
4. Dentro do formulário real, identifica o perfil correspondente, lê avaliações existentes e gera um texto curto e casual sem inventar qualidades.
5. O campo é preenchido automaticamente. O usuário confere ou edita e toca em **Aprovar / próxima**.
6. Depois da última pessoa, tocar em **Publicar**. Somente as avaliações aprovadas são enviadas.

## Controles nativos

- **Revisar pendentes**: inicia todo o processo com um toque.
- **Aprovar / próxima**: guarda o texto e a nota conferidos e avança.
- **Publicar**: envia em sequência apenas o que foi aprovado.

O status da automação aparece acima do navegador, sem depender do painel sobreposto ao site.

## Travas

- Não inclui passageiros mostrados apenas na lista geral da viagem.
- Não inclui quem já aparece como avaliado, avaliação enviada ou publicada.
- Não associa perfis por ordem quando há várias pessoas; exige nome correspondente ou um caso único inequívoco.
- Não gera texto sem encontrar uma avaliação textual e qualidades claras no perfil.
- Não publica durante a revisão individual.
- Só publica avaliações aprovadas pelo usuário.
- Só marca como publicada depois de detectar a confirmação da página.
- Interrompe diante de captcha, erro ou página inesperada.
- Não tenta contornar proteção da plataforma.
- A ponte nativa recebe somente mensagens de status; não expõe senha, cookies ou conteúdo de login.
- Não solicita contatos, localização ou arquivos do aparelho.

## Compilar

Requisitos: Java 17, Android SDK 35 e Gradle 8.9.

```bash
cd android-avaliador
gradle :app:assembleDebug
```

O APK será criado em:

```text
app/build/outputs/apk/debug/app-debug.apk
```