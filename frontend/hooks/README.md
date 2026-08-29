# hooks/

Server/remote data hooks — every one wraps TanStack Query (`useQuery`/`useMutation`), per `AgentGuide/01_ThemeGuideline.md` §10. This is what keeps loading/error states consistent across the app instead of hand-rolled `useEffect` fetching per component.

Exception: `useSearchStream.ts` (built in Step 5) is a dedicated reducer for the live SSE token stream — deliberately NOT TanStack Query or Zustand, since it's transient, uncacheable data, not server state.

Does NOT belong here: shared UI state (→ `stores/`, Zustand), local/ephemeral state (→ plain `useState` in the component).
