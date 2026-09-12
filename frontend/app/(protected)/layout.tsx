import { WorkspaceNav } from "@/components/layout/WorkspaceNav";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <><WorkspaceNav />{children}</>;
}
