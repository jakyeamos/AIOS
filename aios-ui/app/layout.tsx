import type { Metadata } from "next";
import { Geist, JetBrains_Mono } from "next/font/google";
import type { ReactNode } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

import { Providers } from "@/app/providers";

import "@/styles/globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AIOS Knowledge OS",
  description: "Knowledge, workflow memory, grounded retrieval, and orchestration control plane for AIOS.",
};

export default function RootLayout({ children }: { children: ReactNode }): React.JSX.Element {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.variable} ${jetbrainsMono.variable}`}>
        <Providers>
          <div className="app-root">
            <Sidebar />
            <main className="main-content">
              <TopBar />
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
