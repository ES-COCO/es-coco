import { For, Component, JSX, Accessor, createEffect } from "solid-js";
import { Word, fetchWords } from "./Word";
import { db, placeholders, queryToIds, queryToMaps } from "../sql";
import { z } from "zod";
import "./Segment.css";

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

function padDigits(x: number) {
  x = Math.round(x);
  return `${x < 10 ? "0" : ""}${x}`;
}

function formatTime(ms: number) {
  let seconds = ms / 1000;
  let hours = Math.floor(seconds / 3600);
  let minutes = Math.floor((seconds - hours * 3600) / 60);
  seconds = seconds - hours * 3600 - minutes * 60;
  return `${padDigits(hours)}:${padDigits(minutes)}:${padDigits(seconds)}`;
}

export const Segment: Component<{
  index: number;
  data: SegmentData;
  selectedSegment: Accessor<SegmentData | undefined>;
  onClick?: JSX.EventHandlerUnion<HTMLDivElement, MouseEvent>;
}> = (props) => {
  const { index, data, selectedSegment, onClick } = props;
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
  createEffect(() => {
    if (data.id === selectedSegment()?.id) {
      ref?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });
  return (
    <div
      ref={ref}
      onClick={onClick}
      style={`--index: ${index};`}
      classList={{
        segment: true,
        selected: data.id === selectedSegment()?.id,
      }}
    >
      <div class="timestamps">
        <span>{formatTime(data.start)}</span>
        <span>-</span>
        <span>{formatTime(data.end)}</span>
      </div>
      <div class="segment-words">
        <For each={words}>{(w) => <Word data={w} />}</For>
      </div>
    </div>
  );
};
