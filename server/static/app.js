// DevRel Guard Frontend Interactive Logic

let scenarios = {};
let currentScenarioKey = 'pydantic';
let currentScanResult = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (window.lucide) lucide.createIcons();
  await loadScenarios();
  setupEventListeners();
  loadScenario(currentScenarioKey);
});

async function loadScenarios() {
  try {
    const res = await fetch('/api/scenarios');
    scenarios = await res.json();
  } catch (err) {
    console.error('Failed to load scenarios:', err);
  }
}

function setupEventListeners() {
  // Scenario Buttons
  document.querySelectorAll('.scenario-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.scenario-btn').forEach((b) => {
        b.classList.remove('active', 'border-cyan-500/40', 'bg-cyan-500/10', 'text-cyan-300');
        b.classList.add('border-dark-700', 'bg-dark-800', 'text-slate-300');
        const dot = b.querySelector('span');
        if (dot) {
          dot.classList.remove('bg-cyan-400');
          dot.classList.add('bg-slate-500');
        }
      });
      btn.classList.add('active', 'border-cyan-500/40', 'bg-cyan-500/10', 'text-cyan-300');
      btn.classList.remove('border-dark-700', 'bg-dark-800', 'text-slate-300');
      const dot = btn.querySelector('span');
      if (dot) {
        dot.classList.remove('bg-slate-500');
        dot.classList.add('bg-cyan-400');
      }

      const key = btn.getAttribute('data-scenario');
      loadScenario(key);
    });
  });

  // Run Agent Button
  const runBtn = document.getElementById('run-agent-btn');
  if (runBtn) {
    runBtn.addEventListener('click', runAgentPipeline);
  }

  // Rule Catalog Modal
  const rulesBtn = document.getElementById('view-rules-btn');
  const closeRulesBtn = document.getElementById('close-rules-btn');
  const modal = document.getElementById('rules-modal');

  if (rulesBtn && modal) {
    rulesBtn.addEventListener('click', async () => {
      modal.classList.remove('hidden');
      await loadRuleCatalog();
    });
  }

  if (closeRulesBtn && modal) {
    closeRulesBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  window.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });
}

function loadScenario(key) {
  currentScenarioKey = key;
  const sc = scenarios[key];
  if (!sc) return;

  // Update Diff
  const diffEl = document.getElementById('diff-preview');
  if (diffEl) diffEl.textContent = sc.diff;

  // Update Source File
  const fileKeys = Object.keys(sc.files || {});
  const firstFile = fileKeys[0] || 'code.py';
  const fileHeader = document.getElementById('file-header-title');
  if (fileHeader) fileHeader.textContent = firstFile;

  const sourceEl = document.getElementById('source-preview');
  if (sourceEl) sourceEl.textContent = sc.files[firstFile] || '';

  // Reset metrics
  resetMetrics();
}

function resetMetrics() {
  document.getElementById('stat-violations').textContent = '0';
  document.getElementById('stat-fixes').textContent = '0';
  document.getElementById('stat-nodes').textContent = '0';
  document.getElementById('stat-duration').textContent = '0.00s';

  const badge = document.getElementById('pr-status-badge');
  badge.textContent = 'Pending Scan';
  badge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700';

  const container = document.getElementById('review-comments-container');
  container.innerHTML = `
    <div class="text-center py-12 text-slate-400">
      <p>Click <strong>"Run Guard Agent"</strong> above to scan PR for breaking changes.</p>
    </div>
  `;

  document.getElementById('ast-inspector-container').innerHTML = `
    <p class="text-slate-400 text-[11px]">Run agent scan to inspect parsed AST call-sites.</p>
  `;

  document.getElementById('summary-container').textContent = 'Summary will appear here after scan completes.';

  // Reset node states
  ['scan', 'mine', 'ast', 'refactor', 'verify', 'pr'].forEach((n) => {
    const el = document.getElementById(`node-${n}`);
    if (el) el.className = 'agent-node bg-dark-850 border border-dark-700/60 rounded-xl p-3 relative overflow-hidden transition-all duration-300';
  });
}

