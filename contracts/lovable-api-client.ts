/** Integration starting point, NOT connected to the remote Lovable UI yet.
 * Use only behind a tested same-origin reverse proxy to the Python API.
 * Never replace auth failures with mock data or put session/link tokens in localStorage.
 */
export class AssinaApiClient {
  constructor(private orgId: string, private csrf: string) {}
  async request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    const response = await fetch(`/api${path}`, {
      method, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Organization': this.orgId, 'X-CSRF-Token': this.csrf },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    if (!response.ok) throw new Error((await response.json()).detail ?? 'Falha na API');
    return response.json() as Promise<T>;
  }
}
