from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'app' / 'src' / 'main' / 'assets' / 'rotaai-part2.js'
text = path.read_text(encoding='utf-8')
start = text.find('  const startSmartReview = async () => {')
end = text.find('  const currentReviewPassenger =', start)
if start < 0 or end < 0:
    raise RuntimeError('startSmartReview markers not found')

replacement = r'''  let smartReviewRetryTimer = null;
  let smartReviewRetryCount = 0;

  const scheduleSmartReviewRetry = (message) => {
    if (window.RotaAiDebug?.isStopped?.()) return;
    clearTimeout(smartReviewRetryTimer);
    smartReviewRetryCount += 1;
    state.review.autoStart = true;
    state.busy = false;
    setStatus(`${message} (${smartReviewRetryCount}/12)`);
    smartReviewRetryTimer = setTimeout(() => {
      if (window.RotaAiDebug?.isStopped?.()) return;
      startSmartReview();
    }, 700);
  };

  const startSmartReview = async () => {
    if (window.RotaAiDebug?.isStopped?.()) return;
    if (state.busy || state.publish.active || state.review.active) return;
    state.panelOpen = true;
    state.busy = true;
    setStatus('Procurando quem ainda não foi avaliado...');
    await scanTrips();
    state.busy = false;

    if (!state.passengers.length) {
      const pendingAction = findFirstPendingAction();
      if (pendingAction) {
        smartReviewRetryCount = 0;
        state.review.autoStart = true;
        setStatus('Abrindo o resumo da viagem...');
        pendingAction.click();
        return;
      }

      const onTripSummary = /^\/rides\/offer\/?$/i.test(location.pathname);
      if (onTripSummary && smartReviewRetryCount < 12) {
        return scheduleSmartReviewRetry('Aguardando o resumo carregar os passageiros');
      }

      if (!/^\/rides(?:\/|$)/i.test(location.pathname)) {
        smartReviewRetryCount = 0;
        state.review.autoStart = true;
        setStatus('Abrindo suas viagens...');
        location.href = RIDES_URL;
        return;
      }

      smartReviewRetryCount = 0;
      state.review.autoStart = false;
      return setStatus('Nenhum passageiro aguardando avaliação foi encontrado nesta tela.');
    }

    smartReviewRetryCount = 0;
    clearTimeout(smartReviewRetryTimer);
    const queue = state.passengers.filter((p) => !p.published).map((p) => p.key);
    state.review = {
      ...initialState().review,
      active: true,
      autoStart: false,
      queue,
      currentKey: queue[0],
      stage: 'starting'
    };
    state.status = `Abrindo a primeira de ${queue.length} avaliação(ões).`;
    notifyNative(state.status); saveState(); render();
    processReviewFlow(true);
  };
'''

path.write_text(text[:start] + replacement + '\n' + text[end:], encoding='utf-8')
print('patch_dynamic_retry: ok')
