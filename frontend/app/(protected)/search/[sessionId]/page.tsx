"use client";

import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { AnswerPanel } from "@/components/search/AnswerPanel";
import { ApiError } from "@/lib/api-client";
import { useSessionDetail } from "@/hooks/useSessionDetail";
import { useUser } from "@/hooks/useUser";

const PENDING_QUERY_KEY = "wp_pending_query";

/**
 * Session detail — read-only replay of a past search, AgentGuide
 * §3.4/03_MasterPromptGuide.md Step 6 point 4. Reuses AnswerPanel from
 * Step 5 with status="complete" (no streaming animation needed for
 * already-finished content).
 */
export default function SessionDetailPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const { data: me } = useUser();
  const { data: session, isLoading, isError, error } = useSessionDetail(params.sessionId);

  const isNotFound = isError && error instanceof ApiError && error.status === 404;

  const continueSearch = (prompt: string) => {
    sessionStorage.setItem(PENDING_QUERY_KEY, prompt);
    router.push("/search");
  };

  if (isLoading) {
    return null; // loading.tsx handles the route-level skeleton
  }

  if (isNotFound) {
    return (
      <div className="mx-auto max-w-[760px] px-6 py-20 text-center">
        <p className="text-body text-text-primary">This search couldn&apos;t be found.</p>
        <p className="mt-1 text-body-sm text-text-muted">
          It may have been deleted, or the link may be incorrect.
        </p>
        <Link
          href="/history"
          className="mt-6 inline-block rounded-sm bg-accent px-4 py-2 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Back to history
        </Link>
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="mx-auto max-w-[760px] px-6 py-20 text-center">
        <p className="text-body text-text-primary">Couldn&apos;t load this search right now.</p>
        <Link
          href="/history"
          className="mt-6 inline-block rounded-sm px-4 py-2 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Back to history
        </Link>
      </div>
    );
  }

  const pairs: { key: string; prompt: string; answer: string | null; memorySnippets: string[] }[] = [];
  for (const message of session.messages) {
    if (message.role === "user") {
      pairs.push({ key: message.id, prompt: message.content, answer: null, memorySnippets: [] });
    } else if (pairs.length > 0) {
      pairs[pairs.length - 1].answer = message.content;
      pairs[pairs.length - 1].memorySnippets = message.memorySnippets;
    }
  }

  return (
    <motion.div
      key={session.id}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="mx-auto max-w-[760px] px-6 py-12 sm:py-16"
    >
      <Link
        href="/history"
        className="mb-6 inline-flex items-center gap-1.5 text-body-sm text-text-secondary hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to history
      </Link>

      <h1 className="font-display text-2xl text-text-primary mb-8 leading-snug">
        {session.title || "Untitled search"}
      </h1>

      <div className="flex flex-col gap-10">
        {pairs.map((pair) => (
          <div key={pair.key}>
            <p className="text-body-lg text-text-primary font-medium">{pair.prompt}</p>
            <AnswerPanel
              text={pair.answer ?? ""}
              status={pair.answer !== null ? "complete" : "error"}
              errorMessage={pair.answer === null ? "This answer never finished generating." : null}
              retryAfterSeconds={null}
              tier={me?.tier}
              onRetry={() => continueSearch(pair.prompt)}
              retryLabel="Continue this search"
              memorySnippets={pair.memorySnippets}
            />
          </div>
        ))}
      </div>
    </motion.div>
  );
}
