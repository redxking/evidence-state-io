(function initializeEvidenceStateBrowserCore(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.EvidenceStateBrowserCore = api;
})(typeof globalThis === 'object' ? globalThis : this, () => {
  'use strict';

  const PROFILE = 'esio-canonical-json-0.1';
  const RESULT_SCHEMA = 'esio-browser-gateway-result/1.0';
  const MAX_INPUT_BYTES = 1_048_576;
  const MAX_DEPTH = 128;
  const MAX_NUMBER_CHARS = 4_300;

  class DemoValidationError extends Error {
    constructor(code, message) {
      super(message);
      this.name = 'DemoValidationError';
      this.code = code;
    }
  }

  class NumberToken {
    constructor(raw) { this.raw = raw; }
  }

  function parseStrictJson(text) {
    if (typeof text !== 'string') throw new DemoValidationError('INPUT_ENCODING_INVALID', 'Input must be decoded text.');
    if (new TextEncoder().encode(text).length > MAX_INPUT_BYTES) throw new DemoValidationError('INPUT_TOO_LARGE', 'Input exceeds 1 MiB.');
    let index = 0;

    function whitespace() { while (/[\t\n\r ]/.test(text[index] || '')) index += 1; }
    function fail(message) { throw new DemoValidationError('JSON_INVALID', `${message} at byte ${index}.`); }

    function stringValue() {
      const start = index;
      if (text[index] !== '"') fail('Expected a JSON string');
      index += 1;
      while (index < text.length) {
        const character = text[index];
        if (character === '"') {
          index += 1;
          try { return JSON.parse(text.slice(start, index)); } catch { fail('Invalid JSON string'); }
        }
        if (character === '\\') {
          index += 2;
          continue;
        }
        if (text.charCodeAt(index) < 0x20) fail('Unescaped control character');
        index += 1;
      }
      fail('Unterminated JSON string');
    }

    function numberValue() {
      const match = text.slice(index).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
      if (!match) fail('Invalid JSON number');
      if (match[0].length > MAX_NUMBER_CHARS) throw new DemoValidationError('JSON_NUMBER_INVALID', 'Numeric token is too long.');
      index += match[0].length;
      const numeric = Number(match[0]);
      if (!Number.isFinite(numeric)) throw new DemoValidationError('JSON_NUMBER_INVALID', 'Numeric token is not finite.');
      return new NumberToken(match[0]);
    }

    function value(depth) {
      if (depth > MAX_DEPTH) throw new DemoValidationError('JSON_DEPTH_EXCEEDED', 'JSON nesting exceeds 128 levels.');
      whitespace();
      const character = text[index];
      if (character === '{') return objectValue(depth + 1);
      if (character === '[') return arrayValue(depth + 1);
      if (character === '"') return stringValue();
      if (character === '-' || /\d/.test(character || '')) return numberValue();
      for (const [token, result] of [['true', true], ['false', false], ['null', null]]) {
        if (text.startsWith(token, index)) { index += token.length; return result; }
      }
      fail('Expected a JSON value');
    }

    function objectValue(depth) {
      const result = Object.create(null);
      const keys = new Set();
      index += 1;
      whitespace();
      if (text[index] === '}') { index += 1; return result; }
      while (true) {
        whitespace();
        const key = stringValue();
        if (keys.has(key)) throw new DemoValidationError('JSON_DUPLICATE_KEY', `Duplicate object key: ${key}.`);
        keys.add(key);
        whitespace();
        if (text[index] !== ':') fail('Expected a colon');
        index += 1;
        result[key] = value(depth);
        whitespace();
        if (text[index] === '}') { index += 1; return result; }
        if (text[index] !== ',') fail('Expected a comma or closing brace');
        index += 1;
      }
    }

    function arrayValue(depth) {
      const result = [];
      index += 1;
      whitespace();
      if (text[index] === ']') { index += 1; return result; }
      while (true) {
        result.push(value(depth));
        whitespace();
        if (text[index] === ']') { index += 1; return result; }
        if (text[index] !== ',') fail('Expected a comma or closing bracket');
        index += 1;
      }
    }

    const result = value(0);
    whitespace();
    if (index !== text.length) fail('Trailing content');
    return result;
  }

  function canonicalNumber(token) {
    if (!/[.eE]/.test(token.raw)) return BigInt(token.raw).toString();
    const numeric = Number(token.raw);
    if (Object.is(numeric, -0)) return '-0.0';
    if (Number.isInteger(numeric)) return `${numeric.toFixed(1)}`;
    return String(numeric).replace(/e([+-]?)(\d)$/i, 'e$10$2');
  }

  function canonicalJson(value) {
    if (value instanceof NumberToken) return canonicalNumber(value);
    if (value === null || typeof value === 'boolean') return String(value);
    if (typeof value === 'string') return JSON.stringify(value);
    if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
    if (value && typeof value === 'object') {
      return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
    }
    throw new DemoValidationError('MODEL_INVALID', 'Canonical input contains an unsupported value.');
  }

  async function sha256Digest(text) {
    if (!globalThis.crypto || !globalThis.crypto.subtle) throw new DemoValidationError('CRYPTO_UNAVAILABLE', 'Browser SHA-256 is unavailable; evaluation failed closed.');
    const bytes = new TextEncoder().encode(text);
    const result = await globalThis.crypto.subtle.digest('SHA-256', bytes);
    return `sha256:${Array.from(new Uint8Array(result), (byte) => byte.toString(16).padStart(2, '0')).join('')}`;
  }

  function exactFields(value, expected, path) {
    if (!value || typeof value !== 'object' || Array.isArray(value) || value instanceof NumberToken) throw new DemoValidationError('MODEL_INVALID', `${path} must be an object.`);
    const actual = Object.keys(value).sort();
    const required = [...expected].sort();
    if (actual.join('\0') !== required.join('\0')) throw new DemoValidationError('MODEL_INVALID', `${path} has missing or unknown fields.`);
  }

  function integer(value, path) {
    if (!(value instanceof NumberToken) || /[.eE]/.test(value.raw)) throw new DemoValidationError('MODEL_INVALID', `${path} must be an integer.`);
    const result = Number(value.raw);
    if (!Number.isSafeInteger(result) || result < 0) throw new DemoValidationError('MODEL_INVALID', `${path} must be a non-negative safe integer.`);
    return result;
  }

  function dateValue(value, path) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/.test(value)) throw new DemoValidationError('MODEL_INVALID', `${path} must be a UTC ISO-8601 timestamp.`);
    const timestamp = Date.parse(value);
    if (!Number.isFinite(timestamp)) throw new DemoValidationError('MODEL_INVALID', `${path} is not a valid timestamp.`);
    return timestamp;
  }

  function validateRequest(request) {
    exactFields(request, ['subject', 'mode', 'evaluated_at', 'policy', 'envelope'], 'request');
    if (typeof request.subject !== 'string' || request.mode !== 'SCOPED') throw new DemoValidationError('MODEL_INVALID', 'The browser reference supports one scoped synthetic request contract.');
    exactFields(request.policy, ['policy_id', 'policy_version'], 'request.policy');
    if (request.policy.policy_id !== 'esio-p0-safety-floor' || request.policy.policy_version !== '1.0-candidate.4') throw new DemoValidationError('MODEL_INVALID', 'Unsupported policy contract.');
    request.policy = {
      policy_id: 'esio-p0-safety-floor',
      policy_version: '1.0-candidate.4',
      coverage: {
        allow_permission_limited_scope: true,
        minimum_lower_bound: new NumberToken('1.0'),
        reject_interruption: true,
        reject_query_errors: true,
        reject_timeout: true,
        require_complete_pagination: true,
        require_complete_partitions: true,
        require_exact_population: false
      },
      max_index_age_seconds: null,
      max_observation_age_seconds: null,
      reject_envelope_errors: true,
      require_finality_horizon: true,
      require_index_as_of: true,
      require_valid_until: true
    };
    const envelope = request.envelope;
    exactFields(envelope, ['schema_version', 'state', 'query', 'coverage', 'coverage_query_fingerprint', 'matched_count', 'observed_at', 'valid_until', 'source_observations', 'errors', 'notes'], 'request.envelope');
    if (envelope.schema_version !== '1.0') throw new DemoValidationError('MODEL_INVALID', 'Unsupported wire schema.');
    if (!['PRESENT', 'ABSENT_WITHIN_SCOPE', 'NOT_OBSERVED', 'PARTIAL', 'STALE', 'INACCESSIBLE', 'PENDING_WINDOW', 'FAILED', 'CONTRADICTORY'].includes(envelope.state)) throw new DemoValidationError('MODEL_INVALID', 'Unsupported evidence state.');
    integer(envelope.matched_count, 'request.envelope.matched_count');
    if (!Array.isArray(envelope.errors) || !Array.isArray(envelope.source_observations)) throw new DemoValidationError('MODEL_INVALID', 'Envelope errors and source observations must be arrays.');
    if (envelope.source_observations.length !== 1) throw new DemoValidationError('MODEL_INVALID', 'The browser reference requires one source observation.');
    const coverage = envelope.coverage;
    exactFields(coverage, ['examined_units', 'population_basis', 'population_units', 'declared_lower_bound', 'pages_examined', 'pages_expected', 'pagination_complete', 'continuation_token_present', 'partitions_examined', 'partitions_expected', 'partitions_complete', 'timed_out', 'interrupted', 'permission_limited', 'query_errors'], 'request.envelope.coverage');
    for (const field of ['examined_units', 'population_units', 'pages_examined', 'pages_expected', 'partitions_examined', 'partitions_expected']) integer(coverage[field], `request.envelope.coverage.${field}`);
    for (const field of ['pagination_complete', 'continuation_token_present', 'partitions_complete', 'timed_out', 'interrupted', 'permission_limited']) if (typeof coverage[field] !== 'boolean') throw new DemoValidationError('MODEL_INVALID', `request.envelope.coverage.${field} must be boolean.`);
    if (!Array.isArray(coverage.query_errors)) throw new DemoValidationError('MODEL_INVALID', 'Coverage query_errors must be an array.');
    dateValue(request.evaluated_at, 'request.evaluated_at');
    dateValue(envelope.observed_at, 'request.envelope.observed_at');
    if (envelope.valid_until !== null) dateValue(envelope.valid_until, 'request.envelope.valid_until');
    return request;
  }

  function sourceReasons(request) {
    const envelope = request.envelope;
    const observation = envelope.source_observations[0];
    const requirement = request.envelope.query.source_requirements[0];
    if (!observation || !requirement) return ['REQUIRED_SOURCE_MISSING'];
    const statusReason = {
      INACCESSIBLE: 'REQUIRED_SOURCE_INACCESSIBLE',
      PENDING: 'REQUIRED_SOURCE_PENDING',
      STALE: 'REQUIRED_SOURCE_STALE',
      FAILED: 'REQUIRED_SOURCE_FAILED',
      CONTRADICTORY: 'REQUIRED_SOURCE_CONTRADICTORY',
      UNKNOWN: 'REQUIRED_SOURCE_STATUS_UNKNOWN'
    }[observation.status];
    if (statusReason) return [statusReason];
    if (observation.status !== 'OBSERVED') return ['REQUIRED_SOURCE_STATUS_UNKNOWN'];
    if (observation.source_id !== requirement.source_id) return ['REQUIRED_SOURCE_IDENTITY_MISMATCH'];
    if (observation.authorization_context_id !== requirement.authorization_context_id) return ['REQUIRED_SOURCE_AUTHORIZATION_MISMATCH'];
    if (observation.query_fingerprint !== envelope.coverage_query_fingerprint) return ['REQUIRED_SOURCE_ERRORS_PRESENT'];
    if (Array.isArray(observation.errors) && observation.errors.length) return ['REQUIRED_SOURCE_ERRORS_PRESENT'];
    return [];
  }

  function decisionReasons(request) {
    const envelope = request.envelope;
    const coverage = envelope.coverage;
    const reasons = [];
    const add = (reason) => { if (!reasons.includes(reason)) reasons.push(reason); };
    if (envelope.state !== 'ABSENT_WITHIN_SCOPE') add('STATE_NOT_ABSENT_WITHIN_SCOPE');
    if (integer(envelope.matched_count, 'matched_count') !== 0) add('NONZERO_MATCHES');
    const coverageFails = coverage.population_basis !== 'EXACT'
      || integer(coverage.examined_units, 'examined_units') !== integer(coverage.population_units, 'population_units')
      || !coverage.pagination_complete || coverage.continuation_token_present
      || integer(coverage.pages_examined, 'pages_examined') !== integer(coverage.pages_expected, 'pages_expected')
      || !coverage.partitions_complete
      || integer(coverage.partitions_examined, 'partitions_examined') !== integer(coverage.partitions_expected, 'partitions_expected')
      || coverage.timed_out || coverage.interrupted || coverage.permission_limited
      || coverage.query_errors.length > 0;
    if (coverageFails) add('COVERAGE_POLICY_NOT_MET');
    if (envelope.errors.length) add('ENVELOPE_ERRORS_PRESENT');
    sourceReasons(request).forEach(add);
    const evaluatedAt = dateValue(request.evaluated_at, 'evaluated_at');
    const observedAt = dateValue(envelope.observed_at, 'observed_at');
    if (evaluatedAt < observedAt) add('EVALUATION_PRECEDES_OBSERVATION');
    if (envelope.valid_until === null) add('VALIDITY_UNDECLARED');
    else if (evaluatedAt > dateValue(envelope.valid_until, 'valid_until')) add('RESULT_EXPIRED');
    const requirement = envelope.query.source_requirements[0];
    const observation = envelope.source_observations[0];
    if (!requirement.finality_horizon) add('FINALITY_HORIZON_UNDECLARED');
    if (!observation.descriptor.index_as_of) add('INDEX_TIMESTAMP_UNDECLARED');
    else if (requirement.finality_horizon && dateValue(observation.descriptor.index_as_of, 'index_as_of') < dateValue(requirement.finality_horizon, 'finality_horizon')) add('INDEX_PRECEDES_FINALITY_HORIZON');
    return reasons;
  }

  async function evaluate(text, expectedInputDigest) {
    const trace = [];
    try {
      const request = validateRequest(parseStrictJson(text));
      const canonicalInput = canonicalJson(request);
      const inputDigest = await sha256Digest(canonicalInput);
      trace.push({stage: 'parse', status: 'PASS'}, {stage: 'canonicalize', status: 'PASS', profile: PROFILE});
      if (expectedInputDigest && inputDigest !== expectedInputDigest) {
        trace.push({stage: 'retained_digest', status: 'FAIL'});
        const result = {
          schema: RESULT_SCHEMA,
          implementation: 'esio-browser-reference/0.1',
          canonicalization_profile: PROFILE,
          evidence_state: request.envelope.state,
          disposition: 'REJECT_UNVERIFIED_INPUT',
          reasons: ['EXPECTED_INPUT_DIGEST_MISMATCH'],
          input_digest: inputDigest,
          expected_input_digest: expectedInputDigest,
          expected_input_digest_match: false,
          canonical_input: canonicalInput,
          trace,
          limitations: ['Browser-local synthetic reference; no issuer authentication, action authorization, source truth, or operational effect.']
        };
        result.result_digest = await sha256Digest(canonicalJson(result));
        return result;
      }
      trace.push({stage: 'retained_digest', status: expectedInputDigest ? 'PASS' : 'UNESTABLISHED'});
      const reasons = decisionReasons(request);
      const allowed = reasons.length === 0;
      trace.push({stage: 'deterministic_gate', status: allowed ? 'PERMIT' : 'REJECT'});
      const result = {
        schema: RESULT_SCHEMA,
        implementation: 'esio-browser-reference/0.1',
        canonicalization_profile: PROFILE,
        evidence_state: request.envelope.state,
        disposition: allowed ? 'PERMIT_SCOPED_NEGATIVE' : 'REJECT_NEGATIVE',
        reasons,
        input_digest: inputDigest,
        expected_input_digest: expectedInputDigest || null,
        expected_input_digest_match: expectedInputDigest ? true : null,
        canonical_input: canonicalInput,
        trace,
        limitations: ['Browser-local synthetic reference; no issuer authentication, action authorization, source truth, or operational effect.']
      };
      result.result_digest = await sha256Digest(canonicalJson(result));
      return result;
    } catch (error) {
      const failure = error instanceof DemoValidationError ? error : new DemoValidationError('MODEL_INVALID', 'Input failed the browser reference contract.');
      trace.push({stage: 'parse_or_validate', status: 'FAIL', code: failure.code});
      const result = {
        schema: RESULT_SCHEMA,
        implementation: 'esio-browser-reference/0.1',
        canonicalization_profile: PROFILE,
        evidence_state: 'INVALID',
        disposition: 'REJECT_INVALID_INPUT',
        reasons: [failure.code],
        input_digest: null,
        expected_input_digest: expectedInputDigest || null,
        expected_input_digest_match: false,
        canonical_input: null,
        trace,
        limitations: ['Browser-local synthetic reference; invalid input never reaches a permit path.']
      };
      result.result_digest = await sha256Digest(canonicalJson(result));
      return result;
    }
  }

  return { DemoValidationError, NumberToken, canonicalJson, evaluate, parseStrictJson, sha256Digest };
});
