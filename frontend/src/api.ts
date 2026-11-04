import type { TFunction } from 'i18next';

interface ValidationIssue { path: (string | number)[]; code: string; params?: Record<string, unknown>; }

/** Store a descriptor, not translated prose, so existing errors switch live. */
export class ApiError extends Error {
  constructor(
    public readonly code: string,
    public readonly params: Record<string, unknown> = {},
    public readonly issues: ValidationIssue[] = [],
    public readonly status?: number,
  ) { super(code); this.name = 'ApiError'; }
}

const errorKeys = new Set([
  'network', 'invalid_response', 'invalid_experiment', 'cycle_size', 'edge_limit',
  'matrix_vertices', 'matrix_shape', 'matrix_dimension', 'matrix_not_unitary',
  'hadamard_degree', 'density_budget', 'invalid_edge', 'initial_state', 'vertex_parameters',
  'ensemble_budget', 'ensemble_histories', 'atom_id', 'analysis_budget', 'stationary_budget', 'stationary_class',
]);
const validationKeys = new Set([
  'integer', 'finite_number', 'minimum', 'maximum', 'required', 'unexpected_field',
  'unsupported_value', 'invalid_json', 'invalid_structure', 'invalid',
]);
const fieldKeys = new Set(['graph', 'kind', 'size', 'preset', 'seed', 'degree', 'scattering', 'mode', 'initial', 'edge', 'steps', 'strategy', 'trajectories', 'statistics', 'selected_histories', 'vertex_parameters', 'omega', 'beta', 'atom_id', 'vertex', 'vector', 'density', 'vertex_dynamics', 'analysis_steps', 'support_atol', 'include_density', 'stationary_class']);

export function formatError(error: unknown, t: TFunction): string {
  if (!(error instanceof ApiError)) return t('errors:unexpected');
  if (error.code === 'request_validation' && error.issues.length) {
    return error.issues.map((issue) => {
      const field = issue.path.filter((part) => part !== 'body').map((part) => {
        if (typeof part === 'number' || /^\d+$/.test(part)) return String(part);
        return t(`errors:fields.${fieldKeys.has(part) ? part : 'request'}`);
      }).join(' › ') || t('errors:fields.request');
      const key = validationKeys.has(issue.code) ? issue.code : 'invalid';
      return t('errors:validation.issue', { field, reason: t(`errors:validation.${key}`, issue.params ?? {}) });
    }).join(' · ');
  }
  return errorKeys.has(error.code)
    ? t(`errors:${error.code}`, error.params)
    : t('errors:request_failed', { status: error.status ?? '—' });
}

export async function post<T>(route: string, body: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/${route}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('network');
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const issues: ValidationIssue[] = Array.isArray(data?.issues)
      ? data.issues.filter((item: unknown): item is ValidationIssue =>
        typeof item === 'object' && item !== null && 'code' in item && typeof item.code === 'string'
        && 'path' in item && Array.isArray(item.path)
        && item.path.every((part: unknown) => typeof part === 'string' || typeof part === 'number'))
      : [];
    throw new ApiError(typeof data?.code === 'string' ? data.code : 'request_failed', data?.params ?? {}, issues, response.status);
  }
  if (data === null) throw new ApiError('invalid_response');
  return data as T;
}
