import { Component, Resource } from "solid-js";
import { Database } from "sql.js";
import { placeholders, queryToMaps } from "../sql";
import { z } from "zod";

export const WordAnnotationData = z.object({
  wordId: z.number(),
  type: z.string(),
  value: z.string(),
});
export type WordAnnotationData = z.infer<typeof WordAnnotationData>;

export const WordData = z.object({
  id: z.number(),
  segmentId: z.number(),
  surfaceForm: z.string(),
  annotations: z.array(WordAnnotationData),
});
export type WordData = z.infer<typeof WordData>;

export function fetchWords(db: Resource<Database>, word_ids: number[]) {
  const words = new Map<number, WordData>(
    queryToMaps(
      db,
      `
      SELECT id, segment_id, surface_form
      FROM Words
      WHERE id IN (${placeholders(word_ids.length)})
      ORDER BY segment_id, word_index;
      `,
      ...word_ids,
    ).map((w) => {
      const word = WordData.parse({
        id: w.get("id"),
        segmentId: w.get("segment_id"),
        surfaceForm: w.get("surface_form"),
        annotations: [],
      });
      return [word.id, word];
    }),
  );
  const annotations = queryToMaps(
    db,
    `
      SELECT w.id as word_id, at.name as type, a.value
      FROM Words as w
      JOIN WordAnnotations AS a ON a.word_id = w.id
      JOIN AnnotationTypes AS at ON a.annotation_type_id = at.id
      WHERE w.id IN (${placeholders(word_ids.length)})
      ORDER BY w.segment_id, w.word_index, at.name;
      `,
    ...word_ids,
  );
  for (const a of annotations) {
    const annotation = WordAnnotationData.parse({
      wordId: a.get("word_id"),
      type: a.get("type"),
      value: a.get("value"),
    });
    const word = words.get(annotation.wordId);
    if (word === undefined) {
      throw `Could not find word with id ${annotation.wordId}`;
    } else {
      word.annotations.push(annotation);
    }
  }
  return Array.from(words.values());
}

export const Word: Component<{ data: WordData }> = (props) => {
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
      {d.surfaceForm.replace("##", "")}
      <div class="pos">{tag}</div>
    </div>
  );
};
