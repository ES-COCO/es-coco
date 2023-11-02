import { For, Component } from "solid-js";
import { queryToIds } from "./sql";
import "./App.css";
import { Segment, fetchSegments } from "./components/Segment";

const App: Component = () => {
  const segments = () => {
    const segmentIds = queryToIds(
      `
      SELECT DISTINCT s.id
      FROM WordAnnotations AS a
      JOIN Words AS w ON a.word_id = w.id
      JOIN Segments AS s ON w.segment_id = s.id
      WHERE a.annotation_type_id = (SELECT id from AnnotationTypes WHERE name = 'switch');
      `,
    );
    return fetchSegments(segmentIds);
  };

  return (
    <div class="app">
      <For each={segments()}>
        {(s) => <Segment data={s} selected={false} />}
      </For>
    </div>
  );
};

export default App;
