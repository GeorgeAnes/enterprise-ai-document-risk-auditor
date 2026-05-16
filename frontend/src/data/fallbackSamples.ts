import type { SampleDocument, SampleInfo } from "../types";

export const FALLBACK_SAMPLE: SampleDocument = {
  id: "fallback_consulting_report",
  title: "Fallback Consulting Report Sample",
  description: "Frontend fallback sample shown when the FastAPI backend is unavailable.",
  filename: "fallback_consulting_report_sample.md",
  content: `# Fallback Consulting Report Sample

Northbridge Manufacturing is evaluating a shared analytics operating model for procurement and maintenance teams.

The pilot dashboard recorded 418 invoice exceptions in the baseline window and 421 exceptions in the intervention window.

The new operating model is guaranteed to eliminate all manual rework across the enterprise.

The reduction was observed only for the two teams included in the pilot.

The report does not include evidence from finance, legal, or customer support teams.

This fallback text is synthetic and exists only so the frontend remains inspectable when the backend is offline.`
};

export const FALLBACK_SAMPLES: SampleInfo[] = [
  {
    id: FALLBACK_SAMPLE.id,
    title: FALLBACK_SAMPLE.title,
    description: FALLBACK_SAMPLE.description,
    filename: FALLBACK_SAMPLE.filename
  }
];

export function fallbackSampleById(sampleId: string): SampleDocument | null {
  return sampleId === FALLBACK_SAMPLE.id ? FALLBACK_SAMPLE : null;
}
