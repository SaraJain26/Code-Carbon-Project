import { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, AlertCircle, ArrowLeft, ArrowRight, Check, ChevronDown, ChevronRight, ChevronUp, Clock3, Code2, Download, FileCode2, FileText, Flame, Folder, FolderArchive, Gauge, Globe2, Leaf, LoaderCircle, Moon, Play, Search, Sparkles, Sun, Upload, X } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const CATEGORY_COLORS: Record<string, string> = {
  'Computation': '#2e6956',
  'File & I/O': '#3b82f6',
  'Memory': '#8b5cf6',
  'Network': '#06b6d4',
  'Control Flow': '#f59e0b',
  'Other': '#64748b'
};

const SEVERITY_COLORS: Record<string, string> = {
  'High Severity': '#ef4444',
  'High': '#ef4444',
  'Medium Severity': '#f59e0b',
  'Medium': '#f59e0b',
  'Low Severity': '#10b981',
  'Low': '#10b981'
};

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
import * as pdfjsLib from 'pdfjs-dist';
import mammoth from 'mammoth';
import JSZip from 'jszip';
import './App.css';

const API = import.meta.env.DEV
  ? (import.meta.env.VITE_API_URL || '/api')
  : 'https://code-carbon-project.onrender.com/api';

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
      const detail = (parsed as any)?.detail;
      throw new Error(detail
        ? `API request failed: HTTP ${response.status}: ${detail}`
        : `API request failed: HTTP ${response.status}`);
    }
    if (bodyEmpty) throw new Error(`API request failed: HTTP ${response.status} (empty response)`);
    if (isHtml) throw new Error(`API request failed: HTTP ${response.status} (received HTML instead of JSON)`);
    throw new Error(`API request failed: HTTP ${response.status} (invalid JSON response)`);
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
const fixed = (x: unknown, places = 2) => typeof x === 'number' && Number.isFinite(x) ? x.toFixed(places) : '—';

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

interface ResearchMetrics {
  energy_smell_score: number;
  carbon_impact_risk_score: number;
  ess_version: string;
  cirs_version: string;
}

interface ComplexityMetricsDetail {
  cc: number;
  nd: number;
  fd: number;
  sci: number;
  sloc?: number;
}

interface CarbonMetadataDetail {
  zone: string;
  carbon_intensity: number;
  is_mock: boolean;
  timestamp: string;
  source: string;
}

interface FindingComparisonItem {
  rule_id: string;
  rule_name: string;
  category: string;
  line_number?: number | null;
  confidence_before: number;
  confidence_after: number;
  is_resolved: boolean;
}

interface PostRefactorEstimation {
  cirs_before?: number;
  cirs_after?: number;
  ess_before?: number;
  ess_after?: number;
  sci_before?: number;
  sci_after?: number;
  complexity_before?: ComplexityMetricsDetail;
  complexity_after?: ComplexityMetricsDetail;
  energy_before_joules?: number;
  energy_after_joules?: number;
  energy_before_kwh?: number;
  energy_after_kwh?: number;
  hazard_before?: number;
  hazard_after?: number;
  exposure_before?: number;
  exposure_after?: number;
  predicted_reduction_percent?: number;
  measured_reduction_percent?: number;
  findings_comparison?: FindingComparisonItem[];
  structural_changes_summary?: string[];
  carbon_metadata?: CarbonMetadataDetail;
  measurement_reliability?: string;
}

interface AnalyzeResponse {
  filename?: string;
  timestamp?: string;
  pipeline_raw?: {
    energy_smell_report?: {
      summary?: { total_findings?: number; high_severity_count?: number; medium_severity_count?: number; low_severity_count?: number };
      findings?: any[];
    };
    energy_result?: { energy?: { energy_joules?: number; energy_kwh?: number } };
    carbon_result?: { carbon_data?: { carbon_intensity?: number; zone?: { display_name?: string; zone_key?: string } } };
    complexity_metrics?: { cyclomatic_complexity?: number; max_nesting_depth?: number; function_density?: number; sloc?: number };
    complexity_score?: { structural_complexity_index?: number; heuristic_risk_score?: number };
    analysis?: { total_lines_of_code?: number; functions?: any[] };
  };
  research_metrics?: ResearchMetrics;
  recommendations?: any;
  optimized_code?: string;
  post_refactor_estimation?: PostRefactorEstimation;
  findings?: any[];
}

interface ProjectFileResult {
  filename: string;
  relative_path: string;
  lines_of_code: number;
  status: 'success' | 'error';
  error_message?: string | null;
  findings_count: number;
  sci: number;
  ess: number;
  cirs: number;
  energy_joules: number;
  analysis_time_sec: number;
  single_file_response?: AnalyzeResponse;
  original_code?: string;
}

interface ProjectAnalyzeResponse {
  project_name: string;
  timestamp: string;
  total_files: number;
  successful_files: number;
  error_files: number;
  total_lines_of_code: number;
  total_findings: number;
  avg_sci: number;
  avg_ess: number;
  avg_cirs: number;
  total_cirs: number;
  total_energy_joules: number;
  total_energy_kwh: number;
  total_analysis_time_sec: number;
  files: ProjectFileResult[];
}

