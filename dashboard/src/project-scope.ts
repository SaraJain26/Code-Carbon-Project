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
  const findingsInFilesWithFindings = successful
    .filter(file => file.findings_count > 0)
    .reduce((total, file) => total + Number(file.findings_count || 0), 0);
  return {
    totalFiles: files.length,
    successfulFiles: successful.length,
    failedFiles: files.length - successful.length,
    sloc: sum(file => file.lines_of_code),
    findingLocations: sum(file => file.findings_count),
    ruleInstances: sum(file => file.rule_count),
    distinctRules: distinctRules.size,
    filesWithFindings: withFindings,
    findingsInFilesWithFindings,
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
  const rules = new Map<string, Map<string, string>>(SCOPE_CATEGORIES.map(category => [category, new Map()]));
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
      if (ruleId) {
        const bucketRules = rules.get(bucket)!;
        const originalRuleId = String(finding.rule_id);
        bucketRules.set(originalRuleId, String(finding.message || originalRuleId));
      }
    }
  }
  return SCOPE_CATEGORIES.map(name => ({ name, count: counts.get(name) || 0, rules: [...(rules.get(name)?.entries() || [])].map(([id, title]) => `${id} — ${title}`) }));
}

export function getOverviewTakeaways(files: ProjectFileResult[], displayPath: (path: string) => string = path => path) {
  const successful = files.filter(file => file.status === 'success');
  const metrics = getScopeMetrics(files);
  const energyRanked = [...successful].sort((a, b) => b.energy_joules - a.energy_joules);
  const topTen = energyRanked.slice(0, 10);
  const topTenEnergy = topTen.reduce((sum, file) => sum + Number(file.energy_joules || 0), 0);
  const topEnergy = energyRanked[0];
  const categories = getCategoryCounts(files).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  const topCategory = categories.find(category => category.count > 0);
  const filesToFix = successful.filter(file => file.findings_count > 0).sort((a, b) => b.cirs - a.cirs).slice(0, 3);
  const categoryShare = metrics.findingLocations ? (topCategory?.count || 0) / metrics.findingLocations * 100 : 0;
  const concentrationShare = metrics.findingLocations ? metrics.findingsInFilesWithFindings / metrics.findingLocations * 100 : 0;
  const topTenShare = metrics.energyJoules ? topTenEnergy / metrics.energyJoules * 100 : 0;
  const topFileShare = metrics.energyJoules && topEnergy ? topEnergy.energy_joules / metrics.energyJoules * 100 : 0;
  const topFixNames = filesToFix.map(file => displayPath(file.relative_path));
  const highEssCount = getEssBands(files).find(band => band.label === 'High')?.count || 0;
  return {
    topTenShare,
    topFileShare,
    topFilePath: topEnergy?.relative_path || '',
    categoryName: topCategory?.name || '',
    categoryShare,
    categoryCount: topCategory?.count || 0,
    findingLocations: metrics.findingLocations,
    filesWithFindings: metrics.filesWithFindings,
    totalFiles: metrics.successfulFiles,
    concentrationShare,
    filesToFix: filesToFix.map(file => file.relative_path),
    energySentence: topEnergy
      ? `Top 10 = ${topTenShare.toFixed(1)}% of the project's modeled energy; ${displayPath(topEnergy.relative_path)} alone uses ${topFileShare.toFixed(1)}%.`
      : 'No file energy is available in this scope.',
    categorySentence: topCategory?.count
      ? `${topCategory.name} patterns are ${categoryShare.toFixed(1)}% of all findings.`
      : 'No findings were returned in this scope.',
    concentrationSentence: `${metrics.filesWithFindings} of ${metrics.successfulFiles} files hold ${metrics.findingsInFilesWithFindings} of ${metrics.findingLocations} finding locations (${concentrationShare.toFixed(1)}%).`,
    fixFirstSentence: `${highEssCount} files have high smell scores. ${topFixNames.length ? `Start with ${topFixNames.join(', ')}.` : 'No files with findings need review.'}`,
  };
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
