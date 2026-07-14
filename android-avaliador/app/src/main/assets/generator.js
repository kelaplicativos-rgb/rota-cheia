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
      phrases: [
        'chegou certinho no horário',
        'esteve no ponto na hora combinada',
        'cumpriu o horário sem atraso'
      ]
    },
    {
      id: 'educacao',
      patterns: [/\beducad[oa]s?\b/g, /\bcordial\w*\b/g, /\brespeitos[oa]s?\b/g, /\bboa educacao\b/g],
      phrases: [
        'tratou todo mundo bem',
        'teve um jeito bem educado',
        'foi tranquilo no convívio'
      ]
    },
    {
      id: 'comunicacao',
      patterns: [/\bcomunicativ[oa]s?\b/g, /\bboa conversa\b/g, /\bfacil comunicacao\b/g, /\bboa comunicacao\b/g, /\bpapo\b/g],
      phrases: [
        'conversou numa boa',
        'manteve uma conversa fácil',
        'se comunicou sem dificuldade'
      ]
    },
    {
      id: 'simpatia',
      patterns: [/\bsimpatic[oa]s?\b/g, /\bgente boa\b/g, /\bamavel\b/g],
      phrases: [
        'foi bem gente boa',
        'teve um jeito agradável',
        'foi de boa durante o caminho'
      ]
    },
    {
      id: 'tranquilidade',
      patterns: [/\btranquil[oa]s?\b/g, /\bviagem tranquila\b/g, /\bsem problema\b/g, /\bcorreu tudo bem\b/g],
      phrases: [
        'levou a viagem numa boa',
        'manteve o trajeto tranquilo',
        'contribuiu para uma viagem sem problemas'
      ]
    },
    {
      id: 'confiabilidade',
      patterns: [/\bconfiavel\b/g, /\bconfianca\b/g, /\bconforme combinado\b/g, /\bcumpriu.*combinado\b/g],
      phrases: [
        'cumpriu tudo o que combinamos',
        'seguiu certinho o que foi acertado',
        'manteve os combinados sem problema'
      ]
    },
    {
      id: 'prestatividade',
      patterns: [/\bsolicit[oa]s?\b/g, /\bprestativ[oa]s?\b/g, /\bajudou\b/g, /\bdispost[oa].*ajudar\b/g],
      phrases: [
        'ajudou quando foi preciso',
        'colaborou quando necessário',
        'deu uma força quando precisei'
      ]
    },
    {
      id: 'bom_humor',
      patterns: [/\bdivertid[oa]s?\b/g, /\bbem humorad[oa]s?\b/g, /\bbom humor\b/g, /\bdescontraid[oa]s?\b/g],
      phrases: [
        'manteve o clima descontraído',
        'teve bom humor durante o caminho',
        'deixou a viagem mais leve'
      ]
    },
    {
      id: 'gentileza',
      patterns: [/\bgentil\b/g, /\batencios[oa]s?\b/g, /\bdelicad[oa]s?\b/g],
      phrases: [
        'tratou todos com atenção',
        'teve bastante gentileza no trato',
        'foi gentil durante a viagem'
      ]
    },
    {
      id: 'boa_companhia',
      patterns: [/\bboa companhia\b/g, /\botima companhia\b/g, /\bcompanhia agradavel\b/g, /\bagradavel\b/g],
      phrases: [
        'foi uma boa companhia',
        'deixou a viagem agradável',
        'manteve uma presença tranquila no caminho'
      ]
    },
    {
      id: 'flexibilidade',
      patterns: [/\bflexivel\b/g, /\bcompreensiv[oa]s?\b/g, /\bse adaptou\b/g],
      phrases: [
        'lidou bem com os ajustes',
        'teve compreensão com as mudanças',
        'se adaptou ao que foi combinado'
      ]
    },
    {
      id: 'organizacao',
      patterns: [/\borganizad[oa]s?\b/g, /\btudo alinhado\b/g, /\bbem combinado\b/g],
      phrases: [
        'deixou tudo bem alinhado',
        'facilitou os combinados da viagem',
        'manteve os detalhes organizados'
      ]
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
      .sort((left, right) => (
        right.reviewHits - left.reviewHits
        || right.score - left.score
        || left.id.localeCompare(right.id)
      ));
  };

  const choosePhrase = (trait, seed, sourceNormalized) => {
    const ordered = trait.phrases
      .map((phrase, index) => ({ phrase, index, penalty: phrasePenalty(phrase, sourceNormalized) }))
      .sort((left, right) => left.penalty - right.penalty || left.index - right.index);
    const bestPenalty = ordered[0]?.penalty ?? 0;
    const best = ordered.filter((item) => item.penalty === bestPenalty);
    return best[seed % best.length].phrase;
  };

  const phrasePenalty = (phrase, sourceNormalized) => {
    const words = normalize(phrase).split(' ').filter((word) => word.length >= 5);
    return words.reduce((total, word) => total + (sourceNormalized.includes(word) ? 1 : 0), 0);
  };

  const joinPhrases = (phrases) => {
    if (phrases.length === 1) return phrases[0];
    if (phrases.length === 2) return `${phrases[0]} e ${phrases[1]}`;
    return `${phrases.slice(0, -1).join(', ')} e ${phrases.at(-1)}`;
  };

  const capitalize = (value) => value ? value.charAt(0).toUpperCase() + value.slice(1) : value;

  const generateEvaluation = ({ name = '', reviews = [] } = {}) => {
    const cleanReviews = [...new Set(reviews.map((item) => item?.trim()).filter(Boolean))];
    if (!cleanReviews.length) {
      return {
        ok: false,
        text: '',
        reason: 'Nenhuma avaliação textual encontrada no perfil.',
        traits: []
      };
    }

    const sourceNormalized = normalize(cleanReviews.join(' '));
    const traits = scoreTraits(cleanReviews).slice(0, 2);
    if (!traits.length) {
      return {
        ok: false,
        text: '',
        reason: 'As avaliações encontradas não trazem qualidades claras para reformular sem inventar.',
        traits: []
      };
    }

    const seedBase = hashString(`${name}|${sourceNormalized}`);
    const phrases = traits.map((trait, index) => choosePhrase(trait, seedBase + index * 31, sourceNormalized));
    const prefix = name?.trim() ? `${name.trim()} ` : '';
    let text = `${prefix}${joinPhrases(phrases)}.`;

    if (RECOMMENDATION_PATTERN.test(sourceNormalized)) {
      const recommendation = seedBase % 2 === 0 ? 'Recomendo.' : 'Indico.';
      text += ` ${recommendation}`;
    }

    return {
      ok: true,
      text: capitalize(text),
      reason: '',
      traits: traits.map((trait) => trait.id)
    };
  };

  globalThis.RotaAiGenerator = {
    normalize,
    scoreTraits,
    generateEvaluation
  };
})();
