import { For, Component, createResource } from "solid-js";
import { loadDatabase, queryToArray } from "./sql";
import "./App.css";
import { Segment, fetchSegments } from "./components/Segment";
import { z } from "zod";

const App: Component = () => {
  const [db] = createResource(loadDatabase);
  const segments = () => {
    const segmentIds = z.array(z.number()).parse(queryToArray(
      db,
      `
      SELECT DISTINCT s.id
      FROM WordAnnotations AS a
      JOIN Words AS w ON a.word_id = w.id
      JOIN Segments AS s ON w.segment_id = s.id
      WHERE a.annotation_type_id = (SELECT id from AnnotationTypes WHERE name = 'switch');
      `,
    ));
    return fetchSegments(db, segmentIds);
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
