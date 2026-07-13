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
      const score = profileHrefScore(href);
      const imageNames = [...anchor.querySelectorAll('img[alt]')]
        .map((img) => cleanName(img.getAttribute('alt') || '')).filter(isLikelyPersonName);
      const textName = cleanName(safeText(anchor));
      const contextNode = anchor.closest('article, li, section, [data-testid], div') || anchor.parentElement;
      const contextText = safeText(contextNode);
      const names = unique([...imageNames, textName].filter(isLikelyPersonName));
      const isSameSite = /^https:\/\/([a-z0-9-]+\.)?blablacar\.com(\.br)?\//i.test(href);
      const isNavigation = /\/(rides\/offer|search|login|signup|carpool|bus|help|support)(?:[/?#]|$)/i.test(href);
      const reviewScore = /avalia[cç][oõ]es|coment[aá]rios|opini[oõ]es|feedback|estrela|rating|reviews?/i.test(contextText) ? 4 : 0;
      if (!score || !isSameSite || isNavigation) return;
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

    if (scored[0]?.nameScore >= 2) return scored[0].link.href;
    const strong = scored.filter((item) => item.link.score >= 1 && item.link.reviewScore > 0);
    if (strong.length === 1) return strong[0].link.href;
    const explicit = scored.filter((item) => item.link.score >= 1);
    return explicit.length === 1 ? explicit[0].link.href : '';
  };'''

part2 = replace_section(
    part2,
    "  const bestProfileForPassenger = (passenger, links) => {",
    "  const looksLikeReviewText =",
    best_profile,
    "bestProfileForPassenger",
)

first_pending = r'''  const pendingActionCandidates = (passengerName = '') => {
    const normalizedName = normalize(passengerName);
    const firstName = normalizedName.split(' ')[0];
    return [...document.querySelectorAll('a[href], button, [role="button"]')]
      .filter((element) => visible(element) && !element.closest(`#${ROOT_ID}`))
      .map((element) => {
        const textRaw = safeText(element);
        const text = normalize(`${textRaw} ${element.getAttribute('aria-label') || ''}`);
        const contextNode = element.closest('article, li, section, [data-testid], div') || element.parentElement;
        const contextRaw = safeText(contextNode);
        const context = normalize(contextRaw);
        const detectedNames = pendingReviewNamesFromText(`${textRaw} ${contextRaw}`);
        const exactNamed = Boolean(normalizedName && detectedNames.some((name) => normalize(name) === normalizedName));
        const nameMention = Boolean(normalizedName && (text.includes(normalizedName) || context.includes(normalizedName)
          || (firstName && (text.includes(firstName) || context.includes(firstName)))));
        const explicitPrompt = /avalie sua experiencia(?: de viagem)? com/.test(`${text} ${context}`);
        const reviewContext = explicitPrompt || /faca uma avaliacao|fazer avaliacao|avaliar passageir|deixar avaliacao/.test(`${text} ${context}`);
        const rect = element.getBoundingClientRect();
        let score = reviewContext ? 30 : -100;
        if (explicitPrompt) score += 35;
        if (exactNamed) score += 120;
        else if (nameMention) score += 35;
        if (detectedNames.length === 1) score += 12;
        if (detectedNames.length > 1) score -= 70;
        if (/excluir|cancelar|denunciar|editar viagem/.test(text)) score -= 120;
        score -= Math.min(25, text.length / 30);
        return {
          el: element,
          score,
          exactNamed,
          reviewContext,
          top: rect.top,
          text: textRaw,
          detectedNames
        };
      })
      .filter((item) => item.score > 0)
      .sort((left, right) => right.score - left.score || right.top - left.top || left.text.length - right.text.length);
  };

  const findFirstPendingAction = () => {
    const candidates = pendingActionCandidates('');
    const chosen = candidates[0] || null;
    window.RotaAiDebug?.logCandidates?.('first_pending_action', candidates, chosen, {
      rule: 'card-below-v1: em empate escolhe o card visível mais abaixo e com texto mais específico'
    });
    return chosen?.el || null;
  };'''

part2 = replace_section(
    part2,
    "  const findFirstPendingAction = () => {",
    "  const startSmartReview =",
    first_pending,
    "findFirstPendingAction",
)

part2_path.write_text(part2, encoding="utf-8")

part4_path = ASSETS / "rotaai-part4.js"
part4 = part4_path.read_text(encoding="utf-8")

passenger_action = r'''  const findPassengerAction = (passenger) => {
    const candidates = pendingActionCandidates(passenger.name);
    const chosen = candidates[0] || null;
    window.RotaAiDebug?.logCandidates?.('passenger_action', candidates, chosen, {
      passenger: passenger.name,
      rule: 'card-below-v1: exige contexto de avaliação, prioriza o nome exato e o card individual mais abaixo'
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
