(() => {
  'use strict';

  if (window.RotaAiAndroid?.version === '0.4.0') {
    window.RotaAiAndroid.resume?.();
    return;
  }

  const ROOT_ID = 'rotaai-android-panel';
  const STYLE_ID = 'rotaai-android-style';
  const STORAGE_KEY = 'rotaaiAndroidReviewStateV5';
  const RIDES_URL = 'https://www.blablacar.com.br/rides';
  const REQUEST_DELAY_MS = 500;
  const MAX_REVIEW_TEXTS = 30;
  const PROFILE_PATH_MARKERS = ['/member/profile', '/members/', '/user/', '/users/', '/profile/'];
  const SUCCESS_PATTERNS = [
    /avalia[cç][aã]o enviada/i,
    /avalia[cç][aã]o publicada/i,
    /obrigad[oa].*avalia[cç][aã]o/i,
    /feedback enviado/i,
    /opini[aã]o enviada/i
  ];
  const BLOCK_PATTERNS = [
    /captcha/i,
    /verifique que voc[eê] [eé] humano/i,
    /atividade incomum/i,
    /confirme sua identidade/i,
    /muitas tentativas/i
  ];

  const initialState = () => ({
    trips: [],
    passengers: [],
    unresolvedTrips: 0,
    busy: false,
    status: 'Entre na conta e toque em “Revisar pendentes”.',
    panelOpen: false,
    review: {
      active: false,
      paused: false,
      autoStart: false,
      queue: [],
      index: 0,
      stage: 'idle',
      currentKey: '',
      filledKey: '',
      lastActionAt: 0,
      attempts: 0
    },
    publish: {
      active: false,
      paused: false,
      queue: [],
      index: 0,
      stage: 'idle',
      currentKey: '',
      lastActionAt: 0,
      attempts: 0,
      completed: [],
      failures: []
    }
  });

  let state = initialState();
  let automationTimer = null;
  let mutationTimer = null;

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const normalize = window.RotaAiGenerator?.normalize ?? ((value = '') => value.toLowerCase().trim());
  const safeText = (el) => el?.textContent?.replace(/\s+/g, ' ').trim() ?? '';
  const unique = (items) => [...new Set(items.filter(Boolean))];
  const now = () => Date.now();
  const visible = (el) => {
    if (!el || !(el instanceof Element)) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) !== 0
      && rect.width > 2 && rect.height > 2;
  };
  const absoluteUrl = (value, base = location.href) => {
    try { return new URL(value, base).href; } catch { return ''; }
  };
  const offerIdFromUrl = (url = '') => {
    try { return new URL(url).searchParams.get('id') || ''; } catch { return ''; }
  };
  const cleanName = (value = '') => value.replace(/\s+/g, ' ').replace(/^(perfil de|foto de)\s+/i, '').trim();
  const isLikelyPersonName = (value = '') => {
    const cleaned = cleanName(value);
    if (cleaned.length < 2 || cleaned.length > 70) return false;
    if (/^(blablacar|avatar|logo|imagem|foto|carona|motorista|passageiro)$/i.test(cleaned)) return false;
    return /[A-Za-zÀ-ÿ]/.test(cleaned);
  };
  const escapeHtml = (value = '') => value.toString()
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  const pendingReviewNamesFromText = (value = '') => {
    const text = value.toString().replace(/\s+/g, ' ').trim();
    const names = [];
    const pattern = /avalie\s+sua\s+experi[eê]ncia(?:\s+de\s+viagem)?\s+com\s+([^.!?\n]{2,70})(?=[.!?\n]|$)/giu;
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const name = cleanName(match[1] || '').replace(/\s+(?:agora|aqui)$/i, '').trim();
      if (isLikelyPersonName(name)) names.push(name);
    }
    return unique(names);
  };

  const normalizeReviewLabel = (value = '') => value.toString()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();

  const hasPendingReviewLabel = (value = '') => {
    const text = normalizeReviewLabel(value);
    return text.includes('faca uma avaliacao')
      || text.includes('fazer avaliacao')
      || text.includes('avaliar passageiro')
      || text.includes('avaliar passageira')
      || text.includes('deixar avaliacao')
      || text.includes('avalie sua experiencia de viagem com');
  };

  const hasCompletedReviewLabel = (value = '') => {
    const text = normalizeReviewLabel(value);
    return text.includes('avaliacao enviada')
      || text.includes('avaliacao publicada')
      || text.includes('avaliacao concluida')
      || text.includes('ja avaliado')
      || text.includes('ja avaliada')
      || text.includes('voce avaliou');
  };

  if (globalThis.__ROTA_AI_TEST_ONLY__ === true) {
    globalThis.RotaAiPendingReviewTest = { pendingReviewNamesFromText, hasPendingReviewLabel, hasCompletedReviewLabel };
    return;
  }

  const notifyNative = (message) => {
    try { window.RotaAiNative?.status?.(message); } catch { /* interface opcional */ }
  };

  const saveState = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...state, savedAt: new Date().toISOString() }));
    } catch (error) {
      console.warn('RotaAi: falha ao salvar estado.', error);
    }
  };

  const restoreState = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      state = {
        ...initialState(),
        ...saved,
        trips: Array.isArray(saved.trips) ? saved.trips : [],
        passengers: Array.isArray(saved.passengers) ? saved.passengers : [],
        review: { ...initialState().review, ...(saved.review || {}) },
        publish: { ...initialState().publish, ...(saved.publish || {}) }
      };
    } catch (error) {
      console.warn('RotaAi: estado anterior inválido.', error);
      state = initialState();
    }
  };

  const setStatus = (message) => {
    state.status = message;
    notifyNative(message);
    saveState();
    render();
  };

  const parseHtml = (html) => new DOMParser().parseFromString(html, 'text/html');
  const fetchDocument = async (url) => {
    const response = await fetch(url, {
      method: 'GET', credentials: 'include', redirect: 'follow',
      headers: { Accept: 'text/html,application/xhtml+xml' }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const html = await response.text();
    if (/como voc[eê] deseja se conectar|continuar com e-mail|\/login\?/i.test(html)) {
      throw new Error('Faça login na BlaBlaCar antes de continuar.');
    }
    return parseHtml(html);
  };

  const getTripCards = (doc = document) => {
    const cards = [...doc.querySelectorAll('article[data-testid^="e2e-your-rides-trip-card-"]')];
    return cards.length ? cards : [...doc.querySelectorAll('article')];
  };

  const reviewUrlFromElement = (element, baseUrl = location.href) => {
    if (!element) return '';
    const anchor = element.matches?.('a[href]')
      ? element
      : element.closest?.('a[href]') || element.querySelector?.('a[href]');
    return absoluteUrl(anchor?.getAttribute?.('href') || '', baseUrl);
  };

  const extractPendingReviewPassengers = (root) => {
    const found = new Map();
    const add = (name, reviewUrl = '', source = 'named-prompt') => {
      const cleaned = cleanName(name);
      if (!isLikelyPersonName(cleaned)) return;
      const key = normalize(cleaned);
      const previous = found.get(key);
      if (!previous || (!previous.reviewUrl && reviewUrl)) {
        found.set(key, { name: cleaned, reviewUrl, source });
      }
    };

    const nodes = [...root.querySelectorAll('a[href], button, [role="button"], li, section, div, p, span')]
      .map((node) => ({ node, text: safeText(node), names: pendingReviewNamesFromText(safeText(node)) }))
      .filter((item) => item.names.length)
      .sort((left, right) => left.text.length - right.text.length);

    for (const item of nodes) {
      const reviewUrl = reviewUrlFromElement(item.node);
      item.names.forEach((name) => add(name, reviewUrl));
    }

    pendingReviewNamesFromText(safeText(root)).forEach((name) => add(name, '', 'root-text'));
    if (found.size) return [...found.values()];

    const rootText = safeText(root);
    if (!hasPendingReviewLabel(rootText) || hasCompletedReviewLabel(rootText)) return [];
    const imageNames = unique([...root.querySelectorAll('img[data-testid="multiple-logo"][alt], img[alt]')]
      .map((img) => cleanName(img.getAttribute('alt') || '')).filter(isLikelyPersonName));
    if (imageNames.length === 1) {
      const action = [...root.querySelectorAll('a[href], button, [role="button"]')]
        .find((element) => hasPendingReviewLabel(safeText(element)));
      add(imageNames[0], reviewUrlFromElement(action), 'single-passenger-legacy');
    }
    return [...found.values()];
  };

  const tripFromRoot = (root, index, idPrefix = 'trip') => {
    const pendingPassengers = extractPendingReviewPassengers(root);
    if (!pendingPassengers.length) return null;
    const offerAnchor = root.querySelector?.('a[href*="/rides/offer"], a[href*="offer?id="]');
    const offerUrl = absoluteUrl(offerAnchor?.getAttribute('href') || (idPrefix === 'page' ? location.href : ''));
    const departure = safeText(root.querySelector?.('[data-testid="e2e-itinerary-departure-station"]'));
    const arrival = safeText(root.querySelector?.('[data-testid="e2e-itinerary-arrival-station"]'));
    const time = safeText(root.querySelector?.('[data-testid="e2e-itinerary-departure-time"]'));
    const date = safeText(root.querySelector?.('h2, h3'));
    return {
      id: offerUrl || `${idPrefix}-${index}-${date}-${time}-${location.pathname}`,
      offerId: offerIdFromUrl(offerUrl),
      date, time, origin: departure, destination: arrival,
      offerUrl,
      reviewUrl: pendingPassengers.find((item) => item.reviewUrl)?.reviewUrl || '',
      passengers: pendingPassengers.map((item) => item.name),
      pendingPassengers
    };
  };

  const extractTrips = (doc = document) => {
    const trips = getTripCards(doc).map((article, index) => tripFromRoot(article, index)).filter(Boolean);
    const existing = new Set(trips.flatMap((trip) => trip.pendingPassengers.map((item) => normalize(item.name))));
    const pagePassengers = extractPendingReviewPassengers(doc.body || doc.documentElement)
      .filter((item) => !existing.has(normalize(item.name)));
    if (pagePassengers.length) {
      trips.push({
        id: `page-${location.href}`,
        offerId: offerIdFromUrl(location.href),
        date: safeText(doc.querySelector('h1, h2')),
        time: '', origin: '', destination: '', offerUrl: location.href,
        reviewUrl: pagePassengers.find((item) => item.reviewUrl)?.reviewUrl || '',
        passengers: pagePassengers.map((item) => item.name),
        pendingPassengers: pagePassengers
      });
    }
    return trips;
  };

  const passengerKey = (trip, name) => `${trip.id}::${normalize(name)}`;
  const buildPassengerQueue = (trips) => {
    const previous = new Map(state.passengers.map((p) => [p.key, p]));
    const queue = [];
    for (const trip of trips) {
      const pendingPassengers = Array.isArray(trip.pendingPassengers) && trip.pendingPassengers.length
        ? trip.pendingPassengers
        : (trip.passengers || []).map((name) => ({ name, reviewUrl: trip.reviewUrl || '' }));
      for (const pendingPassenger of pendingPassengers) {
        const name = typeof pendingPassenger === 'string' ? pendingPassenger : pendingPassenger.name;
        if (!isLikelyPersonName(name)) continue;
        const key = passengerKey(trip, name);
        const old = previous.get(key) || {};
        queue.push({
          key, name, tripId: trip.id, offerId: trip.offerId,
          date: trip.date, time: trip.time, origin: trip.origin, destination: trip.destination,
          offerUrl: trip.offerUrl,
          reviewUrl: pendingPassenger.reviewUrl || trip.reviewUrl || old.reviewUrl || '',
          profileUrl: old.profileUrl || '', reviews: old.reviews || [], suggestion: old.suggestion || '',
          traits: old.traits || [], status: old.status || 'pendente', reason: old.reason || '',
          rating: Number(old.rating) >= 1 && Number(old.rating) <= 5 ? Number(old.rating) : 5,
          approved: Boolean(old.approved), published: Boolean(old.published), publishedAt: old.publishedAt || ''
        });
      }
    }
    return queue;
  };