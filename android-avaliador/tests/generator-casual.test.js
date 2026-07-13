const fs = require('fs');
const path = require('path');

const source = fs.readFileSync(
  path.join(__dirname, '..', 'app', 'src', 'main', 'assets', 'generator.js'),
  'utf8'
);
global.window = global;
eval(source);

const result = global.RotaAiGenerator.generateEvaluation({
  name: 'Raquel',
  reviews: ['Muito pontual, educada, simpática e ótima companhia. Super recomendo.']
});

if (!result.ok || !result.text) throw new Error('A avaliação casual não foi gerada.');
if (result.traits.length > 2) throw new Error('A avaliação ficou longa demais.');
if (!/Raquel/.test(result.text)) throw new Error('O nome do passageiro não foi mantido.');
if (!/(Recomendo|Indico)\./.test(result.text)) throw new Error('A recomendação existente na base foi perdida.');
if (/postura cordial|tratou todos com consideração|contribuiu para um trajeto/i.test(result.text)) {
  throw new Error(`O tom ainda está formal demais: ${result.text}`);
}
if (/muito pontual, educada, simpática/i.test(result.text.toLowerCase())) {
  throw new Error('O texto original foi repetido praticamente igual.');
}

console.log('generator-casual: ok', result.text);
