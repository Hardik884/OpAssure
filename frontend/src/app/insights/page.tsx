import { Card, Empty, PageContainer, SectionHeader } from "@/components/common/ui";

/**
 * Placeholder route — establishes the page + navigation entry so it is
 * discoverable now. The Insights feature itself is built in a later prompt.
 */
export default function InsightsPage() {
  return (
    <PageContainer>
      <SectionHeader title="Insights" />
      <Card>
        <Empty>Operator Twin habits and performance history will appear here.</Empty>
      </Card>
    </PageContainer>
  );
}
