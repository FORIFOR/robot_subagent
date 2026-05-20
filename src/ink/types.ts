import type {
  LlmChatResponse,
  ParseResponse,
  TraceResponse
} from './pythonBridge.js';

export type LogItem =
  | {type: 'system'; text: string}
  | {type: 'user'; text: string}
  | {type: 'agent'; result: ParseResponse}
  | {type: 'llm'; result: LlmChatResponse}
  | {type: 'trace'; result: TraceResponse}
  | {type: 'error'; text: string};
