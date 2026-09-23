"use client";

/** Fast, practical incident report — event type + a note, nothing more. */
import { useState } from "react";

import type { IncidentEventType } from "@/types";

import { Button } from "../common/ui";

const EVENT_TYPES: { value: IncidentEventType; label: string }[] = [
  { value: "proximity", label: "Proximity" },
  { value: "seatbelt", label: "Seatbelt" },
  { value: "machine", label: "Machine" },
  { value: "ground", label: "Ground" },
  { value: "other", label: "Other" },
];

interface IncidentFormProps {
  defaultEventType?: IncidentEventType;
  submitting: boolean;
  onSubmit: (eventType: IncidentEventType, note: string) => void;
  onCancel: () => void;
}

export function IncidentForm({ defaultEventType = "other", submitting, onSubmit, onCancel }: IncidentFormProps) {
  const [eventType, setEventType] = useState<IncidentEventType>(defaultEventType);
  const [note, setNote] = useState("");

  return (
    <form
      data-testid="incident-form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(eventType, note.trim());
      }}
    >
      <label className="mb-1 block text-xs font-bold uppercase tracking-widest text-foreground-muted" htmlFor="incident-event-type">
        Event Type
      </label>
      <select
        id="incident-event-type"
        value={eventType}
        onChange={(e) => setEventType(e.target.value as IncidentEventType)}
        className="mb-4 min-h-12 w-full rounded-industrial border-2 border-border bg-surface px-3 text-base font-semibold text-foreground"
      >
        {EVENT_TYPES.map(({ value, label }) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>

      <label className="mb-1 block text-xs font-bold uppercase tracking-widest text-foreground-muted" htmlFor="incident-note">
        Note
      </label>
      <textarea
        id="incident-note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={3}
        placeholder="What happened?"
        className="mb-4 w-full rounded-industrial border-2 border-border bg-surface p-3 text-base text-foreground placeholder:text-foreground-muted"
      />

      <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
        {submitting ? "Saving…" : "Save / Record Event"}
      </Button>
      <button
        type="button"
        onClick={onCancel}
        disabled={submitting}
        className="mt-3 min-h-11 w-full text-center text-sm font-bold uppercase tracking-wide text-foreground-muted underline hover:text-foreground disabled:opacity-40"
      >
        Cancel
      </button>
    </form>
  );
}