export default function App() {
  const [view, setView] = useState<View>('workspace');
  const [analysisMode, setAnalysisMode] = useState<'file' | 'project'>('file');
  const [health, setHealth] = useState('checking');
  const [zones, setZones] = useState<any[]>([]);
  const [zone, setZone] = useState('IN');
  const [query, setQuery] = useState('');
  const [code, setCode] = useState('');
  const [filename, setFilename] = useState('untitled.py');
  const [globalAverage, setGlobalAverage] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [projectResult, setProjectResult] = useState<ProjectAnalyzeResponse | null>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('codecarbon-theme') === 'dark');

  const [projectZipFile, setProjectZipFile] = useState<File | null>(null);
  const [projectFiles, setProjectFiles] = useState<ScannedFile[]>([]);
  const [projectSummary, setProjectSummary] = useState<ProjectSummary | null>(null);

  const [tableSearch, setTableSearch] = useState('');
  const [sortColumn, setSortColumn] = useState<'filename' | 'lines_of_code' | 'findings_count' | 'sci' | 'ess' | 'cirs' | 'energy_joules'>('findings_count');
  const [sortAsc, setSortAsc] = useState(false);
  const [expandedRecRule, setExpandedRecRule] = useState<string | null>(null);

  const fileInput = useRef<HTMLInputElement>(null);
  const projectFolderInput = useRef<HTMLInputElement>(null);
  const projectZipInput = useRef<HTMLInputElement>(null);

  useEffect(() => { (async () => {
    try {
      const healthUrl = `${API}/health`;
      const zonesUrl = `${API}/zones`;
      const [healthResponse, zonesResponse] = await Promise.all([fetch(healthUrl), fetch(zonesUrl)]);
      await readApiJson<{ status: string }>(healthResponse, healthUrl);
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
    if (view === 'schedule') {
      const fileJoules = result?.pipeline_raw?.energy_result?.energy?.energy_joules;
      const targetJoules = (analysisMode === 'project' && projectResult)
        ? (projectResult.total_energy_joules || 100.0)
        : (fileJoules || 100.0);
      const forecastUrl = `${API}/forecast?zone=${encodeURIComponent(zone)}&energy_joules=${targetJoules}`;
      setForecastLoading(true);
      setForecastError(null);
      fetch(forecastUrl)
        .then(async response => {
          setForecast(await readApiJson(response, forecastUrl));
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
  const postRefactor = result?.post_refactor_estimation || {};

  // Individual Findings count from backend summary / findings for single file
  const totalFindingsCount =
    raw.energy_smell_report?.summary?.total_findings ??
    (Array.isArray(raw.energy_smell_report?.findings) ? raw.energy_smell_report.findings.length : undefined) ??
    (Array.isArray(result?.findings) ? result.findings.length : recommendations.length);

  // Carbon intensity: Primary value from backend response, fallback to frontend selectedZone ONLY if missing
  const backendCarbonIntensity = (analysisMode === 'project' && projectResult?.files?.[0]?.single_file_response?.post_refactor_estimation?.carbon_metadata?.carbon_intensity)
    ?? postRefactor.carbon_metadata?.carbon_intensity
    ?? carbon.carbon_intensity;

  const carbonIntensityToDisplay = (backendCarbonIntensity !== undefined && backendCarbonIntensity !== null)
    ? backendCarbonIntensity
    : currentZone?.carbon_intensity;

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
      affected_files: { filename: string; relative_path: string; line_number?: number; confidence: number }[];
    }>();

    for (const fileItem of projectResult.files) {
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
            suggested_fix: rec.suggested_fix || '',
            explanation: rec.explanation || rec.description || rec.message || '',
            occurrences: 0,
            affected_files: []
          });
        }
        const entry = map.get(key)!;
        entry.occurrences += 1;
        entry.affected_files.push({
          filename: fileItem.filename,
          relative_path: fileItem.relative_path,
          line_number: rec.line_number,
          confidence: rec.confidence ?? 1.0
        });
      }
    }

    return Array.from(map.values()).sort((a, b) => b.priority_score - a.priority_score);
  }, [projectResult]);

  // Project-wide findings category distribution
  const projectCategoryDistribution = useMemo(() => {
    if (!projectResult?.files) return [];
    const categories: Record<string, number> = {
      'Computation': 0,
      'File & I/O': 0,
      'Memory': 0,
      'Network': 0,
      'Control Flow': 0
    };

    for (const fileItem of projectResult.files) {
      const fileResp = fileItem.single_file_response;
      if (!fileResp) continue;
      const findings = fileResp.pipeline_raw?.energy_smell_report?.findings || [];
      for (const f of findings) {
        const cat = String(f.category || f.rule_id || '').toLowerCase();
        if (cat.includes('io') || cat.includes('file')) categories['File & I/O'] += 1;
        else if (cat.includes('network') || cat.includes('http') || cat.includes('api')) categories['Network'] += 1;
        else if (cat.includes('memory') || cat.includes('allocation')) categories['Memory'] += 1;
        else if (cat.includes('nest') || cat.includes('loop') || cat.includes('compute') || cat.includes('math')) categories['Computation'] += 1;
        else categories['Control Flow'] += 1;
      }
    }

    return Object.entries(categories).map(([name, count]) => ({ name, count }));
  }, [projectResult]);

  // Top ranked file highlights
  const topEnergyFiles = useMemo(() => {
    if (!projectResult?.files) return [];
    return [...projectResult.files].sort((a, b) => b.energy_joules - a.energy_joules).slice(0, 3);
  }, [projectResult]);

  const topFindingsFiles = useMemo(() => {
    if (!projectResult?.files) return [];
    return [...projectResult.files].sort((a, b) => b.findings_count - a.findings_count).slice(0, 3);
  }, [projectResult]);

  const topCarbonFiles = useMemo(() => {
    if (!projectResult?.files) return [];
    return [...projectResult.files]
      .map(f => ({
        ...f,
        carbonGrams: ((f.energy_joules || 0) / 3600000.0) * (carbonIntensityToDisplay || 435)
      }))
      .sort((a, b) => b.carbonGrams - a.carbonGrams)
      .slice(0, 3);
  }, [projectResult, carbonIntensityToDisplay]);

  // Project chart datasets
  const projectFilesEnergyData = useMemo(() => {
    if (!projectResult?.files) return [];
    return projectResult.files.map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      energyJoules: Number(f.energy_joules || 0),
      energyKwh: Number((f.energy_joules || 0) / 3600000.0)
    }));
  }, [projectResult]);

  const projectFilesCarbonData = useMemo(() => {
    if (!projectResult?.files) return [];
    return projectResult.files.map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      carbonGrams: Number(((f.energy_joules || 0) / 3600000.0) * (carbonIntensityToDisplay || 435)),
      cirs: Number(f.cirs || 0)
    }));
  }, [projectResult, carbonIntensityToDisplay]);

  const projectFilesSciData = useMemo(() => {
    if (!projectResult?.files) return [];
    return projectResult.files.map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      sci: Number(f.sci || 0)
    }));
  }, [projectResult]);

  const projectFilesEssData = useMemo(() => {
    if (!projectResult?.files) return [];
    return projectResult.files.map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      ess: Number(f.ess || 0)
    }));
  }, [projectResult]);

  const projectFilesCirsData = useMemo(() => {
    if (!projectResult?.files) return [];
    return projectResult.files.map(f => ({
      name: f.filename,
      relativePath: f.relative_path,
      cirs: Number(f.cirs || 0)
    }));
  }, [projectResult]);

  const projectCategoryDistributionData = useMemo(() => {
    return projectCategoryDistribution.filter(c => c.count > 0);
  }, [projectCategoryDistribution]);

  const projectSeverityDistribution = useMemo(() => {
    if (!projectResult?.files) return [];
    let high = 0, medium = 0, low = 0;
    for (const f of projectResult.files) {
      const fileResp = f.single_file_response;
      if (!fileResp) continue;
      const summary = fileResp.pipeline_raw?.energy_smell_report?.summary;
      if (summary) {
        high += summary.high_severity_count || 0;
        medium += summary.medium_severity_count || 0;
        low += summary.low_severity_count || 0;
      } else {
        const findings = fileResp.pipeline_raw?.energy_smell_report?.findings || fileResp.findings || [];
        for (const finding of findings) {
          const sev = String(finding.severity || '').toLowerCase();
          if (sev === 'high' || sev === 'critical') high++;
          else if (sev === 'low' || sev === 'info') low++;
          else medium++;
        }
      }
    }
    const list = [
      { name: 'High Severity', count: high, color: '#ef4444' },
      { name: 'Medium Severity', count: medium, color: '#f59e0b' },
      { name: 'Low Severity', count: low, color: '#10b981' }
    ];
    return list.filter(item => item.count > 0);
  }, [projectResult]);

  const singleFileComplexityData = useMemo(() => {
    if (!result) return [];
    return [
      { name: 'CC', full: 'Cyclomatic Complexity', value: complexity.cc, rawValue: fixed(complexity.cc, 1), unit: 'decision paths' },
      { name: 'ND', full: 'Nesting Depth', value: complexity.nd, rawValue: fixed(complexity.nd, 0), unit: 'max depth' },
      { name: 'FD (x100)', full: 'Function Density', value: Number((complexity.fd * 100).toFixed(2)), rawValue: fixed(complexity.fd, 4), unit: 'funcs/LOC' },
      { name: 'SCI (x100)', full: 'Structural Index', value: Number((complexity.sci * 100).toFixed(2)), rawValue: fixed(complexity.sci, 4), unit: 'index (0-1)' }
    ];
  }, [result, complexity]);

  const singleFileRefactorComparisonData = useMemo(() => {
    if (!postRefactor || postRefactor.sci_before === undefined) return [];
    return [
      { name: 'SCI (x100)', Before: Number(((postRefactor.sci_before || 0) * 100).toFixed(2)), After: Number(((postRefactor.sci_after || 0) * 100).toFixed(2)) },
      { name: 'ESS (0-10)', Before: Number((postRefactor.ess_before || 0).toFixed(1)), After: Number((postRefactor.ess_after || 0).toFixed(1)) },
      { name: 'Energy (J)', Before: Number((postRefactor.energy_before_joules || 0).toFixed(2)), After: Number((postRefactor.energy_after_joules || 0).toFixed(2)) },
      { name: 'CIRS (x1e4)', Before: Number(((postRefactor.cirs_before || 0) * 10000).toFixed(2)), After: Number(((postRefactor.cirs_after || 0) * 10000).toFixed(2)) }
    ];
  }, [postRefactor]);

  // Sorted and searched project file breakdown table
  const sortedProjectFiles = useMemo(() => {
    if (!projectResult?.files) return [];
    return [...projectResult.files]
      .filter(f => f.filename.toLowerCase().includes(tableSearch.toLowerCase()) || f.relative_path.toLowerCase().includes(tableSearch.toLowerCase()))
      .sort((a, b) => {
        const valA = a[sortColumn];
        const valB = b[sortColumn];
        if (typeof valA === 'string') {
          return sortAsc ? (valA as string).localeCompare(valB as string) : (valB as string).localeCompare(valA as string);
        }
        return sortAsc ? (valA as number) - (valB as number) : (valB as number) - (valA as number);
      });
  }, [projectResult, tableSearch, sortColumn, sortAsc]);

  // Project complexity summary metrics
  const projectComplexitySummary = useMemo(() => {
    if (!projectResult?.files) return { totalFunctions: 0, maxND: 1, avgFD: 0 };
    let totalFuncs = 0;
    let maxND = 1;
    let sumFD = 0;
    let validFDCount = 0;

    for (const f of projectResult.files) {
      const metrics = f.single_file_response?.pipeline_raw?.complexity_metrics;
      if (metrics) {
        if (metrics.max_nesting_depth) maxND = Math.max(maxND, metrics.max_nesting_depth);
        if (metrics.function_density) { sumFD += metrics.function_density; validFDCount++; }
      }
      const analysis = f.single_file_response?.pipeline_raw?.analysis;
      if (analysis && Array.isArray(analysis.functions)) {
        totalFuncs += analysis.functions.length;
      }
    }

    return {
      totalFunctions: totalFuncs,
      maxND,
      avgFD: validFDCount > 0 ? sumFD / validFDCount : 0
    };
  }, [projectResult]);

  const readFile = async (file: File) => {
    setNotice(null); setExtracting(true);
    try {
      let text: string;
      if (/\.pdf$/i.test(file.name)) { pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'; const pdf = await pdfjsLib.getDocument({ data: await file.arrayBuffer() }).promise; const pages = await Promise.all(Array.from({ length: pdf.numPages }, async (_, i) => ((await (await pdf.getPage(i + 1)).getTextContent()).items as any[]).map(v => v.str || '').join(' '))); text = pages.join('\n'); }
      else if (/\.docx$/i.test(file.name)) text = (await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() })).value;
      else text = await file.text();
      if (!text.trim()) throw new Error('No readable code was found in this file.');
      setCode(text); setFilename(file.name.replace(/\.(pdf|docx|txt)$/i, '.py'));
    } catch (err: any) { setNotice(err.message || 'Unable to read that file.'); } finally { setExtracting(false); }
  };

  const analyze = async () => {
    if (!code.trim()) return setNotice('Paste code, choose an example, or upload a file before running an analysis.');
    setLoading(true); setNotice(null);
    try {
      const form = new FormData();
      form.append('file', new File([code], filename.endsWith('.py') ? filename : `${filename}.py`, { type: 'text/x-python' }));
      form.append('zone', zone);
      form.append('use_global_average', String(globalAverage));
      const requestUrl = `${API}/analyze`;
      const response = await fetch(requestUrl, { method: 'POST', body: form });
      setResult(await readApiJson<AnalyzeResponse>(response, requestUrl));
      setAnalysisMode('file');
      setView('results');
    } catch (err: any) { setNotice(err.message || 'Analysis could not be completed.'); } finally { setLoading(false); }
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
      return setNotice('Select a folder of .py files or a .zip archive before running project analysis.');
    }
    setLoading(true); setNotice(null);
    try {
      const form = new FormData();
      let fileToUpload: File;

      if (zipToUpload) {
        fileToUpload = zipToUpload;
        console.log(`[Code-Carbon] Uploading ZIP archive: ${fileToUpload.name} (${Math.round(fileToUpload.size / 1024)} KB)`);
      } else {
        console.log(`[Code-Carbon] Zipping ${filesToUpload.length} project file(s) client-side...`);
        const zip = new JSZip();
        for (const item of filesToUpload) {
          const content = await item.file.arrayBuffer();
          zip.file(item.path, content);
        }
        const zipBlob = await zip.generateAsync({ type: 'blob' });
        const rootName = summaryToUse?.name || 'project';
        fileToUpload = new File([zipBlob], `${rootName}.zip`, { type: 'application/zip' });
        console.log(`[Code-Carbon] Client ZIP created: ${fileToUpload.name} (${Math.round(zipBlob.size / 1024)} KB)`);
      }

      form.append('file', fileToUpload);
      form.append('zone', zone);
      form.append('use_global_average', String(globalAverage));
      const requestUrl = `${API}/analyze-project`;
      console.log(`[Code-Carbon] Sending POST ${requestUrl} payload...`);
      const response = await fetch(requestUrl, { method: 'POST', body: form });
      const projData = await readApiJson<ProjectAnalyzeResponse>(response, requestUrl);
      console.log(`[Code-Carbon] Project analysis complete:`, projData);
      setProjectResult(projData);
      setAnalysisMode('project');
      setView('project');
    } catch (err: any) {
      console.error('[Code-Carbon] Project analysis failed:', err);
      setNotice(err.message || 'Project analysis could not be completed.');
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
            <Sparkles size={14} /> Recommendations ({analysisMode === 'project' && projectResult ? projectAggregatedRecommendations.length : recommendations.length})
          </button>
          <button className={`subnav-tab ${view === 'impact' ? 'is-active' : ''}`} onClick={() => navigateView('impact')}>
            <Activity size={14} /> Refactor & Impact
          </button>
          <button className={`subnav-tab ${view === 'schedule' ? 'is-active' : ''}`} onClick={() => navigateView('schedule')}>
            <Clock3 size={14} /> Green Scheduling
          </button>
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
              <div className={`drop-zone ${dragging ? 'is-dragging' : ''}`} onDragEnter={e => { e.preventDefault(); setDragging(true); }} onDragOver={e => e.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files[0]) readFile(e.dataTransfer.files[0]); }} onClick={() => fileInput.current?.click()} role="button" tabIndex={0} onKeyDown={e => e.key === 'Enter' && fileInput.current?.click()}>
                <input ref={fileInput} type="file" accept=".py,.txt,.pdf,.docx" onChange={e => e.target.files?.[0] && readFile(e.target.files[0])} />
                <span className="upload-icon"><Upload size={21} /></span>
                <strong>{extracting ? 'Reading your file…' : 'Drop a file here'}</strong>
                <p>or browse for Python, TXT, PDF, or DOCX</p>
              </div>
              <div className="editor-wrap">
                <div className="editor-toolbar">
                  <span><span className="editor-dot" />{filename}</span>
                  <div>{samples.map(s => <button key={s.file} onClick={() => { setCode(s.code); setFilename(s.file); }}>{s.label}</button>)}</div>
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

          <div className="analysis-footer">
            <div>
              <label className="switch"><input type="checkbox" checked={globalAverage} onChange={e => setGlobalAverage(e.target.checked)} /><span /><b>Use global average</b></label>
              <p>Use this when your execution region is unknown.</p>
            </div>
            {analysisMode === 'file' ? (
              <button className="primary-button" disabled={loading || extracting || !code.trim()} onClick={analyze}>
                {loading ? <LoaderCircle className="spin" size={18} /> : <Play size={17} fill="currentColor" />}
                {loading ? 'Measuring code…' : 'Run file analysis'}
                <ArrowRight size={17} />
              </button>
            ) : (
              <button className="primary-button" disabled={loading || (!projectZipFile && projectFiles.length === 0)} onClick={() => runProjectAnalysis()}>
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
      {projectResult && view === 'project' && <section className="report">
        <div className="report-hero">
          <div>
            <p className="overline">FULL PROJECT SUSTAINABILITY ANALYSIS</p>
            <h2>{projectResult.project_name}</h2>
            <p>{projectResult.total_files} Python files ({projectResult.successful_files} analyzed, {projectResult.error_files} errors) · {projectResult.total_lines_of_code} Total SLOC · Analyzed in {projectResult.total_analysis_time_sec}s</p>
          </div>
          <button className="secondary-button" onClick={() => setView('workspace')}>New project analysis <ChevronRight size={17} /></button>
        </div>

        <div className="metric-grid">
          <Metric label="Total Files" metric={String(projectResult.total_files)} unit="COUNT" tone="blue" />
          <Metric label="Total Project SLOC" metric={String(projectResult.total_lines_of_code)} unit="SUM (lines of code)" tone="blue" />
          <Metric label="Total Individual Findings" metric={String(projectResult.total_findings)} unit="SUM (energy smells)" tone="blue" />
          <Metric label="Macro-Avg SCI" metric={fixed(projectResult.avg_sci, 4)} unit="MACRO-AVG (index 0-1)" tone="green" />
          <Metric label="Macro-Avg ESS" metric={fixed(projectResult.avg_ess, 1)} unit="MACRO-AVG (out of 10)" tone="amber" />
          <Metric label="Total Project Energy" metric={fixed(projectResult.total_energy_joules, 2)} unit={`SUM (${fixed(projectResult.total_energy_kwh, 6)} kWh)`} tone="green" />
          <Metric label="Primary Research CIRS" metric={fixed(projectResult.avg_cirs, 6)} unit="MACRO-AVG (gCO₂eq/run)" tone="ink" />
          <Metric label="Total CIRS Capacity" metric={fixed(projectResult.total_cirs, 6)} unit="SUM (gCO₂eq/run)" tone="ink" />
        </div>

        {/* PROJECT TOP FILES SPOTLIGHT */}
        <section className="chart-section">
          <div className="chart-section-title">
            <div>
              <p className="overline">PROJECT HIGHLIGHTS</p>
              <h3>High-Impact Files Spotlight</h3>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontFamily: 'DM Mono, monospace' }}>
              Ranked from real runtime & static metrics
            </span>
          </div>
          <div className="top-files-grid">
            {topEnergyFiles[0] ? (
              <article className="top-file-card">
                <span className="top-file-badge energy">
                  <Flame size={12} /> Highest Energy Demand
                </span>
                <h4 title={topEnergyFiles[0].filename}>{topEnergyFiles[0].filename}</h4>
                <small title={topEnergyFiles[0].relative_path}>{topEnergyFiles[0].relative_path}</small>
                <div className="stat-val">{fixed(topEnergyFiles[0].energy_joules, 2)} J</div>
                <div className="stat-sub">
                  {fixed(topEnergyFiles[0].energy_joules / 3600000.0, 6)} kWh ({fixed((topEnergyFiles[0].energy_joules / (projectResult.total_energy_joules || 1)) * 100, 1)}% of project energy)
                </div>
              </article>
            ) : null}

            {topCarbonFiles[0] ? (
              <article className="top-file-card">
                <span className="top-file-badge carbon">
                  <Leaf size={12} /> Highest Carbon Footprint
                </span>
                <h4 title={topCarbonFiles[0].filename}>{topCarbonFiles[0].filename}</h4>
                <small title={topCarbonFiles[0].relative_path}>{topCarbonFiles[0].relative_path}</small>
                <div className="stat-val">{fixed(topCarbonFiles[0].carbonGrams, 4)} g</div>
                <div className="stat-sub">
                  gCO₂eq per run (CIRS score: {fixed(topCarbonFiles[0].cirs, 6)})
                </div>
              </article>
            ) : null}

            {topFindingsFiles[0] ? (
              <article className="top-file-card">
                <span className="top-file-badge smells">
                  <Sparkles size={12} /> Most Smell-Dense File
                </span>
                <h4 title={topFindingsFiles[0].filename}>{topFindingsFiles[0].filename}</h4>
                <small title={topFindingsFiles[0].relative_path}>{topFindingsFiles[0].relative_path}</small>
                <div className="stat-val">{topFindingsFiles[0].findings_count} Smells</div>
                <div className="stat-sub">
                  ESS Score: {fixed(topFindingsFiles[0].ess, 1)} / 10 ({topFindingsFiles[0].lines_of_code} LOC)
                </div>
              </article>
            ) : null}
          </div>
        </section>

        {/* SECTION 1: ENERGY & CARBON ANALYTICS */}
        <section className="chart-section">
          <div className="chart-section-title">
            <div>
              <p className="overline">ENERGY & CARBON METRICS BY FILE</p>
              <h3>Resource & Emissions Breakdown</h3>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontFamily: 'DM Mono, monospace' }}>
              Comparison across {projectResult.files.length} analyzed files
            </span>
          </div>

          <div className="chart-grid-2">
            <section className="panel">
              <div className="panel-head">
                <div>
                  <p className="overline">ENERGY CONSUMPTION</p>
                  <h3>Energy Consumption by File (Joules)</h3>
                </div>
                <span>Real backend measurements</span>
              </div>
              {projectFilesEnergyData.length ? (
                <div className="chart" style={{ marginTop: '16px' }}>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={projectFilesEnergyData} margin={{ top: 10, right: 15, left: -10, bottom: 25 }}>
                      <CartesianGrid vertical={false} stroke="#e7e4dd" strokeDasharray="3 3" />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: '#6d6a63', fontSize: 11 }}
                        interval={0}
                        angle={projectFilesEnergyData.length > 5 ? -25 : 0}
                        textAnchor={projectFilesEnergyData.length > 5 ? 'end' : 'middle'}
                      />
                      <YAxis tick={{ fill: '#6d6a63', fontSize: 11 }} />
                      <Tooltip
                        cursor={{ fill: '#f3f1eb' }}
                        formatter={(val: any, _name: any, item: any) => [
                          `${fixed(val, 3)} Joules (${fixed(item?.payload?.energyKwh, 8)} kWh)`,
                          'Energy Consumption'
                        ]}
                        labelFormatter={(_label, items) => items?.[0]?.payload?.relativePath || _label}
                      />
                      <Bar dataKey="energyJoules" name="Energy (J)" fill="#2f6b57" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <ChartFallback title="No data available for this visualization" />}
            </section>

            <section className="panel">
              <div className="panel-head">
                <div>
                  <p className="overline">CARBON IMPACT</p>
                  <h3>Carbon Impact by File (gCO₂eq)</h3>
                </div>
                <span>Grid intensity: {fixed(carbonIntensityToDisplay, 1)} gCO₂eq/kWh</span>
              </div>
              {projectFilesCarbonData.length ? (
                <div className="chart" style={{ marginTop: '16px' }}>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={projectFilesCarbonData} margin={{ top: 10, right: 15, left: -10, bottom: 25 }}>
                      <CartesianGrid vertical={false} stroke="#e7e4dd" strokeDasharray="3 3" />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: '#6d6a63', fontSize: 11 }}
                        interval={0}
                        angle={projectFilesCarbonData.length > 5 ? -25 : 0}
                        textAnchor={projectFilesCarbonData.length > 5 ? 'end' : 'middle'}
                      />
                      <YAxis tick={{ fill: '#6d6a63', fontSize: 11 }} />
                      <Tooltip
                        cursor={{ fill: '#f3f1eb' }}
                        formatter={(val: any, _name: any, item: any) => [
                          `${fixed(val, 5)} gCO₂eq (CIRS: ${fixed(item?.payload?.cirs, 6)})`,
                          'Carbon Footprint'
                        ]}
                        labelFormatter={(_label, items) => items?.[0]?.payload?.relativePath || _label}
                      />
                      <Bar dataKey="carbonGrams" name="Carbon (gCO₂eq)" fill="#c38c3d" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <ChartFallback title="No data available for this visualization" />}
            </section>
          </div>
        </section>

        {/* SECTION 2: CODE QUALITY & SUSTAINABILITY SCORES */}
        <section className="chart-section">
          <div className="chart-section-title">
            <div>
              <p className="overline">CODE QUALITY & SUSTAINABILITY INDEXES</p>
              <h3>SCI, ESS & CIRS Metrics across Files</h3>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontFamily: 'DM Mono, monospace' }}>
              {projectComplexitySummary.totalFunctions} functions · Max Nesting Depth {projectComplexitySummary.maxND} · Avg FD {fixed(projectComplexitySummary.avgFD, 3)}
            </span>
          </div>

          <div className="chart-grid-3">
            <section className="panel">
              <div className="panel-head">
                <div>
                  <p className="overline">STRUCTURAL COMPLEXITY</p>
                  <h3>SCI by File</h3>
                </div>
                <span>Index 0–1</span>
              </div>
              {projectFilesSciData.length ? (
                <div className="chart" style={{ marginTop: '14px' }}>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={projectFilesSciData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                      <CartesianGrid vertical={false} stroke="#e7e4dd" strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fill: '#6d6a63', fontSize: 10 }} interval={0} angle={projectFilesSciData.length > 4 ? -25 : 0} textAnchor={projectFilesSciData.length > 4 ? 'end' : 'middle'} />
                      <YAxis tick={{ fill: '#6d6a63', fontSize: 10 }} domain={[0, 1]} />
                      <Tooltip cursor={{ fill: '#f3f1eb' }} formatter={(val: any) => [fixed(val, 4), 'SCI Score']} labelFormatter={(_label, items) => items?.[0]?.payload?.relativePath || _label} />
                      <Bar dataKey="sci" fill="#2e6956" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <ChartFallback title="No data available" />}
            </section>

            <section className="panel">
              <div className="panel-head">
                <div>
                  <p className="overline">ENERGY SMELL SCORE</p>
                  <h3>ESS by File</h3>
                </div>
                <span>Score out of 10</span>
              </div>
              {projectFilesEssData.length ? (
                <div className="chart" style={{ marginTop: '14px' }}>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={projectFilesEssData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                      <CartesianGrid vertical={false} stroke="#e7e4dd" strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fill: '#6d6a63', fontSize: 10 }} interval={0} angle={projectFilesEssData.length > 4 ? -25 : 0} textAnchor={projectFilesEssData.length > 4 ? 'end' : 'middle'} />
                      <YAxis tick={{ fill: '#6d6a63', fontSize: 10 }} domain={[0, 10]} />
                      <Tooltip cursor={{ fill: '#f3f1eb' }} formatter={(val: any) => [fixed(val, 1), 'ESS Score']} labelFormatter={(_label, items) => items?.[0]?.payload?.relativePath || _label} />
                      <Bar dataKey="ess" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <ChartFallback title="No data available" />}
            </section>

            <section className="panel">
              <div className="panel-head">
                <div>
                  <p className="overline">CARBON RISK SCORE</p>
                  <h3>CIRS by File</h3>
                </div>
                <span>gCO₂eq/run</span>
              </div>
              {projectFilesCirsData.length ? (
                <div className="chart" style={{ marginTop: '14px' }}>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={projectFilesCirsData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                      <CartesianGrid vertical={false} stroke="#e7e4dd" strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fill: '#6d6a63', fontSize: 10 }} interval={0} angle={projectFilesCirsData.length > 4 ? -25 : 0} textAnchor={projectFilesCirsData.length > 4 ? 'end' : 'middle'} />
                      <YAxis tick={{ fill: '#6d6a63', fontSize: 10 }} />
                      <Tooltip cursor={{ fill: '#f3f1eb' }} formatter={(val: any) => [fixed(val, 6), 'CIRS']} labelFormatter={(_label, items) => items?.[0]?.payload?.relativePath || _label} />
                      <Bar dataKey="cirs" fill="#475569" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <ChartFallback title="No data available" />}
            </section>
          </div>
        </section>

        {/* SECTION 3: FINDINGS & SEVERITY DISTRIBUTION */}
        <section className="chart-section">
          <div className="chart-section-title">
            <div>
              <p className="overline">ENERGY SMELL AUDIT</p>
              <h3>Findings Distribution & Severity Breakdown</h3>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontFamily: 'DM Mono, monospace' }}>
              Total {projectResult.total_findings} smells detected
            </span>
          </div>

          <div className="chart-grid-2">
            <section className="panel">
              <div className="panel-head">
                <div>
                  <p className="overline">FINDINGS CATEGORIES</p>
                  <h3>Smells Distribution by Category</h3>
                </div>
                <span>{projectCategoryDistributionData.length} categories active</span>
              </div>
              {projectCategoryDistributionData.length > 0 ? (
                <div className="chart" style={{ marginTop: '14px' }}>
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie
                        data={projectCategoryDistributionData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={85}
                        paddingAngle={4}
                        dataKey="count"
                        nameKey="name"
                      >
                        {projectCategoryDistributionData.map((entry, index) => (
                          <Cell key={`cat-${index}`} fill={CATEGORY_COLORS[entry.name] || '#2e6956'} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(val: any, name: any) => [`${val} smell(s)`, name]} />
                      <Legend verticalAlign="bottom" height={36} iconType="circle" />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <ChartFallback title="No data available for this visualization" message="No findings were reported for any of the categories." />
              )}
            </section>

            <section className="panel">
              <div className="panel-head">
                <div>
                  <p className="overline">SEVERITY AUDIT</p>
                  <h3>Findings by Severity</h3>
                </div>
                <span>Risk levels</span>
              </div>
              {projectSeverityDistribution.length > 0 ? (
                <div className="chart" style={{ marginTop: '14px' }}>
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie
                        data={projectSeverityDistribution}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={85}
                        paddingAngle={4}
                        dataKey="count"
                        nameKey="name"
                      >
                        {projectSeverityDistribution.map((entry, index) => (
                          <Cell key={`sev-${index}`} fill={entry.color || SEVERITY_COLORS[entry.name] || '#2e6956'} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(val: any, name: any) => [`${val} smell(s)`, name]} />
                      <Legend verticalAlign="bottom" height={36} iconType="circle" />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <ChartFallback title="No data available for this visualization" message="No severity levels present in the findings data." />
              )}
            </section>
          </div>
        </section>

        <section className="panel project-files-panel" style={{ marginTop: '24px' }}>
          <div className="panel-head" style={{ alignItems: 'center' }}>
            <div>
              <p className="overline">PROJECT FILE DRILLDOWN</p>
              <h3>Analyzed Source Files ({sortedProjectFiles.length} of {projectResult.files.length})</h3>
            </div>
            <div className="search-field" style={{ width: '220px', height: '36px' }}>
              <Search size={14} />
              <input value={tableSearch} onChange={e => setTableSearch(e.target.value)} placeholder="Filter file name…" />
            </div>
          </div>

          <div className="project-table-wrap">
            <table className="project-table">
              <thead>
                <tr>
                  <th onClick={() => { if (sortColumn === 'filename') setSortAsc(!sortAsc); else { setSortColumn('filename'); setSortAsc(true); } }} style={{ cursor: 'pointer' }}>
                    File Name {sortColumn === 'filename' ? (sortAsc ? '▲' : '▼') : ''}
                  </th>
                  <th onClick={() => { if (sortColumn === 'lines_of_code') setSortAsc(!sortAsc); else { setSortColumn('lines_of_code'); setSortAsc(false); } }} style={{ cursor: 'pointer' }}>
                    LOC {sortColumn === 'lines_of_code' ? (sortAsc ? '▲' : '▼') : ''}
                  </th>
                  <th>Status</th>
                  <th onClick={() => { if (sortColumn === 'findings_count') setSortAsc(!sortAsc); else { setSortColumn('findings_count'); setSortAsc(false); } }} style={{ cursor: 'pointer' }}>
                    Findings {sortColumn === 'findings_count' ? (sortAsc ? '▲' : '▼') : ''}
                  </th>
                  <th onClick={() => { if (sortColumn === 'sci') setSortAsc(!sortAsc); else { setSortColumn('sci'); setSortAsc(false); } }} style={{ cursor: 'pointer' }}>
                    SCI {sortColumn === 'sci' ? (sortAsc ? '▲' : '▼') : ''}
                  </th>
                  <th onClick={() => { if (sortColumn === 'ess') setSortAsc(!sortAsc); else { setSortColumn('ess'); setSortAsc(false); } }} style={{ cursor: 'pointer' }}>
                    ESS {sortColumn === 'ess' ? (sortAsc ? '▲' : '▼') : ''}
                  </th>
                  <th onClick={() => { if (sortColumn === 'cirs') setSortAsc(!sortAsc); else { setSortColumn('cirs'); setSortAsc(false); } }} style={{ cursor: 'pointer' }}>
                    Research CIRS {sortColumn === 'cirs' ? (sortAsc ? '▲' : '▼') : ''}
                  </th>
                  <th onClick={() => { if (sortColumn === 'energy_joules') setSortAsc(!sortAsc); else { setSortColumn('energy_joules'); setSortAsc(false); } }} style={{ cursor: 'pointer' }}>
                    Energy (J) {sortColumn === 'energy_joules' ? (sortAsc ? '▲' : '▼') : ''}
                  </th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedProjectFiles.map((fileItem: any, idx: number) => (
                  <tr key={idx} className={fileItem.status === 'error' ? 'row-error' : ''}>
                    <td>
                      <div className="file-name-cell">
                        <FileCode2 size={16} />
                        <div>
                          <strong>{fileItem.filename}</strong>
                          <small>{fileItem.relative_path}</small>
                        </div>
                      </div>
                    </td>
                    <td>{fileItem.lines_of_code}</td>
                    <td><span className={`status-badge ${fileItem.status}`}>{fileItem.status}</span></td>
                    <td><span className={`findings-badge ${fileItem.findings_count > 0 ? 'has-findings' : ''}`}>{fileItem.findings_count}</span></td>
                    <td>{fixed(fileItem.sci, 4)}</td>
                    <td>{fixed(fileItem.ess, 1)}</td>
                    <td>{fixed(fileItem.cirs, 6)}</td>
                    <td>{fixed(fileItem.energy_joules, 3)}</td>
                    <td>
                      {fileItem.single_file_response && (
                        <button className="small-button inspect-file-btn" onClick={() => {
                          setResult(fileItem.single_file_response);
                          setFilename(fileItem.filename);
                          if (fileItem.original_code) setCode(fileItem.original_code);
                          setAnalysisMode('file');
                          navigateView('results');
                        }}>
                          Inspect <ArrowRight size={13} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
              <button className="secondary-button back-to-project-hero-btn" onClick={() => navigateView('project')}>
                <ArrowLeft size={16} /> Back to Project Overview
              </button>
            )}
            <button className="secondary-button" onClick={() => navigateView('recommendations')}>View recommendations <ChevronRight size={17} /></button>
          </div>
        </div>

        <div className="metric-grid">
          <Metric label="Estimated Energy" metric={fixed(energy.energy_joules, 3)} unit="joules" tone="green" />
          <Metric label="Research CIRS" metric={fixed(metrics?.carbon_impact_risk_score, 6)} unit="gCO₂eq/run" tone="ink" />
          <Metric label="Energy Smell Score" metric={fixed(metrics?.energy_smell_score, 1)} unit="out of 10" tone="amber" />
          <Metric label="Individual Findings" metric={String(totalFindingsCount)} unit="findings" tone="blue" />
        </div>

        <div className="metric-grid" style={{ marginTop: '16px' }}>
          <Metric label="Cyclomatic Complexity (CC)" metric={fixed(complexity.cc, 1)} unit="decision paths" tone="blue" />
          <Metric label="Nesting Depth (ND)" metric={fixed(complexity.nd, 0)} unit="max depth" tone="blue" />
          <Metric label="Function Density (FD)" metric={fixed(complexity.fd, 4)} unit="funcs / LOC" tone="blue" />
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
              <span>SLOC: {complexity.sloc}</span>
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
            <div className="intensity"><strong>{fixed(carbonIntensityToDisplay, 2)}</strong><span>gCO₂eq/kWh</span></div>
            <p className="soft-copy">
              Single-run footprint: {fixed(((energy.energy_joules || 0) / 3600000.0) * carbonIntensityToDisplay, 6)} gCO₂eq ({fixed(energy.energy_joules, 3)} Joules consumed).
            </p>
            <button className="text-button" onClick={() => setView('schedule')}>Explore better execution times <ArrowRight size={15} /></button>
          </section>

          {singleFileRefactorComparisonData.length > 0 ? (
            <section className="panel">
              <div className="panel-head">
                <div><p className="overline">POST-REFACTOR COMPARISON</p><h3>Metrics Before vs After AST Refactor</h3></div>
                <span>Safe transformation</span>
              </div>
              <div className="chart">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={singleFileRefactorComparisonData} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#e7e4dd" strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fill: '#6d6a63', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#6d6a63', fontSize: 11 }} />
                    <Tooltip cursor={{ fill: '#f3f1eb' }} />
                    <Legend />
                    <Bar dataKey="Before" fill="#c38c3d" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="After" fill="#2f6b57" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          ) : (
            <section className="panel">
              <div className="panel-head">
                <div><p className="overline">RESEARCH METRICS</p><h3>CIRS & ESS Ratings</h3></div>
              </div>
              <div style={{ padding: '16px 0', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: 'var(--paper)', padding: '14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
                  <p style={{ margin: 0, fontSize: '11px', color: 'var(--muted)' }}>Energy Smell Score (ESS)</p>
                  <strong style={{ fontSize: '24px', color: 'var(--ink)', display: 'block', marginTop: '4px' }}>{fixed(metrics?.energy_smell_score, 1)} / 10</strong>
                  <span style={{ fontSize: '10px', color: 'var(--muted)' }}>Version: {metrics?.ess_version || '1.0.0'}</span>
                </div>
                <div style={{ background: 'var(--paper)', padding: '14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
                  <p style={{ margin: 0, fontSize: '11px', color: 'var(--muted)' }}>Carbon Risk Score (CIRS)</p>
                  <strong style={{ fontSize: '20px', color: 'var(--forest)', display: 'block', marginTop: '4px' }}>{fixed(metrics?.carbon_impact_risk_score, 6)}</strong>
                  <span style={{ fontSize: '10px', color: 'var(--muted)' }}>gCO₂eq / run</span>
                </div>
              </div>
            </section>
          )}
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
                <p>Aggregated optimization rules surfaced across all {projectResult.total_files} analyzed project files.</p>
              </div>
              <span className="count-pill">{projectAggregatedRecommendations.length} unique rules aggregated</span>
            </div>

            {projectAggregatedRecommendations.length ? (
              <div className="recommendation-list">
                {projectAggregatedRecommendations.map((rec, i) => (
                  <article className="recommendation" key={rec.rule_id || i}>
                    <span className="finding-number">{String(i + 1).padStart(2, '0')}</span>
                    <div>
                      <div className="recommendation-title">
                        <div>
                          <p className="overline">{rec.rule_id} · {rec.category}</p>
                          <h3>{rec.title}</h3>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <span className="count-pill" style={{ background: 'var(--sage)', color: 'var(--deep)', border: 0 }}>
                            {rec.affected_files.length} affected file(s) ({rec.occurrences} occurrences)
                          </span>
                          <span className={`severity ${String(rec.severity).toLowerCase()}`}>{rec.severity}</span>
                        </div>
                      </div>
                      <p>{rec.explanation || 'This pattern may create unnecessary work at runtime across multiple files.'}</p>
                      {rec.suggested_fix && <div className="fix"><Check size={16} /><span>{rec.suggested_fix}</span></div>}

                      <div style={{ marginTop: '14px' }}>
                        <button
                          className="small-button"
                          onClick={() => setExpandedRecRule(expandedRecRule === rec.rule_id ? null : rec.rule_id)}
                        >
                          {expandedRecRule === rec.rule_id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          {expandedRecRule === rec.rule_id ? 'Hide Affected Files' : `View Affected Code Paths (${rec.affected_files.length} files)`}
                        </button>

                        {expandedRecRule === rec.rule_id && (
                          <div style={{ marginTop: '10px', display: 'grid', gap: '6px' }}>
                            {rec.affected_files.map((aff, idx) => (
                              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--card)', border: '1px solid var(--line)', padding: '8px 12px', borderRadius: '6px', fontSize: '12px' }}>
                                <span><FileCode2 size={13} style={{ display: 'inline', marginRight: '6px' }} /> <strong>{aff.filename}</strong> ({aff.relative_path})</span>
                                <span>Line {aff.line_number ?? '—'} · Confidence: {fixed(aff.confidence, 2)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : <Empty text="No actionable recommendations were detected across the project." />}
          </section>
        ) : result ? (
          <section>
            <div className="report-hero">
              <div>
                <p className="overline">{projectResult ? `INSPECTING FILE IN ${projectResult.project_name.toUpperCase()}` : 'REFINEMENT QUEUE'}</p>
                <h2>{result.filename || filename} — Recommendations</h2>
                <p>Ordered by available impact signals from your analysis of {result.filename || filename}.</p>
              </div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                {projectResult && (
                  <button className="secondary-button back-to-project-hero-btn" onClick={() => navigateView('project')}>
                    <ArrowLeft size={16} /> Back to Project Overview
                  </button>
                )}
                <span className="count-pill">{recommendations.length} recommendations</span>
              </div>
            </div>
            {recommendations.length ? (
              <div className="recommendation-list">
                {recommendations.map((item: any, i: number) => (
                  <article className="recommendation" key={item.recommendation_id || i}>
                    <span className="finding-number">{String(i + 1).padStart(2, '0')}</span>
                    <div>
                      <div className="recommendation-title">
                        <div>
                          <p className="overline">{display(item.rule_id, 'ENERGY PATTERN')}</p>
                          <h3>{display(item.title || item.name || item.rule_name, 'Review this code path')}</h3>
                        </div>
                        <span className={`severity ${String(item.severity || 'medium').toLowerCase()}`}>{display(item.severity, 'review')}</span>
                      </div>
                      <p>{display(item.explanation || item.description || item.message, 'This pattern may create unnecessary work at runtime.')}</p>
                      {item.suggested_fix && <div className="fix"><Check size={16} /><span>{item.suggested_fix}</span></div>}
                    </div>
                  </article>
                ))}
              </div>
            ) : <Empty text="This analysis did not return actionable recommendations." />}
          </section>
        ) : null
      )}

      {/* IMPACT VIEW (HANDLES BOTH PROJECT & SINGLE FILE) */}
      {view === 'impact' && (
        analysisMode === 'project' && projectResult ? (
          <section className="report">
            <div className="report-hero">
              <div>
                <p className="overline">FULL PROJECT ENERGY & CARBON OUTLOOK</p>
                <h2>{projectResult.project_name} — Project Impact</h2>
                <p>Summed energy footprint, regional carbon intensity, and Research CIRS capacity for the entire project.</p>
              </div>
            </div>

            <div className="metric-grid">
              <Metric label="Total Project Energy" metric={`${fixed(projectResult.total_energy_joules, 2)} J`} unit={`SUM (${fixed(projectResult.total_energy_kwh, 6)} kWh)`} tone="green" />
              <Metric label="Project Carbon Footprint" metric={fixed(projectResult.total_energy_kwh * carbonIntensityToDisplay, 4)} unit="gCO₂eq" tone="amber" />
              <Metric label="Grid Carbon Intensity" metric={fixed(carbonIntensityToDisplay, 2)} unit="gCO₂eq/kWh" tone="blue" />
              <Metric label="Primary Research CIRS" metric={fixed(projectResult.avg_cirs, 6)} unit="MACRO-AVG (gCO₂eq/run)" tone="ink" />
              <Metric label="Total CIRS Capacity" metric={fixed(projectResult.total_cirs, 6)} unit="SUM (gCO₂eq/run)" tone="ink" />
            </div>

            <section className="panel project-files-panel" style={{ marginTop: '20px' }}>
              <div className="panel-head">
                <div>
                  <p className="overline">PROJECT REFACTORING SCOPE</p>
                  <h3>Automated AST Refactoring by File ({projectResult.files.length} files)</h3>
                </div>
              </div>
              <div className="project-table-wrap">
                <table className="project-table">
                  <thead>
                    <tr>
                      <th>File Name</th>
                      <th>LOC</th>
                      <th>SCI (Before → After)</th>
                      <th>Energy Joules</th>
                      <th>Refactor Fixes Available</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {projectResult.files.map((fileItem: any, idx: number) => {
                      const post = fileItem.single_file_response?.post_refactor_estimation || {};
                      const fixes = fileItem.single_file_response?.auto_applied_fixes || [];
                      return (
                        <tr key={idx}>
                          <td><strong>{fileItem.filename}</strong></td>
                          <td>{fileItem.lines_of_code}</td>
                          <td>{post.sci_before !== undefined ? `${fixed(post.sci_before, 3)} → ${fixed(post.sci_after, 3)}` : fixed(fileItem.sci, 3)}</td>
                          <td>{fixed(fileItem.energy_joules, 2)}</td>
                          <td>{fixes.length > 0 ? <span className="status-badge success">{fixes.length} AST Fix(es)</span> : <span className="status-badge">Clean</span>}</td>
                          <td>
                            {fileItem.single_file_response && (
                              <button className="small-button" onClick={() => {
                                setResult(fileItem.single_file_response);
                                setFilename(fileItem.filename);
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
                <p>AST transformation results, post-refactor estimation comparison, and sandboxed execution speedup for {result.filename || filename}.</p>
              </div>
              {projectResult && (
                <button className="secondary-button back-to-project-hero-btn" onClick={() => navigateView('project')}>
                  <ArrowLeft size={16} /> Back to Project Overview
                </button>
              )}
            </div>

            {postRefactor.sci_before !== undefined && (
              <div className="refactor-impact-grid metric-grid">
                <Metric label="SCI (Before → After)" metric={`${fixed(postRefactor.sci_before, 4)} → ${fixed(postRefactor.sci_after, 4)}`} unit="index (0-1)" tone="green" />
                <Metric label="ESS (Before → After)" metric={`${fixed(postRefactor.ess_before, 2)} → ${fixed(postRefactor.ess_after, 2)}`} unit="out of 10" tone="amber" />
                <Metric label="Energy (Before → After)" metric={`${fixed(postRefactor.energy_before_joules, 3)} → ${fixed(postRefactor.energy_after_joules, 3)}`} unit="joules" tone="amber" />
                <Metric label="Research CIRS (Before → After)" metric={`${fixed(postRefactor.cirs_before, 6)} → ${fixed(postRefactor.cirs_after, 6)}`} unit="gCO₂eq/run" tone="ink" />
                <Metric label="Measured Speedup" metric={postRefactor.measured_reduction_percent !== undefined ? `${fixed(postRefactor.measured_reduction_percent, 1)}%` : '—'} unit={postRefactor.measurement_reliability || 'reliable'} tone="blue" />
              </div>
            )}

            <div className="impact-card">
              <div className="impact-icon"><Sparkles size={24} /></div>
              <div>
                <p className="overline">NEXT BEST STEP</p>
                <h3>Apply the safe AST recommendations, then verify with a fresh run.</h3>
                <p>The report measures both static structural complexity reduction and sandboxed execution runtime speedups.</p>
              </div>
              <button className="primary-button" onClick={() => navigateView('recommendations')}>Review fixes <ArrowRight size={17} /></button>
            </div>

            {postRefactor.findings_comparison && postRefactor.findings_comparison.length > 0 && (
              <section className="panel project-files-panel" style={{ marginTop: '20px' }}>
                <div className="panel-head">
                  <div>
                    <p className="overline">FINDINGS RESOLUTION AUDIT</p>
                    <h3>Resolved Energy Smells ({postRefactor.findings_comparison.filter((f: any) => f.is_resolved).length} of {postRefactor.findings_comparison.length})</h3>
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
              metric={analysisMode === 'project' && projectResult ? `${fixed(projectResult.total_energy_joules, 2)} J` : `${fixed(energy.energy_joules, 3)} J`}
              unit={analysisMode === 'project' && projectResult ? `${fixed(projectResult.total_energy_kwh, 6)} kWh` : `${fixed((energy.energy_joules || 0) / 3600000.0, 8)} kWh`}
              tone="green"
            />
            <Metric
              label="Current Grid Intensity"
              metric={fixed(currentZone?.carbon_intensity ?? forecast?.current_carbon_intensity ?? carbonIntensityToDisplay, 2)}
              unit="gCO₂eq/kWh"
              tone="amber"
            />
            <Metric
              label="Current Workload Carbon Footprint"
              metric={analysisMode === 'project' && projectResult ? fixed(projectResult.total_energy_kwh * (currentZone?.carbon_intensity ?? forecast?.current_carbon_intensity ?? carbonIntensityToDisplay), 4) : fixed(((energy.energy_joules || 0) / 3600000.0) * (currentZone?.carbon_intensity ?? forecast?.current_carbon_intensity ?? carbonIntensityToDisplay), 6)}
              unit="gCO₂eq"
              tone="ink"
            />
          </div>

          <ForecastView forecast={forecast} zoneName={currentZone?.display_name || zone} zoneKey={zone} loading={forecastLoading} error={forecastError} />
        </section>
      )}
    </main>
  </div>;
}

function Metric({ label, metric, unit, tone }: { label: string; metric: string; unit: string; tone: string }) {
  return <article className={`metric ${tone}`}><p>{label}</p><strong>{metric}</strong><span>{unit}</span></article>;
}
function Empty({ text }: { text: string }) {
  return <div className="empty-panel"><Check size={21} /><div><h3>Nothing urgent surfaced.</h3><p>{text}</p></div></div>;
}

function formatWindowTime(isoStr?: string): string {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    const datePart = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    const startHour = String(d.getUTCHours()).padStart(2, '0') + ':00';
    const nextH = (d.getUTCHours() + 1) % 24;
    const endHour = String(nextH).padStart(2, '0') + ':00';
    return `${datePart} · ${startHour}–${endHour} UTC`;
  } catch {
    return isoStr;
  }
}

function formatHour(isoStr?: string): string {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return String(d.getUTCHours()).padStart(2, '0') + ':00';
  } catch {
    return isoStr;
  }
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

  const recTimeStr = formatWindowTime(forecast.recommended_execution_time);
  const recTimeIso = forecast.recommended_execution_time;

  const chartData = hourly.map((item: any) => {
    const isOptimal = item.timestamp === recTimeIso;
    return {
      time: formatHour(item.timestamp),
      intensity: item.carbon_intensity,
      emissions: item.emissions_g,
      isOptimal,
      rawTs: item.timestamp
    };
  });

  return (
    <div style={{ display: 'grid', gap: '20px', marginTop: '20px' }}>
      <section className="panel" style={{ background: 'var(--card)', border: '1px solid var(--line)', padding: '20px', borderRadius: '10px' }}>
        <div className="panel-head">
          <div>
            <p className="overline" style={{ color: '#2e6956', fontWeight: 600 }}>RECOMMENDED GREEN WINDOW</p>
            <h2 style={{ fontSize: '24px', margin: '4px 0 0', color: 'var(--ink)' }}>{recTimeStr}</h2>
          </div>
          <span className="status-badge success" style={{ padding: '6px 12px', fontSize: '13px' }}>
            <Leaf size={14} style={{ display: 'inline', marginRight: '4px' }} /> Optimal Execution Window
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginTop: '16px' }}>
          <div style={{ background: 'var(--bg)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
            <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0 }}>Forecast Grid Intensity</p>
            <strong style={{ fontSize: '20px', color: 'var(--forest)', display: 'block', margin: '4px 0 0' }}>
              {fixed(forecast.lowest_forecast_intensity, 1)} <small style={{ fontSize: '11px', color: 'var(--muted)' }}>gCO₂eq/kWh</small>
            </strong>
          </div>

          <div style={{ background: 'var(--bg)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
            <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0 }}>Current Grid Intensity</p>
            <strong style={{ fontSize: '20px', color: 'var(--ink)', display: 'block', margin: '4px 0 0' }}>
              {fixed(forecast.current_carbon_intensity, 1)} <small style={{ fontSize: '11px', color: 'var(--muted)' }}>gCO₂eq/kWh</small>
            </strong>
          </div>

          <div style={{ background: 'var(--bg)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--line)' }}>
            <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0 }}>Potential Intensity Reduction</p>
            <strong style={{ fontSize: '20px', color: forecast.percentage_reduction > 0 ? 'var(--forest)' : 'var(--ink)', display: 'block', margin: '4px 0 0' }}>
              {fixed(forecast.percentage_reduction, 1)}%
            </strong>
          </div>
        </div>

        <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '14px 0 0' }}>
          Based on forecast grid carbon intensity for {zoneName} ({zoneKey}).
        </p>
      </section>

      <section className="panel" style={{ background: 'var(--card)', border: '1px solid var(--line)', padding: '20px', borderRadius: '10px' }}>
        <div className="panel-head">
          <div>
            <p className="overline">24-HOUR CARBON INTENSITY FORECAST</p>
            <h3>Regional Grid Carbon Intensity Forecast (gCO₂eq/kWh)</h3>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--muted)', fontFamily: 'DM Mono, monospace' }}>
            {hourly.length} forecast points
          </span>
        </div>

        <div className="chart" style={{ marginTop: '16px' }}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} margin={{ top: 20, right: 15, left: -15, bottom: 10 }}>
              <CartesianGrid vertical={false} stroke="#e7e4dd" strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fill: '#6d6a63', fontSize: 11 }} />
              <YAxis tick={{ fill: '#6d6a63', fontSize: 11 }} domain={['dataMin - 10', 'dataMax + 10']} />
              <Tooltip
                cursor={{ fill: '#f3f1eb' }}
                formatter={(val: any, _name: any, item: any) => [
                  `${val} gCO₂eq/kWh (${fixed(item?.payload?.emissions, 6)} g workload footprint)`,
                  'Grid Carbon Intensity'
                ]}
                labelFormatter={(label: any, items: readonly any[]) => {
                  const ts = items?.[0]?.payload?.rawTs;
                  return ts ? formatWindowTime(ts) : String(label || '');
                }}
              />
              {forecast.current_carbon_intensity && (
                <ReferenceLine
                  y={forecast.current_carbon_intensity}
                  stroke="#ef4444"
                  strokeDasharray="4 4"
                  label={{ value: `Current (${fixed(forecast.current_carbon_intensity, 1)})`, fill: '#ef4444', fontSize: 10, position: 'top' }}
                />
              )}
              <Bar dataKey="intensity" name="Grid Intensity" radius={[4, 4, 0, 0]}>
                {chartData.map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={entry.isOptimal ? '#10b981' : '#2f6b57'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="legend-custom-wrap">
          <div className="legend-custom-item">
            <span className="legend-custom-dot" style={{ background: '#10b981' }}></span>
            <span>Recommended Green Window</span>
          </div>
          <div className="legend-custom-item">
            <span className="legend-custom-dot" style={{ background: '#2f6b57' }}></span>
            <span>24h Regional Grid Forecast</span>
          </div>
          <div className="legend-custom-item">
            <span className="legend-custom-dot" style={{ background: '#ef4444' }}></span>
            <span>Current Grid Intensity Reference</span>
          </div>
        </div>
      </section>
    </div>
  );
}
