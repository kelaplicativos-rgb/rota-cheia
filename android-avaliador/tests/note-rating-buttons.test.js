const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const part3 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part3.js'), 'utf8');
const part4 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part4.js'), 'utf8');

assert(part3.includes('const clickRatingChoice = (rating) =>'), 'deve existir seletor de nota compatível com botões textuais');
assert(part3.includes('/^excelente$/i'), 'nota 5 deve reconhecer o botão Excelente');
assert(part3.includes("'semantic_rating_button'"), 'seleção textual deve ser registrada no diagnóstico');
assert(part3.includes('ratingSelected = clickRatingChoice'), 'revisão deve usar o seletor textual');
assert(part3.includes("stage = 'rating-selected'"), 'mudança automática para /comment deve ser reconhecida');
assert(part4.includes('ratingOnly = clickRatingChoice'), 'publicação deve usar o mesmo seletor textual');
assert(part4.includes('location.pathname !== ratingPathBefore'), 'publicação deve detectar avanço automático da etapa /note');

console.log('note-rating-buttons.test: ok');
