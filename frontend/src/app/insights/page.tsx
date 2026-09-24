"use client";

/**
 * Insights — the Athlete Card (Operator Twin as a stat card, not a plain
 * metrics grid), Habit Radar, Focus, and Proven Impact (measured before/after
 * training results). NOT a management analytics dashboard: no charts, no
 * dense tables, no filtering. Glanceable cards only.
 */
import { AthleteCard } from "@/components/insights/AthleteCard";
import { FocusCard } from "@/components/insights/FocusCard";
import { HabitRadarCard } from "@/components/insights/HabitRadarCard";
import { TrainingImpactCard } from "@/components/insights/TrainingImpactCard";
import { Card, Empty, ErrorNote, PageContainer } from "@/components/common/ui";
import { useAthleteProfile } from "@/hooks/useAthleteProfile";
import { useInsights } from "@/hooks/useInsights";
import { useTrainingImpact } from "@/hooks/useTrainingImpact";

export default function InsightsPage() {
  const { profile, loading: profileLoading, error: profileError } = useAthleteProfile();
  const { habits, focus, loading: insightsLoading, error: insightsError } = useInsights();
  const { cases, loading: impactLoading } = useTrainingImpact();

  const loading = profileLoading || insightsLoading;
  const error = profileError ?? insightsError;

  return (
    <PageContainer>
      <h1 className="mb-4 text-2xl font-black uppercase tracking-tight text-foreground sm:text-3xl">Insights</h1>

      {error && <ErrorNote>{error}</ErrorNote>}

      {loading ? (
        <Card>
          <Empty>Loading insights…</Empty>
        </Card>
      ) : (
        <div className="space-y-4">
          {profile && <AthleteCard profile={profile} />}

          <div className="grid gap-4 lg:grid-cols-2">
            <HabitRadarCard habits={habits} />
            <FocusCard items={focus} />
          </div>

          {!impactLoading && <TrainingImpactCard cases={cases} />}
        </div>
      )}
    </PageContainer>
  );
}
