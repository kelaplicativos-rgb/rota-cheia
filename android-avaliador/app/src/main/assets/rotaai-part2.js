  const profileHrefScore = (href = '') => PROFILE_PATH_MARKERS.reduce(
    (score, marker) => score + (href.toLowerCase().includes(marker) ? 2 : 0), 0);

  const collectProfileLinks = (doc, baseUrl) => {
    const links = [];
    for (const anchor of doc.querySelectorAll('a[href]')) {
      const href = absoluteUrl(anchor.getAttribute('href') || '', baseUrl);
      const score = profileHrefScore(href);
      const imageNames = [...anchor.querySelectorAll('img[alt]')]
        .map((img) => cleanName(img.getAttribute('alt') || '')).filter(isLikelyPersonName);
      const textName = cleanName(safeText(anchor));
      const names = unique([...imageNames, textName].filter(isLikelyPersonName));
      const isSameSite = /^https:\/\/([a-z0-9-]+\.)?blablacar\.com(\.br)?\//i.test(href);
      const isNavigation = /\/(rides\/offer|search|login|signup|carpool|bus|help|support)(?:[/?#]|$)/i.test(href);
      // Para evitar abrir o link de avaliação ou outro link com o nome da pessoa,
      // só considera URLs que tenham formato explícito de perfil.
      if (!score || !isSameSite || isNavigation) continue;
      links.push({ href, names, score });
    }
    const deduped = new Map();
    for (const link of links) {
      if (!link.href) continue;
      const old = deduped.get(link.href);
      if (!old || link.score > old.score) deduped.set(link.href, link);
    }
    return [...deduped.values()];
  };

  const nameSimilarity = (left = '', right = '') => {
    const a = normalize(left).split(' ').filter(Boolean);
    const b = normalize(right).split(' ').filter(Boolean);
    if (!a.length || !b.length) return 0;
    const overlap = a.filter((part) => b.includes(part)).length;
    return overlap + (a[0] === b[0] ? 2 : 0);
  };

  const matchProfilesToPassengers = (tripPassengers, links) => {
    const remaining = [...links];
    const result = new Map();
    for (const passenger of tripPassengers) {
      let bestIndex = -1;
      let bestScore = 0;
      remaining.forEach((link, index) => {
        const score = Math.max(0, ...link.names.map((candidate) => nameSimilarity(passenger.name, candidate)));
        if (score > bestScore) { bestScore = score; bestIndex = index; }
      });
      if (bestIndex >= 0 && bestScore >= 2) {
        result.set(passenger.key, remaining[bestIndex].href);
        remaining.splice(bestIndex, 1);
      }
    }
    const unmatched = tripPassengers.filter((p) => !result.has(p.key));
    const strong = remaining.filter((link) => link.score >= 1);
    if (unmatched.length === 1 && strong.length === 1) {
      result.set(unmatched[0].key, strong[0].href);
    }
    return result;
  };

  const bestProfileForPassenger = (passenger, links) => {
    const scored = links.map((link) => ({
      link,
      nameScore: Math.max(0, ...link.names.map((candidate) => nameSimilarity(passenger.name, candidate)))
    })).sort((left, right) => right.nameScore - left.nameScore || right.link.score - left.link.score);
    if (scored[0]?.nameScore >= 2) return scored[0].link.href;
    const strong = links.filter((link) => link.score >= 1);
    return strong.length === 1 ? strong[0].href : '';
  };

  const looksLikeReviewText = (value = '') => {
    const text = value.replace(/\s+/g, ' ').trim();
    if (text.length < 12 || text.length > 900) return false;
    if (/^(avalia[cç][oõ]es|ver mais|mostrar mais|responder|publicado em|membro desde)$/i.test(text)) return false;
    if (/cookie|privacidade|termos e condi|central de ajuda|baixar o app/i.test(text)) return false;
    return text.split(' ').length >= 3;
  };

  const extractReviewTextsFromDom = (doc) => {
    const results = [];
    const containers = unique([
      ...doc.querySelectorAll('[data-testid*="review" i], [data-testid*="feedback" i], [data-testid*="comment" i]'),
      ...doc.querySelectorAll('[class*="review" i], [class*="feedback" i], [class*="comment" i]')
    ]);
    for (const container of containers) {
      const leaves = container.querySelectorAll('blockquote, p, [data-testid*="text" i]');
      if (leaves.length) {
        for (const leaf of leaves) if (looksLikeReviewText(safeText(leaf))) results.push(safeText(leaf));
      } else if (looksLikeReviewText(safeText(container))) results.push(safeText(container));
    }
    return results;
  };

  const extractReviewTextsFromJson = (doc) => {
    const results = [];
    const reviewKey = /(review|rating|comment|feedback|opinion|avaliacao|avaliacoes)/i;
    const textKey = /^(text|comment|content|description|message|body|value)$/i;
    const visit = (value, context = '', depth = 0) => {
      if (depth > 14 || value == null) return;
      if (typeof value === 'string') {
        if (reviewKey.test(context) && looksLikeReviewText(value)) results.push(value.trim());
        return;
      }
      if (Array.isArray(value)) return value.slice(0, 500).forEach((item) => visit(item, context, depth + 1));
      if (typeof value === 'object') {
        const keys = Object.keys(value);
        const objectReview = keys.some((key) => reviewKey.test(key));
        for (const [key, item] of Object.entries(value)) {
          if (typeof item === 'string' && textKey.test(key) && objectReview && looksLikeReviewText(item)) results.push(item.trim());
          else visit(item, objectReview || reviewKey.test(context) ? `review.${key}` : key, depth + 1);
        }
      }
    };
    for (const script of doc.querySelectorAll('script')) {
      const raw = script.textContent?.trim();
      if (!raw || raw.length < 2) continue;
      const type = script.getAttribute('type') || '';
      if (type.includes('json') || raw.startsWith('{') || raw.startsWith('[')) {
        try { visit(JSON.parse(raw)); } catch { /* JavaScript não JSON */ }
      }
    }
    return results;
  };

  const extractReviews = (doc) => {
    const seen = new Set();
    const output = [];
    for (const raw of [...extractReviewTextsFromDom(doc), ...extractReviewTextsFromJson(doc)]) {
      const text = raw.replace(/\s+/g, ' ').trim();
      const key = normalize(text);
      if (!looksLikeReviewText(text) || seen.has(key)) continue;
      seen.add(key); output.push(text);
      if (output.length >= MAX_REVIEW_TEXTS) break;
    }
    return output;
  };

  const scanTrips = async () => {
    const cards = getTripCards(document);
    const pendingCards = cards.filter((article) => hasPendingReviewLabel(safeText(article)));
    const trips = extractTrips(document);
    state.trips = trips;
    state.passengers = buildPassengerQueue(trips);
    state.unresolvedTrips = Math.max(0, pendingCards.length - trips.length);
    if (state.passengers.length) {
      state.status = `${state.passengers.length} passageiro(s) ainda sem avaliação em ${trips.length} viagem(ns).`;
      if (state.unresolvedTrips) {
        state.status += ` ${state.unresolvedTrips} viagem(ns) não exibiram o nome de quem falta avaliar; abra cada uma e escaneie novamente.`;
      }
    } else if (state.unresolvedTrips) {
      state.status = `${state.unresolvedTrips} viagem(ns) indicam avaliação pendente, mas não mostram o nome. Abra a viagem e escaneie novamente.`;
    } else {
      state.status = 'Nenhum passageiro sem avaliação foi encontrado nesta página.';
    }
    saveState(); render();
  };

  const discoverProfiles = async () => {
    if (!state.passengers.length) return setStatus('Escaneie primeiro a página de viagens.');
    state.busy = true; render();
    const groups = new Map();
    for (const passenger of state.passengers) {
      if (!groups.has(passenger.tripId)) groups.set(passenger.tripId, []);
      groups.get(passenger.tripId).push(passenger);
    }

    let processed = 0;
    for (const trip of state.trips) {
      const passengers = groups.get(trip.id) || [];
      if (!passengers.length) continue;
      state.status = `Buscando perfis: ${processed + 1} de ${state.trips.length}`; render();

      // Primeiro usa o convite individual de cada passageiro. Esse é o caminho
      // mais seguro para não associar a avaliação ao perfil errado.
      for (const passenger of passengers) {
        if (passenger.profileUrl) continue;
        const sourceUrl = passenger.reviewUrl || '';
        if (!sourceUrl) continue;
        try {
          if (profileHrefScore(sourceUrl) >= 2) {
            passenger.profileUrl = sourceUrl;
          } else {
            const sourceDoc = await fetchDocument(sourceUrl);
            passenger.profileUrl = bestProfileForPassenger(
              passenger,
              collectProfileLinks(sourceDoc, sourceUrl)
            );
          }
        } catch (error) {
          console.warn('RotaAi: convite individual não revelou o perfil.', passenger.name, error);
        }
        await sleep(250);
      }

      // Depois usa a página geral da viagem somente para quem ainda ficou sem
      // perfil e exige correspondência pelo nome (ou caso único inequívoco).
      const unmatched = passengers.filter((passenger) => !passenger.profileUrl);
      if (unmatched.length && trip.offerUrl) {
        try {
          const tripDoc = await fetchDocument(trip.offerUrl);
          const links = collectProfileLinks(tripDoc, trip.offerUrl);
          const matched = matchProfilesToPassengers(unmatched, links);
          for (const passenger of unmatched) {
            passenger.profileUrl = matched.get(passenger.key) || '';
          }
        } catch (error) {
          console.warn('RotaAi: página geral da viagem não revelou os perfis.', error);
        }
      }

      for (const passenger of passengers) {
        if (!passenger.profileUrl && passenger.status !== 'pronto') {
          passenger.status = 'sem_perfil';
          passenger.reason = 'Perfil não identificado com segurança nessa viagem.';
        }
      }
      processed += 1; saveState(); await sleep(REQUEST_DELAY_MS);
    }

    const found = state.passengers.filter((p) => p.profileUrl).length;
    state.busy = false;
    state.status = `${found} de ${state.passengers.length} perfis identificados com segurança.`;
    saveState(); render();
  };

  const analyzePassenger = async (passenger) => {
    if (!passenger.profileUrl) {
      passenger.status = 'sem_perfil'; passenger.reason = 'O link do perfil não foi encontrado.'; return;
    }
    passenger.status = 'analisando'; passenger.reason = ''; render();
    try {
      const profileDoc = await fetchDocument(passenger.profileUrl);
      passenger.reviews = extractReviews(profileDoc);
      const generated = window.RotaAiGenerator.generateEvaluation({ name: passenger.name, reviews: passenger.reviews });
      passenger.suggestion = generated.text;
      passenger.traits = generated.traits;
      passenger.reason = generated.reason;
      passenger.status = generated.ok ? 'pronto' : 'sem_base';
      if (!generated.ok) passenger.approved = false;
    } catch (error) {
      passenger.status = 'erro'; passenger.reason = error?.message || 'Falha ao ler o perfil.';
      passenger.approved = false;
    }
  };

  const generateAll = async () => {
    if (!state.passengers.length) return setStatus('Não há passageiros na fila.');
    state.busy = true; render();
    const pending = state.passengers.filter((p) => p.profileUrl && !p.published);
    let done = 0;
    for (const passenger of pending) {
      state.status = `Gerando avaliação de ${passenger.name} (${done + 1}/${pending.length})`; render();
      await analyzePassenger(passenger); done += 1; saveState(); await sleep(REQUEST_DELAY_MS);
    }
    state.busy = false;
    const ready = state.passengers.filter((p) => p.status === 'pronto' && p.suggestion).length;
    state.status = `${ready} avaliações prontas. Revise o texto e as estrelas.`;
    saveState(); render();
  };

  const prepareAll = async () => {
    if (state.busy || state.publish.active || state.review.active) return;
    await scanTrips();
    if (!state.passengers.length) return;
    await discoverProfiles();
    await generateAll();
    const ready = state.passengers.filter((p) => p.status === 'pronto' && p.suggestion?.trim()).length;
    state.status = `${ready} avaliação(ões) preparada(s). Agora revise uma por uma.`;
    saveState(); render();
  };

  const currentReviewPassenger = () => {
    const key = state.review.queue[state.review.index];
    return state.passengers.find((p) => p.key === key) || null;
  };

  const selectedRating = () => {
    const checked = [...document.querySelectorAll('input[type="radio"]')]
      .find((input) => input.checked && Number(input.value) >= 1 && Number(input.value) <= 5 && isSiteElement(input));
    if (checked) return Number(checked.value);
    const selected = [...document.querySelectorAll('[aria-checked="true"], [aria-selected="true"]')]
      .find((element) => /estrela|star/i.test(`${safeText(element)} ${element.getAttribute('aria-label') || ''}`) && isSiteElement(element));
    const match = `${safeText(selected)} ${selected?.getAttribute?.('aria-label') || ''}`.match(/([1-5])/);
    return match ? Number(match[1]) : 0;
  };

