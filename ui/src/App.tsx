import {
  For,
  Component,
  createSignal,
  Signal,
  Show,
  createEffect,
} from "solid-js";
import { db, queryToIds } from "./sql";
import "./App.css";
import { Segment, SegmentData, fetchSegments } from "./components/Segment";

const SegmentContainer: Component<{ segmentsSignal: Signal<SegmentData[]> }> = (
  props,
) => {
  const [segments, setSegments] = props.segmentsSignal;
  const [selectedSegmentId, setSelectedSegmentId] = createSignal<number>();
  const selectSegment = (segment: SegmentData) => {
    const segmentIds = queryToIds(
      `
        SELECT id
        FROM Segments
        WHERE data_source_id = ?
      `,
      segment.dataSourceId,
    );
    setSelectedSegmentId(segment.id);
    setSegments(fetchSegments(segmentIds));
  };
  return (
    <div classList={{ ["segment-container"]: true }}>
      <For each={segments()}>
        {(s, i) => (
          <Segment
            index={i()}
            data={s}
            selected={s.id === selectedSegmentId()}
            onClick={() => selectSegment(s)}
          />
        )}
      </For>
    </div>
  );
};

const App: Component = () => {
  const [segments, setSegments] = createSignal<SegmentData[]>([]);
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
        <SegmentContainer segmentsSignal={[segments, setSegments]} />
      </Show>
    </div>
  );
};

export default App;
