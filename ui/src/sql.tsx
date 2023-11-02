import { createResource } from "solid-js";
import initSqlJs from "sql.js";
import dbUrl from "./assets/escoco.db?url";
import sqlJsWasm from "../node_modules/sql.js/dist/sql-wasm.wasm?url";
import { z } from "zod";

export const [db] = createResource(async () => {
  const sqlPromise = initSqlJs({ locateFile: () => sqlJsWasm });
  const dataPromise = fetch(dbUrl).then((res) => res.arrayBuffer());
  const [SQL, buf] = await Promise.all([sqlPromise, dataPromise]);
  return new SQL.Database(new Uint8Array(buf));
});

export function placeholders(n: number): string {
  return "?,".repeat(n).slice(0, -1);
}

export function queryToArray(query: string, ...params: any[]) {
  const connection = db();
  if (!connection) {
    return [];
  }
  return connection.exec(query, params)[0].values.flat();
}

export function queryToIds(query: string, ...params: any[]) {
  return z.array(z.number()).parse(queryToArray(query, ...params));
}

export function queryToMaps(
  query: string,
  ...params: any[]
): Map<string, string | number>[] {
  const connection = db();
  if (!connection) {
    return [];
  }
  const result = connection.exec(query, params)[0];
  return result.values.map((values) => {
    const m = new Map();
    for (let i = 0; i < result.columns.length; i++) {
      m.set(result.columns[i], values[i]);
    }
    return m;
  });
}

export function toIdMap<T extends { id: number }>(
  objects: T[],
): Map<number, T> {
  return new Map(objects.map((o) => [o.id, o]));
}
