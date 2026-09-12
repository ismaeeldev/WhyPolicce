"use client";

import { getAccessToken } from "@auth0/nextjs-auth0";
import { useCallback, useReducer, useRef } from "react";

import { trackEvent } from "@/lib/analytics";
import { ApiError } from "@/lib/api-client";
import { parseSseStream } from "@/lib/sse";

import type { SearchSource } from "@/lib/sse";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export type StreamStatus =
  | "idle"
  | "submitting"
  | "streaming"
  | "complete"
  | "error"
  | "rate_limited"
  | "upgrade_required";

type State = {
  status: StreamStatus;
  text: string;
  sessionId: string | null;
  errorMessage: string | null;
  retryAfterSeconds: number | null;
  memorySnippets: string[];
  sources: SearchSource[];
};

type Action =
  | { type: "submit" }
  | { type: "token"; data: string }
  | { type: "done"; sessionId: string; memorySnippets: string[]; sources: SearchSource[] }
  | { type: "error"; message: string }
  | { type: "rate_limited"; message: string; retryAfterSeconds: number }
  | { type: "upgrade_required"; message: string }
  | { type: "reset" };

const initialState: State = {
  status: "idle",
  text: "",
  sessionId: null,
  errorMessage: null,
  retryAfterSeconds: null,
  memorySnippets: [],
  sources: [],
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "submit":
      return { ...initialState, status: "submitting" };
    case "token":
      return { ...state, status: "streaming", text: state.text + action.data };
    case "done":
      return {
        ...state,
        status: "complete",
        sessionId: action.sessionId,
        memorySnippets: action.memorySnippets,
        sources: action.sources,
      };
    case "error":
      return { ...state, status: "error", errorMessage: action.message };
    case "rate_limited":
      return {
        ...state,
        status: "rate_limited",
        errorMessage: action.message,
        retryAfterSeconds: action.retryAfterSeconds,
      };
    case "upgrade_required":
      return { ...state, status: "upgrade_required", errorMessage: action.message };
    case "reset":
      return initialState;
  }
}

/**
 * Dedicated SSE streaming state — AgentGuide/01_ThemeGuideline.md §10:
 * deliberately NOT TanStack Query (this isn't cacheable server data) and NOT
 * Zustand (it's local to one search interaction, not shared app state).
 */
export function useSearchStream() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const abortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  const submit = useCallback(
    async (params: { prompt: string; sessionId?: string; deepSearch: boolean; state?: string | null }) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const requestId = ++requestIdRef.current;
      const isCurrent = () => requestId === requestIdRef.current;

      dispatch({ type: "submit" });
      trackEvent("search_submitted", { deepSearch: params.deepSearch });

      let token: string | undefined;
      try {
        token = await getAccessToken();
      } catch {
        // No session — the backend will 401, surfaced as a generic error below.
      }

      if (!isCurrent()) return;

      try {
        const res = await fetch(`${BACKEND_URL}/api/search/stream`, {
          method: "POST",
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            prompt: params.prompt,
            sessionId: params.sessionId,
            deepSearch: params.deepSearch,
            // State Selector, Step 7 — real client-requested feature,
            // matching the client's own pasted request body exactly
            // (`state: params.state`). Omitted (undefined) when no
            // state is selected — the backend schema already treats a
            // missing/null state as "no scoping," the same general
            // search behavior as before this feature existed.
            state: params.state ?? undefined,
          }),
        });

        if (!isCurrent()) return;

        if (res.status === 429) {
          const body = await res.json();
          if (!isCurrent()) return;
          dispatch({
            type: "rate_limited",
            message: body.message ?? "Rate limit exceeded.",
            retryAfterSeconds: body.retryAfterSeconds ?? 60,
          });
          trackEvent("rate_limited_hit", { retryAfterSeconds: body.retryAfterSeconds });
          return;
        }

        if (res.status === 403) {
          const body = await res.json();
          if (!isCurrent()) return;
          if (body.error === "upgrade_required") {
            dispatch({ type: "upgrade_required", message: body.message ?? "" });
            trackEvent("upgrade_modal_shown", { reason: "deep_search" });
            return;
          }
        }

        if (!res.ok || !res.body) {
          const body = await res.json().catch(() => ({ message: "Something went wrong." }));
          if (!isCurrent()) return;
          dispatch({ type: "error", message: body.message ?? "Something went wrong." });
          trackEvent("search_interrupted", { status: res.status });
          return;
        }

        let receivedDone = false;
        let receivedTokens = false;
        for await (const event of parseSseStream(res.body, controller.signal)) {
          if (!isCurrent()) return;
          if (event.type === "token") {
            receivedTokens = true;
            dispatch({ type: "token", data: event.data });
          } else if (event.type === "done") {
            receivedDone = true;
            dispatch({
              type: "done",
              sessionId: event.sessionId,
              memorySnippets: event.memorySnippets ?? [],
              sources: event.sources ?? [],
            });
            trackEvent("search_completed", { sessionId: event.sessionId });
            return;
          } else if (event.type === "error") {
            dispatch({ type: "error", message: event.message });
            trackEvent("search_interrupted", { reason: "stream_error" });
            return;
          }
        }
        if (!isCurrent()) return;
        if (receivedTokens && !receivedDone) {
          // Stream ended after tokens but before a done event — show the answer
          // instead of a false "interrupted" error (can happen on slow networks).
          dispatch({ type: "done", sessionId: "", memorySnippets: [], sources: [] });
          trackEvent("search_completed", { sessionId: "unknown" });
          return;
        }
        if (!receivedDone) {
          // Found during hardening: the previous message ("is the backend
          // running on port 8000?") was a hardcoded local-dev assumption,
          // shown verbatim in production too — misleading for a real user
          // and for anyone investigating a real report of this error,
          // since a production backend obviously isn't on port 8000. This
          // path fires when the connection reached the server (unlike the
          // TypeError case below, which never connected at all) but
          // closed before any answer arrived — a real possibility now
          // that RAG retrieval can add real, sometimes 20-30s+ delay
          // before the first token streams, if an intermediate proxy or
          // the browser itself times out an idle connection first.
          dispatch({
            type: "error",
            message: "that answer didn't arrive — the search may have taken too long.",
          });
          trackEvent("search_interrupted", { reason: "stream_closed_early" });
        }
      } catch (err) {
        if (controller.signal.aborted || !isCurrent()) return;
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof TypeError
              ? "we couldn't reach the search service — check your connection."
              : "that answer didn't arrive.";
        dispatch({ type: "error", message });
        trackEvent("search_interrupted", { reason: "network_error" });
      }
    },
    [],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "reset" });
  }, []);

  const reset = useCallback(() => dispatch({ type: "reset" }), []);

  return { ...state, submit, cancel, reset };
}
