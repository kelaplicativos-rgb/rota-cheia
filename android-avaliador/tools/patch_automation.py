from __future__ import annotations

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

collect_profiles = r'''  const collectProfileLinks = (doc, baseUrl) => {
    const links = [];
    const anchors = [...doc.querySelectorAll('a[href]')];
    anchors.forEach((anchor, domIndex) => {
      const href = absoluteUrl(anchor.getAttribute('href') || '', baseUrl);
      let pathname = '';
      try { pathname = new URL(href).pathname.toLowerCase(); } catch { return; }
      const score = profileHrefScore(href);
      const imageNames = [...anchor.querySelectorAll('img[alt]')]
        .map((img) => cleanName(img.getAttribute('alt') || '')).filter(isLikelyPersonName);
      const textName = cleanName(safeText(anchor));
      const contextNode = anchor.closest('article, li, section, [data-testid], div') || anchor.parentElement;
      const contextText = safeText(contextNode);
      const names = unique([...imageNames, textName].filter(isLikelyPersonName));
      const isSameSite = /^https:\/\/([a-z0-9-]+\.)?blablacar\.com(\.br)?\//i.test(href);
      const isOwnProfileMenu = /^\/dashboard\/profile(?:\/menu)?(?:\/|$)/i.test(pathname);
      const isNavigation = /^\/(?:rides|ratings|search|login|signup|carpool|bus|help|support|dashboard)(?:\/|$)/i.test(pathname);
      const reviewScore = /avalia[cç][oõ]es|coment[aá]rios|opini[oõ]es|feedback|estrela|rating|reviews?/i.test(contextText) ? 4 : 0;
      if (!score || !isSameSite || isOwnProfileMenu || isNavigation) return;
      links.push({ href, names, score, reviewScore, domIndex, contextText: contextText.slice(0, 260) });
    });
    const deduped = new Map();
    for (const link of links) {
      if (!link.href) continue;
      const old = deduped.get(link.href);
      if (!old
          || link.reviewScore > old.reviewScore
          || (link.reviewScore === old.reviewScore && link.score > old.score)
          || (link.reviewScore === old.reviewScore && link.score === old.score && link.domIndex > old.domIndex)) {
        deduped.set(link.href, link);
      }
    }
    const result = [...deduped.values()];
    window.RotaAiDebug?.log?.('profile', 'profile_links_collected', {
      baseUrl: (() => { try { const u = new URL(baseUrl); return `${u.origin}${u.pathname}`; } catch { return ''; } })(),
      count: result.length,
      links: result.slice(0, 12).map((link) => ({
        href: (() => { try { const u = new URL(link.href); return `${u.origin}${u.pathname}`; } catch { return ''; } })(),
        names: link.names,
        score: link.score,
        reviewScore: link.reviewScore,
        domIndex: link.domIndex,
        context: link.contextText
      }))
    });
    return result;
  };'''

part2 = replace_section(
    part2,
    "  const collectProfileLinks = (doc, baseUrl) => {",
    "  const nameSimilarity =",
    collect_profiles,
    "collectProfileLinks",
)

best_profile = r'''  const bestProfileForPassenger = (passenger, links) => {
    const scored = links.map((link) => {
      const nameScore = Math.max(0, ...link.names.map((candidate) => nameSimilarity(passenger.name, candidate)));
      const totalScore = nameScore * 100 + Number(link.reviewScore || 0) * 20 + Number(link.score || 0) * 5
        + Math.min(Number(link.domIndex || 0), 999) / 1000;
      return { link, nameScore, totalScore };
    }).sort((left, right) => right.totalScore - left.totalScore);

    window.RotaAiDebug?.log?.('profile', 'profile_candidate_ranking', {
      passenger: passenger.name,
      candidates: scored.slice(0, 12).map((item) => ({
        href: (() => { try { const u = new URL(item.link.href); return `${u.origin}${u.pathname}`; } catch { return ''; } })(),
        names: item.link.names,
        nameScore: item.nameScore,
        reviewScore: item.link.reviewScore,
        domIndex: item.link.domIndex,
        totalScore: item.totalScore,
        context: item.link.contextText
      }))
    });

    // Nunca usa um perfil genérico ou o menu da própria conta como fallback.
    // O perfil precisa corresponder ao nome do passageiro.
    return scored[0]?.nameScore >= 2 ? scored[0].link.href : '';
  };'''

part2 = replace_section(
    part2,
    "  const bestProfileForPassenger = (passenger, links) => {",
    "  const looksLikeReviewText =",
    best_profile,
    "bestProfileForPassenger",
)

