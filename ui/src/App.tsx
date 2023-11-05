import { For, Component, createSignal, Show, createEffect } from "solid-js";
import { db, queryToIds } from "./sql";
import "./App.css";
import { Segment, SegmentData, fetchSegments } from "./components/Segment";
import { DataSource } from "./components/DataSource";

const App: Component = () => {
  const [segments, setSegments] = createSignal<SegmentData[]>([]);
  const [selectedSegment, setSelectedSegment] = createSignal<SegmentData>();
  createEffect(() => {
    db(); // Force initial value to get set after DB load.
    const segmentIds = queryToIds(
      `
    SELECT DISTINCT s.id
    FROM WordAnnotations AS a
    JOIN Words AS w ON a.word_id = w.id
    JOIN Segments AS s ON w.segment_id = s.id
    WHERE a.annotation_type_id = (SELECT id from AnnotationTypes WHERE name = 'switch');
    `,
    );
    setSegments(fetchSegments(segmentIds));
  });

  return (
    <div class="app">
      <Show when={db()} fallback={<p class="loading">Loading...</p>}>
        <Show
          when={selectedSegment() !== undefined}
          fallback={
            <div class="segment-container">
              <For each={segments()}>
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
          }
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
