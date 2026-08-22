(() => {
  const toggle = document.querySelector('.nav-toggle');
  const navigation = document.querySelector('.site-nav');
  if (toggle && navigation) {
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      navigation.classList.toggle('open', !expanded);
    });
    navigation.addEventListener('click', (event) => {
      if (event.target instanceof HTMLAnchorElement) {
        toggle.setAttribute('aria-expanded', 'false');
        navigation.classList.remove('open');
      }
    });
  }

  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(button.dataset.copy || '');
        button.textContent = 'Copied';
      } catch {
        button.textContent = 'Select commands';
      }
      window.setTimeout(() => { button.textContent = original; }, 1800);
    });
  });

  const demo = {
    scenario: document.getElementById('demo-scenario'),
    description: document.getElementById('demo-description'),
    input: document.getElementById('demo-input'),
    upload: document.getElementById('demo-upload'),
    run: document.getElementById('demo-run'),
    reset: document.getElementById('demo-reset'),
    download: document.getElementById('demo-download'),
    status: document.getElementById('demo-status'),
    verdict: document.getElementById('demo-verdict'),
    disposition: document.getElementById('demo-disposition'),
    evidenceState: document.getElementById('demo-evidence-state'),
    custody: document.getElementById('demo-custody'),
    inputDigest: document.getElementById('demo-input-digest'),
    resultDigest: document.getElementById('demo-result-digest'),
    reasons: document.getElementById('demo-reasons'),
    canonical: document.getElementById('demo-canonical'),
    receipt: document.getElementById('demo-receipt')
  };

  if (demo.scenario && window.EvidenceStateBrowserCore) {
    let scenarios = [];
    let lastReceipt = null;

    const selected = () => scenarios.find((item) => item.id === demo.scenario.value);
    const resetScenario = () => {
      const scenario = selected();
      if (!scenario) return;
      demo.input.value = scenario.input;
      demo.description.textContent = scenario.description;
      demo.status.textContent = 'Scenario loaded. Run the gate to produce a new local result.';
    };

    const render = (result) => {
      lastReceipt = result;
      demo.disposition.textContent = result.disposition;
      demo.evidenceState.textContent = result.evidence_state;
      demo.custody.textContent = result.expected_input_digest_match === true ? 'MATCH' : result.expected_input_digest_match === false ? 'MISMATCH / FAILED CLOSED' : 'UNESTABLISHED';
      demo.inputDigest.textContent = result.input_digest || 'not computed';
      demo.resultDigest.textContent = result.result_digest;
      demo.verdict.dataset.state = result.disposition.startsWith('PERMIT') ? 'permit' : 'reject';
      demo.reasons.textContent = '';
      const reasons = result.reasons.length ? result.reasons : ['NONE — all represented checks passed'];
      reasons.forEach((reason) => {
        const item = document.createElement('li');
        item.textContent = reason;
        demo.reasons.appendChild(item);
      });
      demo.canonical.textContent = result.canonical_input || 'Canonicalization did not complete.';
      demo.receipt.textContent = JSON.stringify(result, null, 2);
      demo.download.disabled = false;
      demo.status.textContent = `Evaluation complete: ${result.disposition}. No data left this browser.`;
    };

    demo.scenario.addEventListener('change', resetScenario);
    demo.reset.addEventListener('click', resetScenario);
    demo.run.addEventListener('click', async () => {
      const scenario = selected();
      demo.run.disabled = true;
      demo.status.textContent = 'Parsing, canonicalizing, hashing, and evaluating locally…';
      const result = await window.EvidenceStateBrowserCore.evaluate(
        demo.input.value,
        scenario ? scenario.expected_input_digest : null
      );
      render(result);
      demo.run.disabled = false;
    });
    demo.upload.addEventListener('change', async () => {
      const [file] = demo.upload.files || [];
      if (!file) return;
      if (file.size > 1_048_576) {
        demo.status.textContent = 'File rejected: the browser demo accepts at most 1 MiB.';
        return;
      }
      demo.input.value = await file.text();
      demo.status.textContent = 'Local file loaded. The selected scenario digest remains the custody comparison.';
    });
    demo.download.addEventListener('click', () => {
      if (!lastReceipt) return;
      const blob = new Blob([`${JSON.stringify(lastReceipt, null, 2)}\n`], {type: 'application/json'});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'evidence-state-browser-receipt.json';
      link.click();
      URL.revokeObjectURL(url);
    });

    fetch('demo-fixtures.json', {cache: 'no-store'})
      .then((response) => {
        if (!response.ok) throw new Error('fixture load failed');
        return response.json();
      })
      .then((fixture) => {
        if (fixture.scenario_schema !== 'esio-browser-demo-scenarios/1.0' || !Array.isArray(fixture.scenarios)) throw new Error('fixture contract mismatch');
        scenarios = fixture.scenarios;
        demo.scenario.textContent = '';
        scenarios.forEach((scenario) => {
          const option = document.createElement('option');
          option.value = scenario.id;
          option.textContent = scenario.label;
          demo.scenario.appendChild(option);
        });
        for (const control of [demo.scenario, demo.input, demo.upload, demo.run, demo.reset]) control.disabled = false;
        resetScenario();
      })
      .catch(() => {
        demo.description.textContent = 'Versioned fixtures could not be loaded. The browser demonstration is unavailable and remains fail closed.';
        demo.status.textContent = 'Demo unavailable: no evaluation was performed.';
        demo.verdict.dataset.state = 'reject';
        demo.disposition.textContent = 'REJECT_FIXTURE_UNAVAILABLE';
      });
  }
})();
