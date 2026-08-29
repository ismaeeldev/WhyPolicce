# stores/

Zustand stores only — **one small store per concern**, never a mega app-state store.

Belongs here (per `AgentGuide/01_ThemeGuideline.md` §10): global client/UI state that's shared across components but isn't server data — modal open/closed state, collapsed/expanded UI panels, dark-mode preference backing.

Does NOT belong here: server/remote data (→ `hooks/`, TanStack Query), local/ephemeral state only one component cares about (→ `useState`), the live SSE search stream (→ `hooks/useSearchStream.ts`, a dedicated reducer, not this).
