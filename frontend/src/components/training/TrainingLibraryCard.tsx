import type { TrainingClip } from "@/types";

import { Button, Card } from "../common/ui";

export function TrainingLibraryCard({ clip }: { clip: TrainingClip }) {
  return (
    <Card>
      <p className="text-xs font-bold uppercase tracking-widest text-foreground-muted">{clip.category}</p>
      <h3 className="mt-1 text-lg font-black uppercase tracking-tight text-foreground">{clip.title}</h3>
      <p className="mt-1 text-sm font-medium text-foreground-muted">{clip.description}</p>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs font-bold uppercase tracking-widest text-foreground-muted">{clip.durationMin} min</span>
        <Button variant="secondary">Watch</Button>
      </div>
    </Card>
  );
}
