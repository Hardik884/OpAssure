"use client";

/**
 * Safety overview. Reuses the same SafetyStatus component and useSafety hook
 * as Active Task (no duplicated safety logic) plus a short recent-incidents
 * list. The persistent Safety strip embedded in Active Task remains the
 * primary, real-time-updated view while a task is running — this page is a
 * reachable standalone summary, not a second source of truth.
 */
import { SafetyStatus } from "@/components/safety/SafetyStatus";
import { Card, Empty, ErrorNote, PageContainer, PageTitle, SectionHeader } from "@/components/common/ui";
import { useRecentIncidents } from "@/hooks/useRecentIncidents";
import { useSafety } from "@/hooks/useSafety";

export default function SafetyPage() {
  const { events, loading: safetyLoading, error: safetyError } = useSafety();
  const { incidents, loading: incidentsLoading } = useRecentIncidents();

  return (
    <PageContainer>
      <PageTitle title="Safety" />

      {safetyError && <ErrorNote>{safetyError}</ErrorNote>}

      <div className="grid gap-4 lg:grid-cols-2">
        {safetyLoading ? (
          <Card>
            <Empty>Loading safety status…</Empty>
          </Card>
        ) : (
          <SafetyStatus events={events} />
        )}

        <Card>
          <SectionHeader title="Recent incidents" />
          {incidentsLoading ? (
            <Empty>Loading…</Empty>
          ) : incidents.length === 0 ? (
            <Empty>No incidents reported today.</Empty>
          ) : (
            <ul className="space-y-3">
              {incidents.map((incident) => (
                <li key={incident.id} className="border-b border-border pb-3 last:border-0 last:pb-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">
                    {incident.eventType} · {new Date(incident.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                  <p className="text-sm font-medium text-foreground">{incident.note}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </PageContainer>
  );
}
