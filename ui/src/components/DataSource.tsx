import { Component, Resource } from "solid-js";

import { Database } from "sql.js";
import "./App.css";

import { SegmentData } from "./Segment";
import { z } from "zod";
import { db, placeholders, queryToMaps } from "../sql";

export const DataSourceData = z.object({
  id: z.string(),
  name: z.string(),
  url: z.string(),
});
export type DataSourceData = z.infer<typeof DataSourceData>;

function fetchDataSources(dataSourceIds: number[]) {
  return z.array(DataSourceData).parse(
    queryToMaps(
      db,
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

// export const DataSource: Component<{
//   data: DataSourceData;
//   selectedSegmentId: number;
// }> = (props) => {
//   const { data, selectedSegmentId } = props;
// };
