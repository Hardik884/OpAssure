"use client";

/**
 * Insights — Operator Twin, Habit Radar, Focus. NOT a management analytics
 * dashboard: no charts, no dense tables, no filtering. Glanceable cards only.
 */
import { FocusCard } from "@/components/insights/FocusCard";
import { HabitRadarCard } from "@/components/insights/HabitRadarCard";
import { OperatorTwinCard } from "@/components/insights/OperatorTwinCard";
import { Card, Empty, ErrorNote, PageContainer } from "@/components/common/ui";
import { useInsights } from "@/hooks/useInsights";

export default function InsightsPage() {
  const { twin, habits, focus, loading, error } = useInsights();

  return (
    <PageContainer>
      <h1 className="mb-4 text-2xl font-black uppercase tracking-tight text-foreground sm:text-3xl">Insights</h1>

      {error && <ErrorNote>{error}</ErrorNote>}

      {loading ? (
        <Card>
          <Empty>Loading insights…</Empty>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {twin && <OperatorTwinCard twin={twin} />}
          <HabitRadarCard habits={habits} />
          <FocusCard items={focus} />
        </div>
      )}
    </PageContainer>
  );
}
