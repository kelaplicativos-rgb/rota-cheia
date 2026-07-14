      return true;
    }
    return false;
  };

  const findPassengerAction = (passenger) => {
    const normalizedName = normalize(passenger.name);
    const first = normalizedName.split(' ')[0];
    const candidates = clickableElements().map((el) => {
      const text = normalize(`${safeText(el)} ${el.getAttribute('aria-label') || ''}`);
      const parentText = normalize(safeText(el.closest('article, li, section, div')));
      const combined = `${text} ${parentText}`;
      const reviewContext = /avaliar|fazer avaliacao|deixar avaliacao|avalie sua experiencia|faca uma avaliacao/.test(combined);
      let score = reviewContext ? 8 : -20;
      if (text.includes(normalizedName)) score += 12;
      else if (first && text.includes(first)) score += 6;
      if (parentText.includes(normalizedName)) score += 5;
      else if (first && parentText.includes(first)) score += 2;
      if (/excluir|cancelar|denunciar/.test(text)) score -= 30;
      return { el, score };
    }).filter((item) => item.score > 0).sort((a, b) => b.score - a.score);
    return candidates[0]?.el || null;
  };

  const navigateToPassengerTrip = (passenger) => {
    const target = passenger.reviewUrl || passenger.offerUrl;
    if (!target) return false;
    if (absoluteUrl(location.href) === absoluteUrl(target)) return false;
    location.href = target;
    return true;
  };

  const processPublication = async (force = false) => {
    if (!state.publish.active) return;
    if (!force && now() - state.publish.lastActionAt < 800) return;
    const passenger = currentPublishingPassenger();
    if (!passenger) return finishPublication();
    state.publish.currentKey = passenger.key;

    if (hasBlockingPage()) return pausePublication('A BlaBlaCar solicitou uma verificação manual.');

    if (hasSuccessMessage()) {
      markCurrentPublished();
      const next = currentPublishingPassenger();
      if (!next) return finishPublication();
      state.status = `Publicado ${state.publish.completed.length}/${state.publish.queue.length}. Abrindo ${next.name}...`;
      notifyNative(state.status); saveState(); render();
      await sleep(500);
      if (!navigateToPassengerTrip(next)) processPublication(true);
      return;
    }

    const field = findReviewField();
    if (field) {
      state.publish.stage = 'form';
      const currentValue = (field.value ?? field.textContent ?? '').toString();
      if (currentValue.trim() !== passenger.suggestion.trim()) nativeSetValue(field, passenger.suggestion);
      clickRating(Number(passenger.rating));
      const submit = findClickableByText([/^publicar$/i, /^enviar$/i, /enviar avalia/i, /publicar avalia/i, /confirmar avalia/i, /salvar avalia/i]);
      if (submit && !submit.disabled && submit.getAttribute('aria-disabled') !== 'true') {
        state.publish.lastActionAt = now();
        state.publish.stage = 'submitted';
        state.status = `Publicando avaliação de ${passenger.name}...`;
        notifyNative(state.status); saveState(); render();
        submit.click();
        return;
      }
      const next = findClickableByText([/^continuar$/i, /^pr[oó]ximo$/i, /^avan[cç]ar$/i]);
      if (next && !next.disabled) {
        state.publish.lastActionAt = now();
        state.publish.stage = 'form-next';
        state.status = `Continuando a avaliação de ${passenger.name}...`;
        notifyNative(state.status); saveState(); render();
        next.click();
        return;
      }
      state.publish.lastActionAt = now();
      saveState();
      return;
    }

    const ratingOnly = clickRating(Number(passenger.rating));
    if (ratingOnly) {
      const next = findClickableByText([/^continuar$/i, /^pr[oó]ximo$/i, /^avan[cç]ar$/i, /escrever avalia/i]);
      if (next && !next.disabled) {
        state.publish.lastActionAt = now();
        state.publish.stage = 'rating-next';
        state.status = `Nota de ${passenger.name} selecionada.`;
        notifyNative(state.status); saveState(); render();
        next.click();
        return;
      }
    }

    const passengerAction = findPassengerAction(passenger);
    if (passengerAction) {
      state.publish.lastActionAt = now();
      state.publish.stage = 'opening-review';
      state.status = `Abrindo avaliação de ${passenger.name}...`;
      notifyNative(state.status); saveState(); render();
      passengerAction.click();
      return;
    }

    const generalAction = findClickableByText([/fazer avalia/i, /avaliar passageiro/i, /deixar avalia/i, /^avaliar$/i, /fa[cç]a uma avalia/i]);
    if (generalAction) {
      state.publish.lastActionAt = now();
      state.publish.stage = 'opening-general';
      state.status = 'Abrindo avaliações pendentes...';
      notifyNative(state.status); saveState(); render();
      generalAction.click();
      return;
    }

    if (navigateToPassengerTrip(passenger)) {
      state.publish.lastActionAt = now();
      state.publish.stage = 'navigate-trip';
      state.status = `Abrindo a viagem de ${passenger.name}...`;
      notifyNative(state.status); saveState(); render();
      return;
    }

    state.publish.attempts += 1;
    state.publish.lastActionAt = now();
    saveState();
    if (state.publish.attempts >= 10) {
      pausePublication(`A tela de ${passenger.name} não foi reconhecida.`);
    }
  };

  const clearQueue = () => {
    if (!confirm('Limpar a fila e recomeçar?')) return;
    localStorage.removeItem(STORAGE_KEY);
    state = initialState();
    notifyNative(state.status); render();
  };

  const statusLabel = (status) => ({
    pendente: 'Pendente', analisando: 'Lendo perfil', pronto: 'Pronto', aprovado: 'Aprovado', sem_perfil: 'Sem perfil',
    sem_base: 'Sem base', erro: 'Erro', publicado: 'Publicado'
  }[status] || status);

  const renderPassengerCard = (passenger, index) => {
    const route = [passenger.origin, passenger.destination].filter(Boolean).join(' → ');
    const disabled = passenger.published ? 'disabled' : '';
    return `<div class="rai-card ${passenger.published ? 'rai-published' : ''}" data-index="${index}">
      <div class="rai-row rai-between"><div><strong>${escapeHtml(passenger.name)}</strong>
      <div class="rai-meta">${escapeHtml([passenger.date, passenger.time, route].filter(Boolean).join(' · '))}</div></div>
      <span class="rai-badge">${escapeHtml(statusLabel(passenger.status))}</span></div>
      <textarea data-role="suggestion" ${disabled} placeholder="O texto será preenchido ao abrir a avaliação.">${escapeHtml(passenger.suggestion || '')}</textarea>
      <div class="rai-row rai-controls">
        <label>Nota <select data-role="rating" ${disabled}>${[5,4,3,2,1].map((n) => `<option value="${n}" ${passenger.rating === n ? 'selected' : ''}>${n} estrela${n > 1 ? 's' : ''}</option>`).join('')}</select></label>
        <label class="rai-approve"><input type="checkbox" data-role="approved" ${passenger.approved ? 'checked' : ''} ${disabled}> Aprovada</label>
      </div>
      ${passenger.reason ? `<div class="rai-note">${escapeHtml(passenger.reason)}</div>` : ''}
      ${passenger.reviews?.length ? `<details><summary>${passenger.reviews.length} avaliação(ões) usada(s) como base</summary><ol>${passenger.reviews.slice(0, 5).map((r) => `<li>${escapeHtml(r)}</li>`).join('')}</ol></details>` : ''}
    </div>`;
  };

  const addStyles = () => {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      #${ROOT_ID}{position:fixed;left:0;right:0;bottom:0;z-index:2147483646;font:14px/1.35 system-ui,-apple-system,sans-serif;color:#173333;pointer-events:none}
      #${ROOT_ID} *{box-sizing:border-box}#${ROOT_ID} .rai-shell{pointer-events:auto;background:#fff;border-radius:18px 18px 0 0;box-shadow:0 -6px 30px #0004;max-height:78vh;display:flex;flex-direction:column}
      #${ROOT_ID}.rai-closed .rai-body{display:none}#${ROOT_ID}.rai-closed .rai-shell{width:max-content;max-width:95vw;margin-left:auto;border-radius:16px 0 0 0}
      .rai-head{display:flex;align-items:center;gap:8px;padding:11px 14px;background:#006a6a;color:#fff;border-radius:18px 18px 0 0}.rai-head-title{font-weight:800;flex:1}.rai-head small{display:block;font-weight:400;opacity:.9}
      .rai-head button{background:#fff;color:#006a6a;border:0;border-radius:10px;padding:8px 10px;font-weight:800}.rai-body{overflow:auto;padding:10px}.rai-actions{display:grid;grid-template-columns:1fr 1fr;gap:7px}.rai-actions button{border:1px solid #006a6a;background:#fff;color:#006a6a;border-radius:11px;padding:11px 7px;font-weight:800}.rai-actions button.rai-primary{background:#006a6a;color:#fff}.rai-actions button.rai-danger{border-color:#a33;color:#a33}.rai-actions button:disabled{opacity:.4}
      .rai-status{margin:9px 0;padding:9px 10px;background:#e9f6f5;border-radius:10px}.rai-list{display:flex;flex-direction:column;gap:9px}.rai-card{border:1px solid #d7e4e4;border-radius:12px;padding:10px;background:#fff}.rai-published{background:#edf9ef}.rai-row{display:flex;align-items:center;gap:9px}.rai-between{justify-content:space-between}.rai-meta{font-size:11px;color:#5d7171;margin-top:2px}.rai-badge{font-size:11px;background:#e8eeee;border-radius:999px;padding:4px 7px;white-space:nowrap}.rai-card textarea{width:100%;min-height:72px;margin:8px 0 5px;border:1px solid #b8c9c9;border-radius:9px;padding:8px;font:inherit;resize:vertical}.rai-controls{justify-content:space-between;flex-wrap:wrap}.rai-controls select{padding:6px;border-radius:7px}.rai-approve{font-weight:700}.rai-note{font-size:12px;color:#8b3b20;margin-top:7px}details{font-size:12px;margin-top:7px}ol{padding-left:20px}.rai-empty{text-align:center;padding:16px;color:#687}
      @media(min-width:700px){#${ROOT_ID}{left:auto;width:430px}.rai-shell{border-radius:18px 0 0 0}.rai-head{border-radius:18px 0 0 0}}
    `;
    document.documentElement.appendChild(style);
  };

  const ensureRoot = () => {
    addStyles();
    let root = document.getElementById(ROOT_ID);
    if (!root) { root = document.createElement('aside'); root.id = ROOT_ID; document.documentElement.appendChild(root); }
    return root;
  };

  const bindEvents = (root) => {
    root.querySelector('[data-action="toggle"]')?.addEventListener('click', () => {
      state.panelOpen = !state.panelOpen; saveState(); render();
    });
    root.querySelector('[data-action="smart-review"]')?.addEventListener('click', startSmartReview);
    root.querySelector('[data-action="review-approve"]')?.addEventListener('click', () => moveReviewNext(true));
    root.querySelector('[data-action="review-skip"]')?.addEventListener('click', () => moveReviewNext(false));
    root.querySelector('[data-action="review-resume"]')?.addEventListener('click', resumeReviewFlow);
    root.querySelector('[data-action="publish"]')?.addEventListener('click', startPublish);
    root.querySelector('[data-action="resume"]')?.addEventListener('click', resumePublication);
    root.querySelector('[data-action="stop"]')?.addEventListener('click', () => pausePublication('Interrompida por você.'));
    root.querySelector('[data-action="clear"]')?.addEventListener('click', clearQueue);

    root.querySelectorAll('[data-index]').forEach((card) => {
      const passenger = state.passengers[Number(card.dataset.index)];
      card.querySelector('[data-role="suggestion"]')?.addEventListener('input', (event) => {
        passenger.suggestion = event.target.value; passenger.approved = false; saveState();
      });
      card.querySelector('[data-role="rating"]')?.addEventListener('change', (event) => {
        passenger.rating = Number(event.target.value); passenger.approved = false; saveState();
      });
      card.querySelector('[data-role="approved"]')?.addEventListener('change', (event) => {
        passenger.approved = event.target.checked; saveState();
      });
    });
  };

  const render = () => {
    const root = ensureRoot();
    root.classList.toggle('rai-closed', !state.panelOpen);
    const publish = state.publish;
    const cards = state.passengers.length ? state.passengers.map(renderPassengerCard).join('') : '<div class="rai-empty">A fila aparecerá ao tocar em Revisar pendentes.</div>';
    root.innerHTML = `<div class="rai-shell"><div class="rai-head"><div class="rai-head-title">RotaAi — Avaliações
      <small>${publish.active ? `Publicando ${Math.min(publish.index + 1, publish.queue.length)}/${publish.queue.length}` : state.review.active ? `Revisando ${Math.min(state.review.index + 1, state.review.queue.length)}/${state.review.queue.length}` : 'Revisar e publicar'}</small></div>
      <button data-action="toggle">${state.panelOpen ? 'Fechar' : 'Abrir'}</button></div>
      <div class="rai-body"><div class="rai-actions">
        <button class="rai-primary" data-action="smart-review" ${state.busy || publish.active || state.review.active ? 'disabled' : ''}>Revisar pendentes</button>
        ${state.review.active && state.review.stage === 'awaiting-user' ? '<button class="rai-primary" data-action="review-approve">Aprovar e próxima</button><button data-action="review-skip">Pular esta</button>' : ''}
        ${state.review.paused ? '<button class="rai-primary" data-action="review-resume">Retomar revisão</button>' : ''}
        <button class="rai-primary" data-action="publish" ${state.busy || publish.active || state.review.active || !state.passengers.some((p) => p.approved && !p.published) ? 'disabled' : ''}>Publicar aprovadas</button>
        ${publish.paused ? '<button class="rai-primary" data-action="resume">Retomar publicação</button>' : ''}
        ${publish.active ? '<button class="rai-danger" data-action="stop">Parar publicação</button>' : ''}
        <button class="rai-danger" data-action="clear" ${publish.active || state.review.active ? 'disabled' : ''}>Recomeçar</button>
      </div><div class="rai-status">${escapeHtml(state.status)}</div><div class="rai-list">${cards}</div></div></div>`;
    bindEvents(root);
  };

  const automationPulse = () => {
    if (state.review.autoStart && !state.review.active && !state.busy && now() - state.review.lastActionAt > 1200) {
      state.review.lastActionAt = now();
      startSmartReview();
      return;
    }
    if (state.review.active) processReviewFlow(false);
    if (state.publish.active) processPublication(false);
    if (!document.getElementById(ROOT_ID)) render();
  };

  const installNavigationHooks = () => {
    if (window.__rotaAiNavigationHooks) return;
    window.__rotaAiNavigationHooks = true;
    for (const method of ['pushState', 'replaceState']) {
      const original = history[method];
      history[method] = function(...args) {
        const result = original.apply(this, args);
        setTimeout(automationPulse, 350);
        return result;
      };
    }
    addEventListener('popstate', () => setTimeout(automationPulse, 350));
    const observer = new MutationObserver(() => {
      clearTimeout(mutationTimer);
      mutationTimer = setTimeout(automationPulse, 300);
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  };

  const startTimer = () => {
    clearInterval(automationTimer);
    automationTimer = setInterval(automationPulse, 900);
  };

  const openPanel = () => { state.panelOpen = true; saveState(); render(); };
  const resume = () => {
    restoreState(); render(); startTimer();
    setTimeout(automationPulse, 500);
  };

  window.RotaAiAndroid = {
    version: '0.4.0',
    openPanel,
    resume,
    scanTrips,
    prepareAll,
    startSmartReview,
    startPublish,
    moveReviewNext,
    processReviewFlow,
    processPublication,
    getStatus: () => state.status
  };
  restoreState();
  installNavigationHooks();
  render();
  startTimer();
  notifyNative(state.status);
  setTimeout(automationPulse, 700);
})();