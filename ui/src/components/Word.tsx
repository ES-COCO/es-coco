import { Component } from "solid-js";
import { placeholders, queryToMaps } from "../sql";
import { z } from "zod";

export const WordAnnotationData = z.object({
  id: z.number(),
  wordId: z.number(),
  type: z.string(),
  value: z.string(),
});
export type WordAnnotationData = z.infer<typeof WordAnnotationData>;
export function fetchWordAnnotations(word_ids: number[]) {
  return z.array(WordAnnotationData).parse(
    queryToMaps(
      `
      SELECT a.id, a.word_id, at.name as type, a.value
      FROM WordAnnotations AS a
      JOIN AnnotationTypes AS at ON a.annotation_type_id = at.id
      WHERE a.word_id IN (${placeholders(word_ids.length)});
    `,
      ...word_ids,
    ).map((a) => {
      return {
        id: a.get("id"),
        wordId: a.get("word_id"),
        type: a.get("type"),
        value: a.get("value"),
      };
    }),
  );
}

export const WordData = z.object({
  id: z.number(),
  segmentId: z.number(),
  surfaceForm: z.string(),
});
export type WordData = z.infer<typeof WordData>;
export function fetchWords(ids: number[]) {
  return z.array(WordData).parse(
    queryToMaps(
      `
      SELECT id, segment_id, surface_form
      FROM Words
      WHERE id IN (${placeholders(ids.length)})
      ORDER BY segment_id, word_index;
      `,
      ...ids,
    ).map((w) => {
      return {
        id: w.get("id"),
        segmentId: w.get("segment_id"),
        surfaceForm: w.get("surface_form"),
      };
    }),
  );
}

export const Word: Component<{ data: WordData }> = (props) => {
  const d = props.data;
  const annotations = fetchWordAnnotations([d.id]);
  const language = annotations.filter((a) => a.type == "language")[0].value;
  const tag = annotations.filter((a) => a.type == "pos")[0].value;
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
