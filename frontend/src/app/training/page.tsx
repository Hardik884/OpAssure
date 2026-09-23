import { Card, Empty, PageContainer, SectionHeader } from "@/components/common/ui";

/**
 * Placeholder route — establishes the page + navigation entry so it is
 * discoverable now. The Training feature itself is built in a later prompt.
 */
export default function TrainingPage() {
  return (
    <PageContainer>
      <SectionHeader title="Training" />
      <Card>
        <Empty>Just-in-time training recommendations will appear here.</Empty>
      </Card>
    </PageContainer>
  );
}
