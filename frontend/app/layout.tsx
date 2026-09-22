import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { Footer } from "@/components/layout/Footer";
import { Navbar } from "@/components/layout/Navbar";
import { Providers } from "@/providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  // Display/hero headline only — AgentGuide/01_ThemeGuideline.md §2. Never body copy.
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "WhyPolice",
  description: "A public forum for police interactions and local incidents. Post, get real replies, connect with a verified attorney.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col bg-bg text-text-primary">
        <Providers>
          <a href="#main-content" className="wp-skip-link">Skip to content</a>
          <Navbar />
          <main id="main-content" tabIndex={-1} className="flex min-w-0 flex-1 flex-col outline-none">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
