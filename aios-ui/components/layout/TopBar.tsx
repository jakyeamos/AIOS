import Link from "next/link";

import { APP_TITLE } from "@/lib/constants";

export function TopBar(): React.JSX.Element {
  return (
    <header className="topbar">
      <div>
        <p className="topbar-eyebrow">System Monitor / Control Plane / Workflow Debugger</p>
        <h1 className="topbar-title">{APP_TITLE}</h1>
        <div className="chip-row">
          <Link className="button-secondary" href="/">
            Open command center
          </Link>
          <Link className="button-secondary" href="/control">
            Open control plane
          </Link>
          <Link className="button-secondary" href="/feedback">
            Review alignment
          </Link>
          <Link className="button-secondary" href="/query">
            Grounded inspect
          </Link>
        </div>
      </div>
    </header>
  );
}
