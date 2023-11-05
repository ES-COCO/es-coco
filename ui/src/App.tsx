import { Component, createSignal, Show, createEffect } from "solid-js";
import { db, queryToIds } from "./sql";
import "./App.css";
import { SegmentData, fetchSegments } from "./components/Segment";
import { DataSource } from "./components/DataSource";

const App: Component = () => {
  const [selectedSegment, setSelectedSegment] = createSignal<SegmentData>();
  createEffect(() => {
    db(); // Force initial value to get set after DB load.
    const segmentIds = queryToIds(
      `
    SELECT DISTINCT s.id
    FROM WordAnnotations AS a
    JOIN Words AS w ON a.word_id = w.id
    JOIN Segments AS s ON w.segment_id = s.id
    WHERE a.annotation_type_id = (SELECT id from AnnotationTypes WHERE name = 'switch')
    ORDER BY s.start_ms
    LIMIT 2;
    `,
    );
    setSelectedSegment(fetchSegments(segmentIds)[1]);
  });

  return (
    <div class="app">
      <Show when={db()} fallback={<p class="loading">Loading...</p>}>
        <Show
          when={selectedSegment() !== undefined}
          fallback={<p class="loading">Loading...</p>}
        >
          <DataSource
            id={selectedSegment()!.dataSourceId}
            initialSelectedSegment={selectedSegment()!}
          />
        </Show>
      </Show>
    </div>
  );
};

export default App;
