import { notFound } from "next/navigation";

// Internal QA fixtures (theme swatches, UI review harness) — dev only.
export default function DevLayout({ children }: { children: React.ReactNode }) {
  if (process.env.NODE_ENV === "production") notFound();
  return children;
}
