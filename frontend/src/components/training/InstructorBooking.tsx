"use client";

/** Simple mock booking UI — intentionally not a real scheduling system. */
import { useState } from "react";

import type { InstructorSlot } from "@/types";

import { Button, Card, Empty } from "../common/ui";

export function InstructorBooking({ slots }: { slots: InstructorSlot[] }) {
  const [bookedSlotId, setBookedSlotId] = useState<string | null>(null);

  if (slots.length === 0) {
    return (
      <Card>
        <Empty>No instructor slots available right now.</Empty>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {slots.map((slot) => {
        const isBooked = bookedSlotId === slot.slotId;
        return (
          <Card key={slot.slotId} className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-bold text-foreground">{slot.trainingType}</p>
              <p className="text-sm font-medium text-foreground-muted">
                {slot.instructorName} · {slot.time}
              </p>
            </div>
            <Button
              variant={isBooked ? "secondary" : "primary"}
              disabled={isBooked}
              onClick={() => setBookedSlotId(slot.slotId)}
            >
              {isBooked ? "Booked" : "Book"}
            </Button>
          </Card>
        );
      })}
    </div>
  );
}
