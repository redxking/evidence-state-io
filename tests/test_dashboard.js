#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const model = require(path.join(root, 'dashboard_model.js'));

function sectionBytes(section) {
  return [
    ...section.headerPrefixRaw,
    section.headerRaw,
    ...section.leadingRaw,
    ...section.tasks.flatMap((task) => task.rawLines)
  ].join('');
}

function testCurrentFileIsExactlyLossless() {
  const source = fs.readFileSync(path.join(root, 'TASKS.md'), 'utf8');
  const document = model.parse(source);
  assert.equal(model.serialize(document), source, 'current TASKS.md must round-trip byte-for-byte');
  assert.ok(document.sections.length > 0, 'current TASKS.md must expose sections');
  assert.ok(document.sections.some((section) => section.tasks.length > 0), 'current TASKS.md must expose tasks');

  const task = document.sections.flatMap((section) => section.tasks)
    .find((candidate) => candidate.rawLines.some((line) => line.includes('Prepare the exact corpus')));
  assert.ok(task, 'plain indented task detail fixture must be found');
  const originalBlock = task.rawLines.join('');
  model.setTaskChecked(task, !task.checked);
  const changedBlock = task.rawLines.join('');
  assert.ok(changedBlock.includes('  - Prepare the exact corpus'), 'plain detail bullet must survive an edit/autosave payload');
  assert.equal(
    changedBlock.replace(/^(-\s+\[)[ xX](\])/m, '$1?$2'),
    originalBlock.replace(/^(-\s+\[)[ xX](\])/m, '$1?$2'),
    'checking a task may change only its checkbox marker'
  );
  model.setTaskChecked(task, !task.checked);
  assert.equal(task.rawLines.join(''), originalBlock, 'reversing the edit must restore the exact raw block');
  assert.equal(model.serialize(document), source, 'reversed edit must restore the exact file');
}

function testRawBlocksMoveWithoutReconstruction() {
  const source = fs.readFileSync(path.join(root, 'TASKS.md'), 'utf8');
  const document = model.parse(source);
  assert.ok(document.sections.length >= 2, 'move fixture needs two sections');
  const from = document.sections.find((section) => section.tasks.length > 0);
  const to = document.sections.find((section) => section !== from);
  const task = from.tasks[0];
  const rawTask = task.rawLines.join('');
  from.tasks.shift();
  task.section = to.id;
  to.tasks.push(task);
  assert.equal(task.rawLines.join(''), rawTask, 'task move must carry its complete raw block');
  assert.ok(model.serialize(document).includes(rawTask), 'moved raw task block must remain in output');

  const section = document.sections[0];
  const rawSection = sectionBytes(section);
  document.sections.shift();
  document.sections.push(section);
  assert.equal(sectionBytes(section), rawSection, 'section move must carry its complete raw block');
  assert.ok(model.serialize(document).endsWith(rawSection), 'moved section block must serialize intact at its destination');
}

function testDetailsBlankLinesAndChecklistEditsSurvive() {
  const source = [
    '# Tasks\r\n',
    '\r\n',
    '## Active\r\n',
    '\r\n',
    '- [ ] **Parent** - note\r\n',
    '  - plain detail one\r\n',
    '\r\n',
    '  - [ ] Child <img src=x onerror=alert(1)>\r\n',
    '    continuation that the UI does not understand\r\n',
    '\r\n'
  ].join('');
  const document = model.parse(source);
  assert.equal(model.serialize(document), source, 'CRLF fixture must round-trip exactly');
  const task = document.sections[0].tasks[0];
  assert.equal(task.subtasks.length, 1, 'indented checklist subtask must be editable');

  model.setSubtaskChecked(task, 0, true);
  model.setSubtaskText(task, 0, 'Edited child <script>neverRuns()</script>');
  const output = model.serialize(document);
  assert.ok(output.includes('  - plain detail one\r\n\r\n'), 'plain detail and adjacent blank line must survive');
  assert.ok(output.includes('    continuation that the UI does not understand\r\n\r\n'), 'unknown continuation and blank line must survive');
  assert.ok(output.includes('  - [x] Edited child <script>neverRuns()</script>\r\n'), 'subtask edit must update its original line');

  model.addSubtask(document, task, 'New child');
  assert.ok(model.serialize(document).includes('  - [ ] New child\r\n\r\n'), 'new subtask must precede preserved trailing blanks');
  model.removeSubtask(task, 1);
  assert.ok(!model.serialize(document).includes('New child'), 'new subtask must remain removable');
}

