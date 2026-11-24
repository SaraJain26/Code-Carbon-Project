import { Component, type ErrorInfo, type ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, AlertCircle, ArrowLeft, ArrowRight, ChevronDown, ChevronRight, Clock3, Code2, Copy, Download, FileCode2, FileText, Flame, Folder, FolderArchive, Gauge, Globe2, Leaf, LoaderCircle, Moon, Play, Search, Sparkles, Sun, Upload, X } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { AnalyzeResponse, ForecastResponse, ProjectAnalyzeResponse, ProjectFileResult, LocationSuggestion } from './api-types';
import { getCategoryCounts, getEssBands, getEssFineHistogram, getOverviewTakeaways, getScopeFiles, getScopeMetrics, isTestOrExamplePath } from './project-scope';

const CARBON_METHOD_NOTE = 'Carbon = modeled energy (relative J -> kWh) x grid intensity (gCO2eq/kWh). The energy score is a relative model, so carbon is a modeled comparison, not a measured emission.';
const LOCAL_TIME_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata';
const LOCAL_TIME_ZONE_LABEL = ['Asia/Kolkata', 'Asia/Calcutta'].includes(LOCAL_TIME_ZONE) ? 'IST' : LOCAL_TIME_ZONE;

function ChartFallback({ title, message }: { title?: string; message?: string }) {
  return (
    <div className="empty-chart-fallback">
      <AlertCircle size={22} style={{ color: 'var(--muted)', marginBottom: '8px' }} />
      <p style={{ margin: 0, fontWeight: 600, color: 'var(--ink)', fontSize: '13px' }}>
        {title || 'No data available for this visualization'}
      </p>
      {message && <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: '11px' }}>{message}</p>}
    </div>
  );
}

type RankedMetricItem = { name: string; relativePath: string; value: number; valueLabel?: string; valueHelp?: string };

function uniqueRankedPath(path: string, allPaths: string[], limit = 34): string {
  const parts = path.replace(/\\/g, '/').split('/');
  let depth = Math.min(2, parts.length);
  for (; depth < parts.length; depth += 1) {
    const suffix = parts.slice(-depth).join('/');
    if (allPaths.filter(candidate => candidate.replace(/\\/g, '/').endsWith(`/${suffix}`) || candidate.replace(/\\/g, '/') === suffix).length === 1) break;
  }
  const suffix = parts.slice(-depth).join('/');
  const candidate = `${depth < parts.length ? '…/' : ''}${suffix}`;
  if (candidate.length <= limit) return candidate;
  const parent = parts.slice(Math.max(0, parts.length - depth), -1).join('/');
  const filename = parts.at(-1) || path;
  const parentPart = parent ? `${parent}/` : '';
  const filenameBudget = Math.max(8, limit - parentPart.length - 5);
  const filenameStart = Math.ceil(filenameBudget / 2);
  const filenameEnd = Math.floor(filenameBudget / 2);
  return `…/${parentPart}${filename.slice(0, filenameStart)}…${filename.slice(-filenameEnd)}`;
}

