export type NavItem = {
  href: string;
  label: string;
};

export const PRIMARY_NAV: NavItem[] = [
  { href: "/", label: "Overview" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/projects", label: "Projects" },
  { href: "/control", label: "Control Plane" },
  { href: "/query", label: "Grounded Query" },
  { href: "/runs", label: "Runs" },
  { href: "/prompts", label: "Rules" },
  { href: "/workflows", label: "Workflow Metrics" },
  { href: "/costs", label: "Efficiency" },
  { href: "/automations", label: "Automations" },
  { href: "/settings", label: "Settings" },
];

export const APP_TITLE = "AIOS Knowledge OS";
