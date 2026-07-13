const fs = require('fs');
const path = require('path');

const generatorSource = fs.readFileSync(
  path.join(__dirname, '..', 'app', 'src', 'main', 'assets', 'generator.js'),
  'utf8'
);

global.window = global;
eval(generatorSource);

const result = global.RotaAiGenerator.generateEvaluation({
  name: 'Sofia',
  reviews: []
});

if (!result.ok) throw new Error('Perfil sem avaliações precisa gerar rascunho revisável.');
if (result.text !== 'Viajei com Sofia e recomendo para futuras caronas.') {
  throw new Error(`Texto neutro inesperado: ${result.text}`);
}
if (!result.traits.includes('rascunho_neutro')) {
  throw new Error('O rascunho precisa ser identificado como neutro.');
}
if (!/sua revisão/i.test(result.reason)) {
  throw new Error('A interface precisa informar que o texto exige revisão.');
}

const automationSource = fs.readFileSync(
  path.join(__dirname, '..', 'app', 'src', 'main', 'assets', 'rotaai-part2.js'),
  'utf8'
);

if (!automationSource.includes('profile_without_reviews_allowed')) {
  throw new Error('O perfil exato sem avaliações ainda não é aceito pela automação.');
}
if (!automationSource.includes('candidateReviews, candidateUrl')) {
  throw new Error('A URL exata do perfil não está sendo usada para confirmar a identidade.');
}

console.log('profile-without-reviews: ok', result.text);
