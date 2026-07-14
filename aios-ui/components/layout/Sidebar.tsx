"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PRIMARY_NAV, SECONDARY_NAV } from "@/lib/constants";

export function Sidebar(): React.JSX.Element {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-title">AIOS</div>
      <nav aria-label="Primary">
        <ul className="sidebar-nav">
          {PRIMARY_NAV.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={active ? "sidebar-link sidebar-link-active" : "sidebar-link"}
                  aria-current={active ? "page" : undefined}
                >
                  <span className="sidebar-label-full">{item.label}</span>
                  <span className="sidebar-label-short">{item.short}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <details className="sidebar-more">
        <summary>More surfaces</summary>
        <nav aria-label="Contextual surfaces">
          <ul className="sidebar-nav sidebar-nav-secondary">
            {SECONDARY_NAV.map((item) => {
              const active = pathname.startsWith(item.href);

              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={active ? "sidebar-link sidebar-link-active" : "sidebar-link"}
                    aria-current={active ? "page" : undefined}
                  >
                    <span className="sidebar-label-full">{item.label}</span>
                    <span className="sidebar-label-short">{item.short}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </details>
    </aside>
  );
}
