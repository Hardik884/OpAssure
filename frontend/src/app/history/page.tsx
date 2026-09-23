import { Card, Empty, PageContainer, SectionHeader } from "@/components/common/ui";

/**
 * Placeholder route — establishes the page + navigation entry so it is
 * discoverable now. The History feature itself is built in a later prompt.
 */
export default function HistoryPage() {
  return (
    <PageContainer>
      <SectionHeader title="History" />
      <Card>
        <Empty>Past shifts and completed tasks will appear here.</Empty>
      </Card>
    </PageContainer>
  );
}
