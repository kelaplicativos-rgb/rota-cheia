from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "src" / "main" / "assets"


def replace_section(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise RuntimeError(f"Marcador inicial não encontrado: {label}")
    end_index = text.find(end, start_index)
    if end_index < 0:
        raise RuntimeError(f"Marcador final não encontrado: {label}")
    return text[:start_index] + replacement.rstrip() + "\n\n" + text[end_index:]


part2_path = ASSETS / "rotaai-part2.js"
part2 = part2_path.read_text(encoding="utf-8")

derived_profiles = r'''  const derivedProfileUrls = (passenger) => {
    const participantId = ratingParticipantIdFromUrl(passenger.reviewUrl || location.href);
    if (!participantId) return [];
    const origin = location.origin;
    return unique([
      `${origin}/user/show/${participantId}/reviews`,
      `${origin}/user/show/${participantId}`,
      `${origin}/member/profile/${participantId}`,
      `${origin}/members/${participantId}`,
      `${origin}/user/${participantId}`,
      `${origin}/users/${participantId}`,
      `${origin}/profile/${participantId}`
    ]);
  };'''

part2 = replace_section(
    part2,
    "  const derivedProfileUrls = (passenger) => {",
    "  const profileDocumentMatchesPassenger =",
    derived_profiles,
    "derivedProfileUrls",
)
part2_path.write_text(part2, encoding="utf-8")


part4_path = ASSETS / "rotaai-part4.js"
part4 = part4_path.read_text(encoding="utf-8")

rating_navigation = r'''  const ratingFlowKey = (value = location.href) => {
    try {
      const match = new URL(value, location.href).pathname.match(/^\/ratings\/([^/]+)\/([^/?#]+)/i);
      return match ? `${match[1]}::${match[2]}` : '';
    } catch { return ''; }
  };

  const isSameRatingFlow = (left, right) => {
    const leftKey = ratingFlowKey(left);
    const rightKey = ratingFlowKey(right);
    return Boolean(leftKey && rightKey && leftKey === rightKey);
  };

  const navigateToPassengerTrip = (passenger) => {
    const target = passenger.reviewUrl || passenger.offerUrl;
    if (!target) return false;
    if (isSameRatingFlow(location.href, target)) {
      window.RotaAiDebug?.log?.('navigation', 'same_rating_flow_kept', {
        passenger: passenger.name,
        flowKey: ratingFlowKey(target),
        currentPath: location.pathname
      });
      return false;
    }
    if (absoluteUrl(location.href) === absoluteUrl(target)) return false;
    location.href = target;
    return true;
  };'''

part4 = replace_section(
    part4,
    "  const navigateToPassengerTrip = (passenger) => {",
    "  const processPublication =",
    rating_navigation,
    "navigateToPassengerTrip/ratingFlowKey",
)
part4_path.write_text(part4, encoding="utf-8")


part3_path = ASSETS / "rotaai-part3.js"
part3 = part3_path.read_text(encoding="utf-8")

review_flow = r'''  let reviewFlowRetryTimer = globalThis.__rotaAiReviewFlowRetryTimer || null;

  const scheduleReviewFlowRetry = (passenger, message) => {
    clearTimeout(reviewFlowRetryTimer);
    if (!state.review.active || window.RotaAiDebug?.isStopped?.()) return;
    state.review.lastActionAt = now();
    state.status = message;
    notifyNative(state.status); saveState(); render();
    reviewFlowRetryTimer = setTimeout(() => {
      if (!state.review.active || window.RotaAiDebug?.isStopped?.()) return;
      if (currentReviewPassenger()?.key !== passenger.key) return;
      processReviewFlow(true);
    }, 850);
    globalThis.__rotaAiReviewFlowRetryTimer = reviewFlowRetryTimer;
  };

  const processReviewFlow = async (force = false) => {
    if (!state.review.active || window.RotaAiDebug?.isStopped?.()) return;
    if (!force && now() - state.review.lastActionAt < 700) return;
    const passenger = currentReviewPassenger();
    if (!passenger) return finishReviewFlow();
    state.review.currentKey = passenger.key;

    if (hasBlockingPage()) return pauseReviewFlow('A BlaBlaCar solicitou uma verificação manual.');

    const targetUrl = passenger.reviewUrl || passenger.offerUrl;
    const insideTargetFlow = Boolean(targetUrl && isSameRatingFlow(location.href, targetUrl));
    let field = findReviewField();

    if (!passenger.suggestion?.trim() && (field || passenger.profileUrl || insideTargetFlow)) {
      state.review.stage = 'reading-profile';
      state.status = `Lendo avaliações existentes de ${passenger.name}...`;
      notifyNative(state.status); saveState(); render();
      await preparePassengerFromCurrentPage(passenger);
      saveState(); render();
      field = findReviewField();
    }

    if (field) {
      if (!passenger.suggestion?.trim()) {
        const prepared = await preparePassengerFromCurrentPage(passenger);
        if (!prepared || !passenger.suggestion?.trim()) {
          return pauseReviewFlow(`Não encontrei uma avaliação existente no perfil de ${passenger.name} para usar como base.`);
        }
      }
      if (state.review.filledKey !== passenger.key) {
        nativeSetValue(field, passenger.suggestion);
        clickRating(Number(passenger.rating));
        state.review.filledKey = passenger.key;
      }
      state.review.attempts = 0;
      state.review.stage = 'awaiting-user';
      state.review.lastActionAt = now();
      state.status = `Confira ${passenger.name}. Edite se quiser e toque em “Aprovar e próxima”.`;
      notifyNative(state.status); saveState(); render();
      return;
    }

    if (!passenger.suggestion?.trim()) {
      const currentLinks = collectProfileLinks(document, location.href);
      const profile = bestProfileForPassenger(passenger, currentLinks);
      if (profile) {
        passenger.profileUrl = profile;
        const prepared = await analyzePassenger(passenger);
        saveState(); render();
        if (prepared) {
          state.review.lastActionAt = 0;
          return processReviewFlow(true);
        }
      }
    }

    if (insideTargetFlow) {
      if (!passenger.profileUrl) passenger.profileUrl = derivedProfileUrls(passenger)[0] || '';
      if (!passenger.suggestion?.trim() && passenger.profileUrl) {
        await analyzePassenger(passenger);
        saveState(); render();
      }

      field = findReviewField();
      if (field) {
        state.review.lastActionAt = 0;
        return processReviewFlow(true);
      }

      const ratingSelected = clickRating(Number(passenger.rating));
      const advance = findClickableByText([
        /^continuar$/i,
        /^pr[oó]ximo$/i,
        /^avan[cç]ar$/i,
        /^come[cç]ar$/i,
        /^iniciar$/i,
        /^escrever (uma )?avalia[cç][aã]o$/i,
        /^dar sua opini[aã]o$/i,
        /^continue$/i,
        /^next$/i
      ]);
      if (advance && !advance.disabled && advance.getAttribute('aria-disabled') !== 'true') {
        state.review.attempts = 0;
        state.review.lastActionAt = now();
        state.review.stage = ratingSelected ? 'rating-next' : 'intro-next';
        state.status = ratingSelected
          ? `Nota de ${passenger.name} selecionada. Avançando...`
          : `Avançando na avaliação de ${passenger.name}...`;
        notifyNative(state.status); saveState(); render();
        advance.click();
        return;
      }

      state.review.attempts += 1;
      window.RotaAiDebug?.log?.('automation', 'rating_flow_wait', {
        passenger: passenger.name,
        flowKey: ratingFlowKey(targetUrl),
        path: location.pathname,
        attempts: state.review.attempts,
        ratingSelected
      });
      if (state.review.attempts >= 18) {
        return pauseReviewFlow(`A etapa de avaliação de ${passenger.name} não carregou. O RotaAi interrompeu sem recarregar a página.`);
      }
      return scheduleReviewFlowRetry(
        passenger,
        `Aguardando a etapa de avaliação de ${passenger.name} carregar... (${state.review.attempts}/18)`
      );
    }

    const passengerAction = findPassengerAction(passenger);
    if (passengerAction) {
      state.review.attempts = 0;
      state.review.lastActionAt = now();
      state.review.stage = 'opening-review';
      state.status = `Abrindo o campo de ${passenger.name}...`;
      notifyNative(state.status); saveState(); render();
      passengerAction.click();
      return;
    }

    const generalAction = findClickableByText([/fazer avalia/i, /avaliar passageiro/i, /deixar avalia/i, /^avaliar$/i, /fa[cç]a uma avalia/i]);
    if (generalAction) {
      state.review.attempts = 0;
      state.review.lastActionAt = now();
      state.review.stage = 'opening-general';
      state.status = 'Abrindo as avaliações pendentes...';
      notifyNative(state.status); saveState(); render();
      generalAction.click();
      return;
    }

    if (targetUrl && absoluteUrl(location.href) !== absoluteUrl(targetUrl)) {
      state.review.lastActionAt = now();
      state.review.stage = 'navigate-trip';
      state.status = `Abrindo a avaliação de ${passenger.name}...`;
      notifyNative(state.status); saveState(); render();
      if (navigateToPassengerTrip(passenger)) return;
    }

    state.review.attempts += 1;
    state.review.lastActionAt = now();
    saveState();
    if (state.review.attempts >= 10) {
      pauseReviewFlow(`A tela de ${passenger.name} não foi reconhecida. Abra o convite dessa pessoa e toque em “Retomar”.`);
    }
  };'''

part3 = replace_section(
    part3,
    "  const processReviewFlow = async (force = false) => {",
    "  const approveAll =",
    review_flow,
    "processReviewFlow same-rating-flow-v3",
)
part3_path.write_text(part3, encoding="utf-8")

print("patch_rating_flow: ok")