analysis_section = r'''  const passengerAnalysisLocks = globalThis.__rotaAiPassengerAnalysisLocks || new Map();
  globalThis.__rotaAiPassengerAnalysisLocks = passengerAnalysisLocks;

  const ratingParticipantIdFromUrl = (value = location.href) => {
    try {
      const match = new URL(value).pathname.match(/^\/ratings\/[^/]+\/([^/?#]+)/i);
      return match?.[1] || '';
    } catch { return ''; }
  };

  const derivedProfileUrls = (passenger) => {
    const participantId = ratingParticipantIdFromUrl(passenger.reviewUrl || location.href);
    if (!participantId) return [];
    const origin = location.origin;
    return unique([
      `${origin}/member/profile/${participantId}`,
      `${origin}/members/${participantId}`,
      `${origin}/user/${participantId}`,
      `${origin}/users/${participantId}`,
      `${origin}/profile/${participantId}`
    ]);
  };

  const profileDocumentMatchesPassenger = (doc, passenger, reviews) => {
    if (!reviews.length) return false;
    const page = normalize(safeText(doc.body || doc.documentElement));
    const fullName = normalize(passenger.name);
    const firstName = fullName.split(' ')[0];
    return Boolean(fullName && (page.includes(fullName) || (firstName && page.includes(firstName))));
  };

  const analyzePassenger = async (passenger, currentDoc = null) => {
    const lockKey = passenger.key || normalize(passenger.name);
    if (passengerAnalysisLocks.has(lockKey)) {
      window.RotaAiDebug?.log?.('profile', 'analysis_join_existing', { passenger: passenger.name });
      return passengerAnalysisLocks.get(lockKey);
    }

    const task = (async () => {
      passenger.status = 'analisando'; passenger.reason = ''; render();
      try {
        let profileDoc = currentDoc;
        let reviews = profileDoc ? extractReviews(profileDoc) : [];

        if (!profileDocumentMatchesPassenger(profileDoc || document, passenger, reviews)) {
          profileDoc = null;
          reviews = [];
        }

        const candidates = unique([
          passenger.profileUrl || '',
          ...derivedProfileUrls(passenger)
        ]).filter(Boolean).filter((url) => !/\/dashboard\/profile(?:\/menu)?(?:[/?#]|$)/i.test(url));

        for (const candidateUrl of candidates) {
          if (profileDoc) break;
          window.RotaAiDebug?.log?.('profile', 'profile_probe_start', {
            passenger: passenger.name,
            url: (() => { try { const u = new URL(candidateUrl); return `${u.origin}${u.pathname}`; } catch { return ''; } })()
          });
          try {
            const candidateDoc = await fetchDocument(candidateUrl);
            const candidateReviews = extractReviews(candidateDoc);
            const matches = profileDocumentMatchesPassenger(candidateDoc, passenger, candidateReviews);
            window.RotaAiDebug?.log?.('profile', 'profile_probe_result', {
              passenger: passenger.name,
              matches,
              reviewCount: candidateReviews.length,
              url: (() => { try { const u = new URL(candidateUrl); return `${u.origin}${u.pathname}`; } catch { return ''; } })()
            });
            if (matches) {
              passenger.profileUrl = candidateUrl;
              profileDoc = candidateDoc;
              reviews = candidateReviews;
            }
          } catch (error) {
            window.RotaAiDebug?.log?.('profile', 'profile_probe_failed', {
              passenger: passenger.name,
              error: error?.message || String(error),
              url: (() => { try { const u = new URL(candidateUrl); return `${u.origin}${u.pathname}`; } catch { return ''; } })()
            }, 'warn');
          }
        }

        if (!profileDoc) throw new Error('Perfil do passageiro não identificado com segurança.');
        passenger.reviews = reviews;
        const generated = window.RotaAiGenerator.generateEvaluation({ name: passenger.name, reviews });
        passenger.suggestion = generated.text;
        passenger.traits = generated.traits;
        passenger.reason = generated.reason;
        passenger.status = generated.ok ? 'pronto' : 'sem_base';
        if (!generated.ok) passenger.approved = false;
        return generated.ok;
      } catch (error) {
        passenger.status = 'erro'; passenger.reason = error?.message || 'Falha ao ler o perfil.';
        passenger.approved = false;
        return false;
      }
    })();

    passengerAnalysisLocks.set(lockKey, task);
    try { return await task; }
    finally { passengerAnalysisLocks.delete(lockKey); }
  };'''

