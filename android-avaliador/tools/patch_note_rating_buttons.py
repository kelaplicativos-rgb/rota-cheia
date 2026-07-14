from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "src" / "main" / "assets"

part3_path = ASSETS / "rotaai-part3.js"
part3 = part3_path.read_text(encoding="utf-8")

retry_marker = "  let reviewFlowRetryTimer = globalThis.__rotaAiReviewFlowRetryTimer || null;"
helper = r'''  const clickRatingChoice = (rating) => {
    const numericRating = Number(rating);
    const clickKey = `${location.pathname}::${numericRating}`;
    const previousClick = globalThis.__rotaAiRatingChoiceClick || { key: '', at: 0 };
    if (previousClick.key === clickKey && now() - previousClick.at < 1800) {
      window.RotaAiDebug?.log?.('selector', 'semantic_rating_click_locked', {
        rating: numericRating,
        path: location.pathname,
        elapsedMs: now() - previousClick.at
      });
      return true;
    }

    const patternsByRating = {
      5: [/^excelente$/i, /^otim[oa]$/i, /^muito bom$/i, /^muito boa$/i],
      4: [/^bom$/i, /^boa$/i],
      3: [/^regular$/i, /^razoavel$/i],
      2: [/^ruim$/i],
      1: [/^pessim[oa]$/i, /^muito ruim$/i, /^muito ruim mesmo$/i]
    };
    const patterns = patternsByRating[numericRating] || patternsByRating[5];
    const semanticButton = clickableElements().find((element) => {
      const label = normalize(`${safeText(element)} ${element.getAttribute('aria-label') || ''}`);
      return patterns.some((pattern) => pattern.test(label));
    });
    if (semanticButton) {
      globalThis.__rotaAiRatingChoiceClick = { key: clickKey, at: now() };
      window.RotaAiDebug?.log?.('selector', 'semantic_rating_button', {
        rating: numericRating,
        text: safeText(semanticButton),
        path: location.pathname
      });
      semanticButton.click();
      return true;
    }
    return clickRating(numericRating);
  };

'''

if retry_marker not in part3:
    raise RuntimeError("O patch principal do fluxo de avaliação ainda não foi aplicado")
if "  const clickRatingChoice = (rating) => {" not in part3:
    part3 = part3.replace(retry_marker, helper + retry_marker, 1)

old_review_rating = "      const ratingSelected = clickRating(Number(passenger.rating));\n      const advance = findClickableByText(["
new_review_rating = "      const ratingSelected = clickRatingChoice(Number(passenger.rating));\n      const advance = findClickableByText(["
if old_review_rating not in part3:
    raise RuntimeError("Trecho de seleção de nota da revisão não encontrado")
part3 = part3.replace(old_review_rating, new_review_rating, 1)
part3_path.write_text(part3, encoding="utf-8")

part4_path = ASSETS / "rotaai-part4.js"
part4 = part4_path.read_text(encoding="utf-8")

field_rating = "      clickRating(Number(passenger.rating));"
if field_rating not in part4:
    raise RuntimeError("Seleção de nota do formulário de publicação não encontrada")
part4 = part4.replace(field_rating, "      clickRatingChoice(Number(passenger.rating));", 1)

old_publish_rating = "    const ratingOnly = clickRating(Number(passenger.rating));\n    if (ratingOnly) {"
new_publish_rating = "    const ratingOnly = clickRatingChoice(Number(passenger.rating));\n    if (ratingOnly) {"
if old_publish_rating not in part4:
    raise RuntimeError("Seleção de nota da publicação não encontrada")
part4 = part4.replace(old_publish_rating, new_publish_rating, 1)
part4_path.write_text(part4, encoding="utf-8")

print("patch_note_rating_buttons: ok")
