import type { ProjectFileResult } from './api-types';

export const SCOPE_CATEGORIES = ['File & I/O', 'Memory', 'Network', 'Computation', 'Control Flow'] as const;

export function isTestOrExamplePath(path: string): boolean {
  const normalized = path.replace(/\\/g, '/').toLowerCase();
  return /(?:^|\/)(?:tests?|examples?)(?:\/|$)/.test(normalized)
    || /(?:^|\/)test_[^/]*(?:\/|$)/.test(normalized);
}

export function getScopeFiles(files: ProjectFileResult[], sourceOnly: boolean): ProjectFileResult[] {
  return files.filter(file => !sourceOnly || !isTestOrExamplePath(file.relative_path));
}

export function getScopeMetrics(files: ProjectFileResult[]) {
  const successful = files.filter(file => file.status === 'success');
  const sum = (pick: (file: ProjectFileResult) => number) => successful.reduce((total, file) => total + Number(pick(file) || 0), 0);
  const distinctRules = new Set<string>();
  for (const file of successful) {
    const findings = file.single_file_response?.pipeline_raw?.energy_smell_report?.findings || [];
    for (const finding of findings) if (finding.rule_id) distinctRules.add(String(finding.rule_id));
  }
  const withFindings = successful.filter(file => file.findings_count > 0).length;
  return {
    totalFiles: files.length,
    successfulFiles: successful.length,
    failedFiles: files.length - successful.length,
    sloc: sum(file => file.lines_of_code),
    findingLocations: sum(file => file.findings_count),
    ruleInstances: sum(file => file.rule_count),
    distinctRules: distinctRules.size,
    filesWithFindings: withFindings,
    cleanFiles: successful.length - withFindings,
    meanSci: successful.length ? sum(file => file.sci) / successful.length : 0,
    meanEss: successful.length ? sum(file => file.ess) / successful.length : 0,
    energyJoules: sum(file => file.energy_joules),
    meanCirs: successful.length ? sum(file => file.cirs) / successful.length : 0,
    totalCirs: sum(file => file.cirs),
    beforeEnergy: sum(file => file.before_energy),
    afterEnergy: sum(file => file.after_energy),
    beforeEss: sum(file => file.before_ess),
    afterEss: sum(file => file.after_ess),
    beforeCirs: sum(file => file.before_cirs),
    afterCirs: sum(file => file.after_cirs),
    highEssFiles: successful.filter(file => file.ess >= 7).length,
  };
}

export function getCategoryCounts(files: ProjectFileResult[]) {
  const counts = new Map<string, number>(SCOPE_CATEGORIES.map(category => [category, 0]));
  for (const file of files) {
    if (file.status !== 'success') continue;
    const findings = file.single_file_response?.pipeline_raw?.energy_smell_report?.findings || [];
    for (const finding of findings) {
      const category = String(finding.category || '').toLowerCase();
      const ruleId = String(finding.rule_id || '').toLowerCase();
      const bucket = ruleId.includes('io-') || ['io', 'file & i/o', 'file and i/o'].includes(category) ? 'File & I/O'
        : ruleId.includes('net-') || ['network', 'http', 'api'].some(part => category.includes(part)) ? 'Network'
          : ruleId.includes('mem-') || ['memory', 'allocation'].some(part => category.includes(part)) ? 'Memory'
            : ruleId.includes('comp-') || ['nest', 'loop', 'comput', 'math'].some(part => category.includes(part)) ? 'Computation'
              : 'Control Flow';
      counts.set(bucket, (counts.get(bucket) || 0) + 1);
    }
  }
  return SCOPE_CATEGORIES.map(name => ({ name, count: counts.get(name) || 0 }));
}

export function getEssBands(files: ProjectFileResult[]) {
  const successful = files.filter(file => file.status === 'success');
  return [
    { label: 'Low', min: 0, max: 3, count: successful.filter(file => file.ess < 3).length },
    { label: 'Medium', min: 3, max: 7, count: successful.filter(file => file.ess >= 3 && file.ess < 7).length },
    { label: 'High', min: 7, max: 10, count: successful.filter(file => file.ess >= 7).length },
  ];
}

export function getEssFineHistogram(files: ProjectFileResult[]) {
  const bins = [
    { label: '0-2', min: 0, max: 2, count: 0 }, { label: '2-4', min: 2, max: 4, count: 0 },
    { label: '4-6', min: 4, max: 6, count: 0 }, { label: '6-8', min: 6, max: 8, count: 0 },
    { label: '8-10', min: 8, max: 10.000001, count: 0 },
  ];
  for (const file of files) {
    if (file.status !== 'success') continue;
    const bin = bins.find(item => file.ess >= item.min && file.ess < item.max);
    if (bin) bin.count += 1;
  }
  return bins;
}
