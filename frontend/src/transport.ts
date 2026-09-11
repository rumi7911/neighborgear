/** Retry one uncertain transport failure without changing the command identity. */
export async function fetchWithRetry(url: string, options: RequestInit, network: typeof fetch = fetch): Promise<Response> {
  try {
    return await network(url, {...options, signal: AbortSignal.timeout(20000)});
  } catch {
    return network(url, {...options, signal: AbortSignal.timeout(20000)});
  }
}
