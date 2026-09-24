"use client";

/**
 * The operator's "today" screen — not a management dashboard. Shows the
 * mission list through the existing centralized mock/API layer (lib/api.ts),
 * gates starting the primary task behind a Pre-Task Threat Briefing, then
 * hands off to /task (Active Task).
 */
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { useOperatorContext } from "@/components/layout/OperatorProvider";
import { api } from "@/lib/api";
import { getGreeting } from "@/lib/format";
import { useMissionTasks } from "@/hooks/useMissionTasks";
import type { MissionTask, ThreatBriefingItem } from "@/types";

import { Modal } from "../common/Modal";
import { Card, Empty, ErrorNote, PageContainer, PageTitle } from "../common/ui";
import { TaskCard } from "./TaskCard";
import { ThreatBriefing } from "./ThreatBriefing";

export function MissionBoard() {
  const { context } = useOperatorContext();
  const { tasks, loading, error } = useMissionTasks();
  const router = useRouter();

  const [briefingTask, setBriefingTask] = useState<MissionTask | null>(null);
  // null = still loading (distinct from a genuinely empty briefing) so the modal
  // never flashes "clear to start" before the facts have actually arrived.
  const [briefingItems, setBriefingItems] = useState<ThreatBriefingItem[] | null>(null);
  const [viewTask, setViewTask] = useState<MissionTask | null>(null);

  const openBriefing = useCallback((task: MissionTask) => {
    setBriefingTask(task);
    setBriefingItems(null);
    api.getThreatBriefing(task.taskId).then(setBriefingItems).catch(() => setBriefingItems([]));
  }, []);

  const acknowledgeAndStart = () => {
    setBriefingTask(null);
    router.push("/task");
  };

  const [primary, ...rest] = tasks;

  return (
    <PageContainer>
      <PageTitle eyebrow={`${getGreeting()}, ${context.operator.name}`} title="Today's Mission" />

      {error ? (
        <ErrorNote>{error}</ErrorNote>
      ) : loading ? (
        <Card>
          <Empty>Loading today&apos;s mission…</Empty>
        </Card>
      ) : tasks.length === 0 ? (
        <Card>
          <Empty>No tasks scheduled today.</Empty>
        </Card>
      ) : (
        <div className="space-y-4">
          {primary && <TaskCard task={primary} variant="primary" onStart={() => openBriefing(primary)} />}
          {rest.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2">
              {rest.map((task) => (
                <TaskCard key={task.taskId} task={task} variant="secondary" onView={() => setViewTask(task)} />
              ))}
            </div>
          )}
        </div>
      )}

      {briefingTask && (
        <Modal title="Pre-Task Threat Briefing" dismissible={false}>
          <ThreatBriefing
            task={briefingTask}
            items={briefingItems}
            onAcknowledge={acknowledgeAndStart}
            onCancel={() => setBriefingTask(null)}
          />
        </Modal>
      )}

      {viewTask && (
        <Modal title={viewTask.taskId} onClose={() => setViewTask(null)}>
          <TaskDetail task={viewTask} />
        </Modal>
      )}
    </PageContainer>
  );
}

/** Read-only summary for the Mission Board's "View" action — no start/incident actions here. */
function TaskDetail({ task }: { task: MissionTask }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
      <Row label="Task type" value={task.taskType} />
      <Row label="Start time" value={task.startTime} />
      <Row label="Zone" value={`Zone ${task.zone}`} />
      <Row label="Weather" value={task.weather} />
      <Row
        label={task.etaMin === task.etaMax ? "Plan ETA" : "ETA range"}
        value={task.etaMin === task.etaMax ? `${task.etaMin} min` : `${task.etaMin}–${task.etaMax} min`}
      />
      <Row label="Plan estimate" value={`${task.originalEta} min`} />
      <Row label="Buckets remaining" value={String(task.bucketsRemaining)} />
      <Row label="Risk level" value={task.riskLevel[0].toUpperCase() + task.riskLevel.slice(1)} />
    </dl>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">{label}</dt>
      <dd className="font-semibold text-foreground">{value}</dd>
    </div>
  );
}
