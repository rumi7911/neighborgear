import type { Mutation, Snapshot } from "./types";
import { fetchWithRetry } from "./transport";
const base = import.meta.env.VITE_API_BASE || "/api";
const tokenKey = "neighborgear.sandbox.v1";
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const token = localStorage.getItem(tokenKey);
  const response = await fetchWithRetry(`${base}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Sandbox-Token": token } : {}),
      ...(method !== "GET" ? { "Idempotency-Key": crypto.randomUUID() } : {}),
      ...(sessionStorage.getItem("neighborgear.judge")
        ? { "X-Judge-Key": sessionStorage.getItem("neighborgear.judge")! }
        : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    let reason;
    try {
      reason = await response.json();
    } catch {
      reason = { detail: `Request failed (${response.status})` };
    }
    throw new Error(
      typeof reason.detail === "string"
        ? reason.detail
        : JSON.stringify(reason.detail),
    );
  }
  return response.json();
}
let initialization: Promise<void> | undefined;
export function forgetSession() {
  localStorage.removeItem(tokenKey);
  initialization = undefined;
}
export function initialize() {
  if (!initialization)
    initialization = (async () => {
      if (!localStorage.getItem(tokenKey)) {
        const session = await api<{ token: string }>("/sessions", "POST", {});
        localStorage.setItem(tokenKey, session.token);
      }
    })().catch((e) => {
      initialization = undefined;
      throw e;
    });
  return initialization;
}
export const snapshot = () => api<Snapshot>("/snapshot");
export const mutate = (path: string, body: unknown = {}) =>
  api<Mutation>(path, "POST", body);
