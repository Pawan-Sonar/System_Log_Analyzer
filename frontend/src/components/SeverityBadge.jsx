import React from "react";

const SEV = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
};

export default function SeverityBadge({ severity, children }) {
  const s = (severity || "low").toLowerCase();
  return (
    <span className={`badge-sev ${SEV[s] || SEV.low}`} data-testid={`sev-${s}`}>
      {children || s}
    </span>
  );
}
