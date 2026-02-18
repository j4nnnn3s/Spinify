const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface NfcCurrent {
  uid: string | null;
  record: RecordMapping | null;
  record_cover_url: string | null;
}

export interface RecordMapping {
  record_id: string;
  nfc_uid: string;
  name: string;
  spotify_uri: string;
  type: 'album' | 'playlist';
  created_at: string;
}

export interface PlaybackState {
  is_playing: boolean;
  context_uri: string | null;
  context_image_url: string | null;
  track_uri: string;
  track_index: number;
  position_ms: number;
  duration_ms: number;
  track_name: string;
  album_name: string;
  artist_name: string;
}

export const api = {
  nfc: {
    current: () => fetchApi<NfcCurrent>('/api/nfc/current'),
    scan: () => fetchApi<{ uid: string }>('/api/nfc/scan', { method: 'POST' }),
    simulate: (uid: string | null) =>
      fetchApi<{ ok: boolean; uid: string | null }>(
        `/api/nfc/simulate${uid != null ? `?uid=${encodeURIComponent(uid)}` : ''}`,
        { method: 'POST' }
      ),
  },
  playback: {
    get: () => fetchApi<PlaybackState>('/api/playback'),
    start: (context_uri?: string) =>
      fetchApi<{ ok: boolean }>('/api/playback/start', {
        method: 'POST',
        body: JSON.stringify(context_uri != null ? { context_uri } : {}),
      }),
    stop: () => fetchApi<{ ok: boolean }>('/api/playback/stop', { method: 'POST' }),
    position: () => fetchApi<{ position_ms: number; duration_ms: number; track_index: number }>('/api/playback/position'),
  },
  records: {
    list: () => fetchApi<{ records: RecordMapping[] }>('/api/records'),
    create: (body: { nfc_uid: string; name: string; spotify_uri: string; type: 'album' | 'playlist' }) =>
      fetchApi<RecordMapping>('/api/records', { method: 'POST', body: JSON.stringify(body) }),
    update: (id: string, body: Partial<{ name: string; spotify_uri: string; type: 'album' | 'playlist' }>) =>
      fetchApi<RecordMapping>(`/api/records/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: (id: string) => fetchApi<void>(`/api/records/${id}`, { method: 'DELETE' }),
  },
  spotify: {
    authUrl: () => fetchApi<{ auth_url: string | null; error?: string }>('/api/spotify/auth-url'),
    completeLogin: (body: { redirect_url?: string; code?: string }) =>
      fetchApi<{ ok: boolean; message?: string }>('/api/spotify/complete-login', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },
}
