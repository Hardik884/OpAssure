"use client";

/**
 * Training Hub — recommended-for-you, the training library, and mock
 * instructor booking. All data flows through lib/api.ts; nothing here
 * calculates a recommendation.
 */
import { InstructorBooking } from "@/components/training/InstructorBooking";
import { TrainingLibraryCard } from "@/components/training/TrainingLibraryCard";
import { TrainingRecommendationCard } from "@/components/training/TrainingRecommendationCard";
import { useTrainingLibrary } from "@/hooks/useTrainingLibrary";
import { useTrainingRecommendation } from "@/hooks/useTrainingRecommendation";

import { Card, Empty, ErrorNote, PageContainer, PageTitle, SectionHeader } from "@/components/common/ui";

export default function TrainingPage() {
  const { recommendation, loading: recommendationLoading } = useTrainingRecommendation();
  const { clips, slots, loading: libraryLoading, error } = useTrainingLibrary();

  return (
    <PageContainer>
      <PageTitle title="Training" />

      {error && <ErrorNote>{error}</ErrorNote>}

      <section className="mb-6">
        <SectionHeader title="Recommended for you" />
        {recommendationLoading ? (
          <Card>
            <Empty>Loading recommendation…</Empty>
          </Card>
        ) : recommendation ? (
          <TrainingRecommendationCard recommendation={recommendation} dismissible={false} />
        ) : (
          <Card>
            <Empty>No recommendation right now — nice work.</Empty>
          </Card>
        )}
      </section>

      <section className="mb-6">
        <SectionHeader title="Training library" />
        {libraryLoading ? (
          <Card>
            <Empty>Loading training library…</Empty>
          </Card>
        ) : clips.length === 0 ? (
          <Card>
            <Empty>No training clips available.</Empty>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {clips.map((clip) => (
              <TrainingLibraryCard key={clip.clipId} clip={clip} />
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader title="Instructor / book training" />
        {libraryLoading ? (
          <Card>
            <Empty>Loading instructor availability…</Empty>
          </Card>
        ) : (
          <InstructorBooking slots={slots} />
        )}
      </section>
    </PageContainer>
  );
}
