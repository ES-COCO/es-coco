import { For, Component, Resource } from "solid-js";
import { Word, WordData, fetchWords } from "./Word";
import { placeholders, queryToArray, queryToMaps } from "../sql";
import { Database } from "sql.js";
import { z } from "zod";

export const SegmentData = z.object({
  id: z.number(),
  start: z.number(),
  end: z.number(),
  sourceName: z.string(),
  words: z.array(WordData),
});
export type SegmentData = z.infer<typeof SegmentData>;

export function fetchSegments(
  db: Resource<Database>,
  segmentIds: number[],
): SegmentData[] {
  const connection = db();
  if (!connection) {
    return [];
  }
  const segments = new Map(
    queryToMaps(
      db,
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
      db,
      `
      SELECT id
      FROM Words
      WHERE segment_id IN (${placeholders(segmentIds.length)});
    `,
      ...segmentIds,
    ),
  );
  for (const w of fetchWords(db, wordIds)) {
    const segment = segments.get(w.segmentId);
    if (segment) {
      segment.words.push(w);
    } else {
      console.error(`Cannot find segment with id: ${w.segmentId}`);
    }
  }
  return Array.from(segments.values());
}

export const Segment: Component<{ data: SegmentData }> = (props) => {
  return (
    <div class="segment card">
      <For each={props.data.words}>{(t) => <Word data={t} />}</For>
    </div>
  );
};
