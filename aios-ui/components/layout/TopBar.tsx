import { APP_TITLE } from "@/lib/constants";

export function TopBar(): React.JSX.Element {
  return (
    <header className="topbar">
      <div>
        <p className="topbar-eyebrow">Operator View</p>
        <h1 className="topbar-title">{APP_TITLE}</h1>
      </div>
    </header>
  );
}
