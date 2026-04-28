"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PRIMARY_NAV } from "@/lib/constants";

export function Sidebar(): React.JSX.Element {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-title">AIOS</div>
      <nav>
        <ul className="sidebar-nav">
          {PRIMARY_NAV.map((item) => {
            const activePath = item.activePath ?? item.href.split(/[?#]/, 1)[0];
            const active = activePath === "/" ? pathname === "/" : pathname.startsWith(activePath);

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={active ? "sidebar-link sidebar-link-active" : "sidebar-link"}
                >
                  <span className="sidebar-label-full">{item.label}</span>
                  <span className="sidebar-label-short">{item.short}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
