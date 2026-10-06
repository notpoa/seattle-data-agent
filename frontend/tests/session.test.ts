import assert from 'node:assert/strict';
import test from 'node:test';
import { EventReader, emptySession, reduceEvent } from '../lib/session.ts';
test('stream parser preserves split JSON and last line', () => {
  const reader = new EventReader();
  assert.deepEqual(reader.push('{"type":"pro'), []);
  assert.deepEqual(reader.push('gress","message":"Searching"}\n{"type":"error","message":"Missing key"}'), [{type: 'progress', message: 'Searching'}]);
  assert.deepEqual(reader.finish(), [{type: 'error', message: 'Missing key'}]);
});
test('discovery deduplicates and configuration errors preserve actual candidates', () => {
  const dataset = {dataset_id: 'abcd-1234', title: 'Synthetic fixture', description: ''};
  let state = reduceEvent(emptySession(), {type: 'datasets', datasets: [dataset, dataset]});
  state = reduceEvent(state, {type: 'error', message: 'Missing key'});
  assert.equal(state.datasets.length, 1); assert.equal(state.error, 'Missing key'); assert.equal(state.answer, '');
});
test('clarification is not represented as a successful answer', () => {
  const state = reduceEvent(emptySession(), {type: 'answer', status: 'clarification', message: 'Which years?'});
  assert.equal(state.status, 'clarification'); assert.equal(state.results.length, 0);
});
