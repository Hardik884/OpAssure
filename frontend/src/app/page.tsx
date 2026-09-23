"use client";

import { useOperatorContext } from "@/components/layout/OperatorProvider";
import { Card, ErrorNote, MetricDisplay, PageContainer, SectionHeader, StatusBadge } from "@/components/common/ui";

/**
 * Shell landing view: a one-glance snapshot of who/what/current task/safety
 * state. Not the Mission Board (task list, zone detail, live controls) —
 * that's later work; this page exists to prove the operator context and
 * shell render correctly end to end.
 */
export default function HomePage() {
  const { context, error } = useOperatorContext();
  const { operator, machine, currentTask, safetyStatus } = context;

  return (
    <PageContainer>
      <SectionHeader title="Shift overview" action={<StatusBadge status={safetyStatus} />} />

      {error && <ErrorNote>{error} — showing last known data.</ErrorNote>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <MetricDisplay label="Operator" value={operator.name} />
          <p className="mt-1 text-sm font-semibold text-line-500">
            {operator.operatorId} · {operator.skill}
          </p>
        </Card>

        <Card>
          <MetricDisplay label="Machine" value={machine.machineId} />
          <p className="mt-1 text-sm font-semibold text-line-500">
            {machine.model} · {machine.type}
          </p>
        </Card>

        <Card>
          {currentTask ? (
            <>
              <MetricDisplay label="Current task" value={currentTask.taskId} />
              <p className="mt-1 text-sm font-semibold text-line-500">
                {currentTask.taskType.replace(/_/g, " ")} · Zone {currentTask.zone}
              </p>
            </>
          ) : (
            <>
              <div className="text-xs font-bold uppercase tracking-widest text-ink-600">Current task</div>
              <p className="mt-1 text-sm font-semibold text-line-500">No task assigned.</p>
            </>
          )}
        </Card>
      </div>
    </PageContainer>
  );
}
