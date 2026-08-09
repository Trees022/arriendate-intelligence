interface StatePanelProps {
  title: string;
  message: string;
  tone?: "neutral" | "error";
}

export function StatePanel({ title, message, tone = "neutral" }: StatePanelProps) {
  return (
    <div className={`state-panel state-panel--${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span className="state-panel__mark" aria-hidden="true">
        {tone === "error" ? "!" : "·"}
      </span>
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}
