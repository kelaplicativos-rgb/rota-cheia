const fs = require('fs');
const path = require('path');

const assets = path.join(__dirname, '..', 'app', 'src', 'main', 'assets');
const source = [1, 2, 3, 4]
  .map((part) => fs.readFileSync(path.join(assets, `rotaai-part${part}.js`), 'utf8'))
  .join('\n');
global.window = global;
global.__ROTA_AI_TEST_ONLY__ = true;
eval(source);

const api = global.RotaAiPendingReviewTest;
if (!api) throw new Error('Gancho de teste do filtro pendente não foi carregado.');

const screenText = [
  'Faça uma avaliação! Avalie sua experiência de viagem com Raquel.',
  'Faça uma avaliação! Avalie sua experiência de viagem com Sofia.',
  'Faça uma avaliação! Avalie sua experiência de viagem com Erick.'
].join(' ');
const names = api.pendingReviewNamesFromText(screenText);
if (JSON.stringify(names) !== JSON.stringify(['Raquel', 'Sofia', 'Erick'])) {
  throw new Error(`Esperado Raquel, Sofia e Erick; recebido ${JSON.stringify(names)}`);
}

const alreadyReviewed = 'Passageiros: Raquel, Sofia e Erick. Você avaliou Raquel. Avaliação publicada.';
if (api.pendingReviewNamesFromText(alreadyReviewed).length !== 0) {
  throw new Error('Passageiro já avaliado entrou na fila.');
}
if (!api.hasCompletedReviewLabel(alreadyReviewed)) {
  throw new Error('Status concluído não foi reconhecido.');
}

const genericPassengerList = 'Fazer avaliação. Passageiros: Ana, Bia e Caio.';
if (api.pendingReviewNamesFromText(genericPassengerList).length !== 0) {
  throw new Error('Lista geral de passageiros foi tratada como pendência individual.');
}
if (!api.hasPendingReviewLabel(screenText)) {
  throw new Error('Convite individual de avaliação pendente não foi reconhecido.');
}

console.log('pending-review-filter: ok');
