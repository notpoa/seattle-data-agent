export type Dataset = { dataset_id: string; title: string; description: string; supported?: boolean; limitation?: string; source_url?: string };
export type Result = { dataset_id: string; title: string; rows: Record<string, unknown>[]; source_url: string; retrieved_at: string; warnings: string[]; truncated: boolean; query: {time_bucket?: unknown; group_by?: string[]}; parameters: Record<string, string> };
export type Event =
  | {type: 'progress' | 'warning' | 'error'; message: string}
  | {type: 'datasets'; datasets: Dataset[]}
  | {type: 'selected'; dataset: Dataset; source_url: string}
  | {type: 'result'; result: Result}
  | {type: 'answer'; status: string; message: string};
export type Session = { progress: string; datasets: Dataset[]; selected: Dataset[]; results: Result[]; answer: string; status: string; error: string; warnings: string[] };
export const emptySession = (): Session => ({progress: '', datasets: [], selected: [], results: [], answer: '', status: '', error: '', warnings: []});
export function reduceEvent(state: Session, event: Event): Session {
  switch (event.type) {
    case 'progress': return {...state, progress: event.message};
    case 'datasets': {
      const unique = new Map(state.datasets.map(d => [d.dataset_id, d]));
      event.datasets.forEach(d => unique.set(d.dataset_id, d));
      return {...state, datasets: [...unique.values()]};
    }
    case 'selected': return {...state, selected: [...state.selected.filter(d => d.dataset_id !== event.dataset.dataset_id), {...event.dataset, source_url: event.source_url}]};
    case 'result': return {...state, results: [...state.results, event.result]};
    case 'answer': return {...state, answer: event.message, status: event.status, progress: ''};
    case 'error': return {...state, error: event.message, progress: ''};
    case 'warning': return {...state, warnings: [...state.warnings, event.message]};
  }
}

// Network chunks can split in the middle of a JSON line or UTF-8 character.
export class EventReader {
  private pending = '';
  push(text: string): Event[] {
    this.pending += text;
    const lines = this.pending.split('\n');
    this.pending = lines.pop() || '';
    return lines.filter(l => l.trim()).map(l => JSON.parse(l) as Event);
  }
  finish(): Event[] {
    const rest = this.pending.trim(); this.pending = '';
    return rest ? [JSON.parse(rest) as Event] : [];
  }
}
