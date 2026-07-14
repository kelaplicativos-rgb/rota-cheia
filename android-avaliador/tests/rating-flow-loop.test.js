const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const part2 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part2.js'), 'utf8');
const part3 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part3.js'), 'utf8');
const part4 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part4.js'), 'utf8');

const ratingFlowKey = (value) => {
  const match = new URL(value).pathname.match(/^\/ratings\/([^/]+)\/([^/?#]+)/i);
  return match ? `${match[1]}::${match[2]}` : '';
};

const base = 'https://www.blablacar.com.br/ratings/ride-123/user-456';
assert.strictEqual(ratingFlowKey(base), ratingFlowKey(`${base}/intro`));
assert.strictEqual(ratingFlowKey(base), ratingFlowKey(`${base}/details?step=2`));
assert.notStrictEqual(ratingFlowKey(base), ratingFlowKey('https://www.blablacar.com.br/ratings/ride-123/user-999/intro'));

assert(part2.includes('/user/show/${participantId}/reviews'), 'perfil público de avaliações precisa ser a primeira rota derivada');
assert(part4.includes('same_rating_flow_kept'), 'navegação deve reconhecer o mesmo fluxo de avaliação');
assert(part4.includes('isSameRatingFlow(location.href, target)'), 'navigateToPassengerTrip deve bloquear recarga do mesmo convite');
assert(part3.includes('insideTargetFlow'), 'processReviewFlow deve tratar /intro como parte da avaliação atual');
assert(part3.includes('rating_flow_wait'), 'fluxo deve aguardar controles em vez de recarregar');
assert(part3.includes('O RotaAi interrompeu sem recarregar a página'), 'deve haver limite seguro de tentativas');

console.log('rating-flow-loop.test: ok');
