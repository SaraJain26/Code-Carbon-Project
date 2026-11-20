import test from 'node:test';
import assert from 'node:assert/strict';
import { getCategoryCounts, getEssBands, getScopeFiles, getScopeMetrics, isTestOrExamplePath } from '../dashboard/src/project-scope.ts';

function file(relative_path, overrides = {}) {
  return {
    filename: relative_path.split('/').at(-1), relative_path, lines_of_code: 100,
    status: 'success', findings_count: 0, rule_count: 0, sci: 0.2, ess: 1,
    cirs: 0.01, energy_joules: 10, before_energy: 10, after_energy: 10,
    before_cirs: 0.01, after_cirs: 0.01, before_ess: 1, after_ess: 1,
    fix_status: 'not_auto_fixable', fix_reason: '', auto_fixable_count: 0,
    auto_applied_count: 0, analysis_time_sec: 0,
    single_file_response: { pipeline_raw: { energy_smell_report: { findings: [] } } },
    ...overrides,
  };
}

test('shared scope selection recomputes project totals and retains zero categories', () => {
  const rows = [
    file('src/app.py', { findings_count: 2, rule_count: 1, energy_joules: 20, ess: 4, cirs: 0.02,
      single_file_response: { pipeline_raw: { energy_smell_report: { findings: [
        { rule_id: 'EKB-IO-001', category: 'io' }, { rule_id: 'EKB-MEM-001', category: 'memory' },
      ] } } } }),
    file('tests/test_app.py', { findings_count: 1, rule_count: 1, energy_joules: 30, ess: 8, cirs: 0.03,
      single_file_response: { pipeline_raw: { energy_smell_report: { findings: [{ rule_id: 'EKB-NET-001', category: 'network' }] } } } }),
    file('examples/demo.py', { energy_joules: 40 }),
  ];
  const allFiles = getScopeFiles(rows, false);
  const sourceFiles = getScopeFiles(rows, true);
  assert.equal(getScopeMetrics(allFiles).totalFiles, 3);
  assert.equal(getScopeMetrics(allFiles).energyJoules, 90);
  assert.equal(getScopeMetrics(allFiles).findingLocations, 3);
  assert.equal(getScopeMetrics(sourceFiles).totalFiles, 1);
  assert.equal(getScopeMetrics(sourceFiles).energyJoules, 20);
  assert.equal(getScopeMetrics(sourceFiles).findingLocations, 2);
  assert.deepEqual(getCategoryCounts(sourceFiles), [
    { name: 'File & I/O', count: 1 }, { name: 'Memory', count: 1 }, { name: 'Network', count: 0 },
    { name: 'Computation', count: 0 }, { name: 'Control Flow', count: 0 },
  ]);
  assert.deepEqual(getEssBands(allFiles).map(band => band.count), [1, 1, 1]);
  assert.equal(isTestOrExamplePath('pkg/tests/test_x.py'), true);
  assert.equal(isTestOrExamplePath('pkg/examples/demo.py'), true);
  assert.equal(isTestOrExamplePath('pkg/src/app.py'), false);
});
