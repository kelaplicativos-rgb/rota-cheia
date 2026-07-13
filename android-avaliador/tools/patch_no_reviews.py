from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "src" / "main" / "assets"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Trecho não encontrado: {label}")
    return text.replace(old, new, 1)


part2_path = ASSETS / "rotaai-part2.js"
part2 = part2_path.read_text(encoding="utf-8")

old_matcher = r'''  const profileDocumentMatchesPassenger = (doc, passenger, reviews) => {
    if (!reviews.length) return false;
    const page = normalize(safeText(doc.body || doc.documentElement));
    const fullName = normalize(passenger.name);
    const firstName = fullName.split(' ')[0];
    return Boolean(fullName && (page.includes(fullName) || (firstName && page.includes(firstName))));
  };'''

new_matcher = r'''  const profileDocumentMatchesPassenger = (doc, passenger, reviews, sourceUrl = '') => {
    const page = normalize(safeText(doc.body || doc.documentElement));
    const fullName = normalize(passenger.name);
    const firstName = fullName.split(' ')[0];
    const nameMatches = Boolean(fullName && (page.includes(fullName) || (firstName && page.includes(firstName))));

    // profile_without_reviews_allowed:
    // o ID do perfil vem diretamente do convite /ratings/ daquele passageiro.
    // Uma resposta 200 em /user/show/ID ou /user/show/ID/reviews confirma o perfil,
    // mesmo quando a pessoa ainda não possui avaliações anteriores.
    const participantId = ratingParticipantIdFromUrl(passenger.reviewUrl || location.href);
    let exactDerivedProfile = false;
    try {
      const pathname = new URL(sourceUrl || '', location.href).pathname.toLowerCase();
      const escapedId = participantId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').toLowerCase();
      exactDerivedProfile = Boolean(participantId
        && new RegExp(`^/user/show/${escapedId}(?:/reviews)?/?$`, 'i').test(pathname));
    } catch { /* URL inválida */ }

    return Boolean(nameMatches || exactDerivedProfile);
  };'''

part2 = replace_once(part2, old_matcher, new_matcher, "profileDocumentMatchesPassenger")
part2 = replace_once(
    part2,
    "const matches = profileDocumentMatchesPassenger(candidateDoc, passenger, candidateReviews);",
    "const matches = profileDocumentMatchesPassenger(candidateDoc, passenger, candidateReviews, candidateUrl);",
    "profileDocumentMatchesPassenger candidateUrl",
)
part2_path.write_text(part2, encoding="utf-8")


generator_path = ASSETS / "generator.js"
generator = generator_path.read_text(encoding="utf-8")

old_empty = r'''    if (!cleanReviews.length) {
      return {
        ok: false,
        text: '',
        reason: 'Nenhuma avaliação textual encontrada no perfil.',
        traits: []
      };
    }'''

new_empty = r'''    if (!cleanReviews.length) {
      const passengerName = name?.trim();
      const text = passengerName
        ? `Viajei com ${passengerName} e recomendo para futuras caronas.`
        : 'Viajamos juntos e recomendo para futuras caronas.';
      return {
        ok: true,
        text,
        reason: 'Perfil sem avaliações anteriores. Rascunho neutro criado para sua revisão.',
        traits: ['rascunho_neutro'],
        source: 'profile_without_reviews'
      };
    }'''

generator = replace_once(generator, old_empty, new_empty, "fallback sem avaliações")
generator_path.write_text(generator, encoding="utf-8")

print("patch_no_reviews: ok")
