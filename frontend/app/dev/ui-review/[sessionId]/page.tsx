"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Auth0Provider } from "@auth0/nextjs-auth0";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Search from "@/app/(protected)/search/page";
import History from "@/app/(protected)/history/page";
import Account from "@/app/account/page";
import Memory from "@/app/(protected)/account/memory/page";
import Billing from "@/app/(protected)/account/billing/page";
import Upgrade from "@/app/(protected)/upgrade/page";
import Session from "@/app/(protected)/search/[sessionId]/page";
import { WorkspaceNav } from "@/components/layout/WorkspaceNav";
const views = { search: Search, history: History, account: Account, memory: Memory, billing: Billing, upgrade: Upgrade, session: Session };
/**
 * Navbar's auth state comes from useUser() (@auth0/nextjs-auth0), which
 * always does a real fetch("/auth/profile") on mount — it ignores
 * Auth0Provider's `user` prop entirely (that prop only seeds SSR; this
 * fixture is client-only). That fetch always loses the race against a
 * client-side patch (a useEffect here would run after SWR's mount-time
 * fetch already fired), so Navbar renders logged-out here regardless.
 * That's a fixture-only cosmetic gap, not a real app bug — a live
 * session makes Navbar + WorkspaceNav render as the intended two-tier
 * brand-nav + workspace-nav layout. To screenshot this route with an
 * accurate logged-in Navbar, intercept the request at the network layer
 * (page.setRequestInterception in Puppeteer, or a service worker) rather
 * than patching window.fetch from inside the page — see
 * scripts/_capture_protected.mjs-style callers for the working pattern.
 */
export default function UIReview() {
 const params=useSearchParams();
 const [client]=useState(()=>{
  const q=new QueryClient({defaultOptions:{queries:{staleTime:Infinity,retry:false,refetchOnWindowFocus:false}}});
  const now=new Date().toISOString();
  q.setQueryData(["me"],{id:"fixture",email:"review@example.com",tier:"free"});
  q.setQueryData(["search-history"],[{id:"fixture",title:"A long question about local public safety records and case updates in the community",createdAt:now,isDeepSearch:true,hasSources:true}]);
  q.setQueryData(["memory-notes"],[{id:"fixture",content:"I research local public safety. Reference: "+"longreference".repeat(12),createdAt:now,updatedAt:now}]);
  q.setQueryData(["search-session","fixture"],{id:"fixture",title:"Understanding local public safety records",messages:[{id:"q",role:"user",content:"How can I find official records?",memorySnippets:[],sources:[]},{id:"a",role:"assistant",content:"This is a layout test answer. "+"LongReference".repeat(40),memorySnippets:[],sources:[]}]});
  return q;
 });
 const View=views[(params.get("view")??"search") as keyof typeof views]??Search;
 if(process.env.NODE_ENV!=="development") return null;
 return <Auth0Provider user={{sub:"fixture",name:"Layout Review",email:"review@example.com"}}><QueryClientProvider client={client}><WorkspaceNav/><View/></QueryClientProvider></Auth0Provider>;
}
