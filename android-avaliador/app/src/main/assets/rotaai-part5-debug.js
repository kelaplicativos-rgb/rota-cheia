(() => {
  'use strict';

  const VERSION = '0.5.0';
  const DEBUG_KEY = 'rotaaiDebugEventsV2';
  const MAX_EVENTS = 1800;
  const PERSIST_EVENTS = 900;
  const MAX_TEXT = 260;
  const STATE_KEYS = [
    'rotaaiAndroidReviewStateV5',
    'rotaaiAndroidReviewStateV4',
    'rotaaiAndroidReviewStateV3'
  ];

  if (window.RotaAiDebug?.version === VERSION) {
    window.RotaAiDebug.log('lifecycle', 'debug_resume', { reason: 'script reinjected' });
    return;
  }

  const safeUrl = (value = location.href) => {
    try {
      const url = new URL(value, location.href);
      return `${url.origin}${url.pathname}`;
    } catch {
      return String(value || '').slice(0, MAX_TEXT);
    }
  };

  const redact = (value = '') => String(value)
    .replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, '[email]')
    .replace(/(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[-\s]?\d{4}/g, '[telefone]')
    .replace(/\b(?:senha|password|token|cookie|authorization)\s*[:=]\s*\S+/gi, '$1=[oculto]')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, MAX_TEXT);

  const cssPath = (element) => {
    if (!(element instanceof Element)) return '';
    const parts = [];
    let node = element;
    for (let depth = 0; node && depth < 5; depth += 1) {
      let part = node.tagName.toLowerCase();
      if (node.id) {
        part += `#${CSS.escape(node.id)}`;
        parts.unshift(part);
        break;
      }
      const testId = node.getAttribute('data-testid');
      if (testId) part += `[data-testid="${redact(testId)}"]`;
      else if (node.getAttribute('role')) part += `[role="${redact(node.getAttribute('role'))}"]`;
      const parent = node.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter((child) => child.tagName === node.tagName);
        if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(' > ').slice(0, 500);
  };

  const describeElement = (element) => {
    if (!(element instanceof Element)) return null;
    const rect = element.getBoundingClientRect();
    const inputType = (element.getAttribute('type') || '').toLowerCase();
    const sensitive = inputType === 'password' || /senha|password|token/i.test(
      `${element.getAttribute('name') || ''} ${element.getAttribute('id') || ''} ${element.getAttribute('autocomplete') || ''}`
    );
    return {
      tag: element.tagName.toLowerCase(),
      path: cssPath(element),
      text: sensitive ? '[campo sensível]' : redact(element.textContent || element.getAttribute('aria-label') || ''),
      ariaLabel: sensitive ? '[campo sensível]' : redact(element.getAttribute('aria-label') || ''),
      testId: redact(element.getAttribute('data-testid') || ''),
      role: redact(element.getAttribute('role') || ''),
      href: element.matches('a[href]') ? safeUrl(element.href) : '',
      top: Math.round(rect.top),
      left: Math.round(rect.left),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      visible: rect.width > 2 && rect.height > 2
    };
  };

  let events = [];
  let sequence = 0;
  let stopped = false;
  let lastMutationAt = 0;

  try {
    const saved = JSON.parse(localStorage.getItem(DEBUG_KEY) || '[]');
    if (Array.isArray(saved)) events = saved.slice(-PERSIST_EVENTS);
    sequence = Number(events.at(-1)?.seq || 0);
  } catch {
    events = [];
  }

  const stateSummary = () => {
    for (const key of STATE_KEYS) {
      try {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        const state = JSON.parse(raw);
        return {
          key,
          status: redact(state.status || ''),
          busy: Boolean(state.busy),
          passengerCount: Array.isArray(state.passengers) ? state.passengers.length : 0,
          reviewActive: Boolean(state.review?.active),
          reviewStage: redact(state.review?.stage || ''),
          reviewIndex: Number(state.review?.index || 0),
          publishActive: Boolean(state.publish?.active),
          publishStage: redact(state.publish?.stage || ''),
          publishIndex: Number(state.publish?.index || 0)
        };
      } catch {
        // Estado inválido é registrado em outro evento quando necessário.
      }
    }
    return null;
  };

  const persist = () => {
    try {
      localStorage.setItem(DEBUG_KEY, JSON.stringify(events.slice(-PERSIST_EVENTS)));
    } catch {
      // Falha de quota não pode interromper a automação.
    }
  };

  const log = (category, action, details = {}, level = 'info') => {
    const event = {
      ts: new Date().toISOString(),
      seq: ++sequence,
      source: 'javascript',
      level,
      category: redact(category),
      action: redact(action),
      url: safeUrl(),
      title: redact(document.title || ''),
      stopped,
      state: stateSummary(),
      details
    };
    events.push(event);
    if (events.length > MAX_EVENTS) events.splice(0, events.length - MAX_EVENTS);
    if (sequence % 8 === 0 || level !== 'info') persist();
    try { window.RotaAiNative?.log?.(JSON.stringify(event)); } catch { /* ponte opcional */ }
    return event;
  };

  const logCandidates = (kind, candidates, chosen = null, extra = {}) => {
    const compact = (candidates || []).slice(0, 12).map((item, index) => ({
      index,
      score: Number(item.score || 0),
      exactNamed: Boolean(item.exactNamed),
      reviewContext: Boolean(item.reviewContext),
      top: Number(item.top ?? item.el?.getBoundingClientRect?.().top ?? 0),
      text: redact(item.text || item.el?.textContent || ''),
      target: describeElement(item.el)
    }));
    log('selector', `${kind}_candidates`, {
      ...extra,
      count: candidates?.length || 0,
      candidates: compact,
      chosen: describeElement(chosen?.el || chosen || null)
    });
  };

  const exportDebugLog = () => {
    persist();
    const header = {
      ts: new Date().toISOString(),
      source: 'javascript',
      type: 'rotaai-debug-header',
      version: VERSION,
      userAgent: redact(navigator.userAgent),
      url: safeUrl(),
      state: stateSummary(),
      eventCount: events.length
    };
    return [JSON.stringify(header), ...events.map((event) => JSON.stringify(event))].join('\n');
  };

  const stopAll = (reason = 'Stop acionado pelo usuário') => {
    stopped = true;
    log('control', 'stop_requested', { reason: redact(reason) }, 'warn');
    for (const key of STATE_KEYS) {
      try {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        const state = JSON.parse(raw);
        state.busy = false;
        state.status = 'Automação parada pelo usuário.';
        state.review = {
          ...(state.review || {}),
          active: false,
          autoStart: false,
          paused: true,
          stage: 'stopped',
          lastActionAt: Date.now()
        };
        state.publish = {
          ...(state.publish || {}),
          active: false,
          paused: true,
          stage: 'stopped',
          lastActionAt: Date.now()
        };
        localStorage.setItem(key, JSON.stringify(state));
      } catch (error) {
        log('control', 'stop_state_update_failed', { key, error: redact(error?.message || error) }, 'error');
      }
    }
    try { window.RotaAiNative?.status?.('STOP: automação interrompida.'); } catch { /* opcional */ }
    setTimeout(() => location.reload(), 120);
    return true;
  };

  const clearStop = (reason = 'automação iniciada') => {
    if (stopped) log('control', 'stop_cleared', { reason: redact(reason) });
    stopped = false;
  };

  const wrapApi = () => {
    const api = window.RotaAiAndroid;
    if (!api || api.__debugWrapped) return false;
    api.__debugWrapped = true;
    for (const method of ['startSmartReview', 'startPublish', 'moveReviewNext', 'processReviewFlow', 'processPublication', 'scanTrips', 'prepareAll']) {
      const original = api[method];
      if (typeof original !== 'function') continue;
      api[method] = function(...args) {
        if (method === 'startSmartReview' || method === 'startPublish') clearStop(method);
        if (stopped && !['startSmartReview', 'startPublish'].includes(method)) {
          log('automation', 'call_blocked_after_stop', { method, args: args.map((value) => redact(value)) }, 'warn');
          return undefined;
        }
        const startedAt = performance.now();
        log('automation', 'method_start', { method, args: args.map((value) => redact(value)) });
        try {
          const result = original.apply(this, args);
          if (result?.then) {
            return result.then((value) => {
              log('automation', 'method_done', { method, durationMs: Math.round(performance.now() - startedAt) });
              return value;
            }).catch((error) => {
              log('automation', 'method_failed', { method, durationMs: Math.round(performance.now() - startedAt), error: redact(error?.stack || error?.message || error) }, 'error');
              throw error;
            });
          }
          log('automation', 'method_done', { method, durationMs: Math.round(performance.now() - startedAt) });
          return result;
        } catch (error) {
          log('automation', 'method_failed', { method, durationMs: Math.round(performance.now() - startedAt), error: redact(error?.stack || error?.message || error) }, 'error');
          throw error;
        }
      };
    }
    api.stopAll = stopAll;
    api.exportDebugLog = exportDebugLog;
    api.getDebugLog = () => [...events];
    api.debugLog = log;
    log('lifecycle', 'api_wrapped', { version: api.version || '' });
    return true;
  };

  const originalClick = HTMLElement.prototype.click;
  HTMLElement.prototype.click = function(...args) {
    const target = describeElement(this);
    if (stopped && !this.closest?.('#rotaai-debug-controls')) {
      log('dom', 'programmatic_click_blocked', { target }, 'warn');
      return undefined;
    }
    log('dom', 'programmatic_click', { target });
    return originalClick.apply(this, args);
  };

  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target.closest('button, a[href], [role="button"], label, input, textarea') || event.target : null;
    log('user', 'click', { target: describeElement(target) });
  }, true);

  document.addEventListener('input', (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    log('user', 'input', {
      target: describeElement(target),
      valueLength: typeof target.value === 'string' ? target.value.length : Number(target.textContent?.length || 0)
    });
  }, true);

  addEventListener('error', (event) => {
    log('error', 'window_error', {
      message: redact(event.message || ''),
      filename: safeUrl(event.filename || ''),
      line: Number(event.lineno || 0),
      column: Number(event.colno || 0),
      stack: redact(event.error?.stack || '')
    }, 'error');
  });

  addEventListener('unhandledrejection', (event) => {
    log('error', 'unhandled_rejection', { reason: redact(event.reason?.stack || event.reason?.message || event.reason || '') }, 'error');
  });

  for (const method of ['pushState', 'replaceState']) {
    const original = history[method];
    if (original.__rotaAiDebugWrapped) continue;
    const wrapped = function(...args) {
      const before = safeUrl();
      const result = original.apply(this, args);
      log('navigation', method, { before, after: safeUrl() });
      return result;
    };
    wrapped.__rotaAiDebugWrapped = true;
    history[method] = wrapped;
  }
  addEventListener('popstate', () => log('navigation', 'popstate', { url: safeUrl() }));
  addEventListener('beforeunload', () => log('navigation', 'beforeunload', { url: safeUrl() }));
  addEventListener('pageshow', (event) => log('navigation', 'pageshow', { persisted: Boolean(event.persisted) }));

  const originalFetch = window.fetch;
  window.fetch = async function(input, init) {
    const url = safeUrl(typeof input === 'string' ? input : input?.url || '');
    const startedAt = performance.now();
    log('network', 'fetch_start', { method: redact(init?.method || 'GET'), url });
    try {
      const response = await originalFetch.apply(this, arguments);
      log('network', 'fetch_done', { url, status: response.status, durationMs: Math.round(performance.now() - startedAt) });
      return response;
    } catch (error) {
      log('network', 'fetch_failed', { url, durationMs: Math.round(performance.now() - startedAt), error: redact(error?.message || error) }, 'error');
      throw error;
    }
  };

  const observer = new MutationObserver((mutations) => {
    const current = Date.now();
    if (current - lastMutationAt < 900) return;
    lastMutationAt = current;
    const added = mutations.reduce((total, mutation) => total + mutation.addedNodes.length, 0);
    const removed = mutations.reduce((total, mutation) => total + mutation.removedNodes.length, 0);
    log('dom', 'mutation_batch', { mutationCount: mutations.length, added, removed });
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  window.RotaAiDebug = {
    version: VERSION,
    log,
    logCandidates,
    describeElement,
    exportDebugLog,
    stopAll,
    clearStop,
    isStopped: () => stopped
  };

  log('lifecycle', 'debug_installed', { readyState: document.readyState });
  wrapApi();
  const wrapTimer = setInterval(() => {
    if (wrapApi()) clearInterval(wrapTimer);
  }, 250);
  setTimeout(() => clearInterval(wrapTimer), 10000);
})();