async function runAgentPipeline() {
  const sc = scenarios[currentScenarioKey];
  if (!sc) return;

  const statusEl = document.getElementById('pipeline-status');
  statusEl.textContent = 'Running Agent...';
  statusEl.className = 'text-xs font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/40 px-2.5 py-1 rounded-md animate-pulse';

  const nodeIds = ['scan', 'mine', 'ast', 'refactor', 'verify', 'pr'];

  // Animate node progress
  for (let i = 0; i < nodeIds.length; i++) {
    const prev = nodeIds[i - 1];
    if (prev) {
      const pEl = document.getElementById(`node-${prev}`);
      if (pEl) {
        pEl.classList.remove('running');
        pEl.classList.add('completed');
      }
    }
    const curr = nodeIds[i];
    const cEl = document.getElementById(`node-${curr}`);
    if (cEl) cEl.classList.add('running');
    await new Promise((r) => setTimeout(r, 180));
  }

  try {
    const res = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        diff: sc.diff,
        files: sc.files,
      }),
    });

    const data = await res.json();
    currentScanResult = data;

    // Mark last node completed
    const lastEl = document.getElementById(`node-${nodeIds[nodeIds.length - 1]}`);
    if (lastEl) {
      lastEl.classList.remove('running');
      lastEl.classList.add('completed');
    }

    statusEl.textContent = data.passed ? 'Verified Clean ✅' : 'Violations Patched 🛡️';
    statusEl.className = data.passed
      ? 'text-xs font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2.5 py-1 rounded-md'
      : 'text-xs font-mono text-amber-400 bg-amber-950/60 border border-amber-800/40 px-2.5 py-1 rounded-md';

    renderResults(data);
  } catch (err) {
    console.error('Scan failed:', err);
    statusEl.textContent = 'Scan Error';
  }
}

function renderResults(data) {
  // Update stats
  document.getElementById('stat-violations').textContent = data.violations.length;
  document.getElementById('stat-fixes').textContent = data.fixes.length;
  document.getElementById('stat-nodes').textContent = data.nodes_scanned;
  document.getElementById('stat-duration').textContent = `${data.duration_seconds}s`;

  // Status Badge
  const prBadge = document.getElementById('pr-status-badge');
  if (data.passed) {
    prBadge.textContent = 'All Dependencies Clean ✅';
    prBadge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
  } else {
    prBadge.textContent = `${data.violations.length} Breaking Changes Detected ⚠️`;
    prBadge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20';
  }

  // Render AST Call-Graph Explorer
  renderASTExplorer(data.violations);

  // Render Review Comments
  renderComments(data.violations, data.fixes, data.review_comments);

  // Summary Markdown
  document.getElementById('summary-container').textContent = data.summary_markdown;

  if (window.lucide) lucide.createIcons();
}

function renderASTExplorer(violations) {
  const container = document.getElementById('ast-inspector-container');
  if (!violations || violations.length === 0) {
    container.innerHTML = `<p class="text-emerald-400 text-xs">No breaking AST nodes detected. Code is compatible.</p>`;
    return;
  }

  container.innerHTML = violations
    .map((v) => {
      return `
      <div class="p-2.5 rounded-lg bg-dark-800/80 border border-dark-700/80 flex flex-col space-y-1">
        <div class="flex items-center justify-between">
          <span class="text-cyan-400 font-bold">${v.file_path}:${v.line_number}</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] bg-red-500/20 text-red-300 font-semibold">${v.rule.severity}</span>
        </div>
        <div class="text-[11px] text-slate-300 flex items-center space-x-1.5">
          <span class="text-slate-400">Node:</span>
          <code class="text-indigo-300 font-semibold">${v.node_type}</code>
          <span class="text-slate-400">• Symbol:</span>
          <code class="text-amber-300 font-semibold">${v.symbol}</code>
        </div>
        <div class="text-[10px] text-slate-400 truncate">${v.rule.description}</div>
      </div>
    `;
    })
    .join('');
}

