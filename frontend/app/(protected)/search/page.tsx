"use client";

import { useEffect, useRef, useState } from "react";

import { AnswerPanel } from "@/components/search/AnswerPanel";
import { SearchBar } from "@/components/search/SearchBar";
import { useSearchStream } from "@/hooks/useSearchStream";
import { useUser } from "@/hooks/useUser";
import { useUpgradeModalStore } from "@/stores/useUpgradeModalStore";

const PENDING_QUERY_KEY = "wp_pending_query";

/**
 * The authenticated search screen — AgentGuide/02_ApplicationFlow.md §3.3,
 * all 7 states (route loading is search/loading.tsx). Core product feature.
 */
export default function SearchPage() {
  const [deepSearch, setDeepSearch] = useState(false);
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
    stream.submit({ prompt: prefill, deepSearch });
    // Mount-only handoff — stream/deepSearch intentionally excluded.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill]);

  useEffect(() => {
    if (stream.status === "upgrade_required") {
      openUpgradeModal("deep_search");
    }
  }, [stream.status, openUpgradeModal]);

  const handleSubmit = (query: string) => {
    lastPromptRef.current = query;
    stream.submit({ prompt: query, deepSearch });
  };

  const handleRetry = () => {
    if (lastPromptRef.current) {
      stream.submit({ prompt: lastPromptRef.current, deepSearch });
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
        />
      </div>
    </div>
  );
}
