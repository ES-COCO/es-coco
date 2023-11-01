import { For, Component, createResource, Resource } from "solid-js";

import initSqlJs, { Database } from "sql.js";
import dbUrl from "./assets/escoco.db?url";
import sqlJsWasm from "../node_modules/sql.js/dist/sql-wasm.wasm?url";
import "./App.css";

interface Segment {
  id: number;
  sourceName: string;
  tokens: Word[];
}

interface Word {
  id: number;
  surface_form: string;
  annotations: Annotation[];
}

interface Annotation {
  type: string;
  value: string;
}

function queryToMaps(
  db: Resource<Database>,
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

const Segment: Component<{ data: Segment }> = (props) => {
  return (
    <div class="segment card">
      <For each={props.data.tokens}>{(t) => <Word data={t} />}</For>
    </div>
  );
};

const Word: Component<{ data: Word }> = (props) => {
  const d = props.data;
  const language = d.annotations.filter((a) => a.type == "language")[0].value;
  const tag = d.annotations.filter((a) => a.type == "pos")[0].value;
  return (
    <div
      classList={{
        token: true,
        english: language == "eng",
        spanish: language == "spa",
      }}
    >
      {d.surface_form.replace("##", "")}
      <div class="pos">{tag}</div>
    </div>
  );
};

const App: Component = () => {
  const [db] = createResource(async () => {
    const sqlPromise = initSqlJs({ locateFile: () => sqlJsWasm });
    const dataPromise = fetch(dbUrl).then((res) => res.arrayBuffer());
    const [SQL, buf] = await Promise.all([sqlPromise, dataPromise]);
    return new SQL.Database(new Uint8Array(buf));
  });
  const segments = () => {
    const segments = queryToMaps(
      db,
      `
      SELECT DISTINCT s.id, s.start_ms, s.end_ms, d.name as source_name
      FROM WordAnnotations AS a
      JOIN AnnotationTypes AS at ON a.annotation_type_id = at.id
      JOIN Words AS w ON a.word_id = w.id
      JOIN Segments AS s ON w.segment_id = s.id
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
      FROM Words
      WHERE segment_id IN (${placeholders})
      ORDER BY segment_id, word_index;
      `,
      ...segment_ids,
    );
    const annotations = queryToMaps(
      db,
      `
      SELECT w.id as word_id, at.name as type, a.value
      FROM Words as w
      JOIN WordAnnotations AS a ON a.word_id = w.id
      JOIN AnnotationTypes AS at ON a.annotation_type_id = at.id
      WHERE w.segment_id IN (${placeholders})
      ORDER BY w.segment_id, w.word_index, at.name;
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

    const words: Map<number, Word> = new Map();
    for (const t of surface_forms) {
      const id = t.get("id") as number;
      const word = {
        id,
        surface_form: t.get("surface_form"),
        annotations: [],
      } as Word;
      words.set(id, word);
      result.get(t.get("segment_id") as number)!.tokens.push(word);
    }

    for (const a of annotations) {
      const word = words.get(a.get("word_id") as number)!;
      word.annotations.push({
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
