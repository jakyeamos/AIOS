import Link from "next/link";

import { APP_TITLE } from "@/lib/constants";

export function TopBar(): React.JSX.Element {
  return (
    <header className="topbar">
      <div>
        <p className="topbar-eyebrow">Knowledge OS / Workflow OS / Control Plane</p>
        <h1 className="topbar-title">{APP_TITLE}</h1>
        <div className="chip-row">
          <Link className="button-secondary" href="/knowledge">
            Browse knowledge
          </Link>
          <Link className="button-secondary" href="/control">
            Open control plane
          </Link>
          <Link className="button-secondary" href="/query">
            Ask grounded query
          </Link>
        </div>
      </div>
    </header>
  );
}
