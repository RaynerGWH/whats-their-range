export const API = import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "";

export async function request<T>(
  path: string,
  token: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch(`${API}/api${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    // Keep the existing session-control validation messages available.
    if (!/^\/tables\/[^/]+\/traces(?:[/?]|$)/.test(path)) {
      const data = await res.json().catch(() => ({}));
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : `Request failed (${res.status}).`,
      );
    }
    // Do not render arbitrary server/proxy bodies in the trace inspector.
    const messages: Record<number, string> = {
      401: "Access denied. Check Connections.",
      403: "Access denied. Check Connections.",
      404: "Not found. Trace endpoints may be unavailable on this backend.",
    };
    throw new Error(messages[res.status] || `Request failed (${res.status}).`);
  }
  return res.json();
}