function testNewTasksAndSectionsRemainParseable() {
  const document = model.parse('# Tasks\n\n## Active\n');
  const section = document.sections[0];
  const task = model.createTask(document, section, 'New task');
  assert.ok(task, 'new task must be created');
  section.tasks.push(task);
  const later = model.createSection(document, 'Later');
  assert.ok(later, 'new section must be created');
  const laterTask = model.createTask(document, later, 'Second task');
  later.tasks.push(laterTask);
  const output = model.serialize(document);
  const reparsed = model.parse(output);
  assert.deepEqual(
    reparsed.sections.map((item) => [item.name, item.tasks.map((entry) => entry.title)]),
    [['Active', ['New task']], ['Later', ['Second task']]],
    'new sections and tasks must survive save/reload'
  );

  const duplicates = model.parse('# Tasks\n\n## Same\n- [ ] First\n\n## Same\n- [ ] Second\n');
  assert.equal(duplicates.sections.length, 2, 'duplicate display names must not merge sections');
  assert.notEqual(duplicates.sections[0].id, duplicates.sections[1].id, 'duplicate display names need distinct safe identities');
  assert.equal(model.serialize(duplicates), '# Tasks\n\n## Same\n- [ ] First\n\n## Same\n- [ ] Second\n');
}

function testHostileTextUsesTextOnlySinks() {
  const hostile = '<img src=x onerror="globalThis.pwned=true"><script>pwned()</script>';
  const fakeElement = {
    _text: '',
    set textContent(value) { this._text = value; },
    get textContent() { return this._text; },
    set innerHTML(_) { throw new Error('unsafe HTML sink invoked'); }
  };
  model.setElementText(fakeElement, hostile);
  assert.equal(fakeElement.textContent, hostile, 'hostile markup must remain literal text');

  const parsed = model.parse(`# Tasks\n\n## ${hostile}\n- [ ] **${hostile}**\n  - [ ] ${hostile}\n`);
  assert.equal(parsed.sections[0].name, hostile);
  assert.equal(parsed.sections[0].tasks[0].title, hostile);
  assert.equal(parsed.sections[0].tasks[0].subtasks[0].text, hostile);
  assert.match(parsed.sections[0].id, /^section-\d+$/, 'section DOM identity must not derive from hostile text');
  assert.match(parsed.sections[0].tasks[0].id, /^task-\d+$/, 'task DOM identity must not derive from hostile text');

  const dashboard = fs.readFileSync(path.join(root, 'dashboard.html'), 'utf8');
  assert.ok(dashboard.includes('<script src="./dashboard_model.js"></script>'), 'dashboard must load the tested model');
  const taskRegion = dashboard.slice(
    dashboard.indexOf('// ===== TASKS FUNCTIONALITY ====='),
    dashboard.indexOf('// ===== MEMORY FUNCTIONALITY =====')
  );
  for (const match of taskRegion.matchAll(/\.innerHTML\s*=\s*([^;\n]+)/g)) {
    assert.match(match[1].trim(), /^(?:''|"")$/, `task UI has a non-clearing innerHTML sink: ${match[0]}`);
  }
  for (const requiredSafeSink of [
    'TaskDashboardModel.setElementText(title, task.title)',
    'TaskDashboardModel.setElementText(note, task.note',
    'TaskDashboardModel.setElementText(subtaskText, subtask.text)',
    'TaskDashboardModel.setElementText(columnTitle, title)',
    'TaskDashboardModel.setElementText(sectionTitle, section.name)',
    'TaskDashboardModel.setElementText(sectionBtn, sectionName)'
  ]) {
    assert.ok(taskRegion.includes(requiredSafeSink), `missing safe text sink: ${requiredSafeSink}`);
  }

  // Tag matching follows the HTML rules rather than the convenient subset.
  // Tag names are case-insensitive, and an end tag may carry ignored trailing
  // content, so `</script foo>` and `</SCRIPT\n>` both close a block.  A
  // pattern that misses either would silently drop a script region from the
  // safe-render regression below while the regression kept reporting success.
  const scriptBlocks = [
    ...dashboard.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script(?:\s[^>]*)?>/gi)
  ];
  const openingTags = dashboard.match(/<script\b/gi) ?? [];
  assert.strictEqual(
    scriptBlocks.length,
    openingTags.length,
    `extracted ${scriptBlocks.length} script blocks but the document opens ${openingTags.length}; a script region is not being covered`
  );
  const inlineScripts = scriptBlocks.map((match) => match[1]).filter((script) => script.trim());
  assert.ok(inlineScripts.length > 0, 'dashboard inline script must be found');
  for (const script of inlineScripts) new Function(script);

  class FakeElement {
    constructor(tagName) {
      this.tagName = tagName.toUpperCase();
      this.children = [];
      this.dataset = {};
      this.style = {};
      this.className = '';
      this._textContent = '';
      this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
    }
    set textContent(value) { this._textContent = String(value); }
    get textContent() { return this._textContent; }
    set innerHTML(value) {
      if (value !== '') throw new Error(`unsafe HTML sink invoked with ${value}`);
      this.children = [];
      this._textContent = '';
    }
    get innerHTML() { return ''; }
    append(...children) { this.children.push(...children); }
    appendChild(child) { this.children.push(child); return child; }
    addEventListener() {}
    querySelectorAll() { return []; }
    querySelector() { return null; }
    contains() { return false; }
    remove() {}
  }

  const elements = new Map();
  const fakeDocument = {
    body: new FakeElement('body'),
    createElement(tagName) { return new FakeElement(tagName); },
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, new FakeElement('div'));
      return elements.get(id);
    },
    querySelectorAll() { return []; },
    addEventListener() {},
    removeEventListener() {}
  };
  const context = {
    console,
    confirm() { return false; },
    document: fakeDocument,
    setInterval() { return 1; },
    clearInterval() {},
    setTimeout() { return 1; },
    clearTimeout() {}
  };
  context.window = {
    EvidenceStateTaskDashboardModel: model,
    addEventListener() {},
    innerWidth: 1024
  };
  vm.createContext(context);
  for (const script of inlineScripts) vm.runInContext(script, context);
  const hostileTask = parsed.sections[0].tasks[0];
  const card = context.createCard(hostileTask);
  const column = context.createColumn(parsed.sections[0].id, parsed.sections[0].name, [hostileTask]);
  const descendants = (element) => [element, ...element.children.flatMap(descendants)];
  const rendered = [...descendants(card), ...descendants(column)];
  assert.ok(rendered.some((element) => element.textContent === hostileTask.title), 'board card must render hostile title as textContent');
  assert.ok(rendered.some((element) => element.textContent === parsed.sections[0].name), 'board column must render hostile section as textContent');
  assert.ok(rendered.some((element) => element.textContent === hostileTask.subtasks[0].text), 'board card must render hostile subtask as textContent');
  assert.ok(!rendered.some((element) => ['IMG', 'SCRIPT', 'SVG', 'IFRAME'].includes(element.tagName)), 'hostile task text must not create markup elements');

  context.parseTaskMarkdown(`# Tasks\n\n## ${hostile}\n- [ ] **${hostile}**\n  - [ ] ${hostile}\n`);
  context.switchTaskView('list');
  const listRendered = descendants(elements.get('listView'));
  assert.ok(listRendered.some((element) => element.textContent === hostile), 'list view must retain hostile TASKS-derived strings as textContent');
  assert.ok(!listRendered.some((element) => ['IMG', 'SCRIPT', 'SVG', 'IFRAME'].includes(element.tagName)), 'hostile list text must not create markup elements');
}

testCurrentFileIsExactlyLossless();
testRawBlocksMoveWithoutReconstruction();
testDetailsBlankLinesAndChecklistEditsSurvive();
testNewTasksAndSectionsRemainParseable();
testHostileTextUsesTextOnlySinks();

process.stdout.write('Dashboard lossless/safe-render regression passed.\n');
