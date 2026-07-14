const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const part3 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part3.js'), 'utf8');
const part4 = fs.readFileSync(path.join(root, 'app/src/main/assets/rotaai-part4.js'), 'utf8');

assert(part3.includes('semantic_rating_click_locked'), 'a nota textual deve ter trava contra cliques repetidos');
assert(part4.includes('publicationPathStep'), 'a publicação deve reconhecer intro, note, comment e preview');
assert(part4.includes('currentFlow !== targetFlow'), 'a publicação deve conferir o passageiro antes de preencher o formulário');
assert(part4.includes('e2e-leave-rating-intro-continue-button-mobile'), 'a etapa intro deve avançar pelo controle real');
assert(part4.includes('e2e-leave-rating-comment-continue-button-mobile'), 'a etapa comment deve avançar pelo controle real');
assert(part4.includes("step === 'preview'"), 'a prévia precisa de tratamento próprio');
assert(part4.includes("stage === 'submitted'"), 'a publicação enviada deve aguardar confirmação sem clicar novamente');
assert(part4.includes('Nada foi marcado como publicado'), 'falha de confirmação não pode gerar falso positivo');

const flowGuard = part4.indexOf('currentFlow !== targetFlow');
const commentField = part4.indexOf("if (step === 'comment')");
assert(flowGuard >= 0 && commentField > flowGuard, 'o passageiro correto deve ser validado antes do campo de comentário');

console.log('publication-flow-state.test: ok');
