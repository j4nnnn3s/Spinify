const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    let message = text;
    try {
      const json = JSON.parse(text) as { detail?: string };
      if (typeof json.detail === 'string') message = json.detail;
    } catch {
      /* use text as-is */
    }
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface NfcCurrent {
  uid: string | null;
  spotify_uri: string | null;
  record_name: string | null;
  record_cover_url: string | null;
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

export interface Record {
  record_id: string;
  nfc_uid: string;
  name: string;
  spotify_uri: string;
  type: string;
  created_at: string;
}

export const api = {
  nfc: {
    current: () => fetchApi<NfcCurrent>('/api/nfc/current'),
    scan: () => fetchApi<{ uid: string }>('/api/nfc/scan', { method: 'POST' }),
    simulate: (uid: string | null, spotify_uri?: string) => {
      const params = new URLSearchParams()
      if (uid != null) params.set('uid', uid)
      if (spotify_uri != null) params.set('spotify_uri', spotify_uri)
      return fetchApi<{ ok: boolean; uid: string | null; spotify_uri: string | null }>(
        `/api/nfc/simulate${params.toString() ? `?${params.toString()}` : ''}`,
        { method: 'POST' }
      )
    },
  },
  playback: {
    get: () => fetchApi<PlaybackState>('/api/playback'),
    start: (context_uri?: string) =>
      fetchApi<{ ok: boolean }>('/api/playback/start', {
        method: 'POST',
        body: JSON.stringify(context_uri != null ? { context_uri } : {}),
      }),
    stop: () => fetchApi<{ ok: boolean }>('/api/playback/stop', { method: 'POST' }),
    position: () =>
      fetchApi<{ position_ms: number; duration_ms: number; track_index: number }>(
        '/api/playback/position'
      ),
  },
  motors: {
    toneArm: {
      get: () =>
        fetchApi<{ steps_from_home: number; angle_deg: number; total_steps_per_rev: number }>(
          '/api/motors/tone-arm'
        ),
      sync: () =>
        fetchApi<{
          ok: boolean;
          reason?: string;
          fraction?: number;
          track_index?: number;
          total_tracks?: number;
        }>('/api/motors/tone-arm/sync', { method: 'POST' }),
      jog: (steps: number, absolute = false, fromSettings = false) =>
        fetchApi<{ ok: boolean; error?: string }>('/api/motors/tone-arm', {
          method: 'POST',
          body: JSON.stringify({
            position: absolute ? 'absolute' : 'relative',
            steps,
            from_settings: fromSettings,
          }),
        }),
    },
  },
  spotify: {
    authUrl: () =>
      fetchApi<{ auth_url: string | null; error?: string; logged_in?: boolean }>('/api/spotify/auth-url'),
    completeLogin: (body: { redirect_url?: string; code?: string }) =>
      fetchApi<{ ok: boolean; message?: string }>('/api/spotify/complete-login', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    logout: () => fetchApi<{ ok: boolean }>('/api/spotify/logout', { method: 'POST' }),
    defaultDevice: () =>
      fetchApi<{ device_id: string | null; name: string | null }>('/api/spotify/default-device'),
    saveCurrentDevice: () =>
      fetchApi<{ device_id: string; name: string }>('/api/spotify/default-device/save-current', {
        method: 'POST',
      }),
  },
  records: {
    list: () => fetchApi<Record[]>('/api/records/'),
    create: (body: { nfc_uid: string; spotify_uri?: string; spotify_url?: string }) =>
      fetchApi<Record>('/api/records/', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    update: (record_id: string, body: { name?: string; spotify_uri?: string; spotify_url?: string; type?: string }) =>
      fetchApi<Record>(`/api/records/${record_id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    delete: (record_id: string) =>
      fetchApi<void>(`/api/records/${record_id}`, { method: 'DELETE' }),
  },
}
