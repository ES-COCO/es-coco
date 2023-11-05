import { Component, For, createSignal } from "solid-js";

import { z } from "zod";
import { placeholders, queryToIds, queryToMaps } from "../sql";
import { Segment, fetchSegments } from "./Segment";
import "./DataSource.css";
import { SegmentData } from "./Segment";

export const DataSourceData = z.object({
  id: z.number(),
  name: z.string(),
  creator: z.string(),
  url: z.string(),
});
export type DataSourceData = z.infer<typeof DataSourceData>;
export function fetchDataSources(dataSourceIds: number[]) {
  return z.array(DataSourceData).parse(
    queryToMaps(
      `
    SELECT id, name, url, creator
    FROM DataSources
    WHERE id IN (${placeholders(dataSourceIds.length)});
    `,
      ...dataSourceIds,
    ).map((d) => {
      return {
        id: d.get("id"),
        name: d.get("name"),
        creator: d.get("creator"),
        url: d.get("url"),
      };
    }),
  );
}

export const DataSource: Component<{
  id: number;
  initialSelectedSegment: SegmentData;
}> = (props) => {
  const { id, initialSelectedSegment } = props;
  const data = fetchDataSources([id])[0];
  const segmentIds = queryToIds(
    `
    SELECT id
    FROM Segments
    WHERE data_source_id = ?
  `,
    data.id,
  );
  const segments = fetchSegments(segmentIds);
  const [selectedSegment, setSelectedSegment] = createSignal(
    initialSelectedSegment,
  );
  return (
    <div class="data-source">
      <div class="data-source-header">
        <div class="data-source-metadata">
          <a class="source-name" href={data.url}>
            {data.name}
          </a>
          <div>{data.creator}</div>
        </div>
        <iframe
          style="border-radius:12px"
          src={`https://open.spotify.com/embed/episode/0JNeWCADwaEat4QqE5Tz9i?utm_source=generator&t=${Math.floor(
            selectedSegment().start / 1000,
          )}`}
          width="100%"
          height="152"
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
          loading="lazy"
        ></iframe>
      </div>
      <div class="data-source-segments">
        <For each={segments}>
          {(s, i) => (
            <Segment
              index={i()}
              data={s}
              selectedSegment={selectedSegment}
              onClick={() => setSelectedSegment(s)}
            />
          )}
        </For>
      </div>
    </div>
  );
};
