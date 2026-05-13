export type NavItem = {
  href: string;
  label: string;
  short: string;
};

export const PRIMARY_NAV: NavItem[] = [
  { href: "/", label: "Command Center", short: "Home" },
  { href: "/knowledge", label: "Knowledge", short: "Wiki" },
  { href: "/projects", label: "Projects", short: "Projects" },
  { href: "/control", label: "Control Plane", short: "Control" },
  { href: "/context", label: "Context Compiler", short: "Context" },
  { href: "/runs", label: "Runs", short: "Runs" },
  { href: "/runs/divergent", label: "Strategy Runs", short: "Strategy" },
  { href: "/prompts", label: "Prompts & Rules", short: "Prompts" },
  { href: "/workflows", label: "Workflows", short: "Workflows" },
  { href: "/compare", label: "Experiments", short: "Experiments" },
  { href: "/feedback", label: "Alignment", short: "Alignment" },
  { href: "/costs", label: "Efficiency", short: "Efficiency" },
  { href: "/automations", label: "Automations", short: "Automations" },
  { href: "/settings", label: "Settings", short: "Settings" },
];

export const APP_TITLE = "AIOS Command Center";
