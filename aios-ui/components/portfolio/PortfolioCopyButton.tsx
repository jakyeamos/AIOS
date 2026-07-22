"use client";

import { useState } from "react";

type PortfolioCopyButtonProps = {
  text: string;
};

type CopyState = "idle" | "copied" | "failed";

export function PortfolioCopyButton({ text }: PortfolioCopyButtonProps): React.JSX.Element {
  const [state, setState] = useState<CopyState>("idle");

  const copyUpdate = async (): Promise<void> => {
    if (!navigator.clipboard) {
      setState("failed");
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
  };

  const label = state === "copied" ? "Copied" : state === "failed" ? "Copy unavailable" : "Copy update";

  return (
    <button type="button" className="button-primary" onClick={() => void copyUpdate()}>
      {label}
    </button>
  );
}
