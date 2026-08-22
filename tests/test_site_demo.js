#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const build = path.join(root, '.site-build');
const core = require(path.join(root, 'site', 'demo-core.js'));

async function main() {
  const fixturePath = path.join(build, 'demo-fixtures.json');
  assert.ok(fs.existsSync(fixturePath), 'run scripts/build_site.py before the browser demo test');
  const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
  assert.equal(fixture.scenario_schema, 'esio-browser-demo-scenarios/1.0');
  assert.deepEqual(
    fixture.scenarios.map((scenario) => scenario.id),
    ['valid', 'incomplete', 'stale', 'ambiguous', 'conflicting', 'tampered', 'invalid']
  );

  for (const scenario of fixture.scenarios) {
    const first = await core.evaluate(scenario.input, scenario.expected_input_digest);
    const second = await core.evaluate(scenario.input, scenario.expected_input_digest);
    assert.deepEqual(second, first, `${scenario.id} must be byte-model deterministic`);
    for (const field of ['disposition', 'evidence_state', 'reasons']) {
      assert.deepEqual(first[field], scenario.expected[field], `${scenario.id} ${field} must match Python-generated evidence`);
    }
    if (scenario.expected.input_digest) {
      assert.equal(first.input_digest, scenario.expected.input_digest, `${scenario.id} canonical digest must match Python`);
      assert.equal(first.expected_input_digest_match, true, `${scenario.id} retained digest must match`);
    }
    assert.match(first.result_digest, /^sha256:[0-9a-f]{64}$/);
  }

  const duplicate = '{"subject":"one","subject":"two"}';
  const duplicateResult = await core.evaluate(duplicate, null);
  assert.equal(duplicateResult.disposition, 'REJECT_INVALID_INPUT');
  assert.deepEqual(duplicateResult.reasons, ['JSON_DUPLICATE_KEY']);

  const source = fs.readFileSync(path.join(root, 'site', 'index.html'), 'utf8');
  for (const required of [
    'id="demo-scenario"',
    'id="demo-input"',
    'id="demo-upload"',
    'id="demo-run"',
    'id="demo-download"',
    'id="demo-canonical"',
    'id="demo-receipt"'
  ]) assert.ok(source.includes(required), `site is missing ${required}`);

  const app = fs.readFileSync(path.join(root, 'site', 'app.js'), 'utf8');
  assert.ok(app.includes("fetch('demo-fixtures.json'"), 'site must load versioned built fixtures');
  assert.ok(!/\.innerHTML\s*=/.test(app), 'demo UI must not use an HTML injection sink');

  process.stdout.write('Browser demo parity and fail-closed regression passed.\n');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
