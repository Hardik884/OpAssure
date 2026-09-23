import { Card, Empty, PageContainer, SectionHeader } from "@/components/common/ui";

/**
 * Placeholder route — establishes the page + navigation entry so it is
 * discoverable now. The Active Task feature itself is built in a later prompt.
 */
export default function TaskPage() {
  return (
    <PageContainer>
      <SectionHeader title="Active Task" />
      <Card>
        <Empty>Live telemetry, ETA and task progress for the current task will appear here.</Empty>
      </Card>
    </PageContainer>
  );
}
