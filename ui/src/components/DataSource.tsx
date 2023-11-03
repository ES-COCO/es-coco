import { Component, For } from "solid-js";

import { z } from "zod";
import { placeholders, queryToIds, queryToMaps } from "../sql";
import { Segment, fetchSegments } from "./Segment";

export const DataSourceData = z.object({
  id: z.number(),
  name: z.string(),
  url: z.string(),
});
export type DataSourceData = z.infer<typeof DataSourceData>;
export function fetchDataSources(dataSourceIds: number[]) {
  return z.array(DataSourceData).parse(
    queryToMaps(
      `
    SELECT id, name, url
    FROM DataSources
    WHERE id IN (${placeholders(dataSourceIds.length)});
  `,
      ...dataSourceIds,
    ).map((d) => {
      return {
        id: d.get("id"),
        name: d.get("name"),
        url: d.get("url"),
      };
    }),
  );
}

export const DataSource: Component<{
  data: DataSourceData;
  selectedSegmentId: number;
}> = (props) => {
  const { data, selectedSegmentId } = props;
  const segmentIds = queryToIds(
    `
    SELECT id
    FROM Segments
    WHERE data_source_id = ?
  `,
    data.id,
  );
  const segments = fetchSegments(segmentIds);
  return (
    <div class="data-source">
      <For each={segments}>
        {(s) => <Segment data={s} selected={s.id === selectedSegmentId} />}
      </For>
    </div>
  );
};
