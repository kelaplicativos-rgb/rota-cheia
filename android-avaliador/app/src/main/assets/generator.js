(() => {
  'use strict';

  const normalize = (value = '') => value
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();

  const hashString = (value) => {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  };

  const TRAITS = [
    {
      id: 'pontualidade',
      patterns: [/\bpontual\w*\b/g, /\bno horario\b/g, /\bhorario combinado\b/g, /\bchegou.*horario\b/g],
      phrases: ['chegou no horário combinado', 'cumpriu certinho o horário', 'esteve no ponto na hora acertada']
    },
    {
      id: 'educacao',
      patterns: [/\beducad[oa]s?\b/g, /\bcordial\w*\b/g, /\brespeitos[oa]s?\b/g, /\bboa educacao\b/g],
      phrases: ['teve uma postura cordial', 'tratou todos com consideração', 'foi correto no convívio']
    },
    {
      id: 'comunicacao',
      patterns: [/\bcomunicativ[oa]s?\b/g, /\bboa conversa\b/g, /\bfacil comunicacao\b/g, /\bboa comunicacao\b/g, /\bpapo\b/g],
      phrases: ['conversou de forma natural', 'manteve contato com facilidade', 'teve um bom papo durante o caminho']
    },
    {
      id: 'simpatia',
      patterns: [/\bsimpatic[oa]s?\b/g, /\bgente boa\b/g, /\bamavel\b/g],
      phrases: ['foi uma companhia leve', 'teve um jeito bem agradável', 'foi de boa durante o percurso']
    },
    {
      id: 'tranquilidade',
      patterns: [/\btranquil[oa]s?\b/g, /\bviagem tranquila\b/g, /\bsem problema\b/g, /\bcorreu tudo bem\b/g],
      phrases: ['contribuiu para um trajeto sem problemas', 'manteve a viagem bem sossegada', 'manteve o clima tranquilo']
    },
    {
      id: 'confiabilidade',
      patterns: [/\bconfiavel\b/g, /\bconfianca\b/g, /\bconforme combinado\b/g, /\bcumpriu.*combinado\b/g],
      phrases: ['cumpriu o que ficou acertado', 'passou segurança nos combinados', 'manteve tudo conforme o acerto']
    },
    {
      id: 'prestatividade',
      patterns: [/\bsolicit[oa]s?\b/g, /\bprestativ[oa]s?\b/g, /\bajudou\b/g, /\bdispost[oa].*ajudar\b/g],
      phrases: ['esteve disposto a ajudar', 'foi atencioso quando precisei', 'colaborou sempre que necessário']
    },
    {
      id: 'bom_humor',
      patterns: [/\bdivertid[oa]s?\b/g, /\bbem humorad[oa]s?\b/g, /\bbom humor\b/g, /\bdescontraid[oa]s?\b/g],
      phrases: ['manteve um clima descontraído', 'teve bom humor durante o caminho', 'deixou o percurso mais leve']
    },
    {
      id: 'gentileza',
      patterns: [/\bgentil\b/g, /\batencios[oa]s?\b/g, /\bdelicad[oa]s?\b/g],
      phrases: ['foi atencioso durante o percurso', 'teve consideração durante o percurso', 'agiu com muita gentileza']
    },
    {
      id: 'boa_companhia',
      patterns: [/\bboa companhia\b/g, /\botima companhia\b/g, /\bcompanhia agradavel\b/g, /\bagradavel\b/g],
      phrases: ['foi uma boa companhia de viagem', 'deixou o percurso agradável', 'manteve uma presença tranquila no caminho']
    },
    {
      id: 'flexibilidade',
      patterns: [/\bflexivel\b/g, /\bcompreensiv[oa]s?\b/g, /\bse adaptou\b/g],
      phrases: ['lidou bem com os ajustes combinados', 'teve compreensão com os detalhes da viagem', 'foi flexível quando necessário']
    },
    {
      id: 'organizacao',
      patterns: [/\borganizad[oa]s?\b/g, /\btudo alinhado\b/g, /\bbem combinado\b/g],
      phrases: ['manteve os detalhes bem alinhados', 'deixou os combinados bem organizados', 'facilitou a organização da viagem']
    }
  ];

  const RECOMMENDATION_PATTERN = /\b(recomendo|recomendad[oa]s?|indico|indicad[oa]s?|super recomendo)\b/;

  const scoreTraits = (reviews) => {
    const normalizedReviews = reviews.map(normalize).filter(Boolean);
    return TRAITS.map((trait) => {
      let score = 0;
      let reviewHits = 0;
      for (const review of normalizedReviews) {
        let foundInReview = false;
        for (const pattern of trait.patterns) {
          pattern.lastIndex = 0;
          const matches = review.match(pattern);
          if (matches?.length) {
            score += matches.length;
            foundInReview = true;
          }
        }
        if (foundInReview) reviewHits += 1;
      }
      return { ...trait, score, reviewHits };
    })
      .filter((trait) => trait.score > 0)
      .sort((left, right) => right.reviewHits - left.reviewHits || right.score - left.score || left.id.localeCompare(right.id));
  };

  const phrasePenalty = (phrase, sourceNormalized) => {
    const words = normalize(phrase).split(' ').filter((word) => word.length >= 5);
    return words.reduce((total, word) => total + (sourceNormalized.includes(word) ? 1 : 0), 0);
  };

  const choosePhrase = (trait, seed, sourceNormalized) => {
    const ordered = trait.phrases
      .map((phrase, index) => ({ phrase, index, penalty: phrasePenalty(phrase, sourceNormalized) }))
      .sort((left, right) => left.penalty - right.penalty || left.index - right.index);
    const bestPenalty = ordered[0]?.penalty ?? 0;
    const best = ordered.filter((item) => item.penalty === bestPenalty);
    return best[seed % best.length].phrase;
  };

  const joinPhrases = (phrases) => {
    if (phrases.length === 1) return phrases[0];
    if (phrases.length === 2) return `${phrases[0]} e ${phrases[1]}`;
    return `${phrases.slice(0, -1).join(', ')} e ${phrases.at(-1)}`;
  };

  const capitalize = (value) => value ? value.charAt(0).toUpperCase() + value.slice(1) : value;

  const generateEvaluation = ({ name = '', reviews = [] } = {}) => {
    const cleanReviews = [...new Set(reviews.map((item) => item?.trim()).filter(Boolean))];
    if (!cleanReviews.length) return { ok: false, text: '', reason: 'Nenhuma avaliação textual encontrada no perfil.', traits: [] };

    const sourceNormalized = normalize(cleanReviews.join(' '));
    const traits = scoreTraits(cleanReviews).slice(0, 3);
    if (!traits.length) {
      return { ok: false, text: '', reason: 'As avaliações não trazem qualidades claras para reformular sem inventar.', traits: [] };
    }

    const seedBase = hashString(`${name}|${sourceNormalized}`);
    const phrases = traits.map((trait, index) => choosePhrase(trait, seedBase + index * 31, sourceNormalized));
    const prefix = name?.trim() ? `${name.trim()} ` : '';
    let text = `${prefix}${joinPhrases(phrases)}.`;
    if (RECOMMENDATION_PATTERN.test(sourceNormalized)) text += seedBase % 2 === 0 ? ' Recomendo.' : ' Indico para outras caronas.';
    return { ok: true, text: capitalize(text), reason: '', traits: traits.map((trait) => trait.id) };
  };

  globalThis.RotaAiGenerator = { normalize, scoreTraits, generateEvaluation };
})();
