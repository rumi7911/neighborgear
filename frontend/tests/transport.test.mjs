import test from 'node:test';
import assert from 'node:assert/strict';
import { fetchWithRetry } from '../src/transport.ts';

test('a lost response retries with the same idempotency key and body', async () => {
  let accepted;
  let calls = 0;
  const fakeNetwork = async (_url, options) => {
    calls++;
    if (calls === 1) { accepted = options; throw new TypeError('Lost response'); }
    assert.equal(options.headers['Idempotency-Key'], accepted.headers['Idempotency-Key']);
    assert.equal(options.body, accepted.body);
    return new Response('{"run_id":"run-original"}');
  };
  const response = await fetchWithRetry('/api/requests', {method:'POST',headers:{'Idempotency-Key':'one-command'},body:'{"text":"rollator"}'}, fakeNetwork);
  assert.deepEqual(await response.json(), {run_id:'run-original'});
  assert.equal(calls, 2);
});

test('validation and authorization responses are not replayed', async () => {
  let calls = 0;
  const response = await fetchWithRetry('/api/requests', {}, async () => { calls++; return new Response('denied',{status:401}); });
  assert.equal(response.status,401);
  assert.equal(calls,1);
});

test('transport retries are bounded', async () => {
  let calls = 0;
  await assert.rejects(fetchWithRetry('/api/snapshot',{},async () => {calls++; throw new TypeError('Offline');}), /Offline/);
  assert.equal(calls,2);
});
