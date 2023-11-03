import { For, Component, JSX, onMount } from "solid-js";
import { Word, fetchWords } from "./Word";
import { db, placeholders, queryToIds, queryToMaps } from "../sql";
import { z } from "zod";

export const SegmentData = z.object({
  id: z.number(),
  start: z.number(),
  end: z.number(),
  dataSourceId: z.number(),
});
export type SegmentData = z.infer<typeof SegmentData>;
export function fetchSegments(segmentIds: number[]): SegmentData[] {
  const connection = db();
  if (!connection) {
    return [];
  }
  const segments = new Map(
    queryToMaps(
      `
      SELECT DISTINCT id, start_ms as start, end_ms as end, data_source_id
      FROM Segments
      WHERE id IN (${placeholders(segmentIds.length)})
      ORDER BY data_source_id, start;
      `,
      ...segmentIds,
    ).map((s) => {
      const segment = SegmentData.parse({
        id: s.get("id"),
        start: s.get("start"),
        end: s.get("end"),
        dataSourceId: s.get("data_source_id"),
      });
      return [segment.id, segment];
    }),
  );
  return Array.from(segments.values());
}
export const Segment: Component<{
  index: number;
  data: SegmentData;
  selected: boolean;
  onClick?: JSX.EventHandlerUnion<HTMLDivElement, MouseEvent>;
}> = (props) => {
  const { index, data, selected, onClick } = props;
  const wordIds = queryToIds(
    `
    SELECT id
    FROM Words
    WHERE segment_id = ?;
  `,
    data.id,
  );
  const words = fetchWords(wordIds);

  let ref: HTMLDivElement | undefined;
  if (selected) {
    onMount(() => {
      ref?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }
  return (
    <div
      ref={ref}
      onClick={onClick}
      style={`--index: ${index};`}
      classList={{
        segment: true,
        selected,
      }}
    >
      <For each={words}>{(w) => <Word data={w} />}</For>
    </div>
  );
};
