export type NavItem = {
  href: string;
  label: string;
};

export const PRIMARY_NAV: NavItem[] = [
  { href: "/", label: "Command Center" },
  { href: "/runs", label: "Run Inspector" },
  { href: "/workflows", label: "Workflows" },
  { href: "/prompts", label: "Prompts & Rules" },
  { href: "/costs", label: "Efficiency" },
  { href: "/automations", label: "Automations" },
  { href: "/projects", label: "Projects" },
  { href: "/feedback", label: "Alignment" },
  { href: "/compare", label: "Diff & Compare" },
  { href: "/settings", label: "Settings" },
];

export const APP_TITLE = "AIOS Command";
