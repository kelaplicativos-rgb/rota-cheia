from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "src" / "main" / "assets"

part3_path = ASSETS / "rotaai-part3.js"
part3 = part3_path.read_text(encoding="utf-8")

retry_marker = "  let reviewFlowRetryTimer = globalThis.__rotaAiReviewFlowRetryTimer || null;"
helper = r'''  const clickRatingChoice = (rating) => {
    const patternsByRating = {
      5: [/^excelente$/i, /^otim[oa]$/i, /^muito bom$/i, /^muito boa$/i],
      4: [/^bom$/i, /^boa$/i],
      3: [/^regular$/i, /^razoavel$/i],
      2: [/^ruim$/i],
      1: [/^pessim[oa]$/i, /^muito ruim$/i, /^muito ruim mesmo$/i]
    };
    const patterns = patternsByRating[Number(rating)] || patternsByRating[5];
    const semanticButton = clickableElements().find((element) => {
      const label = normalize(`${safeText(element)} ${element.getAttribute('aria-label') || ''}`);
      return patterns.some((pattern) => pattern.test(label));
    });
    if (semanticButton) {
      window.RotaAiDebug?.log?.('selector', 'semantic_rating_button', {
        rating: Number(rating),
        text: safeText(semanticButton),
        path: location.pathname
      });
      semanticButton.click();
      return true;
    }
    return clickRating(Number(rating));
  };

'''

if retry_marker not in part3:
    raise RuntimeError("O patch principal do fluxo de avaliação ainda não foi aplicado")
if "  const clickRatingChoice = (rating) => {" not in part3:
    part3 = part3.replace(retry_marker, helper + retry_marker, 1)

old_review_rating = "      const ratingSelected = clickRating(Number(passenger.rating));\n      const advance = findClickableByText(["
new_review_rating = "      const ratingPathBefore = location.pathname;\n      const ratingSelected = clickRatingChoice(Number(passenger.rating));\n      if (ratingSelected && location.pathname !== ratingPathBefore) {\n        state.review.attempts = 0;\n        state.review.stage = 'rating-selected';\n        return scheduleReviewFlowRetry(passenger, `Nota de ${passenger.name} selecionada. Abrindo o comentário...`);\n      }\n      const advance = findClickableByText(["
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
new_publish_rating = "    const ratingPathBefore = location.pathname;\n    const ratingOnly = clickRatingChoice(Number(passenger.rating));\n    if (ratingOnly && location.pathname !== ratingPathBefore) {\n      state.publish.attempts = 0;\n      state.publish.lastActionAt = 0;\n      state.publish.stage = 'rating-selected';\n      state.status = `Nota de ${passenger.name} selecionada. Abrindo o comentário...`;\n      notifyNative(state.status); saveState(); render();\n      setTimeout(() => {\n        if (state.publish.active && currentPublishingPassenger()?.key === passenger.key) processPublication(true);\n      }, 650);\n      return;\n    }\n    if (ratingOnly) {"
if old_publish_rating not in part4:
    raise RuntimeError("Seleção de nota da publicação não encontrada")
part4 = part4.replace(old_publish_rating, new_publish_rating, 1)
part4_path.write_text(part4, encoding="utf-8")

print("patch_note_rating_buttons: ok")
