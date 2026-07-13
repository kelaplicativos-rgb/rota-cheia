# RotaAi Avaliações — Android

Aplicativo Android com navegador interno para preparar, revisar e publicar avaliações de passageiros na BlaBlaCar.

## Fluxo correto

1. Fazer login na página oficial da BlaBlaCar.
2. Abrir **Minhas viagens**.
3. Tocar em **Preparar pendentes**.
4. O app inclui somente os blocos individuais com **“Faça uma avaliação! Avalie sua experiência de viagem com [nome]”**.
5. Para cada pessoa pendente, tenta abrir o convite individual, identificar o perfil correto e ler avaliações já existentes.
6. Gera uma avaliação curta e casual, preservando apenas as qualidades encontradas na base.
7. Tocar em **Revisar uma por uma**. O app abre o formulário de cada pessoa e preenche o texto sem publicar.
8. Conferir ou editar o texto e a nota; depois tocar em **Aprovar e próxima**.
9. Ao terminar, tocar em **Publicar aprovadas** para enviar uma por vez.

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
- Não usa ponte JavaScript nativa para expor senha ou cookies.
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
