  const finishReviewFlow = () => {
    const total = state.review.queue.length;
    const approved = state.review.queue.filter((key) => state.passengers.find((p) => p.key === key)?.approved).length;
    state.review.active = false;
    state.review.paused = false;
    state.review.autoStart = false;
    state.review.stage = 'done';
    state.status = `Revisão concluída: ${approved} de ${total} aprovada(s). Agora toque em “Publicar”.`;
    notifyNative(state.status); saveState(); render();
  };

  const pauseReviewFlow = (reason) => {
    state.review.active = false;
    state.review.paused = true;
    state.review.stage = 'paused';
    state.status = `Revisão pausada: ${reason}`;
    notifyNative(state.status); saveState(); render();
  };

  const startReviewFlow = () => startSmartReview();

  const resumeReviewFlow = () => {
    if (!state.review.paused || !state.review.queue.length) return;
    state.review.active = true;
    state.review.paused = false;
    state.review.stage = 'resuming';
    state.review.lastActionAt = 0;
    state.status = 'Retomando a revisão.';
    notifyNative(state.status); saveState(); render(); processReviewFlow(true);
  };

  const moveReviewNext = (approved) => {
    const passenger = currentReviewPassenger();
    if (!passenger) return finishReviewFlow();
    const field = findReviewField();
    const edited = field ? (field.value ?? field.textContent ?? '').toString().trim() : '';
    if (approved && edited) passenger.suggestion = edited;
    const rating = selectedRating();
    if (rating) passenger.rating = rating;
    passenger.approved = Boolean(approved && passenger.suggestion?.trim());
    passenger.status = passenger.approved ? 'aprovado' : 'pronto';
    state.review.index += 1;
    state.review.currentKey = state.review.queue[state.review.index] || '';
    state.review.stage = 'next';
    state.review.filledKey = '';
    state.review.lastActionAt = 0;
    state.review.attempts = 0;
    saveState(); render();
    const next = currentReviewPassenger();
    if (!next) return finishReviewFlow();
    state.status = `Abrindo avaliação de ${next.name}...`;
    notifyNative(state.status); saveState(); render();
    if (!navigateToPassengerTrip(next)) processReviewFlow(true);
  };

  const processReviewFlow = async (force = false) => {
    if (!state.review.active) return;
    if (!force && now() - state.review.lastActionAt < 700) return;
    const passenger = currentReviewPassenger();
    if (!passenger) return finishReviewFlow();
    state.review.currentKey = passenger.key;

    if (hasBlockingPage()) return pauseReviewFlow('A BlaBlaCar solicitou uma verificação manual.');

    let field = findReviewField();
    if (!passenger.suggestion?.trim() && (field || passenger.profileUrl)) {
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

    const passengerAction = findPassengerAction(passenger);
    if (passengerAction) {
      state.review.lastActionAt = now();
      state.review.stage = 'opening-review';
      state.status = `Abrindo o campo de ${passenger.name}...`;
      notifyNative(state.status); saveState(); render();
      passengerAction.click();
      return;
    }

    const generalAction = findClickableByText([/fazer avalia/i, /avaliar passageiro/i, /deixar avalia/i, /^avaliar$/i, /fa[cç]a uma avalia/i]);
    if (generalAction) {
      state.review.lastActionAt = now();
      state.review.stage = 'opening-general';
      state.status = `Abrindo as avaliações pendentes...`;
      notifyNative(state.status); saveState(); render();
      generalAction.click();
      return;
    }

    const targetUrl = passenger.reviewUrl || passenger.offerUrl;
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
  };

  const approveAll = () => {
    let count = 0;
    for (const passenger of state.passengers) {
      if (!passenger.published && passenger.suggestion?.trim() && passenger.status === 'pronto') {
        passenger.approved = true;
        if (!(passenger.rating >= 1 && passenger.rating <= 5)) passenger.rating = 5;
        count += 1;
      }
    }
    state.status = `${count} avaliações aprovadas para publicação.`;
    notifyNative(state.status); saveState(); render();
  };

  const resetPublication = () => {
    state.publish = initialState().publish;
    saveState(); render();
  };

  const startPublish = () => {
    if (state.publish.active || state.review.active) return;
    const queue = state.passengers.filter((p) => p.approved && !p.published && p.suggestion?.trim()
      && Number(p.rating) >= 1 && Number(p.rating) <= 5).map((p) => p.key);
    if (!queue.length) return setStatus('Revise e aprove pelo menos uma avaliação antes de publicar.');
    const names = queue.map((key) => state.passengers.find((p) => p.key === key)?.name).filter(Boolean);
    const confirmed = confirm(`Publicar ${queue.length} avaliação(ões) agora?\n\n${names.join(', ')}\n\nA fila para se houver erro ou verificação.`);
    if (!confirmed) return;
    state.panelOpen = true;
    state.publish = {
      ...initialState().publish,
      active: true,
      queue,
      index: 0,
      stage: 'starting',
      currentKey: queue[0],
      lastActionAt: 0,
      attempts: 0,
      completed: [],
      failures: []
    };
    state.status = `Publicação iniciada: 0 de ${queue.length}.`;
    notifyNative(state.status); saveState(); render(); processPublication(true);
  };

  const pausePublication = (reason) => {
    state.publish.active = false;
    state.publish.paused = true;
    state.publish.stage = 'paused';
    const current = currentPublishingPassenger();
    if (current && !state.publish.failures.some((f) => f.key === current.key)) {
      state.publish.failures.push({ key: current.key, name: current.name, reason, url: location.href });
    }
    state.status = `Publicação pausada: ${reason}`;
    notifyNative(state.status); saveState(); render();
  };

  const resumePublication = () => {
    if (!state.publish.paused || !state.publish.queue.length) return;
    state.publish.active = true;
    state.publish.paused = false;
    state.publish.stage = 'resuming';
    state.publish.lastActionAt = 0;
    state.status = 'Retomando a publicação.';
    notifyNative(state.status); saveState(); render(); processPublication(true);
  };

  const currentPublishingPassenger = () => {
    const key = state.publish.queue[state.publish.index];
    return state.passengers.find((p) => p.key === key) || null;
  };

  const markCurrentPublished = () => {
    const passenger = currentPublishingPassenger();
    if (!passenger) return;
    passenger.published = true;
    passenger.publishedAt = new Date().toISOString();
    passenger.status = 'publicado';
    passenger.approved = false;
    if (!state.publish.completed.includes(passenger.key)) state.publish.completed.push(passenger.key);
    state.publish.index += 1;
    state.publish.currentKey = state.publish.queue[state.publish.index] || '';
    state.publish.stage = 'next';
    state.publish.lastActionAt = 0;
    state.publish.attempts = 0;
    saveState(); render();
  };

  const finishPublication = () => {
    const total = state.publish.queue.length;
    const completed = state.publish.completed.length;
    state.publish.active = false;
    state.publish.paused = false;
    state.publish.stage = 'done';
    state.status = `Concluído: ${completed} de ${total} avaliações publicadas.`;
    notifyNative(state.status); saveState(); render();
  };

  const pageText = () => (document.body?.innerText || '').replace(/\s+/g, ' ').trim();
  const hasSuccessMessage = () => SUCCESS_PATTERNS.some((pattern) => pattern.test(pageText()));
  const hasBlockingPage = () => BLOCK_PATTERNS.some((pattern) => pattern.test(pageText()));

  const isSiteElement = (el) => Boolean(el) && !el.closest(`#${ROOT_ID}`);
  const findVisible = (selector) => [...document.querySelectorAll(selector)].find((el) => visible(el) && isSiteElement(el)) || null;
  const clickableElements = () => [...document.querySelectorAll('button, a[href], [role="button"], label')].filter((el) => visible(el) && isSiteElement(el));
  const findClickableByText = (patterns, root = document) => {
    const elements = [...root.querySelectorAll('button, a[href], [role="button"], label')].filter((el) => visible(el) && isSiteElement(el));
    return elements.find((el) => patterns.some((pattern) => pattern.test(safeText(el)) || pattern.test(el.getAttribute('aria-label') || ''))) || null;
  };

  const nativeSetValue = (element, value) => {
    if (element instanceof HTMLInputElement) {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set?.call(element, value);
    } else if (element instanceof HTMLTextAreaElement) {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set?.call(element, value);
    } else if (element.isContentEditable) {
      element.focus();
      element.textContent = value;
    }
    element.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    element.dispatchEvent(new Event('blur', { bubbles: true }));
  };

  const findReviewField = () => {
    const fields = [...document.querySelectorAll('textarea, [contenteditable="true"], input[type="text"]')].filter((el) => visible(el) && isSiteElement(el));
    if (!fields.length) return null;
    const scored = fields.map((el) => {
      const hint = `${el.getAttribute('placeholder') || ''} ${el.getAttribute('aria-label') || ''} ${el.name || ''} ${el.id || ''}`;
      let score = 0;
      if (/avalia|opini|coment|experi|viagem|mensagem/i.test(hint)) score += 6;
      if (el.tagName === 'TEXTAREA') score += 4;
      if ((el.maxLength || 0) > 40) score += 1;
      if (/pesquisa|buscar|origem|destino|email|senha/i.test(hint)) score -= 20;
      return { el, score };
    }).sort((a, b) => b.score - a.score);
    return scored[0]?.score > 0 ? scored[0].el : null;
  };

  const clickRating = (rating) => {
    const exactSelectors = [
      `input[type="radio"][value="${rating}"]`,
      `[data-testid*="rating-${rating}" i]`, `[data-testid*="star-${rating}" i]`,
      `[aria-label^="${rating} estrela" i]`, `[aria-label*="${rating} de 5" i]`
    ];
    for (const selector of exactSelectors) {
      const target = findVisible(selector);
      if (target) {
        const clickable = target.matches('input') && target.id ? (document.querySelector(`label[for="${CSS.escape(target.id)}"]`) || target) : target;
        clickable.click();
        if (target instanceof HTMLInputElement) {
          target.checked = true;
          target.dispatchEvent(new Event('change', { bubbles: true }));
        }
        return true;
      }
    }
    const stars = clickableElements().filter((el) => /estrela|star/i.test(`${safeText(el)} ${el.getAttribute('aria-label') || ''}`));
    if (stars.length >= 5) {
      const ordered = stars.slice(0, 5);
      ordered[Math.max(0, Math.min(4, rating - 1))].click();