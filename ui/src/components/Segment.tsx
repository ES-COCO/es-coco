import { For, Component } from "solid-js";
import { Word, WordData, fetchWords } from "./Word";
import { db, placeholders, queryToArray, queryToMaps } from "../sql";
import { z } from "zod";

export const SegmentData = z.object({
  id: z.number(),
  start: z.number(),
  end: z.number(),
  sourceName: z.string(),
  words: z.array(WordData),
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
      SELECT DISTINCT s.id, s.start_ms as start, s.end_ms as end, d.name as source_name
      FROM Segments as s
      JOIN DataSources AS d ON data_source_id = d.id
      WHERE s.id IN (${placeholders(segmentIds.length)})
      ORDER BY source_name, start;
      `,
      ...segmentIds,
    ).map((s) => {
      const segment = SegmentData.parse({
        id: s.get("id"),
        start: s.get("start"),
        end: s.get("end"),
        sourceName: s.get("source_name"),
        words: [],
      });
      return [segment.id, segment];
    }),
  );
  const wordIds = z.array(z.number()).parse(
    queryToArray(
      `
      SELECT id
      FROM Words
      WHERE segment_id IN (${placeholders(segmentIds.length)});
    `,
      ...segmentIds,
    ),
  );
  for (const w of fetchWords(wordIds)) {
    const segment = segments.get(w.segmentId);
    if (segment) {
      segment.words.push(w);
    } else {
      console.error(`Cannot find segment with id: ${w.segmentId}`);
    }
  }
  return Array.from(segments.values());
}

export const Segment: Component<{ data: SegmentData; selected: boolean }> = (
  props,
) => {
  const { data, selected } = props;
  return (
    <div
      classList={{
        card: true,
        segment: true,
        selected,
      }}
    >
      <For each={data.words}>{(t) => <Word data={t} />}</For>
    </div>
  );
};
