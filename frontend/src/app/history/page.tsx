"use client";

/** Today's completed activity — operational and glanceable, not an analytics dashboard. */
import { HistoryEntryCard } from "@/components/history/HistoryEntryCard";
import { Card, Empty, ErrorNote, PageContainer, PageTitle, SectionHeader } from "@/components/common/ui";
import { useTaskHistory } from "@/hooks/useTaskHistory";

export default function HistoryPage() {
  const { entries, loading, error } = useTaskHistory();

  return (
    <PageContainer>
      <PageTitle title="History" />

      <SectionHeader title="Today's activity" />

      {error && <ErrorNote>{error}</ErrorNote>}

      {loading ? (
        <Card>
          <Empty>Loading today&apos;s activity…</Empty>
        </Card>
      ) : entries.length === 0 ? (
        <Card>
          <Empty>No completed activity yet today.</Empty>
        </Card>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <HistoryEntryCard key={entry.taskId} entry={entry} />
          ))}
        </div>
      )}
    </PageContainer>
  );
}
