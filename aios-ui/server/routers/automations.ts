import { seededAutomations } from "@/lib/seed";
import type { AutomationHealth } from "@/lib/types";
import { trustedSignal } from "@/lib/trusted-signals";
import { createTRPCRouter, publicProcedure } from "@/server/trpc";

const dayNames: Record<string, string> = {
  MO: "Mon",
  TU: "Tue",
  WE: "Wed",
  TH: "Thu",
  FR: "Fri",
  SA: "Sat",
  SU: "Sun",
};

const parseRrule = (trigger: string): Record<string, string> => {
  const entries = trigger
    .split(";")
    .map((part) => part.split("="))
    .filter((part): part is [string, string] => part.length === 2 && part[0].length > 0);
  return Object.fromEntries(entries);
};

const formatHour = (hour: string | undefined, minute: string | undefined): string => {
  const parsedHour = Number(hour ?? "0");
  const parsedMinute = Number(minute ?? "0");
  if (!Number.isInteger(parsedHour) || !Number.isInteger(parsedMinute)) {
    return "unknown time";
  }
  const suffix = parsedHour >= 12 ? "PM" : "AM";
  const displayHour = parsedHour % 12 === 0 ? 12 : parsedHour % 12;
  return `${displayHour}:${parsedMinute.toString().padStart(2, "0")} ${suffix}`;
};

const formatTrigger = (trigger: string): string => {
  const rule = parseRrule(trigger);
  const days = (rule.BYDAY ?? "").split(",").filter((day) => day.length > 0);
  const time = formatHour(rule.BYHOUR, rule.BYMINUTE);

  if (days.length === 5 && days.every((day) => ["MO", "TU", "WE", "TH", "FR"].includes(day))) {
    return `Weekdays at ${time}`;
  }
  if (days.length === 7) {
    return `Daily at ${time}`;
  }
  if (days.length > 0) {
    return `${days.map((day) => dayNames[day] ?? day).join(", ")} at ${time}`;
  }
  return trigger;
};

const enrichAutomation = (automation: AutomationHealth): AutomationHealth => {
  const triggerLabel = formatTrigger(automation.trigger);
  return {
    ...automation,
    triggerLabel,
    triggerSignal: trustedSignal({
      value: triggerLabel,
      provenance: triggerLabel === automation.trigger ? "missing" : "inferred",
      confidence: triggerLabel === automation.trigger ? 0.3 : 0.8,
      source: { label: "Automation trigger", field: "trigger" },
      freshness: "seeded",
      explanation: triggerLabel === automation.trigger
        ? "Trigger is not recognized as a supported RRULE shape."
        : "Readable schedule is inferred from the persisted RRULE trigger.",
      missingReason: triggerLabel === automation.trigger ? "Unsupported trigger format." : null,
      contradiction: null,
    }),
    successRateSignal: trustedSignal({
      value: automation.successRate,
      provenance: "inferred",
      confidence: 0.7,
      source: { label: "Seeded automation health", field: "successRate" },
      freshness: "seeded",
      explanation: "Success rate is seeded until durable automation run history is available.",
      missingReason: null,
      contradiction: null,
    }),
    statusSignal: trustedSignal({
      value: automation.status,
      provenance: "inferred",
      confidence: 0.7,
      source: { label: "Seeded automation health", field: "status" },
      freshness: "seeded",
      explanation: "Status is seeded until durable automation run history is available.",
      missingReason: null,
      contradiction: null,
    }),
  };
};

export const automationsRouter = createTRPCRouter({
  list: publicProcedure.query((): AutomationHealth[] => seededAutomations.map(enrichAutomation)),
});
