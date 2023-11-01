import { For, createSignal, Component, Show } from "solid-js";

import initSqlJs, { Database } from "sql.js";
import dbUrl from "../../data/test.db?url";
import sqlJsWasm from "../node_modules/sql.js/dist/sql-wasm.wasm?url";
import "./App.css";

const sqlPromise = initSqlJs({ locateFile: () => sqlJsWasm });
const dataPromise = fetch(dbUrl).then((res) => res.arrayBuffer());
const [SQL, buf] = await Promise.all([sqlPromise, dataPromise]);
const db = new SQL.Database(new Uint8Array(buf));

interface Segment {
  id: number;
  sourceName: string;
  tokens: Token[];
}

interface Token {
  id: number;
  surface_form: string;
  annotations: Annotation[];
}

interface Annotation {
  type: string;
  value: string;
}

function queryToMaps(
  db: Database,
  query: string,
  ...params: any[]
): Map<string, string | number>[] {
  const result = db.exec(query, params)[0];
  return result.values.map((values) => {
    const m = new Map();
    for (let i = 0; i < result.columns.length; i++) {
      m.set(result.columns[i], values[i]);
    }
    return m;
  });
}

const Segment: Component<{ data: Segment }> = (props) => {
  return (
    <div class="segment card">
      <For each={props.data.tokens}>
        {(t, i) => {
          const nextToken = props.data.tokens[i() + 1];
          const addSpace =
            nextToken &&
            !t.surface_form.match(/['\-]$/) &&
            !nextToken.surface_form.startsWith("##") &&
            !nextToken.surface_form.match(/[',.?¿"\-]/);
          return (
            <>
              <Token data={t} />
              <Show when={addSpace}> </Show>
            </>
          );
        }}
      </For>
    </div>
  );
};

const Token: Component<{ data: Token }> = (props) => {
  const d = props.data;
  const language = d.annotations.filter(a => a.type == "language")[0].value;
  const tag = d.annotations.filter(a => a.type == "pos")[0].value;
  return <div classList={{
    token: true,
    english: language == "eng",
    spanish: language == "spa",
  }}>{d.surface_form.replace("##", "")}<div class="pos">{tag}</div></div>;
};

const App: Component = () => {
  const [query, setQuery] = createSignal("");
  const segments = () => {
    query();
    const segments = queryToMaps(
      db,
      `
      SELECT DISTINCT s.id, s.start_ms, s.end_ms, d.name as source_name
      FROM Annotations AS a
      JOIN AnnotationTypes AS at ON a.annotation_type_id = at.id
      JOIN Tokens AS t ON a.token_id = t.id
      JOIN Segments AS s ON t.segment_id = s.id
      JOIN DataSources AS d ON s.data_source_id = d.id
      WHERE at.name = 'switch';
      `,
    );
    const placeholders = "?,".repeat(segments.length).slice(0, -1);
    const segment_ids = segments.map((s) => s.get("id"));
    const surface_forms = queryToMaps(
      db,
      `
      SELECT segment_id, id, surface_form
      FROM Tokens
      WHERE segment_id IN (${placeholders})
      ORDER BY segment_id, token_index;
      `,
      ...segment_ids,
    );
    const annotations = queryToMaps(
      db,
      `
      SELECT t.id as token_id, at.name as type, a.value
      FROM Tokens as t
      JOIN Annotations AS a ON a.token_id = t.id
      JOIN AnnotationTypes AS at ON a.annotation_type_id = at.id
      WHERE t.segment_id IN (${placeholders})
      ORDER BY t.segment_id, t.token_index, at.name;
      `,
      ...segment_ids,
    );

    const result: Map<number, Segment> = new Map();
    for (let i = 0; i < segments.length; i++) {
      const s = segments[i];
      const id = s.get("id") as number;
      result.set(id, {
        id,
        sourceName: s.get("source_name"),
        tokens: [],
      } as Segment);
    }

    const tokens: Map<number, Token> = new Map();
    for (const t of surface_forms) {
      const id = t.get("id") as number;
      const token = {
        id,
        surface_form: t.get("surface_form"),
        annotations: [],
      } as Token;
      tokens.set(id, token);
      result.get(t.get("segment_id") as number)!.tokens.push(token);
    }

    for (const a of annotations) {
      const token = tokens.get(a.get("token_id") as number)!;
      token.annotations.push({
        type: a.get("type"),
        value: a.get("value"),
      } as Annotation);
    }
    return Array.from(result.values());
  };

  // <input onInput={(e) => setQuery(e.target.value)} />
  return (
    <>
      <div class="app">
        <For each={segments()}>{(s) => <Segment data={s} />}</For>
      </div>
    </>
  );
};

export default App;
