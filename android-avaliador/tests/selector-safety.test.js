const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const part2 = fs.readFileSync(path.join(root, 'app', 'src', 'main', 'assets', 'rotaai-part2.js'), 'utf8');
const part4 = fs.readFileSync(path.join(root, 'app', 'src', 'main', 'assets', 'rotaai-part4.js'), 'utf8');
const source = `${part2}\n${part4}`;

const required = [
  'exact-rating-v2',
  'isRatingLink && exactNamed && ownReviewPrompt',
  '/rides\\/offer\\/edit',
  '/dashboard\\/profile',
  'profileDocumentMatchesPassenger',
  '__rotaAiPassengerAnalysisLocks',
  'return scored[0]?.nameScore >= 2 ? scored[0].link.href : \'\';'
];

for (const marker of required) {
  if (!source.includes(marker)) {
    throw new Error(`Proteção obrigatória ausente: ${marker}`);
  }
}

if (source.includes("return explicit.length === 1 ? explicit[0].link.href : '';")) {
  throw new Error('Fallback de perfil genérico voltou a ser aceito.');
}

console.log('selector-safety: ok');
