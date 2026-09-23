import { Card, Empty, PageContainer, SectionHeader } from "@/components/common/ui";

/**
 * Placeholder route — establishes the page + navigation entry so it is
 * discoverable now. The Safety feature itself is built in a later prompt.
 */
export default function SafetyPage() {
  return (
    <PageContainer>
      <SectionHeader title="Safety" />
      <Card>
        <Empty>Seatbelt, proximity and idle alerts will appear here.</Empty>
      </Card>
    </PageContainer>
  );
}
