import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, formatError, post } from '../api';
import i18n, { setLanguage } from '../i18n';

beforeEach(async () => { await setLanguage('en'); });

describe('language-independent API errors', () => {
  it('keeps the stable descriptor and translates it only for display', async () => {
    const error = new ApiError('matrix_not_unitary', { vertex: 7 });
    expect(formatError(error, i18n.t)).toContain('vertex 7');
    await setLanguage('de');
    expect(formatError(error, i18n.t)).toContain('Knoten 7');
    expect(error.code).toBe('matrix_not_unitary');
    expect(error.params).toEqual({ vertex: 7 });
  });

  it('translates structured validation fields and reasons without leaking internal messages', async () => {
    const error = new ApiError('request_validation', {}, [{ path: ['body', 'steps'], code: 'maximum', params: { maximum: 200 } }]);
    expect(formatError(error, i18n.t)).toBe('Number of steps: The value must be at most 200.');
    await setLanguage('de');
    expect(formatError(error, i18n.t)).toBe('Schrittzahl: Der Wert darf höchstens 200 betragen.');
  });

  it('uses a translated generic message for future error codes', async () => {
    const error = new ApiError('new_backend_error', {}, [], 503);
    await setLanguage('de');
    expect(formatError(error, i18n.t)).toContain('HTTP 503');
    expect(formatError(error, i18n.t)).not.toContain('new_backend_error');
    expect(formatError(new Error('Raw server prose'), i18n.t)).not.toContain('Raw server prose');
  });

  it('serializes identical experiment data in both interface languages', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ frames: [] }) });
    vi.stubGlobal('fetch', fetchMock);
    const payload = { graph: { kind: 'path', size: 3 }, mode: 'open', seed: 17, scattering: { '1': [[[1, 0], [0, 0]], [[0, 0], [0, 1]]] } };
    await post('simulate', payload);
    await setLanguage('de');
    await post('simulate', payload);
    expect(fetchMock.mock.calls[0]).toEqual(fetchMock.mock.calls[1]);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual(payload);
  });

  it('retains machine-readable error data from HTTP failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ code: 'invalid_edge', params: { target: 2, source: 9 }, detail: 'Original diagnostic' }) }));
    await expect(post('simulate', {})).rejects.toMatchObject({ code: 'invalid_edge', params: { target: 2, source: 9 }, status: 422 });
  });
});
