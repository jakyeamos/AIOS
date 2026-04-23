export type NavItem = {
  href: string;
  label: string;
};

export const PRIMARY_NAV: NavItem[] = [
  { href: "/", label: "Command Center" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/projects", label: "Projects" },
  { href: "/control", label: "Control Plane" },
  { href: "/query", label: "Grounded Query" },
  { href: "/runs", label: "Runs" },
  { href: "/prompts", label: "Prompts & Rules" },
  { href: "/workflows", label: "Workflows" },
  { href: "/compare", label: "Experiments" },
  { href: "/feedback", label: "Alignment" },
  { href: "/costs", label: "Efficiency" },
  { href: "/automations", label: "Automations" },
  { href: "/settings", label: "Settings" },
];

export const APP_TITLE = "AIOS Command Center";
