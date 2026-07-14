from pathlib import Path

path = Path(__file__).resolve().parents[1] / "app" / "src" / "main" / "java" / "br" / "com" / "rotaai" / "avaliador" / "MainActivity.java"
text = path.read_text(encoding="utf-8")
replacements = {
    'appendNativeLog("lifecycle", "activity_create", "version=0.5.0");':
        'appendNativeLog("lifecycle", "activity_create", "version=" + BuildConfig.VERSION_NAME);',
    'title.setText("RotaAi 0.5");':
        'title.setText("RotaAi " + BuildConfig.VERSION_NAME);',
    'settings.setUserAgentString(settings.getUserAgentString() + " RotaAiAvaliador/0.5.0");':
        'settings.setUserAgentString(settings.getUserAgentString() + " RotaAiAvaliador/" + BuildConfig.VERSION_NAME);',
    '+ "Versão: 0.5.0\\n"':
        '+ "Versão: " + BuildConfig.VERSION_NAME + "\\n"',
}
for old, new in replacements.items():
    if old not in text:
        raise RuntimeError(f"Trecho de versão não encontrado: {old}")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patch_native_version: ok")
