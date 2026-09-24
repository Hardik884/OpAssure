/** Shown after an incident is saved — shared by the full form and the quick-report actions. */
import { CheckIcon } from "../common/icons";
import { Button } from "../common/ui";

interface IncidentConfirmationProps {
  onReturn: () => void;
}

export function IncidentConfirmation({ onReturn }: IncidentConfirmationProps) {
  return (
    <div className="animate-rise-in text-center" data-testid="incident-confirmation">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-status-safe-bg text-status-safe-fg" aria-hidden>
        <CheckIcon className="h-8 w-8" />
      </div>
      <h3 className="mt-3 font-display text-xl font-semibold tracking-tight text-foreground">Event recorded</h3>
      <p className="mt-1 text-sm font-medium text-foreground-muted">Telemetry context attached.</p>
      <Button variant="primary" className="mt-5 w-full" onClick={onReturn}>
        Return to Active Task
      </Button>
    </div>
  );
}
