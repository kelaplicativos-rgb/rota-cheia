const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const part3 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part3.js'), 'utf8');
const part4 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part4.js'), 'utf8');

assert(part3.includes('const clickRatingChoice = (rating) =>'), 'deve existir seletor de nota compatível com botões textuais');
assert(part3.includes('/^excelente$/i'), 'nota 5 deve reconhecer o botão Excelente');
assert(part3.includes("'semantic_rating_button'"), 'seleção textual deve ser registrada no diagnóstico');
assert(part3.includes("'semantic_rating_click_locked'"), 'cliques repetidos na mesma nota devem ser bloqueados');
assert(part3.includes('ratingSelected = clickRatingChoice'), 'revisão deve usar o seletor textual');
assert(part4.includes('clickRatingChoice(Number(passenger.rating))'), 'publicação deve usar o mesmo seletor textual');
assert(part4.includes("step === 'note'"), 'publicação deve tratar a etapa /note explicitamente');
assert(part4.includes("stage = 'rating-selected'"), 'a nota selecionada deve aguardar a abertura do comentário');

console.log('note-rating-buttons.test: ok');
