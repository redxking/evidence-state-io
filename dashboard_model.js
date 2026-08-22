(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.EvidenceStateTaskDashboardModel = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const SECTION_HEADER = /^##[ \t]+(.+?)[ \t]*$/;
  const TASK_LINE = /^(-[ \t]+\[)([ xX])(\][ \t]*)(.*)$/;
  const SUBTASK_LINE = /^(\s+-[ \t]+\[)([ xX])(\][ \t]*)(.*)$/;

  function splitLinesKeepEndings(content) {
    if (content === '') return [];
    return content.match(/[^\r\n]*(?:\r\n|\n|\r|$)/g).filter(Boolean);
  }

  function lineEnding(line) {
    const match = line.match(/(\r\n|\n|\r)$/);
    return match ? match[1] : '';
  }

  function lineText(line) {
    return line.slice(0, line.length - lineEnding(line).length);
  }

  function isBlank(line) {
    return lineText(line).trim() === '';
  }

  function sectionNameFromLine(line) {
    const match = lineText(line).match(SECTION_HEADER);
    if (!match) return null;
    let name = match[1].trim();
    if (name.startsWith('**') && name.endsWith('**') && name.length >= 4) {
      name = name.slice(2, -2).trim();
    }
    return name;
  }

  function isTaskLine(line) {
    return TASK_LINE.test(lineText(line));
  }

  function findBlockStart(lines, lineIndex, lowerBound) {
    let start = lineIndex;
    while (start > lowerBound && isBlank(lines[start - 1])) start -= 1;
    return start;
  }

  function parseTask(rawLines, taskLineIndex, id, sectionId) {
    const task = {
      id,
      section: sectionId,
      rawLines,
      taskLineIndex,
      title: '',
      note: '',
      checked: false,
      subtasks: []
    };
    refreshTask(task);
    return task;
  }

  function refreshTask(task) {
    const rawLine = task.rawLines[task.taskLineIndex];
    const match = rawLine && lineText(rawLine).match(TASK_LINE);
    if (!match) throw new Error('Task block no longer contains a valid task line');

    task._taskPrefix = match[1];
    task._taskSpacing = match[3];
    task.checked = match[2].toLowerCase() === 'x';

    const body = match[4];
    const boldMatch = body.match(/^(\*\*)(.+?)(\*\*)(.*)$/);
    if (boldMatch) {
      task._titlePrefix = boldMatch[1];
      task.title = boldMatch[2];
      task._titleSuffix = boldMatch[3] + boldMatch[4];
      task.note = boldMatch[4].replace(/^[ \t]*-[ \t]*/, '').trim();
      task._boldTitle = true;
    } else {
      task._titlePrefix = '';
      task.title = body;
      task._titleSuffix = '';
      task.note = '';
      task._boldTitle = false;
    }

    task.subtasks = [];
    for (let index = task.taskLineIndex + 1; index < task.rawLines.length; index += 1) {
      const subtaskMatch = lineText(task.rawLines[index]).match(SUBTASK_LINE);
      if (!subtaskMatch) continue;
      task.subtasks.push({
        lineIndex: index,
        checked: subtaskMatch[2].toLowerCase() === 'x',
        text: subtaskMatch[4],
        _prefix: subtaskMatch[1],
        _spacing: subtaskMatch[3]
      });
    }
    return task;
  }

  function parse(content) {
    const lines = splitLinesKeepEndings(content);
    const newlineMatch = content.match(/\r\n|\n|\r/);
    const document = {
      newline: newlineMatch ? newlineMatch[0] : '\n',
      prefixRaw: [],
      sections: [],
      nextSectionNumber: 1,
      nextTaskNumber: 1
    };

    const headers = [];
    for (let index = 0; index < lines.length; index += 1) {
      const name = sectionNameFromLine(lines[index]);
      if (name !== null) headers.push({ lineIndex: index, name });
    }
    if (headers.length === 0) {
      document.prefixRaw = lines;
      return document;
    }

    const sectionStarts = headers.map((header, index) => {
      const lowerBound = index === 0 ? 0 : headers[index - 1].lineIndex + 1;
      return findBlockStart(lines, header.lineIndex, lowerBound);
    });
    document.prefixRaw = lines.slice(0, sectionStarts[0]);

    for (let sectionIndex = 0; sectionIndex < headers.length; sectionIndex += 1) {
      const header = headers[sectionIndex];
      const start = sectionStarts[sectionIndex];
      const end = sectionIndex + 1 < headers.length ? sectionStarts[sectionIndex + 1] : lines.length;
      const id = `section-${document.nextSectionNumber++}`;
      const bodyStart = header.lineIndex + 1;
      const taskHeaders = [];
      for (let index = bodyStart; index < end; index += 1) {
        if (isTaskLine(lines[index])) taskHeaders.push(index);
      }

      const taskStarts = taskHeaders.map((taskLineIndex, index) => {
        const lowerBound = index === 0 ? bodyStart : taskHeaders[index - 1] + 1;
        return findBlockStart(lines, taskLineIndex, lowerBound);
      });
      const firstTaskStart = taskStarts.length > 0 ? taskStarts[0] : end;
      const section = {
        id,
        name: header.name,
        headerPrefixRaw: lines.slice(start, header.lineIndex),
        headerRaw: lines[header.lineIndex],
        leadingRaw: lines.slice(bodyStart, firstTaskStart),
        tasks: []
      };

      for (let taskIndex = 0; taskIndex < taskHeaders.length; taskIndex += 1) {
        const taskStart = taskStarts[taskIndex];
        const taskEnd = taskIndex + 1 < taskHeaders.length ? taskStarts[taskIndex + 1] : end;
        const rawLines = lines.slice(taskStart, taskEnd);
        section.tasks.push(parseTask(
          rawLines,
          taskHeaders[taskIndex] - taskStart,
          `task-${document.nextTaskNumber++}`,
          id
        ));
      }
      document.sections.push(section);
    }
    return document;
  }

  function serialize(document) {
    const chunks = [...document.prefixRaw];
    for (const section of document.sections) {
      chunks.push(...section.headerPrefixRaw, section.headerRaw, ...section.leadingRaw);
      for (const task of section.tasks) chunks.push(...task.rawLines);
    }
    return chunks.join('');
  }

  function writeTaskLine(task) {
    const ending = lineEnding(task.rawLines[task.taskLineIndex]);
    const mark = task.checked ? 'x' : ' ';
    task.rawLines[task.taskLineIndex] =
      task._taskPrefix + mark + task._taskSpacing +
      task._titlePrefix + task.title + task._titleSuffix + ending;
  }

  function setTaskChecked(task, checked) {
    task.checked = Boolean(checked);
    writeTaskLine(task);
  }

  function setTaskTitle(task, title) {
    const normalized = normalizeInlineText(title);
    if (!normalized) return false;
    task.title = normalized;
    writeTaskLine(task);
    return true;
  }

  function setTaskNote(task, note) {
    const normalized = normalizeInlineText(note);
    if (normalized === task.note) return false;
    if (!task._boldTitle) {
      task._boldTitle = true;
      task._titlePrefix = '**';
    }
    task.note = normalized;
    task._titleSuffix = `**${normalized ? ` - ${normalized}` : ''}`;
    writeTaskLine(task);
    return true;
  }

  function writeSubtaskLine(task, subtask) {
    const ending = lineEnding(task.rawLines[subtask.lineIndex]);
    task.rawLines[subtask.lineIndex] = subtask._prefix +
      (subtask.checked ? 'x' : ' ') + subtask._spacing + subtask.text + ending;
  }

  function setSubtaskChecked(task, index, checked) {
    const subtask = task.subtasks[index];
    if (!subtask) return false;
    subtask.checked = Boolean(checked);
    writeSubtaskLine(task, subtask);
    return true;
  }

  function setSubtaskText(task, index, text) {
    const normalized = normalizeInlineText(text);
    const subtask = task.subtasks[index];
    if (!subtask) return false;
    if (!normalized) return removeSubtask(task, index);
    subtask.text = normalized;
    writeSubtaskLine(task, subtask);
    return true;
  }

  function removeSubtask(task, index) {
    const subtask = task.subtasks[index];
    if (!subtask) return false;
    task.rawLines.splice(subtask.lineIndex, 1);
    refreshTask(task);
    return true;
  }

  function addSubtask(document, task, text) {
    const normalized = normalizeInlineText(text);
    if (!normalized) return null;
    let insertAt = task.rawLines.length;
    while (insertAt > task.taskLineIndex + 1 && isBlank(task.rawLines[insertAt - 1])) insertAt -= 1;
    const raw = `  - [ ] ${normalized}${document.newline}`;
    task.rawLines.splice(insertAt, 0, raw);
    refreshTask(task);
    return task.subtasks.find((subtask) => subtask.lineIndex === insertAt) || null;
  }

  function documentEndsWithNewline(document) {
    return /(?:\r\n|\n|\r)$/.test(serialize(document));
  }

  function sectionEndsWithNewline(section) {
    const tail = section.tasks.length > 0
      ? section.tasks[section.tasks.length - 1].rawLines
      : section.leadingRaw;
    const last = tail.length > 0 ? tail[tail.length - 1] : section.headerRaw;
    return /(?:\r\n|\n|\r)$/.test(last);
  }

  function normalizeInlineText(value) {
    return String(value == null ? '' : value).replace(/[\r\n]+/g, ' ').trim();
  }

  function createTask(document, section, title) {
    const normalized = normalizeInlineText(title);
    if (!normalized) return null;
    const prefix = sectionEndsWithNewline(section) ? [] : [document.newline];
    return parseTask(
      [...prefix, `- [ ] ${normalized}${document.newline}`],
      prefix.length,
      `task-${document.nextTaskNumber++}`,
      section.id
    );
  }

  function createSection(document, name) {
    const normalized = normalizeInlineText(name);
    if (!normalized) return null;
    const prefix = [];
    const serialized = serialize(document);
    if (serialized && !documentEndsWithNewline(document)) prefix.push(document.newline);
    if (serialized && !/(?:\r\n|\n|\r){2}$/.test(serialize(document) + prefix.join(''))) {
      prefix.push(document.newline);
    }
    const section = {
      id: `section-${document.nextSectionNumber++}`,
      name: normalized,
      headerPrefixRaw: prefix,
      headerRaw: `## ${normalized}${document.newline}`,
      leadingRaw: [],
      tasks: []
    };
    document.sections.push(section);
    return section;
  }

  function setSectionName(section, name) {
    const normalized = normalizeInlineText(name);
    if (!normalized) return false;
    section.name = normalized;
    section.headerRaw = `## ${normalized}${lineEnding(section.headerRaw)}`;
    return true;
  }

  function setElementText(element, text) {
    element.textContent = String(text == null ? '' : text);
    return element;
  }

  return Object.freeze({
    addSubtask,
    createSection,
    createTask,
    normalizeInlineText,
    parse,
    refreshTask,
    removeSubtask,
    serialize,
    setElementText,
    setSectionName,
    setSubtaskChecked,
    setSubtaskText,
    setTaskChecked,
    setTaskNote,
    setTaskTitle,
    splitLinesKeepEndings
  });
}));
