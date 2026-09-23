"use client";

/**
 * The incident flow, in two modes, both recording through the centralized api
 * layer (lib/api.ts) — nothing to rewrite when POST /incidents is wired in:
 *   - full form (Report Issue): operator picks an event type and writes a note.
 *   - quick report (Hit Rock / Ground Wet): pre-filled, records immediately.
 * Both land on the same confirmation.
 */
import { useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { Incident, IncidentEventType } from "@/types";

import { Modal } from "../common/Modal";
import { Empty, ErrorNote } from "../common/ui";
import { IncidentConfirmation } from "./IncidentConfirmation";
import { IncidentForm } from "./IncidentForm";

interface IncidentModalProps {
  operatorId: string;
  machineId: string;
  taskId: string;
  defaultEventType?: IncidentEventType;
  /** When set, skips the form and records this immediately (Hit Rock / Ground Wet). */
  quickReport?: { eventType: IncidentEventType; note: string };
  onClose: () => void;
}

export function IncidentModal({ operatorId, machineId, taskId, defaultEventType, quickReport, onClose }: IncidentModalProps) {
  const [submitting, setSubmitting] = useState(Boolean(quickReport));
  const [error, setError] = useState<string | null>(null);
  const [recorded, setRecorded] = useState<Incident | null>(null);
  const started = useRef(false);

  const record = (eventType: IncidentEventType, note: string) => {
    setSubmitting(true);
    setError(null);
    api
      .recordIncident({ eventType, note, taskId, operatorId, machineId })
      .then(setRecorded)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setSubmitting(false));
  };

  useEffect(() => {
    if (quickReport && !started.current) {
      started.current = true;
      record(quickReport.eventType, quickReport.note);
    }
    // record() is stable for this component's lifetime (closes over its own props/state setters);
    // only re-run if the quick-report payload itself changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quickReport]);

  return (
    <Modal title={recorded ? undefined : "Report Issue"} onClose={submitting ? undefined : onClose}>
      {recorded ? (
        <IncidentConfirmation onReturn={onClose} />
      ) : error ? (
        <ErrorNote>{error}</ErrorNote>
      ) : quickReport ? (
        <Empty>Saving…</Empty>
      ) : (
        <IncidentForm defaultEventType={defaultEventType} submitting={submitting} onSubmit={record} onCancel={onClose} />
      )}
    </Modal>
  );
}
