# RotaAi Avaliações — Android

Aplicativo Android com navegador interno para preparar e publicar avaliações de passageiros na BlaBlaCar.

## Fluxo

1. Fazer login na página oficial da BlaBlaCar.
2. Abrir **Minhas viagens**.
3. Escanear viagens que ainda permitem avaliação.
4. Buscar os perfis e ler somente avaliações visíveis.
5. Gerar textos curtos sem inventar qualidades.
6. Revisar texto e estrelas de cada passageiro.
7. Aprovar os itens desejados.
8. Tocar em **Publicar todas** para enviar, um por vez.

## Travas

- Não inicia publicação sem confirmação explícita.
- Não envia itens sem aprovação individual.
- Registra estados pendente, aprovado e publicado.
- Só marca como publicado após detectar confirmação da página.
- Interrompe a fila diante de captcha, erro ou página inesperada.
- Não tenta contornar captcha ou proteção da plataforma.
- Não usa ponte JavaScript nativa para expor senha ou cookies ao código injetado.
- Não solicita contatos, localização ou acesso aos arquivos do aparelho.

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
