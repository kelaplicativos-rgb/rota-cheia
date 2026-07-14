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


part4_path = ASSETS / "rotaai-part4.js"
part4 = part4_path.read_text(encoding="utf-8")

publication_flow = r'''  let publicationRetryTimer = globalThis.__rotaAiPublicationRetryTimer || null;

  const publicationPathStep = () => {
    const path = location.pathname.replace(/\/+$/, '').toLowerCase();
    if (path.endsWith('/intro')) return 'intro';
    if (path.endsWith('/note')) return 'note';
    if (path.endsWith('/comment')) return 'comment';
    if (path.endsWith('/preview')) return 'preview';
    if (/\/(success|successful|confirmation|confirmed|completed|done|thanks|thank-you)$/.test(path)) return 'success';
    return '';
  };

  const schedulePublicationRetry = (passenger, message, delay = 850) => {
    clearTimeout(publicationRetryTimer);
    if (!state.publish.active || window.RotaAiDebug?.isStopped?.()) return;
    state.publish.lastActionAt = now();
    state.status = message;
    notifyNative(state.status); saveState(); render();
    publicationRetryTimer = setTimeout(() => {
      if (!state.publish.active || window.RotaAiDebug?.isStopped?.()) return;
      if (currentPublishingPassenger()?.key !== passenger.key) return;
      processPublication(true);
    }, delay);
    globalThis.__rotaAiPublicationRetryTimer = publicationRetryTimer;
  };

  const clickPublicationStepOnce = (passenger, target, stage, message) => {
    if (!target || target.disabled || target.getAttribute('aria-disabled') === 'true') return false;
    const token = `${passenger.key}::${location.pathname}::${stage}`;
    const elapsed = now() - Number(state.publish.lastStepClickAt || 0);
    if (state.publish.lastStepToken === token && elapsed < 2500) {
      window.RotaAiDebug?.log?.('publication', 'step_click_locked', {
        passenger: passenger.name,
        stage,
        path: location.pathname,
        elapsedMs: elapsed
      });
      schedulePublicationRetry(passenger, message, 700);
      return true;
    }
    state.publish.lastStepToken = token;
    state.publish.lastStepClickAt = now();
    state.publish.lastActionAt = now();
    state.publish.stage = stage;
    state.status = message;
    notifyNative(state.status); saveState(); render();
    target.click();
    schedulePublicationRetry(passenger, message, 700);
    return true;
  };

  const completePublishedPassenger = async () => {
    markCurrentPublished();
    const next = currentPublishingPassenger();
    if (!next) return finishPublication();
    state.status = `Publicado ${state.publish.completed.length}/${state.publish.queue.length}. Abrindo ${next.name}...`;
    notifyNative(state.status); saveState(); render();
    await sleep(350);
    if (!navigateToPassengerTrip(next)) schedulePublicationRetry(next, `Preparando a avaliação de ${next.name}...`, 500);
  };

  const processPublication = async (force = false) => {
    if (!state.publish.active || window.RotaAiDebug?.isStopped?.()) return;
    if (!force && now() - state.publish.lastActionAt < 700) return;
    const passenger = currentPublishingPassenger();
    if (!passenger) return finishPublication();
    state.publish.currentKey = passenger.key;

    if (hasBlockingPage()) return pausePublication('A BlaBlaCar solicitou uma verificação manual.');
    if (hasSuccessMessage() || publicationPathStep() === 'success') return completePublishedPassenger();

    const targetUrl = passenger.reviewUrl || passenger.offerUrl;
    const targetFlow = ratingFlowKey(targetUrl || '');
    const currentFlow = ratingFlowKey(location.href);

    if (state.publish.stage === 'submitted') {
      state.publish.attempts += 1;
      if (state.publish.attempts >= 12) {
        return pausePublication(`Não consegui confirmar a publicação de ${passenger.name}. Nada foi marcado como publicado.`);
      }
      return schedulePublicationRetry(
        passenger,
        `Aguardando a confirmação da publicação de ${passenger.name}... (${state.publish.attempts}/12)`,
        900
      );
    }

    if (targetFlow && currentFlow !== targetFlow) {
      state.publish.attempts = 0;
      state.publish.lastStepToken = '';
      state.publish.lastStepClickAt = 0;
      state.publish.lastActionAt = now();
      state.publish.stage = 'navigate-passenger';
      state.status = `Abrindo a avaliação correta de ${passenger.name}...`;
      notifyNative(state.status); saveState(); render();
      if (navigateToPassengerTrip(passenger)) return;
      return schedulePublicationRetry(passenger, `Aguardando a avaliação de ${passenger.name} abrir...`, 700);
    }

    if (targetFlow && currentFlow === targetFlow) {
      const step = publicationPathStep();

      if (step === 'intro') {
        const advance = findVisible('button[data-testid="e2e-leave-rating-intro-continue-button-mobile"]')
          || findClickableByText([/^continuar$/i, /^come[cç]ar$/i, /^iniciar$/i, /^pr[oó]ximo$/i, /^avan[cç]ar$/i]);
        if (clickPublicationStepOnce(passenger, advance, 'intro-next', `Iniciando a publicação de ${passenger.name}...`)) return;
        return schedulePublicationRetry(passenger, `Aguardando o início da avaliação de ${passenger.name}...`);
      }

      if (step === 'note') {
        const token = `${passenger.key}::${location.pathname}::rating`;
        const elapsed = now() - Number(state.publish.lastStepClickAt || 0);
        if (state.publish.lastStepToken === token && elapsed < 2500) {
          return schedulePublicationRetry(passenger, `Nota de ${passenger.name} selecionada. Abrindo o comentário...`, 700);
        }
        state.publish.lastStepToken = token;
        state.publish.lastStepClickAt = now();
        const selected = clickRatingChoice(Number(passenger.rating));
        if (selected) {
          state.publish.attempts = 0;
          state.publish.stage = 'rating-selected';
          return schedulePublicationRetry(passenger, `Nota de ${passenger.name} selecionada. Abrindo o comentário...`, 700);
        }
        return schedulePublicationRetry(passenger, `Aguardando as opções de nota de ${passenger.name}...`);
      }

      if (step === 'comment') {
        const field = findReviewField();
        if (!field) return schedulePublicationRetry(passenger, `Aguardando o campo de comentário de ${passenger.name}...`);
        const currentValue = (field.value ?? field.textContent ?? '').toString();
        if (currentValue.trim() !== passenger.suggestion.trim()) nativeSetValue(field, passenger.suggestion);
        const advance = findVisible('button[data-testid="e2e-leave-rating-comment-continue-button-mobile"]')
          || findClickableByText([/^continuar$/i, /^pr[oó]ximo$/i, /^avan[cç]ar$/i, /^revisar$/i]);
        if (clickPublicationStepOnce(passenger, advance, 'comment-next', `Revisando a avaliação de ${passenger.name}...`)) return;
        return schedulePublicationRetry(passenger, `Aguardando a continuação do comentário de ${passenger.name}...`);
      }

      if (step === 'preview') {
        const submit = findVisible('button[data-testid*="leave-rating-preview" i]')
          || findVisible('button[data-testid*="submit-rating" i]')
          || findVisible('button[data-testid*="rating-submit" i]')
          || findClickableByText([/^publicar$/i, /^enviar$/i, /^confirmar$/i, /^concluir$/i, /publicar avalia/i, /enviar avalia/i, /confirmar avalia/i]);
        if (!submit) return schedulePublicationRetry(passenger, `Aguardando a confirmação final de ${passenger.name}...`);
        state.publish.attempts = 0;
        if (clickPublicationStepOnce(passenger, submit, 'submitted', `Publicando avaliação de ${passenger.name}...`)) return;
      }

      return schedulePublicationRetry(passenger, `Aguardando a etapa atual de ${passenger.name} carregar...`);
    }

    if (targetUrl && navigateToPassengerTrip(passenger)) {
      state.publish.lastActionAt = now();
      state.publish.stage = 'navigate-passenger';
      state.status = `Abrindo a avaliação de ${passenger.name}...`;
      notifyNative(state.status); saveState(); render();
      return;
    }

    state.publish.attempts += 1;
    if (state.publish.attempts >= 10) return pausePublication(`A tela de ${passenger.name} não foi reconhecida.`);
    schedulePublicationRetry(passenger, `Localizando a avaliação de ${passenger.name}... (${state.publish.attempts}/10)`);
  };'''

part4 = replace_section(
    part4,
    "  const processPublication = async (force = false) => {",
    "  const clearQueue =",
    publication_flow,
    "processPublication publication-state-machine-v2",
)
part4_path.write_text(part4, encoding="utf-8")

print("patch_publication_flow: ok")
