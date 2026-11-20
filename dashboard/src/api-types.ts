/** Response contracts mirrored from src/api/models.py. */
export type FixStatus = 'applied' | 'rejected_no_improvement' | 'rejected_regression' | 'not_auto_fixable';
export type CarbonSourceType = 'live' | 'fallback' | 'mock' | string;

export interface ProjectMetricTotals {
  energy: number;
  cirs: number;
  ess: number;
}

export interface ProjectFileResult {
  filename: string;
  relative_path: string;
  lines_of_code: number;
  status: 'success' | 'error';
  execution_status?: string;
  error_message?: string | null;
  findings_count: number;
  rule_count: number;
  sci: number;
  ess: number;
  cirs: number;
  energy_joules: number;
  before_energy: number;
  after_energy: number;
  before_cirs: number;
  after_cirs: number;
  before_ess: number;
  after_ess: number;
  fix_status: FixStatus;
  fix_reason: string;
  auto_fixable_count: number;
  auto_applied_count: number;
  analysis_time_sec: number;
  single_file_response?: AnalyzeResponse;
  original_code?: string;
}

export interface ProjectAnalyzeResponse {
  project_name: string;
  timestamp: string;
  total_files: number;
  successful_files: number;
  error_files: number;
  total_lines_of_code: number;
  total_findings: number;
  total_rule_count: number;
  avg_sci: number;
  avg_ess: number;
  avg_cirs: number;
  total_cirs: number;
  total_energy_joules: number;
  total_energy_kwh: number;
  project_before: ProjectMetricTotals;
  project_after: ProjectMetricTotals;
  project_delta: ProjectMetricTotals;
  project_delta_percent: ProjectMetricTotals;
  auto_fixable_count: number;
  auto_applied_count: number;
  total_analysis_time_sec: number;
  carbon_intensity?: number | null;
  carbon_zone?: string | null;
  carbon_source?: string | null;
  carbon_source_type?: CarbonSourceType | null;
  scheduling: Partial<ForecastResponse> & { status?: 'available' | 'unavailable'; error?: string };
  files: ProjectFileResult[];
}

export interface ForecastHourlyPoint {
  timestamp: string;
  carbon_intensity: number;
  emissions_g: number;
}

export interface ForecastResponse {
  zone: string;
  current_carbon_intensity: number;
  lowest_forecast_intensity: number;
  percentage_reduction: number;
  recommended_execution_time: string | null;
  hourly_forecasts: ForecastHourlyPoint[];
  source: string;
  source_type: CarbonSourceType;
  status?: 'available' | 'unavailable' | null;
  error?: string | null;
  window_start?: string | null;
  window_end?: string | null;
  intensity_now?: number | null;
  forecast_minimum_intensity?: number | null;
  intensity_window?: number | null;
  has_cleaner_window?: boolean | null;
  scheduling_reduction_percent?: number | null;
}

export interface AnalyzeResponse {
  filename?: string;
  original_code?: string;
  timestamp?: string;
  carbon_before?: number;
  carbon_after_now?: number;
  carbon_after_green?: number;
  cirs_before?: number;
  cirs_after?: number;
  execution_status?: string;
  window_start?: string | null;
  window_end?: string | null;
  code_only_pct?: number;
  schedule_only_pct?: number;
  total_pct?: number;
  green_window_intensity?: number;
  pipeline_raw?: any;
  research_metrics?: any;
  recommendations?: any;
  optimized_code?: string;
  auto_applied_fixes?: any[];
  manual_fixes?: any[];
  post_refactor_estimation?: any;
  measured_runtime?: any;
  findings?: any[];
  [key: string]: any;
}
