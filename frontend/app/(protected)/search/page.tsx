"use client";

import { useEffect, useRef, useState } from "react";

import { AnswerPanel } from "@/components/search/AnswerPanel";
import { SearchBar } from "@/components/search/SearchBar";
import { useSearchStream } from "@/hooks/useSearchStream";
import { useUser } from "@/hooks/useUser";
import { useUpgradeModalStore } from "@/stores/useUpgradeModalStore";

const PENDING_QUERY_KEY = "wp_pending_query";
const SELECTED_STATE_KEY = "wp_selected_state";

/**
 * The authenticated search screen — AgentGuide/02_ApplicationFlow.md §3.3,
 * all 7 states (route loading is search/loading.tsx). Core product feature.
 */
export default function SearchPage() {
  const [deepSearch, setDeepSearch] = useState(false);
  // State Selector, Step 7/8 — real client-requested feature.
  //
  // Real hydration-mismatch bug found and fixed during Step 8's own live
  // testing (browser console + dev server both surfaced it immediately):
  // the first attempt read localStorage inside the useState lazy
  // initializer, same pattern as `prefill` below — but that pattern is
  // only SSR-safe when the value doesn't change what gets RENDERED
  // differently server vs. client. `prefill` only feeds a text input's
  // value (no visual difference between "" and a prefilled string in
  // the initial paint that matters to hydration), but this feeds which
  // <option> is marked selected in a real <select> — the server always
  // renders with null (nothing in localStorage server-side), so if a
  // real value was already stored client-side, the client's FIRST paint
  // selected a different option than the server's markup, and React
  // correctly flagged the mismatch. Fixed with this project's own
  // already-established pattern for exactly this class of problem (see
  // useOnlineStatus.ts's docstring): render the SSR-safe default (null)
  // on the very first paint always, then correct it in a useEffect
  // immediately after hydration completes — the same "assume X during
  // SSR, correct on the client right after" approach, not a new one.
  const [selectedState, setSelectedStateRaw] = useState<string | null>(null);
  useEffect(() => {
    // Reading localStorage is exactly the "external system" case an
    // effect is for — same pattern as SignupContent.tsx's sessionStorage
    // read (Step 8's actual real fix for the hydration mismatch, see
    // this state's own docstring above).
    const stored = localStorage.getItem(SELECTED_STATE_KEY);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (stored) setSelectedStateRaw(stored);
  }, []);
  const setSelectedState = (value: string | null) => {
    setSelectedStateRaw(value);
    try {
      if (value) {
        localStorage.setItem(SELECTED_STATE_KEY, value);
      } else {
        localStorage.removeItem(SELECTED_STATE_KEY);
      }
    } catch {
      // Storage unavailable (private browsing, quota) — the selection
      // still works for this session via component state, it just won't
      // persist across reloads. Not worth surfacing to the user.
    }
  };
  const [prefill] = useState(() => {
    if (typeof window === "undefined") return "";
    const pending = sessionStorage.getItem(PENDING_QUERY_KEY);
    if (pending) {
      sessionStorage.removeItem(PENDING_QUERY_KEY);
      return pending;
    }
    return "";
  });
  const didAutoSubmit = useRef(false);
  const lastPromptRef = useRef("");
  const stream = useSearchStream();
  const { data: me } = useUser();
  const openUpgradeModal = useUpgradeModalStore((s) => s.open);

  // Auto-submit a query preserved across signup/login or landing redirect.
  useEffect(() => {
    if (didAutoSubmit.current || !prefill) return;
    didAutoSubmit.current = true;
    lastPromptRef.current = prefill;
    stream.submit({ prompt: prefill, deepSearch, state: selectedState });
    // Mount-only handoff — stream/deepSearch/selectedState intentionally excluded.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill]);

  useEffect(() => {
    if (stream.status === "upgrade_required") {
      openUpgradeModal("deep_search");
    }
  }, [stream.status, openUpgradeModal]);

  const handleSubmit = (query: string) => {
    lastPromptRef.current = query;
    stream.submit({ prompt: query, deepSearch, state: selectedState });
  };

  const handleRetry = () => {
    if (lastPromptRef.current) {
      stream.submit({ prompt: lastPromptRef.current, deepSearch, state: selectedState });
    }
  };

  const isBusy = stream.status === "submitting" || stream.status === "streaming";

  return (
    <div className="flex flex-1 flex-col items-center px-6 py-16 sm:py-20">
      <div className="w-full max-w-[760px]">
        <SearchBar
          autoFocus
          initialValue={prefill}
          disabled={isBusy}
          deepSearch={deepSearch}
          onDeepSearchChange={setDeepSearch}
          selectedState={selectedState}
          onStateChange={setSelectedState}
          onSubmit={handleSubmit}
        />
        <AnswerPanel
          text={stream.text}
          status={stream.status}
          errorMessage={stream.errorMessage}
          retryAfterSeconds={stream.retryAfterSeconds}
          tier={me?.tier}
          onRetry={handleRetry}
          memorySnippets={stream.memorySnippets}
          sources={stream.sources}
        />
      </div>
    </div>
  );
}
