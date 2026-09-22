import type { Metadata } from "next";
import { Suspense } from "react";

import { SignupContent } from "@/components/auth/SignupContent";

export const metadata: Metadata = {
  title: "Sign up — WhyPolice",
  description: "Create a free WhyPolice account to post, follow, and reply on the forum.",
  openGraph: {
    title: "Sign up — WhyPolice",
    description: "Create a free WhyPolice account to post, follow, and reply on the forum.",
    type: "website",
  },
};

/**
 * Themed signup page — AgentGuide/02_ApplicationFlow.md §3.2 and
 * AgentGuide/03_MasterPromptGuide.md Step 3. Stays a Server Component (see
 * components/auth/SignupContent.tsx for why) so it can export `metadata` —
 * matches login/page.tsx's split, found missing here during the Step 1-8 audit.
 */
export default function SignupPage() {
  return (
    <Suspense>
      <SignupContent />
    </Suspense>
  );
}
