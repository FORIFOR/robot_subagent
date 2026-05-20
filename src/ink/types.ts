import type {LlmChatResponse, ParseResponse} from './pythonBridge.js';

export type LogItem =
  | {type: 'system'; text: string}
  | {type: 'user'; text: string}
  | {type: 'agent'; result: ParseResponse}
  | {type: 'llm'; result: LlmChatResponse}
  | {type: 'error'; text: string};
