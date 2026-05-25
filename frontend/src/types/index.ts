export type FieldType = 'numeric' | 'text' | 'datetime' | 'boolean' | 'category';

export interface FieldInfo {
  name: string;
  inferred_type: FieldType;
  display_type: FieldType;
  nullable: boolean;
  unique_count: number;
  missing_count: number;
  sample_values: string[];
}

export interface UploadResponse {
  session_id: string;
  filename: string;
  file_size: number;
  row_count: number;
  column_count: number;
  fields: FieldInfo[];
  preview: Record<string, unknown>[];
}

export interface AnalysisProgress {
  session_id: string;
  state: 'uploaded' | 'preview' | 'analyzing' | 'complete' | 'error';
  progress: number;
  error?: string;
}

export interface FieldAnalysis {
  field_name: string;
  field_type: FieldType;
  stats?: Record<string, number>;
  histogram?: { bins: number[]; counts: number[] };
  outliers?: { lower_bound: number; upper_bound: number; outlier_count: number; outlier_rate: number; outlier_values: number[] };
  frequency?: { categories: string[]; counts: number[]; total: number };
}

export interface CorrelationResult {
  fields: string[];
  matrix: (number | null)[][];
  pairs: { field1: string; field2: string; correlation: number; p_value: number; strength: string; direction: string }[];
}

export interface DashboardOverview {
  filename: string;
  row_count: number;
  column_count: number;
  numeric_count: number;
  text_count: number;
  total_missing: number;
  total_outliers: number;
}

export interface CrossTabResult {
  type: 'contingency' | 'group_stats' | 'error';
  row_field?: string;
  col_field?: string;
  row_categories?: string[];
  col_categories?: string[];
  matrix?: number[][];
  chi2?: number | null;
  p_value?: number | null;
  cramers_v?: number | null;
  category_field?: string;
  numeric_field?: string;
  groups?: { category: string; count: number; mean: number; std: number; min: number; max: number }[];
  anova_f?: number | null;
  anova_p?: number | null;
  eta_squared?: number | null;
  message?: string;
}

export interface ChartConfig {
  id: string;
  type: 'histogram' | 'bar' | 'pie' | 'heatmap' | 'boxplot' | 'crosstab' | 'scatter' | 'timeseries';
  title: string;
  field: string;
  data: Record<string, unknown>;
  stats?: Record<string, number>;
}

export interface Insight {
  type: string;
  field: string;
  title: string;
  description: string;
  score: number;
  detail: Record<string, unknown>;
}

export interface KeyDriver {
  field: string;
  type: 'numeric' | 'categorical';
  score: number;
  correlation?: number;
  p_value?: number;
  direction?: string;
  f_statistic?: number;
  eta_squared?: number;
  description: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: string | null;
}