part2 = replace_section(
    part2,
    "  const analyzePassenger = async (passenger, currentDoc = null) => {",
    "  const preparePassengerFromCurrentPage =",
    analysis_section,
    "analyzePassenger",
)

prepare_current = r'''  const preparePassengerFromCurrentPage = async (passenger) => {
    if (passenger.suggestion?.trim()) return true;
    if (!passenger.profileUrl) {
      passenger.profileUrl = bestProfileForPassenger(passenger, collectProfileLinks(document, location.href));
    }
    return analyzePassenger(passenger, document);
  };'''

part2 = replace_section(
    part2,
    "  const preparePassengerFromCurrentPage = async (passenger) => {",
    "  const generateAll =",
    prepare_current,
    "preparePassengerFromCurrentPage",
)

first_pending = r'''  const pendingActionCandidates = (passengerName = '') => {
    const normalizedName = normalize(passengerName);
    const specificPassenger = Boolean(normalizedName);
    return [...document.querySelectorAll('a[href]')]
      .filter((element) => visible(element) && !element.closest(`#${ROOT_ID}`))
      .map((element) => {
        const textRaw = safeText(element);
        const text = normalize(`${textRaw} ${element.getAttribute('aria-label') || ''}`);
        const href = absoluteUrl(element.getAttribute('href') || '', location.href);
        let pathname = '';
        try { pathname = new URL(href).pathname; } catch { /* URL inválida */ }
        const contextNode = element.closest('article, li, section, [data-testid], div') || element.parentElement;
        const contextRaw = safeText(contextNode);
        const ownDetectedNames = pendingReviewNamesFromText(textRaw);
        const exactNamed = Boolean(specificPassenger
          && ownDetectedNames.some((name) => normalize(name) === normalizedName));
        const ownReviewPrompt = hasPendingReviewLabel(textRaw);
        const tripHasPending = hasPendingReviewLabel(contextRaw);
        const isRatingLink = /^\/ratings\/[^/]+\/[^/?#]+(?:\/|$)/i.test(pathname);
        const isTripSummaryLink = /^\/rides\/offer\/?$/i.test(pathname);
        const blocked = /\/rides\/offer\/edit(?:\/|$)|\/dashboard\/profile(?:\/menu)?(?:\/|$)/i.test(pathname);
        const valid = !blocked && (specificPassenger
          ? (isRatingLink && exactNamed && ownReviewPrompt)
          : (isTripSummaryLink && tripHasPending));
        const rect = element.getBoundingClientRect();
        let score = valid ? 1000 : -1000;
        if (specificPassenger && exactNamed) score += 500;
        if (isRatingLink) score += 200;
        if (!specificPassenger && isTripSummaryLink) score += 100;
        score -= Math.min(25, text.length / 30);
        return {
          el: element,
          score,
          exactNamed,
          reviewContext: specificPassenger ? ownReviewPrompt : tripHasPending,
          top: rect.top,
          text: textRaw,
          detectedNames: ownDetectedNames,
          href,
          valid
        };
      })
      .filter((item) => item.valid)
      .sort((left, right) => right.score - left.score || right.top - left.top || left.text.length - right.text.length);
  };

  const findFirstPendingAction = () => {
    const candidates = pendingActionCandidates('');
    const chosen = candidates[0] || null;
    window.RotaAiDebug?.logCandidates?.('first_pending_action', candidates, chosen, {
      rule: 'trip-summary-v2: somente /rides/offer cujo próprio card indica avaliação pendente'
    });
    return chosen?.el || null;
  };'''

part2 = replace_section(
    part2,
    "  const pendingActionCandidates = (passengerName = '') => {",
    "  const startSmartReview =",
    first_pending,
    "pendingActionCandidates/findFirstPendingAction",
)

part2_path.write_text(part2, encoding="utf-8")

part4_path = ASSETS / "rotaai-part4.js"
part4 = part4_path.read_text(encoding="utf-8")

passenger_action = r'''  const findPassengerAction = (passenger) => {
    const candidates = pendingActionCandidates(passenger.name);
    const chosen = candidates[0] || null;
    window.RotaAiDebug?.logCandidates?.('passenger_action', candidates, chosen, {
      passenger: passenger.name,
      rule: 'exact-rating-v2: somente link /ratings/ com convite individual e nome exato do passageiro'
    });
    return chosen?.el || null;
  };'''

part4 = replace_section(
    part4,
    "  const findPassengerAction = (passenger) => {",
    "  const navigateToPassengerTrip =",
    passenger_action,
    "findPassengerAction",
)

part4_path.write_text(part4, encoding="utf-8")

print("patch_automation: ok")
