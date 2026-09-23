/** Shown after an incident is saved — shared by the full form and the quick-report actions. */
import { Button } from "../common/ui";

interface IncidentConfirmationProps {
  onReturn: () => void;
}

export function IncidentConfirmation({ onReturn }: IncidentConfirmationProps) {
  return (
    <div className="text-center" data-testid="incident-confirmation">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-safe-bg text-4xl" aria-hidden>
        ✓
      </div>
      <h3 className="mt-3 text-xl font-black uppercase tracking-wide text-ink-950">Event Recorded</h3>
      <p className="mt-1 text-sm font-semibold text-line-600">Telemetry context attached.</p>
      <Button variant="primary" className="mt-5 w-full" onClick={onReturn}>
        Return to Active Task
      </Button>
    </div>
  );
}
