import { Card, Empty, PageContainer, SectionHeader } from "@/components/common/ui";

/**
 * Placeholder route — establishes the page + navigation entry so it is
 * discoverable now. The Mission Board feature itself is built in a later prompt.
 */
export default function MissionPage() {
  return (
    <PageContainer>
      <SectionHeader title="Mission Board" />
      <Card>
        <Empty>Today&apos;s tasks, weather and machine context will appear here.</Empty>
      </Card>
    </PageContainer>
  );
}
