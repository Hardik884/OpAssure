/** Focus — "what should the operator pay attention to right now." An attention aid, not a management ranking. */
import type { FocusItem } from "@/types";

import { Card, SectionHeader } from "../common/ui";

export function FocusCard({ items }: { items: FocusItem[] }) {
  const sorted = [...items].sort((a, b) => a.rank - b.rank);
  return (
    <Card rounded="lg">
      <SectionHeader title="Focus" />
      <ol className="space-y-3">
        {sorted.map((item) => (
          <li key={item.id} className="flex items-center gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-industrial bg-brand-500 text-sm font-black text-ink-950">
              {item.rank}
            </span>
            <span className="text-sm font-bold text-foreground">{item.label}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
