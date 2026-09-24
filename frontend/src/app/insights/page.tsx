"use client";

/**
 * Insights — Operator Twin, Habit Radar, Focus. NOT a management analytics
 * dashboard: no charts, no dense tables, no filtering. Glanceable cards only.
 */
import { FocusCard } from "@/components/insights/FocusCard";
import { HabitRadarCard } from "@/components/insights/HabitRadarCard";
import { OperatorTwinCard } from "@/components/insights/OperatorTwinCard";
import { Card, Empty, ErrorNote, PageContainer, PageTitle } from "@/components/common/ui";
import { useInsights } from "@/hooks/useInsights";

export default function InsightsPage() {
  const { twin, habits, focus, loading, error } = useInsights();

  return (
    <PageContainer>
      <PageTitle title="Insights" />

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