function RankedMetricBars({ items, color, formatValue, label, valueHelp, colorForValue, allPaths }: {
  items: RankedMetricItem[];
  color: string;
  formatValue: (value: number) => string;
  label: string;
  valueHelp?: string;
  colorForValue?: (value: number) => string;
  allPaths?: string[];
}) {
  if (!items.length) return <ChartFallback title="No successful file results" />;
  const maxValue = Math.max(...items.map(item => item.value), 0);
  if (maxValue <= 0) return <ChartFallback title="No non-zero values to compare" />;
  const pathCandidates = allPaths || items.map(item => item.relativePath);
  return (
    <div className="ranked-metric-list" role="list" aria-label={label}>
      {items.map((item, index) => (
        <div className="ranked-metric-row" role="listitem" key={`${item.relativePath}-${index}`} title={`${item.relativePath} · ${formatValue(item.value)}${item.valueHelp || valueHelp ? ` · ${item.valueHelp || valueHelp}` : ''}`}>
          <span className="ranked-metric-name" title={item.relativePath}>{uniqueRankedPath(item.relativePath, pathCandidates)}</span>
          <span className={`file-scope-chip ${isTestOrExamplePath(item.relativePath) ? 'is-test' : 'is-source'}`}>{isTestOrExamplePath(item.relativePath) ? 'test' : 'source'}</span>
          <span className="ranked-metric-track" aria-hidden="true">
            <span className="ranked-metric-fill" style={{ width: `${Math.max(2, (item.value / maxValue) * 100)}%`, background: colorForValue?.(item.value) || color }} />
          </span>
          <strong className="ranked-metric-value">{item.valueLabel || formatValue(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}

type ComparisonRow = { name: string; before: number; after: number; unit: string; decimals?: number };

const PYTHON_KEYWORDS = new Set(['and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield', 'None']);

function projectFixState(file: ProjectFileResult): 'applied' | 'rejected' | 'not_auto_fixable' | 'no_issues' | 'failed' {
  if (file.status === 'error') return 'failed';
  if (file.findings_count === 0) return 'no_issues';
  if (file.fix_status === 'applied') return 'applied';
  if (file.fix_status?.startsWith('rejected')) return 'rejected';
  return 'not_auto_fixable';
}

const fixStateLabels: Record<string, string> = {
  applied: 'Applied', rejected: 'Rejected', not_auto_fixable: 'Not auto-fixable', no_issues: 'No issues found', failed: 'Analysis failed'
};

function PythonCodeBlock({ code, startLine = 1 }: { code: string; startLine?: number }) {
  const tokenPattern = /(#.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b)/g;
  return (
    <pre className="python-code-block"><code>{code.split(/\r?\n/).map((line, lineIndex) => {
      const tokens: React.ReactNode[] = [];
      let cursor = 0;
      for (const match of line.matchAll(tokenPattern)) {
        const token = match[0];
        const index = match.index ?? 0;
        if (index > cursor) tokens.push(line.slice(cursor, index));
        const className = token.startsWith('#') ? 'python-comment'
          : token.startsWith('"') || token.startsWith("'") ? 'python-string'
            : /^\d/.test(token) ? 'python-number'
              : PYTHON_KEYWORDS.has(token) ? 'python-keyword' : undefined;
        tokens.push(className ? <span className={className} key={`${lineIndex}-${index}`}>{token}</span> : token);
        cursor = index + token.length;
      }
      if (cursor < line.length) tokens.push(line.slice(cursor));
      return <span className="python-code-line" key={lineIndex}><span className="python-line-number">{startLine + lineIndex}</span><span>{tokens.length ? tokens : ' '}</span></span>;
    })}</code></pre>
  );
}

function CopyCodeButton({ code, label = 'Copy code' }: { code: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = code;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      textarea.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };
  return <button className="copy-code-button" type="button" onClick={copy}><Copy size={13} />{copied ? 'Copied' : label}</button>;
}

function unifiedDiffRows(original: string, replacement: string): { sign: ' ' | '-' | '+'; text: string }[] {
  const before = original.split(/\r?\n/);
  const after = replacement.split(/\r?\n/);
  if (before.length * after.length > 40000) return [...before.map(text => ({ sign: '-' as const, text })), ...after.map(text => ({ sign: '+' as const, text }))];
  const lcs = Array.from({ length: before.length + 1 }, () => Array(after.length + 1).fill(0));
  for (let i = before.length - 1; i >= 0; i -= 1) for (let j = after.length - 1; j >= 0; j -= 1) {
    lcs[i][j] = before[i] === after[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
  }
  const rows: { sign: ' ' | '-' | '+'; text: string }[] = [];
  let i = 0, j = 0;
  while (i < before.length && j < after.length) {
    if (before[i] === after[j]) rows.push({ sign: ' ', text: before[i++] }), j++;
    else if (lcs[i + 1][j] >= lcs[i][j + 1]) rows.push({ sign: '-', text: before[i++] });
    else rows.push({ sign: '+', text: after[j++] });
  }
  while (i < before.length) rows.push({ sign: '-', text: before[i++] });
  while (j < after.length) rows.push({ sign: '+', text: after[j++] });
  return rows;
}

const RULE_NAMES: Record<string, string> = {
  'EKB-COMP-001': 'Nested loops',
  'EKB-COMP-002': 'Repeated computation in a loop',
  'EKB-COMP-003': 'Recursive computation',
  'EKB-IO-001': 'Repeated file I/O',
  'EKB-NET-001': 'Repeated network request',
  'EKB-MEM-001': 'Temporary allocation in a loop',
  'EKB-ASYNC-001': 'Synchronous blocking in async',
};

function LocationCodeComparison({ original, replacement, diff, startLine = 1 }: {
  original: string;
  replacement: string;
  diff?: string | null;
  startLine?: number;
}) {
  const [showDiff, setShowDiff] = useState(false);
  const safeOriginal = original || '# Original source unavailable';
  const safeReplacement = replacement;
  const hasReplacement = Boolean(safeReplacement.trim());
  const diffRows = diff
    ? diff.split(/\r?\n/).filter(line => line && !line.startsWith('---') && !line.startsWith('+++') && !line.startsWith('@@'))
      .map(line => ({ sign: (line[0] === '+' || line[0] === '-' ? line[0] : ' ') as ' ' | '-' | '+', text: line.slice(1) }))
    : unifiedDiffRows(safeOriginal, safeReplacement);
  const diffText = diffRows.map(row => `${row.sign}${row.text}`).join('\n');

  return (
    <div className="location-comparison">
      {hasReplacement && <div className="location-comparison-toolbar">
        <button className="small-button diff-toggle-btn" type="button" onClick={() => setShowDiff(value => !value)}>
          {showDiff ? 'Side-by-side view' : 'Unified diff'}
        </button>
      </div>}
      {showDiff && hasReplacement ? (
        <div className="location-diff">
          <div className="code-block-heading">
            <strong>Unified diff</strong>
            <CopyCodeButton code={diffText} label="Copy diff" />
          </div>
          <pre className="python-code-block unified-diff-block">
            <code>
              {diffRows.map((row, index) => (
                <span
                  className={`python-code-line diff-line diff-${row.sign === '+' ? 'added' : row.sign === '-' ? 'removed' : 'context'}`}
                  key={index}
                >
                  <span className="python-line-number">{startLine + index}</span>
                  <span className="diff-sign">{row.sign}</span>
                  <span>{row.text || ' '}</span>
                </span>
              ))}
            </code>
          </pre>
        </div>
      ) : (
        <div className="code-change-columns location-code-columns">
          <section>
            <div className="code-block-heading">
              <strong>Original code</strong>
              <CopyCodeButton code={safeOriginal} label="Copy original" />
            </div>
            <PythonCodeBlock code={safeOriginal} startLine={startLine} />
          </section>
          <section>
            <div className="code-block-heading">
              <strong>Suggested replacement</strong>
            <CopyCodeButton code={hasReplacement ? safeReplacement : safeOriginal} label="Copy" />
            </div>
            <PythonCodeBlock code={hasReplacement ? safeReplacement : safeOriginal} startLine={startLine} />
          </section>
        </div>
      )}
    </div>
  );
}

function SuggestedChangeCard({ card }: { card: {
  key: string; title: string; source: string; finding: any; original: string;
  replacement: string; diff?: string | null; startLine: number; reason?: string;
} }) {
  const replacement = card.replacement || `${card.original.trimEnd()}\n# Suggested local rewrite`;

  return (
    <details className="location-code-card">
      <summary className="location-code-card-header"><h3>{card.title}</h3></summary>
      <LocationCodeComparison
        original={card.original}
        replacement={replacement}
        diff={card.diff}
        startLine={card.startLine}
      />
    </details>
  );
}

function CodeChangesSection({ filename, sourceCode, findings, locationSuggestions = [] }: {
  filename: string;
  sourceCode: string;
  findings: any[];
  autoFixes?: any[];
  manualFixes?: any[];
  recommendations?: any[];
  locationSuggestions?: LocationSuggestion[];
}) {
  const sourceLines = sourceCode.split(/\r?\n/);
  const totalCount = findings.length;

  const findingCards = findings.map((finding, index) => {
    const issueLine = finding.line_number;
    const suggestion = locationSuggestions.find(item => item.rule_id === finding.rule_id && item.line_number === (issueLine ?? null));
    const replacement = suggestion?.replacement_code || '';
    const lineStart = suggestion?.line_start || issueLine || 1;
    const contextOriginal = suggestion?.original_code || (Number.isInteger(lineStart) ? sourceLines.slice(Math.max(0, lineStart - 1), Math.min(sourceLines.length, lineStart + 4)).join('\n') : '');

    const ruleName = RULE_NAMES[finding.rule_id] || finding.message || finding.rule_id;
    return {
      key: `${finding.rule_id}-${issueLine}-${index}`,
      title: `${ruleName} · ${filename}:${issueLine || lineStart}`,
      original: contextOriginal,
      replacement,
      diff: suggestion?.diff,
      startLine: lineStart,
      source: sourceCode,
      finding,
      reason: suggestion?.reason,
    };
  });

  return (
    <div className="code-changes-file">
      <div className="recommendations-summary-line">
        <p>{totalCount} findings</p>
      </div>
      {findingCards.length ? (
        <div className="location-card-list">
          {findingCards.map(card => <SuggestedChangeCard key={card.key} card={card} />)}
        </div>
      ) : null}
    </div>
  );
}

function ProjectCodeChangesSection({ projectResult, projectFiles, projectZipFile, excludeTestCode, targetPath, clearTargetPath }: {
  projectResult: ProjectAnalyzeResponse;
  projectFiles: ScannedFile[];
  projectZipFile: File | null;
  excludeTestCode: boolean;
  targetPath: string | null;
  clearTargetPath: () => void;
}) {
  const [localSources, setLocalSources] = useState<Map<string, string>>(() => new Map());
  const sourceScope = projectResult.timestamp || projectResult.project_name;
  const sourceKey = (path: string) => `${sourceScope}::${path.replace(/\\/g, '/').replace(/^\.\//, '')}`;
  const filesWithFindings = projectResult.files.filter(file =>
    file.status === 'success' && file.single_file_response?.pipeline_raw?.energy_smell_report?.findings?.length
  );
  const visibleFilesWithFindings = filesWithFindings.filter(file => (!excludeTestCode || !isTestOrExamplePath(file.relative_path)) && (!targetPath || file.relative_path === targetPath));

  let totalFindingsCount = 0;
  for (const file of visibleFilesWithFindings) {
    const rawFindings = file.single_file_response?.pipeline_raw?.energy_smell_report?.findings || [];
    totalFindingsCount += rawFindings.length;
  }

  const findingCards: {
    key: string;
    title: string;
    original: string;
    replacement: string;
    diff?: string | null;
    startLine: number;
    source: string;
    finding: any;
    reason?: string;
  }[] = [];

  for (const file of visibleFilesWithFindings) {
    const response = file.single_file_response!;
    const source = file.original_code || response.original_code || localSources.get(sourceKey(file.relative_path)) || '';
    const lines = source.split(/\r?\n/);
    const findings = response.pipeline_raw?.energy_smell_report?.findings || [];
    const suggestions = response.location_suggestions || [];

    for (let index = 0; index < findings.length; index++) {
      const finding = findings[index];
      const ruleId = finding.rule_id || 'UNKNOWN';
      const line = Number(finding.line_number) || 0;
      const suggestion = suggestions.find(item => item.rule_id === ruleId && item.line_number === (line || null));
      const replacement = suggestion?.replacement_code || '';

      const lineStart = suggestion?.line_start || Math.max(1, line - 3);
      const original = suggestion?.original_code || (line ? lines.slice(Math.max(0, line - 4), Math.min(lines.length, line + 3)).join('\n') : '');

      const ruleName = RULE_NAMES[ruleId] || finding.message || ruleId;

      findingCards.push({
        key: `${file.relative_path}:${ruleId}:${line}:${index}`,
        title: `${ruleName} · ${file.relative_path}:${line || lineStart}`,
        original,
        replacement,
        diff: suggestion?.diff,
        startLine: lineStart,
        source,
        finding,
        reason: suggestion?.reason,
      });
    }
  }

  useEffect(() => {
    let cancelled = false;
    const normalizePath = (value: string) => value.replace(/\\/g, '/').replace(/^\.\//, '');
    const missingSources = filesWithFindings.filter(file =>
      !file.original_code && !file.single_file_response?.original_code && !localSources.has(sourceKey(file.relative_path))
    );
    if (!missingSources.length) return;

    void (async () => {
      const nextSources = new Map(localSources);
      for (const item of projectFiles) {
        const path = normalizePath(item.path);
        if (missingSources.some(file => normalizePath(file.relative_path) === path)) {
          try { nextSources.set(sourceKey(path), await item.file.text()); } catch { /* Leave missing source visible as unavailable. */ }
        }
      }
      if (projectZipFile) {
        try {
          const zip = await JSZip.loadAsync(projectZipFile);
          const zipEntries = Object.keys(zip.files).filter(path => !zip.files[path].dir);
          for (const file of missingSources) {
            const target = normalizePath(file.relative_path);
            const matchedPath = zipEntries.find(path => normalizePath(path) === target);
            const entry = matchedPath ? zip.file(matchedPath) : null;
            if (entry) nextSources.set(sourceKey(file.relative_path), await entry.async('string'));
          }
        } catch { /* Keep any folder-source matches already loaded. */ }
      }
      if (!cancelled && nextSources.size !== localSources.size) setLocalSources(nextSources);
    })();

    return () => { cancelled = true; };
  }, [projectResult, projectFiles, projectZipFile, localSources]);

  return (
    <section className="panel suggested-code-section">
      <div className="panel-head">
        <div>
          <p className="overline">ISSUE-BY-ISSUE FIXES</p>
          <h3>Suggested Code Changes</h3>
        </div>
      </div>
      {targetPath && (
        <p className="recommendation-target-note">
          Showing recommendations for <strong title={targetPath}>{targetPath}</strong>{' '}
          <button type="button" className="text-button" onClick={clearTargetPath}>Show all files</button>
        </p>
      )}
      <div className="recommendations-summary-line">
        <p>{totalFindingsCount} findings</p>
      </div>
      {findingCards.length ? (
        <div className="location-card-list">
          {findingCards.map(card => <SuggestedChangeCard key={card.key} card={card} />)}
        </div>
      ) : null}
    </section>
  );
}

function MetricComparison({ rows }: { rows: ComparisonRow[] }) {
  if (!rows.length) return null;
  return (
    <div className="comparison-table-wrap">
      <table className="comparison-table">
        <thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Change</th></tr></thead>
        <tbody>
          {rows.map(row => {
            const delta = row.before > 0 ? ((row.after - row.before) / row.before) * 100 : null;
            const unchanged = Math.abs(row.after - row.before) < Math.pow(10, -(row.decimals ?? 3)) / 2;
            const changeClass = unchanged ? 'unchanged' : delta !== null && delta < 0 ? 'change-good' : 'change-worse';
            const changeText = unchanged
              ? 'No modeled change'
              : delta === null
              ? (row.after === 0 ? 'No change' : 'Increased from zero')
              : `${Math.abs(delta).toFixed(1)}% ${delta < 0 ? 'lower' : 'higher'}`;
            return (
              <tr key={row.name}>
                <th scope="row">{row.name}</th>
                <td>{fixed(row.before, row.decimals ?? 3)} <span>{row.unit}</span></td>
                <td>{fixed(row.after, row.decimals ?? 3)} <span>{row.unit}</span></td>
                <td><strong className={changeClass}>{changeText}</strong></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CarbonScenarioComparison({ result, currentIntensity }: { result: AnalyzeResponse; currentIntensity?: number }) {
  if (result.carbon_before === undefined || result.carbon_after_now === undefined || result.carbon_after_green === undefined) return null;
  const windowLabel = result.window_start && result.window_end
    ? `${new Date(result.window_start).toLocaleString()} – ${new Date(result.window_end).toLocaleTimeString()}`
    : 'Forecast window unavailable';
  const rows = [
    { name: 'Before · run now', value: result.carbon_before, intensity: currentIntensity, when: 'Current grid' },
    { name: 'After · run now', value: result.carbon_after_now, intensity: currentIntensity, when: 'Current grid' },
    { name: 'After · green window', value: result.carbon_after_green, intensity: result.green_window_intensity, when: windowLabel },
  ];
  return (
    <section className="panel">
      <div className="panel-head">
        <div><p className="overline">THREE-ROW CARBON COMPARISON</p><h3>Code change and execution timing</h3></div>
      <span title={CARBON_METHOD_NOTE}>Unweighted modeled footprint in gCO₂eq/run ⓘ; CIRS is shown separately</span>
      </div>
      <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead><tr><th>Scenario</th><th>Intensity</th><th>Execution</th><th>Modeled gCO₂eq/run</th></tr></thead>
          <tbody>{rows.map(row => <tr key={row.name}>
            <th scope="row" title={CARBON_METHOD_NOTE}>{row.name}</th>
            <td title={CARBON_METHOD_NOTE}>{row.intensity === undefined ? '—' : `${fixed(row.intensity, 2)} gCO₂eq/kWh`}</td>
            <td>{row.when}</td>
            <td title={CARBON_METHOD_NOTE}>{fixed(row.value, 9)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <p className="soft-copy" style={{ marginBottom: 0 }}>
        Code only: {fixed(result.code_only_pct, 2)}% · Schedule only: {fixed(result.schedule_only_pct, 2)}% · Total: {fixed(result.total_pct, 2)}%
      </p>
      {result.cirs_before !== undefined && result.cirs_after !== undefined && (
        <p className="soft-copy">Separate unitless CIRS risk score: {fixed(result.cirs_before, 9)} before → {fixed(result.cirs_after, 9)} after.</p>
      )}
      {result.auto_applied_fixes?.length === 0 && <p className="soft-copy">No modeled change: no automatic code fix was applied.</p>}
    </section>
  );
}
import * as pdfjsLib from 'pdfjs-dist';
import mammoth from 'mammoth';
import JSZip from 'jszip';
import './App.css';

const defaultApiUrl = import.meta.env.DEV
  ? '/api'
  : 'https://code-carbon-projectuvicorn-api-main-app.onrender.com/api';
const rawApiUrl = (import.meta.env.VITE_API_URL || defaultApiUrl).trim().replace(/\/+$/, '');
const API = rawApiUrl.endsWith('/api') ? rawApiUrl : `${rawApiUrl}/api`;
const apiRequestUrl = (path: string) => new URL(`${API}${path}`, window.location.href).toString();
const API_REQUEST_TIMEOUT_MS = 70_000;
const SERVER_WAKEUP_MESSAGE = 'Waking up the server, this can take up to a minute.';
let initialApiRequestStarted = false;

async function fetchApi(
  requestUrl: string,
  options: RequestInit = {},
  setRequestNotice?: (message: string | null) => void,
): Promise<Response> {
  const absoluteUrl = new URL(requestUrl, window.location.href).toString();
  const isInitialRequest = !initialApiRequestStarted;
  initialApiRequestStarted = true;
  const attempts = isInitialRequest ? 2 : 1;

  if (isInitialRequest) setRequestNotice?.(SERVER_WAKEUP_MESSAGE);

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const controller = new AbortController();
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, API_REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(absoluteUrl, { ...options, signal: controller.signal });
      if (isInitialRequest && attempt === 0 && [502, 503, 504].includes(response.status)) {
        try { await response.body?.cancel(); } catch { /* Retry the first request once. */ }
        continue;
      }
      if (isInitialRequest) setRequestNotice?.(null);
      return response;
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === 'AbortError';
      const retryable = timedOut || isAbort || error instanceof TypeError;
      if (isInitialRequest && attempt === 0 && retryable) continue;
      if (timedOut) {
        throw new Error(`Request to ${absoluteUrl} timed out after ${API_REQUEST_TIMEOUT_MS / 1000} seconds.`);
      }
      if (isAbort) throw new Error(`Request to ${absoluteUrl} was cancelled before a response arrived.`);
      if (error instanceof TypeError) {
        throw new Error(`Network failure calling ${absoluteUrl}: ${error.message}`);
      }
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  throw new Error(`The first request to ${absoluteUrl} failed after one retry.`);
}

class TabErrorBoundary extends Component<{
  tabName: string;
  children: ReactNode;
}, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[Code-Carbon] ${this.props.tabName} tab render failed:`, error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return <section className="panel tab-error" role="alert">
        <h2>{this.props.tabName} could not be rendered</h2>
        <p>{this.state.error.name}: {this.state.error.message}</p>
      </section>;
    }
    return this.props.children;
  }
}

function normalizeProjectResponse(payload: Partial<ProjectAnalyzeResponse>): ProjectAnalyzeResponse {
  const before = payload.project_before ?? {
    energy: Number(payload.total_energy_joules ?? 0),
    cirs: Number(payload.total_cirs ?? 0),
    ess: Number(payload.avg_ess ?? 0) * Number(payload.successful_files ?? 0),
  };
  const after = payload.project_after ?? before;
  const delta = payload.project_delta ?? {
    energy: after.energy - before.energy,
    cirs: after.cirs - before.cirs,
    ess: after.ess - before.ess,
  };
  const deltaPercent = payload.project_delta_percent ?? {
    energy: before.energy ? delta.energy / before.energy * 100 : 0,
    cirs: before.cirs ? delta.cirs / before.cirs * 100 : 0,
    ess: before.ess ? delta.ess / before.ess * 100 : 0,
  };
  return {
    ...payload,
    project_before: before,
    project_after: after,
    project_delta: delta,
    project_delta_percent: deltaPercent,
    scheduling: payload.scheduling ?? { status: 'unavailable', error: 'The response did not include a scheduling forecast.' },
    auto_fixable_count: Number(payload.auto_fixable_count ?? 0),
    auto_applied_count: Number(payload.auto_applied_count ?? 0),
    files: Array.isArray(payload.files) ? payload.files : [],
  } as ProjectAnalyzeResponse;
}

function isCurrentProjectResponse(payload: Partial<ProjectAnalyzeResponse>): boolean {
  return Boolean(payload.project_before && payload.project_after && payload.project_delta
    && payload.project_delta_percent && Number.isFinite(payload.auto_fixable_count)
    && Number.isFinite(payload.auto_applied_count) && Array.isArray(payload.files)
    && payload.scheduling !== undefined);
}

const PROJECT_REPORT_STORAGE_KEY = 'codecarbon-project-report-v1';

function readSavedProjectReport(): ProjectAnalyzeResponse | null {
  try {
    const value = sessionStorage.getItem(PROJECT_REPORT_STORAGE_KEY);
    if (!value) return null;
    const parsed = JSON.parse(value) as Partial<ProjectAnalyzeResponse>;
    return Array.isArray(parsed.files) && parsed.timestamp && parsed.carbon_intensity != null
      ? normalizeProjectResponse(parsed)
      : null;
  } catch {
    return null;
  }
}

function saveProjectReport(report: ProjectAnalyzeResponse): void {
  try {
    // The file-level original_code is enough to rebuild recommendations; drop
    // the duplicate copy nested in each single-file response to keep this small.
    const compact = {
      ...report,
      files: report.files.map(file => ({
        ...file,
        single_file_response: file.single_file_response
          ? { ...file.single_file_response, original_code: undefined }
          : undefined,
      })),
    };
    sessionStorage.setItem(PROJECT_REPORT_STORAGE_KEY, JSON.stringify(compact));
  } catch (error) {
    console.warn('[Code-Carbon] Could not preserve the loaded project report for this browser session.', error);
  }
}

async function readApiJson<T>(response: Response, requestUrl: string): Promise<T> {
  const contentType = response.headers.get('content-type') || '(none)';
  const rawBody = await response.text();
  const bodyEmpty = rawBody.trim().length === 0;
  const isHtml = /text\/html/i.test(contentType) || /^\s*<(?:!doctype\s+html|html\b)/i.test(rawBody);
  let parsed: T | undefined;
  let parseError: string | undefined;

  if (!bodyEmpty) {
    try {
      parsed = JSON.parse(rawBody) as T;
    } catch (error) {
      parseError = error instanceof Error ? error.message : String(error);
    }
  }

  if (!response.ok || bodyEmpty || parseError) {
    console.error('[Code-Carbon] Invalid API response', {
      url: requestUrl,
      status: response.status,
      contentType,
      bodyEmpty,
      isHtml,
      body: rawBody.slice(0, 2000),
      parseError
    });

    if (!response.ok) {
      const rawDetail = (parsed as any)?.detail;
      let detail = '';
      if (typeof rawDetail === 'string') {
        detail = rawDetail;
      } else if (Array.isArray(rawDetail)) {
        detail = rawDetail.map(d => typeof d === 'string' ? d : (d?.msg || JSON.stringify(d))).join('; ');
      } else if (rawDetail && typeof rawDetail === 'object') {
        detail = (rawDetail as any).msg || JSON.stringify(rawDetail);
      }
      throw new Error(detail
        ? `API request to ${requestUrl} failed: HTTP ${response.status}: ${detail}`
        : `API request to ${requestUrl} failed: HTTP ${response.status}`);
    }
    if (bodyEmpty) throw new Error(`API request to ${requestUrl} failed: HTTP ${response.status} (empty response)`);
    if (isHtml) throw new Error(`API request to ${requestUrl} failed: HTTP ${response.status} (received HTML instead of JSON)`);
    throw new Error(`API request to ${requestUrl} failed: HTTP ${response.status} (invalid JSON response)`);
  }

  return parsed as T;
}

type View = 'workspace' | 'results' | 'recommendations' | 'impact' | 'schedule' | 'project';
const samples = [
  { label: 'Heavy workload', file: 'sample_heavy_workload.py', code: `def process(items):\n    output = []\n    for item in items:\n        factor = (42 * 3.14159) ** 2\n        output.append(item * factor)\n    return output\n\nprocess(range(200000))` },
  { label: 'Mixed smells', file: 'sample_mixed_smells.py', code: `import requests\n\ndef fetch_all(urls):\n    results = []\n    for url in urls:\n        results.append(requests.get(url).json())\n    return results` },
  { label: 'Clean example', file: 'sample_clean.py', code: `def transform(items):\n    multiplier = 4200\n    return [item * multiplier for item in items]` }
];
const display = (x: unknown, fallback = '—') => x === null || x === undefined || x === '' ? fallback : String(x);
const fixed = (x: unknown, places = 2) => typeof x === 'number' && Number.isFinite(x)
  ? x.toLocaleString('en-US', { minimumFractionDigits: places, maximumFractionDigits: places })
  : '—';

interface ScannedFile {
  file: File;
  path: string;
}

interface ProjectSummary {
  name: string;
  type: 'folder' | 'zip';
  count?: number;
  sizeKb?: number;
  samplePaths?: string[];
}

export default function App() {
  const [view, setView] = useState<View>(() => readSavedProjectReport() ? 'project' : 'workspace');
  const [analysisMode, setAnalysisMode] = useState<'file' | 'project'>(() => readSavedProjectReport() ? 'project' : 'file');
  const [health, setHealth] = useState('checking');
  const [zones, setZones] = useState<any[]>([]);
  const [zone, setZone] = useState('IN');
  const [query, setQuery] = useState('');
  const [code, setCode] = useState('');
  const [filename, setFilename] = useState('untitled.py');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [globalAverage, setGlobalAverage] = useState(true);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [projectResult, setProjectResult] = useState<ProjectAnalyzeResponse | null>(() => readSavedProjectReport());
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [projectResponseOutdated, setProjectResponseOutdated] = useState(false);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('codecarbon-theme') === 'dark');
  const [sourceOnly, setSourceOnly] = useState(false);
  const [scopeMenuOpen, setScopeMenuOpen] = useState(false);
  const [recommendationTargetPath, setRecommendationTargetPath] = useState<string | null>(null);
  const excludeTestCode = sourceOnly;
  const setExcludeTestCode = setSourceOnly;
  const [projectMetricTab, setProjectMetricTab] = useState<'complexity' | 'ess' | 'cirs'>('complexity');

  const [projectZipFile, setProjectZipFile] = useState<File | null>(null);
  const [projectFiles, setProjectFiles] = useState<ScannedFile[]>([]);
  const [projectSummary, setProjectSummary] = useState<ProjectSummary | null>(null);

  const [tableSearch, setTableSearch] = useState('');
  const [fileStatusFilter, setFileStatusFilter] = useState<'all' | 'success' | 'error'>('all');
  const [impactStatusFilter, setImpactStatusFilter] = useState<'all' | 'applied' | 'rejected' | 'not_auto_fixable' | 'no_issues'>('all');
  const [sortColumn, setSortColumn] = useState<'filename' | 'lines_of_code' | 'findings_count' | 'sci' | 'ess' | 'cirs' | 'energy_joules'>('energy_joules');
  const [sortAsc, setSortAsc] = useState(false);

  const fileInput = useRef<HTMLInputElement>(null);
  const projectFolderInput = useRef<HTMLInputElement>(null);
  const projectZipInput = useRef<HTMLInputElement>(null);

  useEffect(() => { (async () => {
    try {
      const healthUrl = apiRequestUrl('/health');
      const zonesUrl = apiRequestUrl('/zones');
      const healthResponse = await fetchApi(healthUrl, {}, setNotice);
      await readApiJson<{ status: string }>(healthResponse, healthUrl);
      const zonesResponse = await fetchApi(zonesUrl);
      const data = await readApiJson<Record<string, unknown>>(zonesResponse, zonesUrl);
      setHealth('healthy');
      setZones(Object.entries(data).map(([key, item]) => ({ key, ...(item as object) })));
    } catch (error) {
      setHealth('fallback');
      setNotice(error instanceof Error ? error.message : 'API request failed before a response was received.');
      setZones([{ key: 'IN', display_name: 'India National Grid', country_name: 'India', carbon_intensity: 435 }, { key: 'FR', display_name: 'France Grid', country_name: 'France', carbon_intensity: 50 }, { key: 'DK-DK1', display_name: 'Denmark West', country_name: 'Denmark', carbon_intensity: 150 }, { key: 'GLOBAL', display_name: 'Global average', country_name: 'Global', carbon_intensity: 435 }]);
    }
  })(); }, []);

  useEffect(() => {
    if (view === 'schedule' || view === 'impact') {
      if (analysisMode === 'project' && projectResult?.scheduling?.status === 'available') {
        setForecast(projectResult.scheduling as ForecastResponse);
        setForecastError(null);
        setForecastLoading(false);
        return;
      }
      const fileJoules = result?.pipeline_raw?.energy_result?.energy?.energy_joules;
      const targetJoules = (analysisMode === 'project' && projectResult)
        ? (projectResult.total_energy_joules || 100.0)
        : (fileJoules || 100.0);
      const forecastUrl = apiRequestUrl(`/forecast?zone=${encodeURIComponent(zone)}&energy_joules=${targetJoules}`);
      setForecastLoading(true);
      setForecastError(null);
      fetchApi(forecastUrl)
        .then(async response => {
          setForecast(await readApiJson<ForecastResponse>(response, forecastUrl));
          setForecastError(null);
        })
        .catch((err) => {
          console.error('[Code-Carbon] Forecast fetch error:', err);
          setForecast(null);
          setForecastError(err instanceof Error ? err.message : 'API request failed before a response was received.');
        })
        .finally(() => {
          setForecastLoading(false);
        });
    }
  }, [view, zone, analysisMode, projectResult, result]);
  useEffect(() => { localStorage.setItem('codecarbon-theme', darkMode ? 'dark' : 'light'); }, [darkMode]);

  const navigateView = (targetView: View) => {
    setView(targetView);
    try {
      if (window.location.hash !== `#${targetView}`) {
        window.history.pushState({ view: targetView }, '', `#${targetView}`);
      }
    } catch (e) {}
  };

  useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      if (e.state && e.state.view) {
        setView(e.state.view);
      } else {
        const hash = window.location.hash.replace('#', '') as View;
        if (['workspace', 'results', 'project', 'recommendations', 'impact', 'schedule'].includes(hash)) {
          setView(hash);
        }
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const currentZone = zones.find(z => z.key === zone);
  const raw = result?.pipeline_raw || {}, energy = raw.energy_result?.energy || {}, carbon = raw.carbon_result?.carbon_data || {};
  const metrics = result?.research_metrics;
  const recommendations = Array.isArray(result?.recommendations) ? result.recommendations : (result?.recommendations?.recommendations || []);
  const resultFindings = result?.pipeline_raw?.energy_smell_report?.findings || result?.findings || [];
  const postRefactor = result?.post_refactor_estimation || {};
  const scopeFiles = projectResult ? getScopeFiles(projectResult.files, sourceOnly) : [];
  const scopeMetrics = getScopeMetrics(scopeFiles);
  const scopeLabel = sourceOnly ? 'Source code only' : 'All files';
  const scopeTakeaways = useMemo(() => {
    const paths = scopeFiles.map(file => file.relative_path);
    return getOverviewTakeaways(scopeFiles, path => uniqueRankedPath(path, paths));
  }, [scopeFiles]);
  const analysisTimestampLabel = projectResult?.timestamp && Number.isFinite(new Date(projectResult.timestamp).getTime())
    ? `${new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true }).format(new Date(projectResult.timestamp))} IST`
    : 'time unavailable';
  const projectVisibleFindingCount = scopeMetrics.findingLocations;

  // Individual Findings count from backend summary / findings for single file
  const totalFindingsCount =
    (Array.isArray(raw.energy_smell_report?.findings) ? raw.energy_smell_report.findings.length : undefined) ??
    raw.energy_smell_report?.summary?.total_findings ??
    (Array.isArray(result?.findings) ? result.findings.length : recommendations.length);
  const singleFileIsTestCode = isTestOrExamplePath(result?.filename || filename);
  const singleVisibleFindings = singleFileIsTestCode && excludeTestCode ? [] : resultFindings;
  const singleVisibleFindingCount = singleFileIsTestCode && excludeTestCode ? 0 : totalFindingsCount;

  // Carbon intensity: Primary value from backend response, fallback to frontend selectedZone ONLY if missing
  const projectReferenceFile = projectResult?.files.find(file => file.status === 'success' && file.single_file_response);
  const projectCarbonMetadata = projectReferenceFile?.single_file_response?.post_refactor_estimation?.carbon_metadata;
  const backendCarbonIntensity = (analysisMode === 'project' && projectResult?.carbon_intensity)
    ?? (analysisMode === 'project' && projectCarbonMetadata?.carbon_intensity)
    ?? postRefactor.carbon_metadata?.carbon_intensity
    ?? carbon.carbon_intensity;

  const carbonIntensityToDisplay = (backendCarbonIntensity !== undefined && backendCarbonIntensity !== null)
    ? backendCarbonIntensity
    : currentZone?.carbon_intensity;
  const carbonSourceType = analysisMode === 'project'
    ? projectResult?.carbon_source_type ?? projectCarbonMetadata?.source_type ?? (projectCarbonMetadata?.is_mock ? 'mock' : 'unknown')
    : postRefactor.carbon_metadata?.source_type ?? (postRefactor.carbon_metadata?.is_mock ? 'mock' : 'unknown');
  const carbonSourceZone = analysisMode === 'project'
    ? projectResult?.carbon_zone ?? projectCarbonMetadata?.zone ?? zone
    : postRefactor.carbon_metadata?.zone ?? carbon.zone?.zone_key ?? zone;
  const projectBefore = projectResult?.project_before;
  const projectAfter = projectResult?.project_after;
  const impactForecast = (projectResult?.scheduling?.status === 'available'
    ? projectResult.scheduling as ForecastResponse
    : forecast);
  const projectBeforeEnergy = sourceOnly ? scopeMetrics.beforeEnergy : Number(projectBefore?.energy ?? projectResult?.total_energy_joules ?? scopeMetrics.energyJoules);
  const projectAfterEnergy = sourceOnly ? scopeMetrics.afterEnergy : Number(projectAfter?.energy ?? projectBeforeEnergy);
  const impactCurrentIntensity = Number(impactForecast?.intensity_now ?? projectResult?.carbon_intensity ?? impactForecast?.current_carbon_intensity ?? carbonIntensityToDisplay ?? 0);
  const impactForecastMinimum = Number(impactForecast?.forecast_minimum_intensity ?? impactForecast?.lowest_forecast_intensity ?? impactCurrentIntensity);
  // Do not model the recommended window as a carbon increase when every forecast
  // hour is dirtier than the project's current baseline.
  const impactScheduledIntensity = Number(impactForecast?.intensity_window ?? Math.min(impactCurrentIntensity, impactForecastMinimum));
  const cirsSchedulingRatio = impactCurrentIntensity > 0 ? impactScheduledIntensity / impactCurrentIntensity : 1;
  const impactWindowStart = impactForecast?.window_start || impactForecast?.recommended_execution_time || undefined;
  const currentLocalHour = new Date();
  currentLocalHour.setMinutes(0, 0, 0);
  const impactWindowIsUpcoming = !impactWindowStart || Date.parse(impactWindowStart) >= currentLocalHour.getTime();
  const impactWindowStartsNow = isInCurrentLocalHour(impactWindowStart);
  const impactBeforeValues = {
    energy: projectBeforeEnergy,
    carbon: projectBeforeEnergy / 3_600_000 * impactCurrentIntensity,
    ess: sourceOnly ? scopeMetrics.beforeEss : Number(projectBefore?.ess ?? 0),
    cirs: sourceOnly ? scopeMetrics.beforeCirs : Number(projectResult?.total_cirs ?? projectBefore?.cirs ?? 0),
  };
  const impactAfterValues = {
    energy: projectAfterEnergy,
    carbon: projectAfterEnergy / 3_600_000 * impactScheduledIntensity,
    ess: sourceOnly ? scopeMetrics.afterEss : Number(projectAfter?.ess ?? impactBeforeValues.ess),
    cirs: (sourceOnly ? scopeMetrics.afterCirs : Number(projectAfter?.cirs ?? impactBeforeValues.cirs)) * cirsSchedulingRatio,
  };
  const impactRows = [
    { name: 'Energy', unit: 'modeled J (relative)', digits: 2, before: impactBeforeValues.energy, after: impactAfterValues.energy },
    { name: 'Carbon footprint', unit: 'modeled gCO₂eq/run', digits: 6, before: impactBeforeValues.carbon, after: impactAfterValues.carbon, help: CARBON_METHOD_NOTE },
    { name: 'Finding locations', unit: 'detector locations', digits: 0, before: (projectResult?.files ?? []).reduce((sum, file) => sum + (file.status === 'success' && (!excludeTestCode || !isTestOrExamplePath(file.relative_path)) ? file.findings_count : 0), 0), after: (projectResult?.files ?? []).reduce((sum, file) => sum + (file.status === 'success' && (!excludeTestCode || !isTestOrExamplePath(file.relative_path)) ? Number(file.single_file_response?.post_refactor_estimation?.finding_locations_after ?? file.findings_count) : 0), 0) },
    { name: 'Mean ESS per file', unit: 'index (0–10)', digits: 2, before: scopeMetrics.meanEss, after: scopeFiles.filter(file => file.status === 'success').reduce((sum, file) => sum + file.after_ess, 0) / Math.max(1, scopeMetrics.successfulFiles) },
    { name: 'Sum of per-file ESS (index)', unit: 'index (0–10) · one run per file', digits: 3, before: impactBeforeValues.ess, after: impactAfterValues.ess },
    { name: 'CIRS', unit: 'summed risk-weighted score', digits: 6, before: impactBeforeValues.cirs, after: impactAfterValues.cirs },
  ];
  const scopedAppliedFixDetails = scopeFiles.flatMap(file => (file.single_file_response?.auto_applied_fixes ?? []).map(fix => ({ file, fix })));
  const appliedFixDetails = scopedAppliedFixDetails[0];

  // Complexity metrics for single file
  const rawComplexity = raw.complexity_metrics || {};
  const rawComplexityScore = raw.complexity_score || {};
  const complexity = {
    cc: rawComplexity.cyclomatic_complexity ?? postRefactor.complexity_before?.cc ?? 1.0,
    nd: rawComplexity.max_nesting_depth ?? postRefactor.complexity_before?.nd ?? 1.0,
    fd: rawComplexity.function_density ?? postRefactor.complexity_before?.fd ?? 0.0,
    sloc: rawComplexity.sloc ?? raw.analysis?.total_lines_of_code ?? 0,
    sci: rawComplexityScore.structural_complexity_index ?? postRefactor.sci_before ?? 0.0
  };

  // Aggregated Project Recommendations across all analyzed files
  const projectAggregatedRecommendations = useMemo(() => {
    if (!projectResult?.files) return [];
    const map = new Map<string, {
      rule_id: string;
      title: string;
      category: string;
      severity: string;
      priority_score: number;
      suggested_fix: string;
      explanation: string;
      occurrences: number;
      affected_files: { filename: string; relative_path: string; line_number?: number; confidence: number; source_lines: { line_number: number; code: string }[] }[];
      code_example?: string;
    }>();

    for (const fileItem of projectResult.files) {
      if (excludeTestCode && isTestOrExamplePath(fileItem.relative_path)) continue;
      const fileResp = fileItem.single_file_response;
      if (!fileResp) continue;
      const recs = Array.isArray(fileResp.recommendations)
        ? fileResp.recommendations
        : (fileResp.recommendations?.recommendations || []);

      for (const rec of recs) {
        const key = rec.rule_id || rec.title || rec.name || 'OTHER';
        if (!map.has(key)) {
          map.set(key, {
            rule_id: rec.rule_id || 'UNKNOWN',
            title: rec.title || rec.name || rec.rule_name || 'Optimization Opportunity',
            category: rec.category || 'Code Structure',
            severity: rec.severity || 'medium',
            priority_score: Number(rec.priority_score || rec.severity_score || 0.5),
            suggested_fix: rec.optimization_recommendation || rec.suggested_fix || '',
            explanation: rec.explanation || rec.description || rec.message || '',
            occurrences: 0,
            affected_files: [],
            code_example: rec.code_example || undefined
          });
        }
        const entry = map.get(key)!;
        const sourceLines = String(fileItem.original_code || '').split(/\r?\n/);
        const recFindings = Array.isArray(rec.findings) ? rec.findings : [];
        const lineNumbers = recFindings.map((finding: any) => finding.line_number).filter((line: any) => Number.isInteger(line) && line > 0);
        if (!lineNumbers.length && Number.isInteger(rec.line_number) && rec.line_number > 0) lineNumbers.push(rec.line_number);
        entry.occurrences += Math.max(1, recFindings.length);
        entry.affected_files.push({
          filename: fileItem.filename,
          relative_path: fileItem.relative_path,
          line_number: lineNumbers[0],
          confidence: rec.confidence ?? 1.0,
          source_lines: lineNumbers.map((lineNumber: number) => ({ line_number: lineNumber, code: sourceLines[lineNumber - 1] || '' }))
        });
      }
    }

    return Array.from(map.values()).sort((a, b) => b.priority_score - a.priority_score);
  }, [projectResult, excludeTestCode]);
  const projectRecommendationBadge = projectResult
    ? `${projectAggregatedRecommendations.length} suggestions · ${scopeFiles.reduce((sum, file) => sum + file.auto_fixable_count, 0)} auto-fixable · ${scopeFiles.reduce((sum, file) => sum + file.auto_applied_count, 0)} applied`
    : `${recommendations.length} recommendations`;

  // Project-wide findings category distribution
  const projectCategoryDistribution = useMemo(() => getCategoryCounts(scopeFiles), [scopeFiles]);

  // Top ranked file highlights
  const topEnergyFiles = useMemo(() => {
    return [...scopeFiles].filter(file => file.status === 'success').sort((a, b) => b.energy_joules - a.energy_joules).slice(0, 3);
  }, [scopeFiles]);

  const topFindingsFiles = useMemo(() => {
    return [...scopeFiles].filter(file => file.status === 'success' && file.findings_count > 0).sort((a, b) => b.findings_count - a.findings_count).slice(0, 3);
  }, [scopeFiles]);

  const fixThisFirstFile = useMemo(() => getScopeFiles(projectResult?.files ?? [], true)
    .filter(file => file.status === 'success' && file.findings_count > 0)
    .sort((a, b) => b.energy_joules - a.energy_joules)[0], [projectResult]);

  // Project chart datasets
  const projectFilesEnergyData = useMemo(() => {
    if (!projectResult?.files) return [];
    return scopeFiles.filter(f => f.status === 'success').map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      energyJoules: Number(f.energy_joules || 0),
      energyKwh: Number((f.energy_joules || 0) / 3600000.0)
    })).sort((a, b) => b.energyJoules - a.energyJoules).slice(0, 10);
  }, [projectResult, scopeFiles]);

  const projectFilesSciData = useMemo(() => {
    if (!projectResult?.files) return [];
    return scopeFiles.filter(f => f.status === 'success').map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      sci: Number(f.sci || 0)
    })).sort((a, b) => b.sci - a.sci).slice(0, 10);
  }, [projectResult, scopeFiles]);

  const projectFilesEssData = useMemo(() => {
    if (!projectResult?.files) return [];
    return scopeFiles.filter(f => f.status === 'success').map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      ess: Number(f.ess || 0)
    })).sort((a, b) => b.ess - a.ess).slice(0, 10);
  }, [projectResult, scopeFiles]);

  const projectFilesCirsData = useMemo(() => {
    if (!projectResult?.files) return [];
    return scopeFiles.filter(f => f.status === 'success').map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      cirs: Number(f.cirs || 0)
    })).sort((a, b) => b.cirs - a.cirs).slice(0, 10);
  }, [projectResult, scopeFiles]);
  const projectFilesToFixData = useMemo(() => [...scopeFiles]
    .filter(file => file.status === 'success' && file.findings_count > 0)
    .sort((a, b) => b.cirs - a.cirs)
    .slice(0, 5), [scopeFiles]);

  const projectEssDistribution = useMemo(() => {
    return getEssFineHistogram(scopeFiles);
  }, [scopeFiles]);
  const projectEssBands = useMemo(() => getEssBands(scopeFiles), [scopeFiles]);

  const singleFileComplexityData = useMemo(() => {
    if (!result) return [];
    return [
      { name: 'CC', full: 'Cyclomatic Complexity', value: complexity.cc, rawValue: fixed(complexity.cc, 1), unit: 'decision paths' },
      { name: 'ND', full: 'Nesting Depth', value: complexity.nd, rawValue: fixed(complexity.nd, 0), unit: 'max depth' },
      { name: 'FD (x100)', full: 'Function Density', value: Number((complexity.fd * 100).toFixed(2)), rawValue: fixed(complexity.fd, 4), unit: 'funcs/SLOC' },
      { name: 'SCI (x100)', full: 'Structural Index', value: Number((complexity.sci * 100).toFixed(2)), rawValue: fixed(complexity.sci, 4), unit: 'index (0-1)' }
    ];
  }, [result, complexity]);

  const singleFileRefactorComparisonData = useMemo(() => {
    if (!postRefactor || postRefactor.sci_before === undefined) return [];
    return [
      { name: 'Structural complexity (SCI)', before: postRefactor.sci_before || 0, after: postRefactor.sci_after || 0, unit: 'index (0–1)', decimals: 6 },
      { name: 'Energy smell score (ESS)', before: postRefactor.ess_before || 0, after: postRefactor.ess_after || 0, unit: 'score / 10', decimals: 4 },
      { name: 'Actionable energy smells', before: postRefactor.smells_before || 0, after: postRefactor.smells_after || 0, unit: 'findings', decimals: 0 },
      { name: 'Modeled energy', before: postRefactor.energy_before_joules || 0, after: postRefactor.energy_after_joules || 0, unit: 'modeled J (relative)', decimals: 6 },
      { name: 'Risk-weighted carbon score (CIRS)', before: postRefactor.cirs_before || 0, after: postRefactor.cirs_after || 0, unit: 'unitless score', decimals: 9 }
    ];
  }, [postRefactor]);

  // Sorted and searched project file breakdown table
  const sortedProjectFiles = useMemo(() => {
    if (!projectResult?.files) return [];
    return [...scopeFiles]
      .filter(f => f.filename.toLowerCase().includes(tableSearch.toLowerCase()) || f.relative_path.toLowerCase().includes(tableSearch.toLowerCase()))
      .filter(f => fileStatusFilter === 'all' || f.status === fileStatusFilter)
      .sort((a, b) => {
        const valA = a[sortColumn];
        const valB = b[sortColumn];
        if (typeof valA === 'string') {
          return sortAsc ? (valA as string).localeCompare(valB as string) : (valB as string).localeCompare(valA as string);
        }
        return sortAsc ? (valA as number) - (valB as number) : (valB as number) - (valA as number);
      });
  }, [projectResult, scopeFiles, tableSearch, fileStatusFilter, sortColumn, sortAsc]);

  const impactStatusCounts = useMemo(() => {
    const counts: Record<string, number> = { applied: 0, rejected: 0, not_auto_fixable: 0, no_issues: 0 };
    for (const file of scopeFiles) {
      const state = projectFixState(file);
      if (state in counts) counts[state] += 1;
    }
    return counts;
  }, [scopeFiles]);
  const impactReasonGroups = useMemo(() => {
    const groups = new Map<string, string[]>();
    for (const file of scopeFiles) {
      const state = projectFixState(file);
      if (state !== 'rejected' && state !== 'not_auto_fixable') continue;
      const reason = file.fix_reason || (state === 'not_auto_fixable' ? 'No safe automatic AST transformation was available for this file.' : 'Candidate was rejected by the modeled quality gate.');
      groups.set(reason, [...(groups.get(reason) || []), file.relative_path]);
    }
    return Array.from(groups.entries());
  }, [scopeFiles]);
  const impactFilesSorted = useMemo(() => {
    const statusOrder: Record<string, number> = { applied: 0, rejected: 1, not_auto_fixable: 2, no_issues: 3, failed: 4 };
    return (projectResult?.files ?? [])
      .filter(file => impactStatusFilter === 'all' || projectFixState(file) === impactStatusFilter)
      .slice()
      .sort((a, b) => statusOrder[projectFixState(a)] - statusOrder[projectFixState(b)] || a.relative_path.localeCompare(b.relative_path));
  }, [projectResult, impactStatusFilter]);

  const readFile = async (file: File) => {
    setNotice(null);
    setExtracting(true);
    try {
      const lowerName = file.name.toLowerCase();
      const isPy = lowerName.endsWith('.py');
      const isTxt = lowerName.endsWith('.txt');
      const isPdf = lowerName.endsWith('.pdf');
      const isDocx = lowerName.endsWith('.docx');

      if (!isPy && !isTxt && !isPdf && !isDocx) {
        throw new Error(`Unsupported file type "${file.name}". Please upload a Python (.py) source file.`);
      }

      let text: string;
      if (isPdf) {
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
        const pdf = await pdfjsLib.getDocument({ data: await file.arrayBuffer() }).promise;
        const pages = await Promise.all(
          Array.from({ length: pdf.numPages }, async (_, i) =>
            ((await (await pdf.getPage(i + 1)).getTextContent()).items as any[]).map(v => v.str || '').join(' ')
          )
        );
        text = pages.join('\n');
      } else if (isDocx) {
        text = (await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() })).value;
      } else {
        text = await file.text();
      }

      if (!text.trim()) {
        throw new Error(`File "${file.name}" is empty. No readable code was found.`);
      }

      setCode(text);
      setFilename(file.name);
      setUploadedFile(file);
    } catch (err: any) {
      console.error('[Code-Carbon] File read error:', err);
      setNotice(err.message || 'Unable to read that file.');
    } finally {
      setExtracting(false);
    }
  };

  const analyze = async () => {
    if (!code.trim()) {
      return setNotice('Please upload a Python (.py) file, select a sample preset, or paste code before running an analysis.');
    }
    if (extracting) {
      return setNotice('Reading uploaded file, please wait a moment...');
    }
    // Prevent a prior project archive name and aggregate values from leaking
    // into the new standalone report.
    setProjectResult(null);
    setAnalysisMode('file');
    setLoading(true);
    setNotice(null);
    try {
      const form = new FormData();
      const finalFilename = filename.toLowerCase().endsWith('.py') ? filename : `${filename}.py`;
      const fileToSend = (uploadedFile && uploadedFile.name === filename)
        ? uploadedFile
        : new File([code], finalFilename, { type: 'text/x-python' });
      form.append('file', fileToSend);
      form.append('zone', zone);
      form.append('use_global_average', String(globalAverage));
      const requestUrl = apiRequestUrl('/analyze');
      const response = await fetchApi(requestUrl, { method: 'POST', body: form });
      const data = await readApiJson<AnalyzeResponse>(response, requestUrl);
      setResult(data);
      setAnalysisMode('file');
      navigateView('results');
    } catch (err: any) {
      console.error('[Code-Carbon] File analysis failed:', err);
      const msg = err instanceof Error ? err.message : String(err);
      setNotice(msg || `Analysis request to ${API} could not be completed.`);
    } finally {
      setLoading(false);
    }
  };

  const scanDataTransferItems = async (items: DataTransferItemList): Promise<ScannedFile[]> => {
    const scanned: ScannedFile[] = [];
    const skipDirs = new Set(['.git', '__pycache__', 'venv', 'env', 'node_modules', 'dist', 'build', '.pytest_cache', '.idea', '.vscode']);

    const scanEntry = async (entry: any, currentPath: string = '') => {
      if (!entry) return;
      if (entry.isFile) {
        if (entry.name.toLowerCase().endsWith('.py')) {
          await new Promise<void>((resolve) => {
            entry.file((f: File) => {
              const relPath = currentPath ? `${currentPath}/${f.name}` : f.name;
              scanned.push({ file: f, path: relPath.replace(/\\/g, '/') });
              resolve();
            }, () => resolve());
          });
        }
      } else if (entry.isDirectory) {
        if (entry.name.startsWith('.') || skipDirs.has(entry.name)) return;
        const dirReader = entry.createReader();
        const readAllEntries = (): Promise<any[]> => {
          return new Promise((resolve) => {
            const allEntries: any[] = [];
            const readBatch = () => {
              dirReader.readEntries((entries: any[]) => {
                if (!entries || entries.length === 0) {
                  resolve(allEntries);
                } else {
                  allEntries.push(...entries);
                  readBatch();
                }
              }, () => resolve(allEntries));
            };
            readBatch();
          });
        };

        const entries = await readAllEntries();
        const nextPath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
        for (const childEntry of entries) {
          await scanEntry(childEntry, nextPath);
        }
      }
    };

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.webkitGetAsEntry) {
        const entry = item.webkitGetAsEntry();
        if (entry) await scanEntry(entry, '');
      } else if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file && file.name.toLowerCase().endsWith('.py')) {
          scanned.push({ file, path: file.name });
        }
      }
    }
    return scanned;
  };

  const runProjectAnalysis = async (
    overrideFiles?: ScannedFile[],
    overrideZip?: File | null,
    overrideSummary?: ProjectSummary | null
  ) => {
    const filesToUpload = overrideFiles !== undefined ? overrideFiles : projectFiles;
    const zipToUpload = overrideZip !== undefined ? overrideZip : projectZipFile;
    const summaryToUse = overrideSummary !== undefined ? overrideSummary : projectSummary;

    if (!zipToUpload && (!filesToUpload || filesToUpload.length === 0)) {
      return setNotice('Please select a folder of .py files or a .zip archive before running project analysis.');
    }
    setLoading(true); setNotice(null);
    setProjectResult(null);
    sessionStorage.removeItem(PROJECT_REPORT_STORAGE_KEY);
    setProjectResponseOutdated(false);
    try {
      const form = new FormData();
      let fileToUpload: File;

      if (zipToUpload) {
        fileToUpload = zipToUpload;
      } else {
        const zip = new JSZip();
        for (const item of filesToUpload) {
          const content = await item.file.arrayBuffer();
          zip.file(item.path, content);
        }
        const zipBlob = await zip.generateAsync({ type: 'blob' });
        const rootName = summaryToUse?.name || 'project';
        fileToUpload = new File([zipBlob], `${rootName}.zip`, { type: 'application/zip' });
      }

      form.append('file', fileToUpload);
      form.append('zone', zone);
      form.append('use_global_average', String(globalAverage));
      const requestUrl = apiRequestUrl('/analyze-project');
      const response = await fetchApi(requestUrl, { method: 'POST', body: form });
      const rawProjectData = await readApiJson<Partial<ProjectAnalyzeResponse>>(response, requestUrl);
      const projectIsOutdated = !isCurrentProjectResponse(rawProjectData);
      const projData = normalizeProjectResponse(rawProjectData);
      setProjectResponseOutdated(projectIsOutdated);
      setProjectResult(projData);
      saveProjectReport(projData);
      setAnalysisMode('project');
      navigateView('project');
    } catch (err: any) {
      console.error('[Code-Carbon] Project analysis failed:', err);
      const msg = err instanceof Error ? err.message : String(err);
      setNotice(msg || `Project analysis request to ${API} could not be completed.`);
    } finally {
      setLoading(false);
    }
  };

  const handleFolderSelect = async (filesList: FileList) => {
    setNotice(null);
    const pyFiles: ScannedFile[] = [];
    const skipDirs = ['.git/', '__pycache__/', 'venv/', 'env/', 'node_modules/', 'dist/', 'build/', '.pytest_cache/'];

    for (let i = 0; i < filesList.length; i++) {
      const file = filesList[i];
      const relPath = (file.webkitRelativePath || file.name).replace(/\\/g, '/');
      if (relPath.toLowerCase().endsWith('.py')) {
        if (!skipDirs.some(skip => relPath.includes(skip))) {
          pyFiles.push({ file, path: relPath });
        }
      }
    }

    if (pyFiles.length === 0) {
      setNotice('No Python (.py) files were found in the selected folder.');
      return;
    }

    const rootDirName = pyFiles[0].path.split('/')[0] || 'Selected Folder';
    const summary: ProjectSummary = {
      name: rootDirName,
      type: 'folder',
      count: pyFiles.length,
      samplePaths: pyFiles.slice(0, 3).map(f => f.path)
    };

    setProjectFiles(pyFiles);
    setProjectZipFile(null);
    setProjectSummary(summary);

    await runProjectAnalysis(pyFiles, null, summary);
  };

  const handleZipSelect = async (file: File) => {
    setNotice(null);
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setNotice('Please select a valid .zip archive file.');
      return;
    }
    const summary: ProjectSummary = {
      name: file.name,
      type: 'zip',
      sizeKb: Math.round(file.size / 1024),
      samplePaths: []
    };

    setProjectZipFile(file);
    setProjectFiles([]);
    setProjectSummary(summary);

    await runProjectAnalysis([], file, summary);
  };

  const handleProjectDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    setNotice(null);

    if (e.dataTransfer.files.length === 1 && e.dataTransfer.files[0].name.toLowerCase().endsWith('.zip')) {
      await handleZipSelect(e.dataTransfer.files[0]);
      return;
    }

    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      const scanned = await scanDataTransferItems(e.dataTransfer.items);
      if (scanned.length > 0) {
        const rootDirName = scanned[0].path.split('/')[0] || 'Dropped Project';
        const summary: ProjectSummary = {
          name: rootDirName,
          type: 'folder',
          count: scanned.length,
          samplePaths: scanned.slice(0, 3).map(f => f.path)
        };

        setProjectFiles(scanned);
        setProjectZipFile(null);
        setProjectSummary(summary);

        await runProjectAnalysis(scanned, null, summary);
        return;
      }
    }

    if (e.dataTransfer.files.length > 0) {
      await handleFolderSelect(e.dataTransfer.files);
    }
  };

  const download = (contents: string, name: string, type: string) => {
    const blob = new Blob([contents], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      if (document.body.contains(a)) document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 1000);
  };

  const getOptimizedFilename = (rawName: string): string => {
    const baseName = rawName.split('/').pop()?.split('\\').pop() || 'file.py';
    const cleanStem = baseName.toLowerCase().endsWith('.py') ? baseName.slice(0, -3) : baseName;
    return `${cleanStem}_optimized.py`;
  };
  
  const nav = [
    ['workspace', Code2, 'New analysis'],
    ...(projectResult ? [['project', FolderArchive, 'Project Overview']] as const : []),
    ['results', Gauge, analysisMode === 'project' && projectResult ? 'File Inspection' : 'File Results'],
    ['recommendations', Sparkles, 'Recommendations'],
    ['impact', Activity, 'Impact & Refactor'],
    ['schedule', Clock3, 'Green Scheduling']
  ] as const;

  const rawChartScores = recommendations.slice(0, 6).map((item: any) => Number(item.priority_score ?? item.severity_score ?? 0));
  const maxRawScore = Math.max(...rawChartScores, 1e-6);

  const chart = recommendations.slice(0, 6).map((item: any, i: number) => {
    const rawScore = Number(item.priority_score ?? item.severity_score ?? 0);
    const pct = maxRawScore > 0 ? (rawScore / maxRawScore) * 100 : 0;
    return {
      name: item.rule_id || item.rule_name || `Finding ${i + 1}`,
      displayScore: pct > 0 ? Math.max(pct, 8) : 8,
      rawScore: rawScore
    };
  });

  const overviewVerdict = `${scopeMetrics.successfulFiles} files analyzed. ${scopeMetrics.filesWithFindings} files have energy-smell findings; ${scopeMetrics.cleanFiles} have none. ${scopeMetrics.highEssFiles} files are in the high ESS display band. Biggest energy use: ${topEnergyFiles[0] ? `${uniqueRankedPath(topEnergyFiles[0].relative_path, scopeFiles.map(file => file.relative_path))} (${fixed(scopeMetrics.energyJoules ? topEnergyFiles[0].energy_joules / scopeMetrics.energyJoules * 100 : 0, 1)}% of the project total)` : 'no file energy available'}. ${scopeMetrics.findingLocations} finding locations across ${scopeMetrics.distinctRules} distinct rules.`;

  return <div className={`shell ${darkMode ? 'dark-theme' : ''}`}>
    <aside className="rail">
      <button className="brand" onClick={() => setView('workspace')}><span className="brand-mark"><Leaf size={18} /></span><span>codecarbon</span></button>
      <p className="rail-label">WORKSPACE</p>
      <nav aria-label="Main navigation">
        {nav.map(([id, Icon, label]) => (
          <button key={id} className={`nav-button ${view === id ? 'is-active' : ''}`} onClick={() => navigateView(id as View)}>
            <Icon size={17} />{label}
            {id !== 'workspace' && id !== 'project' && !result && !projectResult && <span className="nav-lock">•</span>}
          </button>
        ))}
      </nav>
      <div className="rail-bottom">
        <div className="connection"><span className={`connection-dot ${health}`} />{health === 'healthy' ? 'Service connected' : health === 'checking' ? 'Checking service' : 'Local data mode'}</div>
        <p>Measure thoughtfully.<br />Ship lighter software.</p>
      </div>
    </aside>

    <main className="content">
      <TabErrorBoundary key={view} tabName={view === 'impact' ? 'Impact' : view === 'schedule' ? 'Green Scheduling' : view === 'project' ? 'Project Overview' : view === 'recommendations' ? 'Recommendations' : 'Analysis'}>
      {projectResponseOutdated && <div className="backend-outdated-banner" role="alert">Backend response is outdated, restart the API. Showing safe fallback values until a fresh analysis is run.</div>}
      <header className="topbar">
        <div>
          <p className="eyebrow">SUSTAINABLE ENGINEERING</p>
          <h1>{view === 'workspace' ? 'Make every run count.' : view === 'project' ? 'Project analysis report' : view === 'results' ? 'File analysis report' : view === 'recommendations' ? 'Where to improve' : view === 'impact' ? 'Potential impact' : 'Choose a cleaner window'}</h1>
        </div>
        <div className="top-actions">
          <button className="theme-toggle" onClick={() => setDarkMode(mode => !mode)} aria-label={`Switch to ${darkMode ? 'light' : 'dark'} mode`} title={`Switch to ${darkMode ? 'light' : 'dark'} mode`}>
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}<span>{darkMode ? 'Light' : 'Dark'}</span>
          </button>
          {projectResult && view !== 'project' && (
            <button className="project-breadcrumb-btn" onClick={() => { setAnalysisMode('project'); navigateView('project'); }} title="Return to project summary breakdown table">
              <ArrowLeft size={14} /> <span>Back to {projectResult.project_name}</span>
            </button>
          )}
          {result && view !== 'project' && (
            <>
              <span className="file-chip"><FileCode2 size={15} />{result.filename || filename}</span>
              <button className="icon-button" title="Download JSON report" onClick={() => download(JSON.stringify(result, null, 2), `carbon-report-${filename.replace(/\.py$/i, '')}.json`, 'application/json')}><Download size={17} /></button>
            </>
          )}
          {projectResult && view === 'project' && (
            <>
              <span className="file-chip"><FolderArchive size={15} />{projectResult.project_name} ({projectResult.total_files} files)</span>
              <button className="icon-button" title="Download Project JSON report" onClick={() => download(JSON.stringify(projectResult, null, 2), `project-report-${projectResult.project_name.replace(/\.zip$/i, '')}.json`, 'application/json')}><Download size={17} /></button>
            </>
          )}
        </div>
      </header>

      {projectResult && ['project', 'recommendations', 'impact'].includes(view) && <div className="project-scope-banner">
        <p><strong>Showing:</strong> {scopeLabel} · {scopeMetrics.totalFiles} of {projectResult.total_files} files</p>
        <button type="button" className="text-button" aria-expanded={scopeMenuOpen} onClick={() => setScopeMenuOpen(open => !open)}>{scopeMenuOpen ? 'Done' : 'Change'}</button>
        {scopeMenuOpen && <div className="scope-banner-options" role="group" aria-label="Project file scope">
          <button type="button" aria-pressed={!sourceOnly} className={!sourceOnly ? 'active' : ''} onClick={() => { setSourceOnly(false); setScopeMenuOpen(false); }}>All files</button>
          <button type="button" aria-pressed={sourceOnly} className={sourceOnly ? 'active' : ''} onClick={() => { setSourceOnly(true); setScopeMenuOpen(false); }}>Source code only</button>
        </div>}
      </div>}

      {(result || projectResult) && view !== 'workspace' && (
        <div className="report-subnav">
          {projectResult && (
            <button className={`subnav-tab ${view === 'project' ? 'is-active' : ''}`} onClick={() => { setAnalysisMode('project'); navigateView('project'); }}>
              <FolderArchive size={14} /> Project Overview
            </button>
          )}
          {result && (
            <button className={`subnav-tab ${view === 'results' ? 'is-active' : ''}`} onClick={() => navigateView('results')}>
              <Gauge size={14} /> File Overview ({result.filename || filename})
            </button>
          )}
          <button className={`subnav-tab ${view === 'recommendations' ? 'is-active' : ''}`} onClick={() => navigateView('recommendations')}>
            <Sparkles size={14} /> {analysisMode === 'project' && projectResult ? projectRecommendationBadge : `Recommendations (${recommendations.length})`}
          </button>
          <button className={`subnav-tab ${view === 'impact' ? 'is-active' : ''}`} onClick={() => navigateView('impact')}>
            <Activity size={14} /> Refactor & Impact
          </button>
          <button className={`subnav-tab ${view === 'schedule' ? 'is-active' : ''}`} onClick={() => navigateView('schedule')}>
            <Clock3 size={14} /> Green Scheduling
          </button>
          {projectResult && view === 'project' && <details className="glossary-popover">
            <summary>What do these mean?</summary>
            <div className="glossary-popover-content">
              <p><strong>SCI</strong> — structural complexity index; lower is simpler.</p>
              <p><strong>ESS</strong> — energy-smell score from 0 to 10; lower means fewer detected patterns.</p>
              <p><strong>CIRS</strong> — unitless carbon impact risk score, weighted by structure and smell exposure.</p>
              <p><strong>Modeled J</strong> — relative energy estimate in joules; it is not metered energy.</p>
              <p><strong>gCO₂eq</strong> — grams of carbon dioxide equivalent; the project carbon value is modeled.</p>
              <details><summary>How are these computed?</summary><p>SCI, ESS, and CIRS use the project analysis model and its documented formulas. Modeled carbon converts relative modeled J to kWh and multiplies by grid intensity. These are comparisons, not measured consumption or emissions.</p></details>
            </div>
          </details>}
        </div>
      )}

      {notice && <div className="notice" role="alert"><AlertCircle size={18} /><span>{notice}</span><button onClick={() => setNotice(null)} aria-label="Dismiss"><X size={16} /></button></div>}

      {view === 'workspace' && <section className="workspace">
        <div className="intro">
          <div>
            <p className="overline">CODE CARBON INTELLIGENCE</p>
            <h2>Find the quiet inefficiencies<br />hiding in your code.</h2>
            <p>Inspect single Python files or full multi-file projects (.zip archives) for energy smells, measure footprint, and refactor efficiently.</p>
          </div>
          <div className="intro-stat"><span>01</span><p>One focused workflow<br />from source to action.</p></div>
        </div>

        <div className="analysis-card">
          <div className="card-heading">
            <div>
              <p className="overline">START HERE</p>
              <h3>Set up an analysis</h3>
            </div>
            <div className="mode-toggle-group">
              <button className={`mode-tab ${analysisMode === 'file' ? 'is-active' : ''}`} onClick={() => setAnalysisMode('file')}>Analyze File</button>
              <button className={`mode-tab ${analysisMode === 'project' ? 'is-active' : ''}`} onClick={() => setAnalysisMode('project')}>Analyze Project (ZIP / Multi-file)</button>
            </div>
          </div>

          <div className="settings-grid">
            <label className="field">
              <span>Electricity grid</span>
              <select value={zone} onChange={e => setZone(e.target.value)}>
                {zones.map(z => <option key={z.key} value={z.key}>{z.display_name || z.key} · {z.carbon_intensity} gCO₂/kWh</option>)}
              </select>
              <small>{currentZone?.country_name || 'Loading regional grid details…'}</small>
            </label>
            <label className="field">
              <span>Find a grid</span>
              <div className="search-field"><Search size={16} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Country or zone code" /></div>
              <div className="zone-results">{query && zones.filter(z => `${z.key} ${z.display_name} ${z.country_name}`.toLowerCase().includes(query.toLowerCase())).slice(0, 4).map(z => <button key={z.key} onClick={() => { setZone(z.key); setQuery(''); }}><span>{z.display_name || z.key}</span><em>{z.carbon_intensity} gCO₂</em></button>)}</div>
            </label>
          </div>

          {analysisMode === 'file' ? (
            <div className="source-grid">
              <div
                className={`drop-zone ${dragging ? 'is-dragging' : ''} ${uploadedFile || (code.trim() && filename !== 'untitled.py') ? 'has-file' : ''}`}
                onDragEnter={e => { e.preventDefault(); setDragging(true); }}
                onDragOver={e => e.preventDefault()}
                onDragLeave={() => setDragging(false)}
                onDrop={e => {
                  e.preventDefault();
                  setDragging(false);
                  if (e.dataTransfer.files[0]) readFile(e.dataTransfer.files[0]);
                }}
                onClick={() => fileInput.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && fileInput.current?.click()}
              >
                <input
                  ref={fileInput}
                  type="file"
                  accept=".py,.txt,.pdf,.docx"
                  style={{ display: 'none' }}
                  onChange={e => {
                    if (e.target.files?.[0]) readFile(e.target.files[0]);
                    e.target.value = '';
                  }}
                />
                <span className="upload-icon">
                  {uploadedFile || (code.trim() && filename !== 'untitled.py') ? <FileCode2 size={24} /> : <Upload size={21} />}
                </span>
                <strong>
                  {extracting
                    ? 'Reading your file…'
                    : uploadedFile
                    ? `File loaded: ${uploadedFile.name}`
                    : (code.trim() && filename !== 'untitled.py')
                    ? `File loaded: ${filename}`
                    : 'Drop a file here'}
                </strong>
                <p>
                  {uploadedFile
                    ? `${(uploadedFile.size / 1024).toFixed(1)} KB · Click or drop another file to replace`
                    : (code.trim() && filename !== 'untitled.py')
                    ? `${code.split('\n').length} lines of code ready for analysis · Click to replace`
                    : 'or browse for Python, TXT, PDF, or DOCX'}
                </p>
              </div>
              <div className="editor-wrap">
                <div className="editor-toolbar">
                  <span><span className="editor-dot" />{filename}</span>
                  <div>{samples.map(s => <button key={s.file} onClick={() => { setCode(s.code); setFilename(s.file); setUploadedFile(null); setNotice(null); }}>{s.label}</button>)}</div>
                </div>
                <textarea value={code} onChange={e => setCode(e.target.value)} spellCheck="false" placeholder="# Paste a Python script here…" aria-label="Python code" />
              </div>
            </div>
          ) : (
            <div className="project-drop-wrap">
              <div
                className={`drop-zone project-zone ${dragging ? 'is-dragging' : ''}`}
                onDragEnter={e => { e.preventDefault(); setDragging(true); }}
                onDragOver={e => e.preventDefault()}
                onDragLeave={() => setDragging(false)}
                onDrop={handleProjectDrop}
              >
                <input
                  ref={projectFolderInput}
                  type="file"
                  {...({ webkitdirectory: '', directory: '' } as any)}
                  multiple
                  style={{ display: 'none' }}
                  onChange={e => {
                    if (e.target.files && e.target.files.length > 0) handleFolderSelect(e.target.files);
                    e.target.value = '';
                  }}
                />
                <input
                  ref={projectZipInput}
                  type="file"
                  accept=".zip"
                  style={{ display: 'none' }}
                  onChange={e => {
                    if (e.target.files?.[0]) handleZipSelect(e.target.files[0]);
                    e.target.value = '';
                  }}
                />
                <span className="upload-icon">
                  {projectSummary?.type === 'folder' ? <Folder size={28} /> : <FolderArchive size={28} />}
                </span>

                {projectSummary ? (
                  <div className="project-selected-info">
                    <strong>
                      {projectSummary.type === 'folder' ? `Folder: ${projectSummary.name}` : `ZIP Archive: ${projectSummary.name}`}
                    </strong>
                    <p>
                      {projectSummary.type === 'folder'
                        ? `${projectSummary.count} Python (.py) file(s) discovered.`
                        : `${projectSummary.sizeKb} KB ZIP archive ready.`}
                    </p>
                    {projectSummary.samplePaths && projectSummary.samplePaths.length > 0 && (
                      <div className="sample-paths-preview">
                        {projectSummary.samplePaths.map((p, idx) => (
                          <span key={idx} className="path-chip"><FileCode2 size={12} /> {p}</span>
                        ))}
                        {(projectSummary.count || 0) > 3 && <span className="path-chip flex-more">+{(projectSummary.count || 0) - 3} more</span>}
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    <strong>Drop a project folder or a .zip archive here</strong>
                    <p>Full project-level static analysis, AST refactoring, and CIRS carbon risk evaluation</p>
                  </>
                )}

                <div className="project-action-buttons">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={e => { e.stopPropagation(); projectFolderInput.current?.click(); }}
                  >
                    <Folder size={16} /> Select Folder
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={e => { e.stopPropagation(); projectZipInput.current?.click(); }}
                  >
                    <FolderArchive size={16} /> Select ZIP Archive
                  </button>
                </div>
              </div>
            </div>
          )}

          {loading && (
            <div className="analysis-loading-banner" role="status" aria-live="polite">
              <LoaderCircle className="spin" size={24} />
              <div>
                <strong>
                  {analysisMode === 'project'
                    ? 'Analyzing multi-file Python project…'
                    : `Analyzing ${filename || 'Python source file'}…`}
                </strong>
                <p>
                  {analysisMode === 'project'
                    ? 'Analyzing eligible Python files in parallel. Large projects can take a few minutes; keep this page open…'
                    : 'Running AST parsing, EKB smell detection, carbon estimation, and runtime profiling…'}
                </p>
                {analysisMode === 'project' && <div className="analysis-progress-track" role="progressbar" aria-label="Project analysis in progress" aria-valuetext="Analysis is running; exact completion is not available yet"><span /></div>}
              </div>
            </div>
          )}

          <div className="analysis-footer">
            <div>
              <label className="switch"><input type="checkbox" checked={globalAverage} onChange={e => setGlobalAverage(e.target.checked)} /><span /><b>Use global average</b></label>
              <p>Use this when your execution region is unknown.</p>
            </div>
            {analysisMode === 'file' ? (
              <button
                className="primary-button analyze-btn"
                disabled={loading}
                onClick={analyze}
                title="Run Code-Carbon analysis"
              >
                {loading ? <LoaderCircle className="spin" size={18} /> : <Play size={17} fill="currentColor" />}
                {loading ? 'Analyzing code…' : 'Analyze'}
                <ArrowRight size={17} />
              </button>
            ) : (
              <button
                className="primary-button analyze-btn"
                disabled={loading}
                onClick={() => runProjectAnalysis()}
                title="Run Code-Carbon project analysis"
              >
                {loading ? <LoaderCircle className="spin" size={18} /> : <FolderArchive size={17} />}
                {loading ? (projectFiles.length > 0 ? 'Packing & analyzing project…' : 'Analyzing project…') : 'Analyze project'}
                <ArrowRight size={17} />
              </button>
            )}
          </div>
        </div>

        <div className="principles">
          <div><span>01</span><h3>Inspect</h3><p>Static rules surface patterns that quietly multiply resource use across files.</p></div>
          <div><span>02</span><h3>Measure</h3><p>Runtime signals translate implementation detail into an energy estimate.</p></div>
          <div><span>03</span><h3>Improve</h3><p>Prioritised fixes keep the next decision clear and proportionate.</p></div>
        </div>
      </section>}

      {!result && !projectResult && view !== 'workspace' && <section className="empty-state">
        <span><FileText size={28} /></span>
        <h2>No analysis yet.</h2>
        <p>Start with a source file or ZIP archive to unlock this view.</p>
        <button className="primary-button" onClick={() => setView('workspace')}>Start an analysis <ArrowRight size={17} /></button>
      </section>}

      {/* FULL PROJECT OVERVIEW */}
      {projectResult && view === 'project' && <section className="report project-overview">
        <div className="report-hero">
          <div>
            <p className="overline">FULL PROJECT SUSTAINABILITY ANALYSIS</p>
            <h2>{projectResult.project_name}</h2>
            <p>{projectResult.total_files} Python files analyzed ({projectResult.successful_files} successful, {projectResult.error_files} errors) · {fixed(projectResult.total_lines_of_code, 0)} SLOC · analyzed in {projectResult.total_analysis_time_sec}s</p>
            <p title={CARBON_METHOD_NOTE}>Grid intensity ⓘ: {projectResult.carbon_intensity == null ? 'Unavailable' : `${fixed(projectResult.carbon_intensity, 2)} gCO₂eq/kWh`} · Zone: {projectResult.carbon_zone || 'Unknown'} · Source: {projectResult.carbon_source_type || 'unknown'} ({projectResult.carbon_source || 'provider unavailable'})</p>
            <p className="overview-carbon-note" title={CARBON_METHOD_NOTE}>Before carbon (modeled): {fixed(impactBeforeValues.carbon, 6)} gCO₂eq/run.</p>
          </div>
          <button className="secondary-button" onClick={() => setView('workspace')}>New project analysis <ChevronRight size={17} /></button>
        </div>

        <section className="overview-verdict" aria-label="Project verdict">
          <div><p className="overline">THE VERDICT</p><p className="overview-verdict-line">{overviewVerdict}</p></div>
          <p className="overview-direction">Lower is better for every score on this page.</p>
        </section>

        <div className="metric-grid overview-kpis">
          <Metric label="Files analyzed" metric={String(scopeMetrics.totalFiles)} unit={`${scopeMetrics.successfulFiles} succeeded · ${scopeMetrics.failedFiles} failed`} tone="blue" />
          <Metric label="Total SLOC" metric={fixed(scopeMetrics.sloc, 0)} unit="sum across analyzed files" tone="blue" />
          <Metric label="Finding locations" metric={fixed(scopeMetrics.findingLocations, 0)} unit={`${fixed(scopeMetrics.distinctRules, 0)} distinct rules`} tone="blue" />
          <Metric label="Structural complexity (SCI)" metric={fixed(scopeMetrics.meanSci, 4)} unit="index (0–1)" tone="green" help="Structural complexity index, 0-1, lower is simpler. Not the Green Software Foundation's Software Carbon Intensity." />
          <Metric label="Mean ESS per file" metric={fixed(scopeMetrics.meanEss, 2)} unit="score (0–10)" tone="amber" />
          <Metric label="Project energy" metric={fixed(scopeMetrics.energyJoules, 2)} unit="modeled J (relative) · one run per file" tone="green" help="Relative model estimate, not metered energy." />
          <Metric label="Mean CIRS per file" metric={fixed(scopeMetrics.meanCirs, 6)} unit="risk-weighted score" tone="ink" help="Unitless risk-weighted score; not physical gCO₂eq." />
          <Metric label="Sum of CIRS scores" metric={fixed(scopeMetrics.totalCirs, 6)} unit="unitless · one run per file" tone="ink" help="Sum of per-file risk-weighted scores." />
        </div>

        <section className="chart-section overview-section">
          <div className="chart-section-title"><div><p className="overline">WHERE TO START</p><h3>Three files to understand first</h3></div></div>
          <div className="top-files-grid overview-spotlights">
            {topEnergyFiles[0] && <article className="top-file-card overview-spotlight-card">
              <span className="top-file-badge energy"><Flame size={12} /> Biggest energy user</span>
              <h4 title={topEnergyFiles[0].relative_path}>{uniqueRankedPath(topEnergyFiles[0].relative_path, scopeFiles.map(file => file.relative_path), 46)}</h4>
              <div className="spotlight-primary">{fixed(topEnergyFiles[0].energy_joules, 2)} <small>modeled J (relative)</small></div>
              <p>{fixed(scopeMetrics.energyJoules ? topEnergyFiles[0].energy_joules / scopeMetrics.energyJoules * 100 : 0, 1)}% of project modeled energy.</p>
              <p className="spotlight-secondary" title={CARBON_METHOD_NOTE}>{carbonIntensityToDisplay == null ? 'Carbon unavailable' : `${fixed(topEnergyFiles[0].energy_joules / 3_600_000 * Number(carbonIntensityToDisplay), 5)} gCO₂eq modeled carbon`}</p>
              <small>Why it matters: reducing repeated work in the largest modeled energy user has the greatest energy impact by file.</small>
            </article>}
            {topFindingsFiles[0] && <article className="top-file-card overview-spotlight-card">
              <span className="top-file-badge smells"><Sparkles size={12} /> Most smell findings</span>
              <h4 title={topFindingsFiles[0].relative_path}>{uniqueRankedPath(topFindingsFiles[0].relative_path, scopeFiles.map(file => file.relative_path), 46)}</h4>
              <div className="spotlight-primary">{fixed(topFindingsFiles[0].rule_count, 0)} <small>{topFindingsFiles[0].rule_count === 1 ? 'rule' : 'rules'}</small></div>
              <p>{fixed(topFindingsFiles[0].findings_count, 0)} finding locations</p>
              <small>Why it matters: this file contains the most detected locations in the active scope.</small>
            </article>}
            {<article className="top-file-card overview-spotlight-card fix-first-card">
              <span className="top-file-badge smells"><Sparkles size={12} /> Fix this first</span>
              {fixThisFirstFile ? <><h4 title={fixThisFirstFile.relative_path}>{uniqueRankedPath(fixThisFirstFile.relative_path, getScopeFiles(projectResult.files, true).map(file => file.relative_path), 46)}</h4><div className="spotlight-primary">{fixed(fixThisFirstFile.energy_joules, 2)} <small>modeled J (relative)</small></div><p>{fixed(fixThisFirstFile.findings_count, 0)} finding locations · Source file</p><small>Chosen as the highest modeled-energy source file that has findings; test/example files are excluded from this choice.</small></> : <p>No source file with findings is available in this analysis.</p>}
            </article>}
          </div>
        </section>

        <section className="chart-section overview-section">
          <div className="chart-section-title"><div><p className="overline">ENERGY HOTSPOTS</p><h3>Which files use the most energy?</h3><p className="overview-takeaway">{scopeTakeaways.energySentence}</p><p className="chart-subtitle" title={CARBON_METHOD_NOTE}>Carbon = modeled energy (J → kWh) × grid intensity. Grid intensity {fixed(carbonIntensityToDisplay, 0)} gCO₂eq/kWh at analysis time ({analysisTimestampLabel}) · {carbonSourceZone} · {carbonSourceType}.</p></div><span className="scope-caption">Top 10 of {scopeMetrics.successfulFiles} files</span></div>
          <section className="panel overview-chart-panel">
            {projectFilesEnergyData.length ? <RankedMetricBars
              items={projectFilesEnergyData.map(item => ({ ...item, value: item.energyJoules, valueLabel: `${fixed(item.energyJoules, 0)} J · ${fixed(item.energyJoules / (scopeMetrics.energyJoules || 1) * 100, 1)}%`, valueHelp: `${fixed(item.energyJoules / 3_600_000 * Number(carbonIntensityToDisplay || 0), 5)} gCO₂eq modeled carbon at analysis-time intensity` }))}
              color="#587780" label="Top 10 files by modeled energy" formatValue={value => `${fixed(value, 2)} J`} allPaths={scopeFiles.map(file => file.relative_path)}
            /> : <ChartFallback title="No successful file results" />}
          </section>
        </section>

        <section className="chart-section overview-section">
          <div className="chart-section-title"><div><p className="overline">SMELL SUMMARY</p></div></div>
          <div className="chart-grid-2 overview-smell-grid">
            <section className="panel overview-chart-panel">
              <div className="panel-head"><div><h3>Where do the findings come from?</h3><p className="overview-takeaway">{scopeTakeaways.categorySentence}</p><p className="chart-subtitle">Where the energy-smell patterns come from.</p></div></div>
              <p className="category-unit-line">{fixed(scopeMetrics.findingLocations, 0)} finding locations (each detector finding record is one location; repeated instances of a rule count separately).</p>
              <div className="category-bars">{[...projectCategoryDistribution].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name)).map(item => {
                const percentage = projectVisibleFindingCount ? item.count / projectVisibleFindingCount * 100 : 0;
                return <div className="category-bar-row" key={item.name} title={item.rules.length ? `Rules: ${item.rules.join('; ')}` : 'No rules in this category'}><strong>{item.name}</strong><span className="category-bar-track"><span style={{ width: `${Math.max(item.count ? 1 : 0, percentage)}%` }} /></span><span>{item.count} <small>({percentage.toFixed(1)}%)</small></span></div>;
              })}</div>
            </section>
            <section className="panel overview-chart-panel">
              <div className="panel-head"><div><h3>How concentrated are the findings?</h3><p className="overview-takeaway">{scopeTakeaways.concentrationSentence}</p></div></div>
              {(() => {
                const total = scopeMetrics.successfulFiles || 1;
                return <>
                  <div className="ess-stacked-bar" aria-label="ESS display bands">
                    {projectEssBands.map(band => <div key={band.label} className={`ess-segment ess-${band.label.toLowerCase()}`} style={{ width: `${band.count / total * 100}%` }} title={`${band.label}: ${band.count} files`} />)}
                  </div>
                  <p className="ess-band-summary">{projectEssBands.map(band => `${band.count} ${band.label.toLowerCase()}${band.count === 1 ? ' file' : ' files'} · ${(band.count / total * 100).toFixed(1)}%`).join(' · ')}</p>
                  <p className="ess-band-legend"><span className="ess-low-key">Green 0–&lt;3</span><span className="ess-medium-key">Amber 3–&lt;7</span><span className="ess-high-key">Red 7–10</span><span>Display bands, not model outputs.</span></p>
                  <details className="fine-ess-distribution"><summary>Show detailed distribution</summary>
                    <div className="chart" style={{ marginTop: '14px' }}><ResponsiveContainer width="100%" height={220}><BarChart data={projectEssDistribution} margin={{ top: 8, right: 12, left: 12, bottom: 20 }}>
                      <CartesianGrid vertical={false} stroke="var(--line)" /><XAxis dataKey="label" tick={{ fontSize: 13 }} label={{ value: 'ESS range', position: 'insideBottom', offset: -7, fontSize: 13 }} /><YAxis allowDecimals={false} tick={{ fontSize: 13 }} label={{ value: 'Number of files', angle: -90, position: 'insideLeft', fontSize: 13 }} /><Tooltip formatter={(value: any) => [`${value} files`, 'Count']} /><Bar dataKey="count" name="Files" fill="#2e6956" radius={[4, 4, 0, 0]} />
                    </BarChart></ResponsiveContainer></div>
                  </details>
                </>;
              })()}
            </section>
          </div>
        </section>

        <section className="chart-section overview-section">
          <div className="chart-section-title"><div><p className="overline">FILE METRICS</p><h3>Which files should I fix first?</h3><p className="overview-takeaway">{scopeTakeaways.fixFirstSentence}</p><p className="chart-subtitle">Ranked by the existing CIRS risk-weighted score, highest first. Status uses the ESS display bands shown above.</p></div></div>
          <section className="panel overview-chart-panel">
            <div className="fix-first-file-list" role="list" aria-label="Top five files to fix, ranked by CIRS">
              {projectFilesToFixData.map(file => {
                const rawFindings = file.single_file_response?.pipeline_raw?.energy_smell_report?.findings || [];
                const descriptionsByRule = new Map<string, string>();
                for (const finding of rawFindings) {
                  const id = String(finding.rule_id || '');
                  if (id && !descriptionsByRule.has(id)) descriptionsByRule.set(id, String(finding.message || id));
                }
                const ruleDescriptions = [...descriptionsByRule.entries()].map(([id, message]) => `${id}: ${message}`);
                const status = file.ess < 3 ? 'OK' : file.ess < 7 ? 'Watch' : 'Needs work';
                const statusClass = file.ess < 3 ? 'ess-low' : file.ess < 7 ? 'ess-medium' : 'ess-high';
                return <article className="fix-first-file-row" role="listitem" key={file.relative_path}>
                  <strong className="fix-first-file-path" title={file.relative_path}>{uniqueRankedPath(file.relative_path, scopeFiles.map(item => item.relative_path), 48)}</strong>
                  <span className="fix-first-file-reason">{file.ess >= 7 ? 'High' : file.ess >= 3 ? 'Medium' : 'Low'} energy-smell score {fixed(file.ess, 1)} · {file.rule_count} {file.rule_count === 1 ? 'rule' : 'rules'}{ruleDescriptions.length ? `: ${ruleDescriptions.slice(0, 2).join('; ')}${ruleDescriptions.length > 2 ? `; +${ruleDescriptions.length - 2} more` : ''}` : ''}</span>
                  <span className={`ess-pill ${statusClass}`}>{status}</span>
                  <button type="button" className="text-button fix-first-recommendations" onClick={() => { setRecommendationTargetPath(file.relative_path); setAnalysisMode('project'); navigateView('recommendations'); }}>See recommendations</button>
                </article>;
              })}
              {!projectFilesToFixData.length && <p className="soft-copy">No files with finding locations in this scope.</p>}
            </div>
            <details className="detailed-metric-expander">
              <summary>Detailed scores</summary>
              <div className="metric-chart-tabs" role="tablist" aria-label="Detailed file scores">
                <button role="tab" aria-selected={projectMetricTab === 'complexity'} className={projectMetricTab === 'complexity' ? 'active' : ''} onClick={() => setProjectMetricTab('complexity')}>Structural complexity (SCI)</button>
                <button role="tab" aria-selected={projectMetricTab === 'ess'} className={projectMetricTab === 'ess' ? 'active' : ''} onClick={() => setProjectMetricTab('ess')}>Energy smells</button>
                <button role="tab" aria-selected={projectMetricTab === 'cirs'} className={projectMetricTab === 'cirs' ? 'active' : ''} onClick={() => setProjectMetricTab('cirs')}>Risk</button>
              </div>
              <p className="chart-subtitle">{projectMetricTab === 'complexity' ? 'Structural complexity index (SCI), 0–1; lower is simpler. Not the Green Software Foundation’s Software Carbon Intensity.' : projectMetricTab === 'ess' ? 'How many energy-wasting patterns a file contains (0–10, lower is better).' : 'CIRS is a unitless modeled risk score; lower is better.'}</p>
              {projectMetricTab === 'ess' && <p className="metric-band-note">Green 0–&lt;3 · Amber 3–&lt;7 · Red 7–10.</p>}
              {projectMetricTab === 'complexity' ? <RankedMetricBars items={projectFilesSciData.map(item => ({ name: item.name, relativePath: item.relativePath, value: item.sci }))} color="#587780" label="Files by structural complexity (SCI)" formatValue={value => fixed(value, 3)} />
                : projectMetricTab === 'ess' ? <RankedMetricBars items={projectFilesEssData.map(item => ({ name: item.name, relativePath: item.relativePath, value: item.ess }))} color="#587780" label="Files by Energy Smell Score" formatValue={value => `${fixed(value, 1)} / 10`} />
                  : <RankedMetricBars items={projectFilesCirsData.map(item => ({ name: item.name, relativePath: item.relativePath, value: item.cirs }))} color="#587780" label="Files by CIRS" formatValue={value => fixed(value, 6)} />}
            </details>
          </section>
        </section>

        <section className="panel project-files-panel overview-section">
          <div className="panel-head" style={{ alignItems: 'center' }}>
            <div><p className="overline">FILE DRILLDOWN</p><h3>Analyzed files ({fixed(sortedProjectFiles.length, 0)} shown · {scopeMetrics.successfulFiles} succeeded · {scopeMetrics.failedFiles} failed)</h3></div>
            <div className="file-table-controls">
              <label className="search-field" style={{ width: '220px', height: '36px' }}><Search size={14} /><input value={tableSearch} onChange={event => setTableSearch(event.target.value)} placeholder="Search file or folder…" /></label>
              <select aria-label="Filter files by analysis status" value={fileStatusFilter} onChange={event => setFileStatusFilter(event.target.value as 'all' | 'success' | 'error')}><option value="all">All statuses</option><option value="success">Successful</option><option value="error">Failed</option></select>
            </div>
          </div>
          <p className="soft-copy static-analysis-note">Static analysis only; code is not executed.</p>
          <div className="project-table-wrap"><table className="project-table compact-project-table">
            <thead><tr>
              <th onClick={() => { if (sortColumn === 'filename') setSortAsc(!sortAsc); else { setSortColumn('filename'); setSortAsc(true); } }}>File</th>
              <th onClick={() => { if (sortColumn === 'energy_joules') setSortAsc(!sortAsc); else { setSortColumn('energy_joules'); setSortAsc(false); } }}>Modeled J {sortColumn === 'energy_joules' ? (sortAsc ? '▲' : '▼') : ''}</th>
              <th onClick={() => { if (sortColumn === 'findings_count') setSortAsc(!sortAsc); else { setSortColumn('findings_count'); setSortAsc(false); } }}>Rules · locations</th>
              <th>Status</th>
              <th onClick={() => { if (sortColumn === 'sci') setSortAsc(!sortAsc); else { setSortColumn('sci'); setSortAsc(false); } }}>Structural complexity (SCI)</th>
              <th onClick={() => { if (sortColumn === 'ess') setSortAsc(!sortAsc); else { setSortColumn('ess'); setSortAsc(false); } }}>ESS</th>
              <th onClick={() => { if (sortColumn === 'cirs') setSortAsc(!sortAsc); else { setSortColumn('cirs'); setSortAsc(false); } }}>CIRS</th>
              <th onClick={() => { if (sortColumn === 'lines_of_code') setSortAsc(!sortAsc); else { setSortColumn('lines_of_code'); setSortAsc(false); } }}>SLOC</th>
              <th>Actions</th>
            </tr></thead>
            <tbody>
              {sortedProjectFiles.length === 0 && <tr><td colSpan={9} className="empty-table-message">No files match the current search and status filter.</td></tr>}
              {sortedProjectFiles.map((fileItem: any) => <tr key={fileItem.relative_path} className={fileItem.status === 'error' ? 'row-error' : ''}>
                <td><div className="file-name-cell"><FileCode2 size={15} /><div className="compact-file-label"><strong title={fileItem.relative_path}>{fileItem.filename}</strong><small title={fileItem.relative_path}>{fileItem.relative_path.replace(/\\/g, '/').split('/').slice(-2, -1)[0] || 'root'}</small><span className={`file-scope-chip ${isTestOrExamplePath(fileItem.relative_path) ? 'is-test' : 'is-source'}`}>{isTestOrExamplePath(fileItem.relative_path) ? 'test' : 'source'}</span></div></div></td>
                <td>{fileItem.status === 'success' ? fixed(fileItem.energy_joules, 2) : '—'}</td>
                <td>{fileItem.status === 'success' ? <span className="findings-badge">{fixed(fileItem.rule_count, 0)} {fileItem.rule_count === 1 ? 'rule' : 'rules'} · {fixed(fileItem.findings_count, 0)} {fileItem.findings_count === 1 ? 'location' : 'locations'}</span> : '—'}</td>
                <td><span className={`status-badge ${fileItem.status}`}>{fileItem.status === 'error' ? 'Failed' : 'Successful'}</span></td>
                <td>{fileItem.status === 'success' ? fixed(fileItem.sci, 4) : '—'}</td>
                <td>{fileItem.status === 'success' ? <span className={`ess-pill ${fileItem.ess < 3 ? 'ess-low' : fileItem.ess < 7 ? 'ess-medium' : 'ess-high'}`}>{fixed(fileItem.ess, 2)}</span> : '—'}</td>
                <td>{fileItem.status === 'success' ? fixed(fileItem.cirs, 6) : '—'}</td><td>{fileItem.status === 'success' ? fixed(fileItem.lines_of_code, 0) : '—'}</td>
                <td>{fileItem.single_file_response && <button className="small-button inspect-file-btn" onClick={() => { setResult(fileItem.single_file_response); setFilename(fileItem.filename); if (fileItem.original_code) setCode(fileItem.original_code); setAnalysisMode('file'); navigateView('results'); }}>Inspect <ArrowRight size={13} /></button>}</td>
              </tr>)}
            </tbody>
          </table></div>
        </section>
      </section>}

      {/* SINGLE FILE OVERVIEW */}
      {result && view === 'results' && <section className="report">
        <div className="report-hero">
          <div>
            <p className="overline">{projectResult ? `INSPECTING FILE IN ${projectResult.project_name.toUpperCase()}` : 'SINGLE FILE ANALYSIS COMPLETE'}</p>
            <h2>{result.filename || filename}</h2>
            <p>{display(carbon.zone?.display_name, currentZone?.display_name || 'Selected grid')} · {display(carbon.zone?.zone_key, zone)}</p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {projectResult && (
              <button className="secondary-button back-to-project-hero-btn" onClick={() => { setAnalysisMode('project'); navigateView('project'); }}>
                <ArrowLeft size={16} /> Back to Project Overview
              </button>
            )}
            <button className="secondary-button" onClick={() => navigateView('recommendations')}>View recommendations <ChevronRight size={17} /></button>
          </div>
        </div>

        {singleFileIsTestCode && <label className="test-code-toggle"><input type="checkbox" checked={excludeTestCode} onChange={event => setExcludeTestCode(event.target.checked)} /> Exclude test/example findings from totals <strong>{excludeTestCode ? 'On' : 'Off'}</strong> · Test code</label>}

        <div className="metric-grid">
          <Metric label="Estimated Energy" metric={fixed(energy.energy_joules, 3)} unit="modeled J (relative)" tone="green" />
              <Metric label="Risk-weighted carbon score (CIRS)" metric={fixed(metrics?.carbon_impact_risk_score, 6)} unit="unitless score" tone="ink" />
          <Metric label="Energy Smell Score" metric={fixed(metrics?.energy_smell_score, 2)} unit="out of 10" tone="amber" />
          <Metric label="Finding locations" metric={String(singleVisibleFindingCount)} unit={singleFileIsTestCode ? 'test-code toggle applied' : 'detector locations in this file'} tone="blue" />
        </div>

        <div className="metric-grid" style={{ marginTop: '16px' }}>
          <Metric label="Cyclomatic Complexity (CC)" metric={fixed(complexity.cc, 1)} unit="decision paths" tone="blue" />
          <Metric label="Nesting Depth (ND)" metric={fixed(complexity.nd, 0)} unit="max depth" tone="blue" />
          <Metric label="Function Density (FD)" metric={fixed(complexity.fd, 4)} unit="funcs / SLOC" tone="blue" />
          <Metric label="Source Lines (SLOC)" metric={fixed(complexity.sloc, 0)} unit="lines of code" tone="blue" />
          <Metric label="Structural Index (SCI)" metric={fixed(complexity.sci, 4)} unit="index (0-1)" tone="green" />
        </div>

        <div className="report-grid">
          <section className="panel">
            <div className="panel-head">
              <div><p className="overline">PRIORITY SIGNALS</p><h3>Recommendation Priority Scores</h3></div>
              <span>{recommendations.length} recommendations</span>
            </div>
            {chart.length ? (
              <div className="chart">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={chart} layout="vertical" margin={{ left: 4, right: 14 }}>
                    <CartesianGrid horizontal={false} stroke="#e7e4dd" />
                    <XAxis type="number" hide />
                    <YAxis type="category" dataKey="name" width={110} tick={{ fill: '#6d6a63', fontSize: 11 }} />
                    <Tooltip
                      cursor={{ fill: '#f3f1eb' }}
                      formatter={(_val: any, _name: any, item: any) => [
                        item?.payload?.rawScore < 0.001 ? item?.payload?.rawScore?.toExponential(4) : item?.payload?.rawScore?.toFixed(6),
                        'Priority Score'
                      ]}
                    />
                    <Bar dataKey="displayScore" fill="#2f6b57" radius={[0, 5, 5, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <ChartFallback title="No priority signals reported" message="No energy smells were reported for this file." />}
          </section>

          <section className="panel">
            <div className="panel-head">
              <div><p className="overline">COMPLEXITY PROFILE</p><h3>Code Structure Metrics</h3></div>
              <span>SLOC: {fixed(complexity.sloc, 0)}</span>
            </div>
            {singleFileComplexityData.length ? (
              <div className="chart">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={singleFileComplexityData} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#e7e4dd" strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fill: '#6d6a63', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#6d6a63', fontSize: 11 }} />
                    <Tooltip
                      cursor={{ fill: '#f3f1eb' }}
                      formatter={(val: any, _name: any, item: any) => [
                        `${item?.payload?.rawValue || val} (${item?.payload?.unit})`,
                        item?.payload?.full || item?.payload?.name
                      ]}
                    />
                    <Bar dataKey="value" fill="#2f6b57" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <ChartFallback title="No complexity metrics available" />}
          </section>
        </div>

        {/* CARBON / ENERGY SUMMARY & REFACTOR COMPARISON */}
        <div className="report-grid" style={{ marginTop: '18px' }}>
          <section className="panel carbon-panel">
            <p className="overline">CARBON / ENERGY SUMMARY</p>
            <h3>{display(carbon.zone?.display_name, currentZone?.display_name)}</h3>
            <div className="intensity" title={CARBON_METHOD_NOTE}><strong>{fixed(carbonIntensityToDisplay, 2)} ⓘ</strong><span>gCO₂eq/kWh</span></div>
            <p className="soft-copy" style={{ marginTop: '-8px' }}>{carbonSourceZone} · {carbonSourceType} · {postRefactor.carbon_metadata?.source || ''}</p>
            <p className="soft-copy">
              <span title={CARBON_METHOD_NOTE}>Estimated unweighted carbon ⓘ: {fixed(((energy.energy_joules || 0) / 3600000.0) * carbonIntensityToDisplay, 6)} modeled gCO₂eq/run from a relative energy score, not metered energy.</span>
            </p>
            <button className="text-button" onClick={() => setView('schedule')}>Explore better execution times <ArrowRight size={15} /></button>
          </section>

          {singleFileRefactorComparisonData.length > 0 ? (
            <section className="panel">
              <div className="panel-head">
                  <div><p className="overline">GENERATED REFACTOR ESTIMATE</p><h3>Metrics Before vs After</h3></div>
                  <span>Modeled estimate; assumes 10 iterations per loop. Timing is separate.</span>
              </div>
              <p className="soft-copy">SCI is structural; loop cost is applied in the runtime estimate.</p>
              <MetricComparison rows={singleFileRefactorComparisonData} />
            </section>
          ) : (
            <section className="panel">
              <div className="panel-head">
                <div><p className="overline">RESEARCH METRICS</p><h3>CIRS & ESS Ratings</h3></div>
              </div>
              <div style={{ padding: '16px 0', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: 'var(--paper)', padding: '14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
                  <p style={{ margin: 0, fontSize: '11px', color: 'var(--muted)' }}>Energy Smell Score (ESS)</p>
                  <strong style={{ fontSize: '24px', color: 'var(--ink)', display: 'block', marginTop: '4px' }}>{fixed(metrics?.energy_smell_score, 2)} / 10</strong>
                  <span style={{ fontSize: '10px', color: 'var(--muted)' }}>Version: {metrics?.ess_version || '1.0.0'}</span>
                </div>
                <div style={{ background: 'var(--paper)', padding: '14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
                  <p style={{ margin: 0, fontSize: '11px', color: 'var(--muted)' }}>Risk-weighted carbon score (CIRS)</p>
                  <strong style={{ fontSize: '20px', color: 'var(--forest)', display: 'block', marginTop: '4px' }}>{fixed(metrics?.carbon_impact_risk_score, 6)}</strong>
                  <span style={{ fontSize: '10px', color: 'var(--muted)' }}>unitless risk-weighted score</span>
                </div>
              </div>
            </section>
          )}
          {result && <CarbonScenarioComparison result={result} currentIntensity={carbonIntensityToDisplay} />}
        </div>
      </section>}

      {/* RECOMMENDATIONS VIEW (HANDLES BOTH PROJECT & SINGLE FILE) */}
      {view === 'recommendations' && (
        analysisMode === 'project' && projectResult ? (
          <section>
            <div className="report-hero">
              <div>
                <p className="overline">PROJECT-LEVEL REFINEMENT QUEUE</p>
                <h2>{projectResult.project_name} — Recommendations</h2>
              </div>
              <span className="count-pill">{projectAggregatedRecommendations.length} unique rules aggregated</span>
            </div>

            <ProjectCodeChangesSection projectResult={projectResult} projectFiles={projectFiles} projectZipFile={projectZipFile} excludeTestCode={excludeTestCode} targetPath={recommendationTargetPath} clearTargetPath={() => setRecommendationTargetPath(null)} />

          </section>
        ) : result ? (
          <section>
            <div className="report-hero">
              <div>
                <p className="overline">{projectResult ? `INSPECTING FILE IN ${projectResult.project_name.toUpperCase()}` : 'REFINEMENT QUEUE'}</p>
                <h2>{result.filename || filename} — Recommendations</h2>
              </div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                {projectResult && (
                  <button className="secondary-button back-to-project-hero-btn" onClick={() => { setAnalysisMode('project'); navigateView('project'); }}>
                    <ArrowLeft size={16} /> Back to Project Overview
                  </button>
                )}
                <span className="count-pill">{recommendations.length} recommendations</span>
              </div>
            </div>
            <section className="panel suggested-code-section">
              <div className="panel-head">
                <div><p className="overline">ISSUE-BY-ISSUE FIXES</p><h3>Suggested Code Changes</h3></div>
              </div>
              <CodeChangesSection
                filename={result.filename || filename}
                sourceCode={code || result.original_code || ''}
                findings={singleVisibleFindings}
                autoFixes={result.auto_applied_fixes || []}
                manualFixes={result.manual_fixes || []}
                recommendations={recommendations}
                locationSuggestions={result.location_suggestions || []}
              />
            </section>
          </section>
        ) : null
      )}

      {/* IMPACT VIEW (HANDLES BOTH PROJECT & SINGLE FILE) */}
      {view === 'impact' && (
        analysisMode === 'project' && projectResult ? (
          <section className="report">
            <div className="report-hero">
              <div>
                <p className="overline">PROJECT REFACTOR IMPACT · MODELED ESTIMATES</p>
                <h2>{projectResult.project_name} — Project Impact</h2>
                <p>After combines accepted refactors with the forecast execution window. Project totals assume one run per file; all values are modeled estimates, not measurements.</p>
              </div>
            </div>

            <section className="panel project-files-panel" style={{ marginTop: '20px' }}>
              <div className="panel-head">
                  <div><p className="overline">PROJECT TOTALS · MODELED ESTIMATES</p><h3>Before | After | Delta</h3></div>
                  <span>After = accepted fixes + green scheduling window</span>
              </div>
              <div className="project-table-wrap">
                <table className="project-table">
                  <thead><tr><th>Estimated metric</th><th>Before</th><th>After</th><th>Delta (after − before)</th><th>Delta %</th></tr></thead>
                  <tbody>
                    {impactRows.map(row => {
                      const deltaPercent = row.before === 0 ? null : (row.after - row.before) / Math.abs(row.before) * 100;
                      return <tr key={row.name}><td><strong title={row.help}>{row.name}{row.help ? ' ⓘ' : ''}</strong></td><td title={row.help}>{fixed(row.before, row.digits)} {row.unit}</td><td title={row.help}>{fixed(row.after, row.digits)} {row.unit}</td><td title={row.help}>{fixed(row.after - row.before, row.digits)} {row.unit}</td><td>{deltaPercent === null ? '—' : `${fixed(deltaPercent, 2)}%`}</td></tr>;
                    })}
                  </tbody>
                </table>
              </div>
              {appliedFixDetails && <p className="soft-copy" style={{ padding: '0 16px 12px' }}><strong>Applied fix:</strong> {appliedFixDetails.file.relative_path} · {appliedFixDetails.fix.rule_id} · {appliedFixDetails.fix.description || 'AST transformation applied.'} {Math.abs(projectBeforeEnergy - projectAfterEnergy) < 1e-9 ? <><strong>Why Energy is unchanged:</strong> the refactor removes the reported smell while the modeled loop-operation estimate remains unchanged.</> : <><strong>Modeled Energy change:</strong> {fixed(projectBeforeEnergy, 2)} → {fixed(projectAfterEnergy, 2)} modeled J (relative), based on the transformed source.</>}</p>}
              <p className="soft-copy" style={{ padding: '0 16px 14px' }}>Scheduling changes carbon and CIRS estimates only; Energy stays at the accepted-refactor estimate. CIRS includes carbon intensity as a term, so its After estimate uses the same window intensity. All figures are modeled, not measured. Source: {impactForecast?.source || projectResult?.carbon_source || 'Unavailable'} · {impactForecast?.source_type || projectResult?.carbon_source_type || 'unknown'}.</p>
            </section>

            <section className="panel project-files-panel" style={{ marginTop: '20px' }}>
              <div className="panel-head">
                <div><p className="overline">GREEN SCHEDULING · MODELED</p><h3>Recommended execution window</h3></div>
                <span>{impactForecast?.source || 'Forecast provider'} · {impactForecast?.source_type || 'source unavailable'}{impactForecast?.source_type !== 'live' && <b className="mock-data-badge">MOCK DATA</b>}</span>
              </div>
              {forecastLoading && !impactForecast ? <p className="soft-copy" style={{ padding: '0 16px 16px' }}>Loading the project forecast…</p> : (forecastError && !impactForecast) ? <p className="soft-copy" role="status" style={{ padding: '0 16px 16px' }}>Forecast unavailable: {forecastError}. Carbon comparison currently uses the selected grid intensity without a schedule adjustment.</p> : (
                <div className="schedule-window-card" style={{ margin: '0 16px 16px' }}>
                  <strong>{impactForecast?.has_cleaner_window === false ? 'No cleaner forecast window · use current schedule' : !impactWindowIsUpcoming ? 'The saved forecast window has passed' : `${impactWindowStartsNow ? 'Starts now · ' : 'Starts later · '}${formatWindowTime(impactWindowStart)}${impactForecast?.window_end ? ` to ${formatHour(impactForecast.window_end ?? undefined)}` : ''}`}</strong>
                  <span title={CARBON_METHOD_NOTE}>{!impactWindowIsUpcoming ? 'This analysis snapshot preserves its original modeled values; refresh the analysis for a new upcoming window. ' : ''}{impactForecast?.has_cleaner_window === false ? `Best forecast hour: ${formatWindowTime(impactForecast?.recommended_execution_time || undefined)} · ` : ''}Intensity now {fixed(impactCurrentIntensity, 2)} → applied in window {fixed(impactScheduledIntensity, 2)} gCO₂eq/kWh · {fixed(impactForecast?.scheduling_reduction_percent ?? 0, 2)}% carbon reduction{impactForecast?.has_cleaner_window === false ? ` (best forecast ${fixed(impactForecastMinimum, 2)} is not cleaner)` : ''}</span>
                </div>
              )}
            </section>

            {scopedAppliedFixDetails.length === 0 && (
              <div className="modeled-no-improvement" role="status"><strong>No modeled change</strong><span>No automatic fix was accepted. The per-file table gives the reason for each file.</span></div>
            )}

            <section className="panel project-files-panel" style={{ marginTop: '20px' }}>
              <div className="panel-head">
                <div>
                  <p className="overline">PER-FILE MODELED COMPARISON</p>
                  <h3>Estimated before and after · {impactFilesSorted.length} files shown</h3>
                </div>
              </div>
              <div className="impact-status-filters" aria-label="Filter files by fix status">
                {(['all', 'applied', 'rejected', 'not_auto_fixable', 'no_issues'] as const).map(state => {
                  const count = state === 'all' ? scopeFiles.length : impactStatusCounts[state];
                  const label = state === 'all' ? 'All' : fixStateLabels[state];
                  return <button type="button" key={state} className={`status-filter-chip ${impactStatusFilter === state ? 'active' : ''}`} onClick={() => setImpactStatusFilter(state)}>{label} <span>{count}</span></button>;
                })}
              </div>
              {impactReasonGroups.length > 0 && <details className="impact-reason-groups"><summary>Grouped fix reasons ({impactReasonGroups.length} distinct)</summary><ul>{impactReasonGroups.map(([reason, files]) => <li key={reason}><strong>{files.length} file{files.length === 1 ? '' : 's'}:</strong> {reason}<small>{files.join(', ')}</small></li>)}</ul></details>}
              <div className="project-table-wrap">
                <table className="project-table">
                  <thead>
                    <tr>
                      <th>File Name</th>
                      <th>SLOC</th>
                      <th>SCI (Before → After)</th>
                      <th>Energy (Before → After, modeled J)</th>
                      <th>Fix status</th>
                      <th>Reason</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {impactFilesSorted.map((fileItem: ProjectFileResult) => {
                      const post = fileItem.single_file_response?.post_refactor_estimation || {};
                      const fixState = projectFixState(fileItem);
                      const groupedReason = impactReasonGroups.find(([, files]) => files.includes(fileItem.relative_path));
                      const fixAttempted = fixState === 'applied' || fixState === 'rejected';
                      return (
                        <tr key={fileItem.relative_path}>
                          <td><strong>{fileItem.filename}</strong></td>
                          <td>{fileItem.lines_of_code}</td>
                          <td>{post.sci_before !== undefined ? `${fixed(post.sci_before, 3)} → ${fixed(post.sci_after, 3)}` : fixed(fileItem.sci, 3)}</td>
                          <td>{fixed(fileItem.before_energy, 2)} → {fixed(fileItem.after_energy, 2)}</td>
                          <td><span className={`status-badge ${fixState === 'applied' ? 'success' : fixState === 'rejected' ? 'error' : ''}`}>{fixStateLabels[fixState]}</span></td>
                          <td>{groupedReason ? <span title={groupedReason[0]}>Reason shared by {groupedReason[1].length} file{groupedReason[1].length === 1 ? '' : 's'}; see grouped reasons above.</span> : fixState === 'no_issues' ? 'No findings were returned for this file.' : '—'}</td>
                          <td>
                            {fileItem.single_file_response && fixAttempted && (
                              <button className="small-button" onClick={() => {
                                const detail = fileItem.single_file_response;
                                if (!detail) return;
                                setResult(detail);
                                setFilename(fileItem.filename);
                                setCode(fileItem.original_code || '');
                                setAnalysisMode('file');
                                navigateView('impact');
                              }}>
                                Inspect AST Refactor <ArrowRight size={13} />
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          </section>
        ) : result ? (
          <section className="report">
            <div className="report-hero">
              <div>
                <p className="overline">{projectResult ? `INSPECTING FILE IN ${projectResult.project_name.toUpperCase()}` : 'IMPROVEMENT OUTLOOK & AFTER-ESTIMATION'}</p>
                <h2>{result.filename || filename} — Refactor & Impact</h2>
                <p>AST transformation results and modeled impact for {result.filename || filename}; uploaded code execution is disabled by default.</p>
              </div>
              {projectResult && (
                <button className="secondary-button back-to-project-hero-btn" onClick={() => { setAnalysisMode('project'); navigateView('project'); }}>
                  <ArrowLeft size={16} /> Back to Project Overview
                </button>
              )}
            </div>

            {postRefactor.no_modeled_improvement && <div className="modeled-no-improvement" role="status"><strong>No modeled improvement</strong><span>The automatic change was withheld because energy, CIRS, ESS, SCI, and actionable smell counts must not regress, with energy or CIRS improving. No transformed code is recommended.</span></div>}

            {postRefactor.sci_before !== undefined && (
              <div className="refactor-impact-grid metric-grid">
                <Metric label="SCI (Before → After)" metric={`${fixed(postRefactor.sci_before, 4)} → ${fixed(postRefactor.sci_after, 4)}`} unit="index (0-1)" tone="green" />
                <Metric label="ESS (Before → After)" metric={`${fixed(postRefactor.ess_before, 3)} → ${fixed(postRefactor.ess_after, 3)}`} unit="out of 10 · distinct rule types" tone="amber" />
                <Metric label="Energy Smells (Before → After)" metric={`${postRefactor.smells_before ?? 0} → ${postRefactor.smells_after ?? 0}`} unit={`actionable (conf ≥ 0.5) · burden ${fixed(postRefactor.smell_burden_before, 2)} → ${fixed(postRefactor.smell_burden_after, 2)}`} tone="amber" />
                <Metric label="Energy (Before → After)" metric={`${fixed(postRefactor.energy_before_joules, 3)} → ${fixed(postRefactor.energy_after_joules, 3)}`} unit="modeled J (relative)" tone="amber" />
                <Metric label="Risk-weighted score (Before → After)" metric={`${fixed(postRefactor.cirs_before, 6)} → ${fixed(postRefactor.cirs_after, 6)}`} unit="unitless CIRS research score" tone="ink" />
                <Metric
                  label="Measured Speedup"
                  metric={postRefactor.measurement_reliability === 'low_confidence_small_workload'
                    ? 'Not measurable (workload too small)'
                    : postRefactor.measurement_reliability === 'disabled'
                      ? 'Not run'
                      : postRefactor.measurement_reliability === 'unavailable'
                        ? '—'
                        : postRefactor.measured_reduction_percent !== undefined
                          ? `${fixed(postRefactor.measured_reduction_percent, 1)}%`
                          : '—'}
                  unit={postRefactor.measurement_reliability === 'low_confidence_small_workload'
                    ? ''
                    : postRefactor.measurement_reliability || 'reliability unavailable'}
                  tone="blue"
                />
              </div>
            )}

            {result.measured_runtime && (
              <p className="muted-copy" role="note">
                {result.execution_status === 'not_executed'
                  ? <>Execution for <strong>{result.filename || filename}</strong>: Not executed (static analysis only).</>
                  : <>Sandbox execution for <strong>{result.filename || filename}</strong>: original {result.measured_runtime.original?.status || 'unknown'}, generated {result.measured_runtime.optimized?.status || 'unknown'}; hard timeout {result.measured_runtime.hard_timeout_sec ?? '—'}s; network blocked by Python socket controls.</>}
              </p>
            )}

            {singleFileRefactorComparisonData.length > 0 && (
              <section className="panel" style={{ marginBottom: '18px' }}>
                <div className="panel-head">
                  <div><p className="overline">BEFORE / AFTER</p><h3>What changed in the estimate</h3></div>
                  <span>Each row keeps its own unit</span>
                </div>
                <MetricComparison rows={singleFileRefactorComparisonData} />
              </section>
            )}
            <CarbonScenarioComparison result={result} currentIntensity={carbonIntensityToDisplay} />

            <div className="impact-card">
              <div className="impact-icon"><Sparkles size={24} /></div>
              <div>
                <p className="overline">NEXT BEST STEP</p>
                <h3>{postRefactor.no_modeled_improvement ? 'No modeled improvement' : 'Apply the safe AST recommendations, then verify with a fresh run.'}</h3>
                <p>
                  {postRefactor.no_modeled_improvement
                    ? 'The generated change was not retained or recommended because modeled energy, CIRS, ESS, SCI, and actionable smell counts must not regress, with energy or CIRS improving.'
                    : result.auto_applied_fixes?.length
                    ? `${result.auto_applied_fixes.length} safe AST change(s) were generated. Your uploaded source file is not overwritten.`
                    : 'No safe automatic source change was generated for this file. The original remains unchanged; review the manual recommendations.'}
                  {' '}Energy, SCI, ESS, and CIRS are model estimates.{' '}
                  {projectResult
                    ? 'Runtime timing is skipped during parallel project analysis; analyze this file individually for an uncontended timing comparison.'
                    : 'Runtime speedup is a separate timing comparison and can vary between runs.'}
                </p>
              </div>
              <button className="primary-button" onClick={() => navigateView('recommendations')}>Review fixes <ArrowRight size={17} /></button>
            </div>

            {postRefactor.findings_comparison && postRefactor.findings_comparison.length > 0 && (
              <section className="panel project-files-panel" style={{ marginTop: '20px' }}>
                <div className="panel-head">
                  <div>
                    <p className="overline">FINDINGS RESOLUTION AUDIT</p>
                    <h3>Distinct rule types resolved: {fixed(postRefactor.resolved_rule_count ?? postRefactor.findings_comparison.filter((f: any) => f.is_resolved).length, 0)}</h3>
                    <span>{fixed(postRefactor.finding_locations_before, 0)} finding locations before → {fixed(postRefactor.finding_locations_after, 0)} after</span>
                  </div>
                </div>
                <div className="project-table-wrap">
                  <table className="project-table">
                    <thead>
                      <tr>
                        <th>Rule / Pattern</th>
                        <th>Line</th>
                        <th>Confidence Before</th>
                        <th>Confidence After</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {postRefactor.findings_comparison.map((f: any, idx: number) => (
                        <tr key={idx}>
                          <td><strong>{f.rule_name || f.rule_id}</strong></td>
                          <td>L{f.line_number}</td>
                          <td>{fixed(f.confidence_before, 2)}</td>
                          <td>{fixed(f.confidence_after, 2)}</td>
                          <td>
                            <span className={`status-badge ${f.is_resolved ? 'success' : 'error'}`}>
                              {f.is_resolved ? 'Resolved' : 'Unchanged'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {result.optimized_code && (
              <section className="code-preview">
                <div className="panel-head">
                  <div><p className="overline">GENERATED REFACTOR</p><h3>Optimized AST Source Code</h3></div>
                  <button className="secondary-button" onClick={() => download(result.optimized_code || '', getOptimizedFilename(result.filename || filename), 'text/x-python')} title="Download optimized file"><Download size={16} /> Download optimized file</button>
                </div>
                <pre>{result.optimized_code}</pre>
              </section>
            )}
          </section>
        ) : null
      )}

      {/* GREEN SCHEDULING VIEW (HANDLES BOTH PROJECT & SINGLE FILE) */}
      {view === 'schedule' && (result || projectResult) && (
        <section>
          <div className="report-hero">
            <div>
              <p className="overline">GREEN SCHEDULING FORECAST</p>
              <h2>{analysisMode === 'project' && projectResult ? `${projectResult.project_name} — Project Green Scheduling` : `${result?.filename || filename} — Green Scheduling`}</h2>
              <p>Forecast availability and recommended low-carbon execution windows for your workload in region {zone}.</p>
            </div>
            <label className="compact-select">
              <Globe2 size={16} />
              <select value={zone} onChange={e => setZone(e.target.value)} aria-label="Select electricity grid country/region">
                {zones.map(z => <option key={z.key} value={z.key}>{z.display_name || z.key} ({z.key})</option>)}
              </select>
              <ChevronDown size={14} className="select-arrow" />
            </label>
          </div>

          <div className="metric-grid" style={{ marginBottom: '24px' }}>
            <Metric
              label="Workload Scope"
              metric={analysisMode === 'project' && projectResult ? `Full Project (${projectResult.total_files} files)` : (result?.filename || filename)}
              unit="TARGET WORKLOAD"
              tone="blue"
            />
            <Metric
              label="Workload Energy Requirement"
              metric={analysisMode === 'project' && projectResult ? fixed(projectAfterEnergy, 2) : fixed(energy.energy_joules, 3)}
              unit={analysisMode === 'project' && projectResult ? 'modeled J (relative) · sum across files (one run each)' : 'modeled J (relative) · not metered energy'}
              help="This is a relative model score, not metered energy. Any kWh-equivalent conversion is an intermediate estimate, not measured consumption."
              tone="green"
            />
            <Metric
              label="Current Grid Intensity"
              metric={fixed(analysisMode === 'project' && projectResult ? impactCurrentIntensity : (currentZone?.carbon_intensity ?? forecast?.current_carbon_intensity ?? carbonIntensityToDisplay), 2)}
              unit={`gCO₂eq/kWh · ${carbonSourceZone} · ${carbonSourceType}`}
              help={CARBON_METHOD_NOTE}
              tone="amber"
            />
            <Metric
              label="Current Workload Carbon Footprint"
              metric={analysisMode === 'project' && projectResult ? fixed((projectAfterEnergy / 3600000.0) * impactCurrentIntensity, 6) : fixed(((energy.energy_joules || 0) / 3600000.0) * (currentZone?.carbon_intensity ?? forecast?.current_carbon_intensity ?? carbonIntensityToDisplay), 6)}
              unit="modeled gCO₂eq/run · unweighted · not metered"
              help={CARBON_METHOD_NOTE}
              tone="ink"
            />
          </div>

          <ForecastView forecast={forecast} zoneName={currentZone?.display_name || zone} zoneKey={zone} loading={forecastLoading} error={forecastError} />
        </section>
      )}
      </TabErrorBoundary>
    </main>
  </div>;
}

function Metric({ label, metric, unit, tone, help, scopeLabel }: { label: string; metric: string; unit: string; tone: string; help?: string; scopeLabel?: string }) {
  return <article className={`metric ${tone}`}><p>{label}{help && <abbr className="metric-help" title={help} aria-label={help}>ⓘ</abbr>}{scopeLabel && <small className="scope-chip">{scopeLabel}</small>}</p><strong>{metric}</strong>{unit && <span>{unit}</span>}</article>;
}
function formatWindowTime(isoStr?: string): string {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    const datePart = d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });
    const startHour = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
    const endDate = new Date(d.getTime() + 60 * 60 * 1000);
    const endHour = endDate.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
    const utcStart = d.toISOString().slice(11, 16);
    const utcEnd = endDate.toISOString().slice(11, 16);
    return `${datePart} · ${startHour}–${endHour} ${LOCAL_TIME_ZONE_LABEL} (${utcStart}–${utcEnd} UTC)`;
  } catch {
    return isoStr;
  }
}

function formatHour(isoStr?: string): string {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleTimeString(undefined, { hour: 'numeric', hour12: true });
  } catch {
    return isoStr;
  }
}

function formatForecastClock(isoStr?: string, includeDate = false): string {
  if (!isoStr) return '—';
  const date = new Date(isoStr);
  if (!Number.isFinite(date.getTime())) return isoStr;
  const clock = date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true });
  return includeDate
    ? `${date.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })} ${clock} ${LOCAL_TIME_ZONE_LABEL}`
    : `${clock} ${LOCAL_TIME_ZONE_LABEL}`;
}

function formatForecastDay(isoStr: string): string {
  const parts = new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short' }).formatToParts(new Date(isoStr));
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.weekday} ${values.day} ${values.month}`;
}

function formatUtcClock(isoStr?: string): string {
  if (!isoStr) return '—';
  const date = new Date(isoStr);
  return Number.isFinite(date.getTime())
    ? `${date.toLocaleTimeString('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hour12: false })} UTC`
    : isoStr;
}

function ordinal(value: number): string {
  const mod100 = value % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${value}th`;
  return `${value}${value % 10 === 1 ? 'st' : value % 10 === 2 ? 'nd' : value % 10 === 3 ? 'rd' : 'th'}`;
}

function isInCurrentLocalHour(isoStr?: string): boolean {
  if (!isoStr) return false;
  const timestamp = Date.parse(isoStr);
  if (!Number.isFinite(timestamp)) return false;
  const now = new Date();
  now.setMinutes(0, 0, 0);
  return timestamp >= now.getTime() && timestamp < now.getTime() + 60 * 60 * 1000;
}

function ForecastView({ forecast, zoneName, zoneKey, loading, error }: { forecast: any; zoneName: string; zoneKey: string; loading?: boolean; error?: string | null }) {
  if (loading) {
    return (
      <div className="empty-panel" style={{ marginTop: '20px' }}>
        <LoaderCircle className="spin" size={24} style={{ color: 'var(--forest)' }} />
        <div>
          <h3>Fetching forecast data...</h3>
          <p>Retrieving regional 24-hour carbon intensity forecast for {zoneName} ({zoneKey}).</p>
        </div>
      </div>
    );
  }

  const hourly = Array.isArray(forecast?.hourly_forecasts) ? forecast.hourly_forecasts : [];

  if (!forecast || hourly.length === 0) {
    const isUnreachable = error?.toLowerCase().includes('unreachable');
    return (
      <div className="empty-panel" style={{ marginTop: '20px' }}>
        <AlertCircle size={24} style={{ color: '#c38c3d' }} />
        <div>
          <h3>{isUnreachable ? 'Backend Service Unreachable' : 'Forecast data unavailable'}</h3>
          <p>{error || `Forecast data is unavailable for ${zoneName} (${zoneKey}) from the configured carbon provider.`}</p>
        </div>
      </div>
    );
  }

  const hasCleanerWindow = forecast.has_cleaner_window ?? (forecast.percentage_reduction > 0);
  const intensityNow = forecast.intensity_now ?? forecast.current_carbon_intensity;
  const forecastMinimum = forecast.forecast_minimum_intensity ?? forecast.lowest_forecast_intensity;
  const intensityWindow = forecast.intensity_window ?? Math.min(intensityNow, forecastMinimum);
  const schedulingReduction = forecast.scheduling_reduction_percent ?? Math.max(0, forecast.percentage_reduction);
  const nowMs = Date.now();
  const currentPointIndex = hourly.reduce((bestIndex: number, item: any, index: number) => {
    const thisTime = Date.parse(item.timestamp);
    const bestTime = Date.parse(hourly[bestIndex]?.timestamp);
    return thisTime <= nowMs && thisTime > bestTime ? index : bestIndex;
  }, Math.max(0, hourly.findIndex((item: any) => Date.parse(item.timestamp) > nowMs) - 1));
  const currentHourStart = Date.parse(hourly[currentPointIndex]?.timestamp);
  const requestedRecIso = forecast.window_start || forecast.recommended_execution_time;
  const requestedRecMs = Date.parse(requestedRecIso);
  const requestedRecIndex = hourly.findIndex((item: any) => {
    const hourStart = Date.parse(item.timestamp);
    return requestedRecMs >= hourStart && requestedRecMs < hourStart + 60 * 60 * 1000;
  });
  const recTimeIndex = hasCleanerWindow && requestedRecIndex >= currentPointIndex ? requestedRecIndex : -1;
  const recTimeIso = recTimeIndex >= 0 ? hourly[recTimeIndex].timestamp : null;
  const recTimeStr = hasCleanerWindow && recTimeIso
    ? `${recTimeIndex === currentPointIndex ? 'Starts now · ' : 'Starts later · '}${formatWindowTime(recTimeIso)}`
    : hasCleanerWindow ? 'Recommended window is outside the remaining forecast hours' : 'No cleaner forecast window · use current schedule';
  const hasCurrentForecastPoint = Number.isFinite(currentHourStart) && currentHourStart <= nowMs && nowMs < currentHourStart + 60 * 60 * 1000;

  const chartData = hourly.map((item: any, index: number) => {
    const timestamp = Date.parse(item.timestamp);
    const previous = index > 0 ? new Date(Date.parse(hourly[index - 1].timestamp)) : null;
    const currentDate = new Date(timestamp);
    const isDayBoundary = Boolean(previous && previous.toLocaleDateString() !== currentDate.toLocaleDateString());
    return {
      time: isDayBoundary
        ? formatForecastDay(item.timestamp)
        : formatHour(item.timestamp),
      tickKey: item.timestamp,
      tickHour: currentDate.getHours(),
      isDayBoundary,
      intensity: Number(item.carbon_intensity),
      emissions: item.emissions_g,
      isOptimal: hasCleanerWindow && index === recTimeIndex && Number(item.carbon_intensity) < Number(intensityNow),
      isCurrent: hasCurrentForecastPoint && index === currentPointIndex,
      rawTs: item.timestamp
    };
  });
  const currentPoint = chartData.find((item: any) => item.isCurrent);
  const remainingForecast = chartData.slice(Math.max(0, currentPointIndex));
  const minPoint = remainingForecast.reduce((best: any, point: any) => !best || point.intensity < best.intensity ? point : best, null);
  const maxPoint = remainingForecast.reduce((worst: any, point: any) => !worst || point.intensity > worst.intensity ? point : worst, null);
  const recommendedPoint = recTimeIndex >= 0 ? chartData[recTimeIndex] : null;
  const liveNumber = Number(intensityNow);
  const currentForecastNumber = Number(currentPoint?.intensity);
  const percentVsLive = (value: number) => liveNumber > 0 ? (value - liveNumber) / liveNumber * 100 : 0;
  const headline = recommendedPoint?.isOptimal
    ? `Best time: ${formatForecastClock(recommendedPoint.rawTs, true)}, ${Math.abs(percentVsLive(recommendedPoint.intensity)).toFixed(1)}% less carbon than now.`
    : `Best time to run: now (${formatForecastClock(currentPoint?.rawTs)}). The grid gets up to ${Math.max(0, percentVsLive(Number(maxPoint?.intensity || liveNumber))).toFixed(1)}% dirtier by ${formatForecastClock(maxPoint?.rawTs)}.`;
  const values = chartData.map((point: any) => point.intensity);
  const rangeMin = Math.min(...values);
  const rangeMax = Math.max(...values);
  const rangeThird = (rangeMax - rangeMin) / 3 || 1;
  const barColor = (value: number) => value <= rangeMin + rangeThird ? '#238653' : value <= rangeMin + rangeThird * 2 ? '#c58a16' : '#c5483c';
  const yMax = Math.max(800, Math.ceil(Math.max(rangeMax, liveNumber) / 200) * 200);
  const yTicks = Array.from({ length: Math.floor(yMax / 200) + 1 }, (_value, index) => index * 200);
  const xTicks = chartData.filter((point: any) => point.isDayBoundary || point.tickHour % 3 === 0).map((point: any) => point.tickKey);
  const currentDay = new Date().toLocaleDateString();
  const todayValues = chartData.filter((point: any) => new Date(point.rawTs).toLocaleDateString() === currentDay).map((point: any) => point.intensity);
  const todayMin = Math.min(...(todayValues.length ? todayValues : values));
  const todayMax = Math.max(...(todayValues.length ? todayValues : values));
  const rankOf = (value: number) => 1 + chartData.filter((point: any) => point.intensity < value).length;
  const rankedTime = (point: any) => `${formatForecastClock(point?.rawTs)} · ${fixed(point?.intensity, 0)} gCO₂eq/kWh`;
  const currentDifferenceNote = Number.isFinite(currentForecastNumber) && currentForecastNumber !== liveNumber
    ? `Live reading ${fixed(liveNumber, 0)}; forecast for the current hour ${fixed(currentForecastNumber, 0)} (different source/time resolution).`
    : `Live reading ${fixed(liveNumber, 0)}; forecast for the current hour ${fixed(currentForecastNumber, 0)}. These are separate live and hourly forecast readings.`;

  return (
    <div style={{ display: 'grid', gap: '20px', marginTop: '20px' }}>
      <section className="panel" style={{ background: 'var(--card)', border: '1px solid var(--line)', padding: '20px', borderRadius: '10px' }}>
        <div className="panel-head">
          <div>
            <p className="overline" style={{ color: '#2e6956', fontWeight: 600 }}>RECOMMENDED GREEN WINDOW</p>
            <h2 style={{ fontSize: '24px', margin: '4px 0 0', color: 'var(--ink)' }}>{recTimeStr}</h2>
          </div>
          <span className={`status-badge ${hasCleanerWindow ? 'success' : ''}`} style={{ padding: '6px 12px', fontSize: '13px' }}>
            {hasCleanerWindow ? <><Leaf size={14} style={{ display: 'inline', marginRight: '4px' }} /> Optimal Execution Window</> : 'No scheduling reduction'}
          </span>
          {forecast.source_type !== 'live' && <span className="mock-data-badge">MOCK DATA</span>}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginTop: '16px' }}>
          <div style={{ background: 'var(--bg)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
            <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0 }} title={CARBON_METHOD_NOTE}>Best forecast hour intensity ⓘ</p>
            <strong title={CARBON_METHOD_NOTE} style={{ fontSize: '20px', color: 'var(--forest)', display: 'block', margin: '4px 0 0' }}>
              {fixed(forecastMinimum, 1)} <small style={{ fontSize: '11px', color: 'var(--muted)' }}>gCO₂eq/kWh</small>
            </strong>
          </div>

          <div style={{ background: 'var(--bg)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
            <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0 }} title={CARBON_METHOD_NOTE}>Current Grid Intensity ⓘ</p>
            <strong title={CARBON_METHOD_NOTE} style={{ fontSize: '20px', color: 'var(--ink)', display: 'block', margin: '4px 0 0' }}>
              {fixed(intensityNow, 1)} <small style={{ fontSize: '11px', color: 'var(--muted)' }}>gCO₂eq/kWh</small>
            </strong>
          </div>

          <div style={{ background: 'var(--bg)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
            <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0 }}>Potential Intensity Reduction</p>
            <strong style={{ fontSize: '20px', color: forecast.percentage_reduction > 0 ? 'var(--forest)' : 'var(--ink)', display: 'block', margin: '4px 0 0' }}>
              {fixed(schedulingReduction, 1)}%
            </strong>
          </div>
        </div>

        <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '14px 0 0' }}>
          <span title={CARBON_METHOD_NOTE}>{hasCleanerWindow ? `Best forecast window: ${formatWindowTime(forecast.window_start || forecast.recommended_execution_time || undefined)} · ${fixed(intensityWindow, 1)} gCO₂eq/kWh. ` : `No forecast window is cleaner than the current grid; modeled carbon reduction is 0% and the current intensity is retained. The best forecast hour is ${formatWindowTime(forecast.recommended_execution_time || undefined)} at ${fixed(forecastMinimum, 1)} gCO₂eq/kWh. `}Source: {forecast.source} · {forecast.source_type} · {zoneName} ({zoneKey}).</span>
        </p>
      </section>

      <section className="panel hourly-forecast-panel" style={{ background: 'var(--card)', border: '1px solid var(--line)', padding: '20px', borderRadius: '10px' }}>
        <div className="panel-head">
          <div>
            <p className="overline">24-HOUR CARBON INTENSITY FORECAST</p>
            <h3>Hourly Grid Carbon Intensity</h3>
            <p className="forecast-headline">{headline}</p>
            <p className="forecast-chart-help">Modeled estimate · Source: {forecast.source} {forecast.source_type} and hourly forecast · {zoneName} ({zoneKey}).</p>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--muted)', fontFamily: 'DM Mono, monospace' }}>
            {hourly.length} forecast points
          </span>
        </div>

        <div className="forecast-key-points" aria-label="Key forecast values">
          <div className="forecast-key-now"><strong>NOW</strong><span>{fixed(liveNumber, 0)} live · forecast {fixed(currentForecastNumber, 0)}</span></div>
          <div className="forecast-key-clean"><strong>CLEANEST</strong><span>{rankedTime(minPoint)}</span></div>
          <div className="forecast-key-dirty"><strong>DIRTIEST</strong><span>{rankedTime(maxPoint)}</span></div>
        </div>
        <div className="forecast-chart-shell">
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={chartData} margin={{ top: 54, right: 112, left: 22, bottom: 32 }} barCategoryGap="22%">
              <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="0" />
              <XAxis dataKey="tickKey" ticks={xTicks} tickFormatter={(value: string) => chartData.find((point: any) => point.tickKey === value)?.time || ''} interval={0} height={42} tick={{ fill: 'var(--muted)', fontSize: 11 }} tickLine={false} axisLine={{ stroke: 'var(--line)' }} label={{ value: `Time (${LOCAL_TIME_ZONE_LABEL})`, position: 'insideBottom', offset: -4, fill: 'var(--muted)', fontSize: 10 }} />
              <YAxis ticks={yTicks} domain={[0, yMax]} width={74} tick={{ fill: 'var(--muted)', fontSize: 11 }} tickLine={false} axisLine={false} label={{ value: 'gCO₂eq/kWh (lower is cleaner)', angle: -90, position: 'insideLeft', fill: 'var(--muted)', fontSize: 10 }} />
              <Tooltip
                cursor={{ fill: 'var(--chart-hover)' }}
                content={({ active, payload }: any) => {
                  const point = payload?.[0]?.payload;
                  if (!active || !point) return null;
                  const delta = percentVsLive(point.intensity);
                  const rank = rankOf(point.intensity);
                  return <div className="forecast-tooltip"><strong>{formatForecastClock(point.rawTs, true)} · {formatUtcClock(point.rawTs)}</strong><span>Forecast intensity: {fixed(point.intensity, 0)} gCO₂eq/kWh</span><span>{delta >= 0 ? '+' : ''}{delta.toFixed(1)}% vs. live now ({fixed(liveNumber, 0)})</span><span>{ordinal(rank)} cleanest of {chartData.length}</span>{point.isCurrent && <span>Forecast for the current hour; live now is {fixed(liveNumber, 0)}.</span>}{point.isOptimal && <span>BEST · recommended hour</span>}<small>Source: {forecast.source} live reading and hourly forecast.</small></div>;
                }}
              />
              <ReferenceLine y={liveNumber} stroke="var(--live-marker)" strokeWidth={1.5} label={{ value: `Live now: ${fixed(liveNumber, 0)}`, position: 'right', fill: 'var(--live-marker)', fontSize: 11, fontWeight: 700 }} />
              <Bar dataKey="intensity" name="Grid carbon intensity" radius={[4, 4, 0, 0]}>
                {chartData.map((entry: any, index: number) => <Cell key={`hour-${index}`} fill={barColor(entry.intensity)} stroke={entry.isCurrent ? 'var(--now-outline)' : entry.isOptimal ? 'var(--best-outline)' : barColor(entry.intensity)} strokeWidth={entry.isCurrent || entry.isOptimal ? 3 : 1} />)}
                <LabelList dataKey="intensity" content={(props: any) => {
                  const point = chartData[props.index];
                  if (!point?.isCurrent && !point?.isOptimal) return null;
                  const label = point.isCurrent && point.isOptimal ? 'NOW · BEST' : point.isCurrent ? 'NOW' : 'BEST';
                  const width = label.length > 5 ? 70 : 46;
                  const x = (props.x || 0) + (props.width || 0) / 2 - width / 2;
                  const y = Math.max(3, (props.y || 0) - 24);
                  const fill = point.isOptimal ? 'var(--best-tag)' : 'var(--now-tag)';
                  return <g><rect x={x} y={y} width={width} height={18} rx={8} fill={fill} /><text x={x + width / 2} y={y + 12} textAnchor="middle" fill="#fff" fontSize={9} fontWeight={800}>{label}</text></g>;
                }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="forecast-scale-legend"><span className="scale-label">Cleaner</span><span className="scale-gradient" aria-hidden="true" /><span className="scale-label">Dirtier</span><span className="scale-marker"><i />NOW outlined</span>{recommendedPoint?.isOptimal && <span className="scale-marker best"><i />BEST outlined</span>}</div>
        <p className="forecast-live-note">{currentDifferenceNote}</p>
        <div className="forecast-summary-chips"><div><span>Best window</span><strong>{recommendedPoint?.isOptimal ? rankedTime(recommendedPoint) : `Now · live ${fixed(liveNumber, 0)} gCO₂eq/kWh`}</strong></div><div><span>Worst window</span><strong>{rankedTime(maxPoint)}</strong></div><div><span>Today's range</span><strong>{fixed(todayMin, 0)}–{fixed(todayMax, 0)} gCO₂eq/kWh</strong></div></div>
      </section>
    </div>
  );
}