function renderComments(violations, fixes, comments) {
  const container = document.getElementById('review-comments-container');
  if (!comments || comments.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 text-slate-400">
        <i data-lucide="shield-check" class="w-10 h-10 mx-auto mb-2 text-emerald-400"></i>
        <p class="font-medium text-slate-200">No breaking changes detected!</p>
        <p class="text-xs mt-1">This pull request is safe to merge without API regressions.</p>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  const fixMap = {};
  (fixes || []).forEach((f) => {
    fixMap[f.violation_id] = f;
  });

  container.innerHTML = violations
    .map((v) => {
      const fix = fixMap[v.id];
      const origCode = fix ? fix.original_code : v.code_snippet;
      const repCode = fix ? fix.replacement_code : '';
      const confidence = fix ? Math.round(fix.confidence * 100) : 95;

      return `
      <div class="border border-dark-700 rounded-xl bg-dark-850 overflow-hidden shadow-lg">
        <!-- Comment Header -->
        <div class="px-4 py-2.5 bg-dark-800 border-b border-dark-700 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="text-xs font-mono font-bold text-cyan-400">${v.file_path}</span>
            <span class="text-[10px] px-2 py-0.5 rounded bg-dark-700 text-slate-300 font-mono">Line ${v.line_number}</span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold">Confidence: ${confidence}%</span>
            <span class="text-[10px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-bold">${v.rule.severity}</span>
          </div>
        </div>

        <!-- Comment Body -->
        <div class="p-4 space-y-3 text-xs">
          <div>
            <span class="font-semibold text-slate-200">Issue:</span>
            <span class="text-slate-300 ml-1">${v.rule.description}</span>
          </div>

          <!-- GitHub Style Suggestion Diff -->
          <div class="github-suggestion-box">
            <div class="github-suggestion-header">
              <span>Suggested change</span>
              <button onclick="applyFix('${v.file_path}')" class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[10px] flex items-center space-x-1 transition">
                <i data-lucide="git-merge" class="w-3 h-3"></i>
                <span>Apply Suggestion</span>
              </button>
            </div>
            <div class="font-mono text-xs p-1">
              <div class="github-diff-line-del">- ${escapeHtml(origCode)}</div>
              <div class="github-diff-line-add">+ ${escapeHtml(repCode)}</div>
            </div>
          </div>

          <div class="text-[11px] text-slate-400 pt-1 flex items-center justify-between">
            <span>Rule: <code class="text-slate-300 font-mono">${v.rule.id}</code></span>
            <a href="${v.rule.migration_guide_url}" target="_blank" class="text-cyan-400 hover:underline flex items-center space-x-1">
              <span>Official Migration Docs</span>
              <i data-lucide="external-link" class="w-3 h-3"></i>
            </a>
          </div>
        </div>
      </div>
    `;
    })
    .join('');

  if (window.lucide) lucide.createIcons();
}

function applyFix(filePath) {
  if (!currentScanResult || !currentScanResult.refactored_files) return;
  const refactored = currentScanResult.refactored_files[filePath];
  if (refactored) {
    const sourceEl = document.getElementById('source-preview');
    sourceEl.textContent = refactored;
    sourceEl.classList.add('ring-2', 'ring-emerald-500');
    setTimeout(() => sourceEl.classList.remove('ring-2', 'ring-emerald-500'), 1500);

    const fileHeader = document.getElementById('file-header-title');
    if (fileHeader) fileHeader.textContent = `${filePath} (Patched ✅)`;
  }
}

async function loadRuleCatalog() {
  const container = document.getElementById('rules-list-container');
  try {
    const res = await fetch('/api/rules');
    const rules = await res.json();

    container.innerHTML = rules
      .map((r) => {
        return `
        <div class="p-4 rounded-xl bg-dark-850 border border-dark-700/80 space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded text-[10px] bg-cyan-500/10 text-cyan-400 font-bold uppercase">${r.package}</span>
              <span class="font-mono font-bold text-white text-xs">${r.symbol}</span>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 font-bold">${r.severity}</span>
          </div>
          <p class="text-slate-300 text-xs leading-relaxed">${r.description}</p>
          <div class="grid grid-cols-2 gap-2 font-mono text-[11px] pt-1">
            <div class="p-2 rounded bg-dark-950 border border-dark-800 text-red-300">
              <span class="text-[9px] uppercase text-slate-500 block mb-0.5 font-sans">Old API</span>
              ${escapeHtml(r.old_pattern)}
            </div>
            <div class="p-2 rounded bg-dark-950 border border-dark-800 text-emerald-300">
              <span class="text-[9px] uppercase text-slate-500 block mb-0.5 font-sans">New API</span>
              ${escapeHtml(r.new_pattern)}
            </div>
          </div>
        </div>
      `;
      })
      .join('');
  } catch (err) {
    container.innerHTML = `<p class="text-red-400">Failed to load rules.</p>`;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
