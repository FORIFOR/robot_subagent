import {execa} from 'execa';
import {z} from 'zod';

const SkillSchema = z.object({
  id: z.string(),
  description: z.string().optional().nullable(),
  aliases: z.array(z.string()).default([]),
  template: z.string().optional().nullable(),
  template_with_color: z.string().optional().nullable(),
  allowed_objects: z.array(z.string()).default([]),
  allowed_colors: z.array(z.string()).default([]),
  object_required: z.boolean().optional().default(true),
  color_required: z.boolean().optional().default(false),
  executor_type: z.string().optional().nullable(),
  single_task: z.string().optional().nullable(),
  policy_path: z.string().optional().nullable()
});

export type Skill = z.infer<typeof SkillSchema>;

const SkillsResponseSchema = z.object({
  skills: z.array(SkillSchema)
});

const RobotCommandSchema = z.object({
  skill_id: z.string(),
  object: z.string().nullable().optional(),
  color: z.string().nullable().optional(),
  vla_instruction: z.string(),
  confidence: z.number(),
  requires_confirmation: z.boolean(),
  executable: z.boolean(),
  reason: z.string()
});

const SafetySchema = z.object({
  ok: z.boolean(),
  level: z.string(),
  reason: z.string()
});

const ParseResponseSchema = z.object({
  ok: z.boolean(),
  command: RobotCommandSchema,
  safety: SafetySchema,
  skill: SkillSchema.nullable(),
  shell_command: z.string().nullable().optional()
});

export type ParseResponse = z.infer<typeof ParseResponseSchema>;

const ExecuteResponseSchema = z.object({
  ok: z.boolean(),
  result: z.unknown().optional(),
  safety: SafetySchema.optional(),
  command: RobotCommandSchema.optional(),
  error: z.string().optional()
});

export type ExecuteResponse = z.infer<typeof ExecuteResponseSchema>;

const PYTHON_BIN = process.env.ROBOT_AGENT_BIN ?? '.venv/bin/robot-agent';

function pickStdoutJson(stdout: string): unknown {
  // The Python CLI may interleave logs with the JSON line; take the last line that
  // starts with `{`.
  const lines = stdout.trim().split(/\r?\n/);
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (line.startsWith('{')) {
      return JSON.parse(line);
    }
  }
  throw new Error(`No JSON object found in stdout`);
}

async function runJson(args: string[]): Promise<unknown> {
  const {stdout, stderr, exitCode} = await execa(PYTHON_BIN, args, {
    env: process.env,
    reject: false
  });
  try {
    return pickStdoutJson(stdout);
  } catch (e) {
    const head = (s: string) => (s.length > 600 ? s.slice(0, 600) + '…' : s);
    const cmd = `${PYTHON_BIN} ${args.join(' ')}`;
    const baseMessage = e instanceof Error ? e.message : String(e);
    throw new Error(
      `${baseMessage}\n  cmd:    ${cmd}\n  exit:   ${exitCode}\n  stderr: ${head(stderr || '(empty)')}\n  stdout: ${head(stdout || '(empty)')}`
    );
  }
}

export async function loadSkills(): Promise<Skill[]> {
  return SkillsResponseSchema.parse(await runJson(['skills-json'])).skills;
}

export async function parseRobotCommand(text: string): Promise<ParseResponse> {
  return ParseResponseSchema.parse(await runJson(['parse-json', text]));
}

// -- LLM test mode -----------------------------------------------------------

const LlmMetricsSchema = z.object({
  cpu_peak_percent: z.number(),
  cpu_avg_percent: z.number(),
  ram_peak_mb: z.number(),
  ram_peak_percent: z.number(),
  gpu_peak_percent: z.number().nullable().optional(),
  gpu_avg_percent: z.number().nullable().optional(),
  vram_peak_mb: z.number().nullable().optional(),
  vram_total_mb: z.number().nullable().optional(),
  samples: z.number()
});

const LlmChatResponseSchema = z.object({
  ok: z.boolean(),
  model: z.string(),
  prompt: z.string(),
  response: z.string(),
  total_time_s: z.number(),
  first_token_time_s: z.number().nullable(),
  eval_count: z.number().nullable(),
  eval_duration_s: z.number().nullable(),
  tokens_per_second: z.number().nullable(),
  ollama_raw: z.any().nullable(),
  metrics: LlmMetricsSchema,
  error: z.string().nullable()
});

export type LlmMetrics = z.infer<typeof LlmMetricsSchema>;
export type LlmChatResponse = z.infer<typeof LlmChatResponseSchema>;

const OllamaModelsResponseSchema = z.object({
  ok: z.boolean(),
  models: z.array(z.string()),
  error: z.string().optional()
});

export async function loadOllamaModels(): Promise<string[]> {
  const parsed = OllamaModelsResponseSchema.parse(await runJson(['ollama-models-json']));
  if (!parsed.ok) throw new Error(parsed.error ?? 'Failed to load Ollama models');
  return parsed.models;
}

export async function llmChatMeasured(
  text: string,
  model: string
): Promise<LlmChatResponse> {
  return LlmChatResponseSchema.parse(
    await runJson(['llm-chat-json', text, '--model', model])
  );
}

// -- task trace --------------------------------------------------------------

const TraceMetricsSchema = z.object({
  total_time_s: z.number(),
  first_token_time_s: z.number().nullable().optional(),
  eval_count: z.number().nullable().optional(),
  eval_duration_s: z.number().nullable().optional(),
  tokens_per_second: z.number().nullable().optional(),
  cpu_peak_percent: z.number().nullable().optional(),
  cpu_avg_percent: z.number().nullable().optional(),
  ram_peak_mb: z.number().nullable().optional(),
  ram_peak_percent: z.number().nullable().optional(),
  gpu_peak_percent: z.number().nullable().optional(),
  gpu_avg_percent: z.number().nullable().optional(),
  vram_peak_mb: z.number().nullable().optional(),
  vram_total_mb: z.number().nullable().optional()
});

const TaskTraceEvaluationSchema = z.object({
  expected_skill: z.string(),
  skill_match: z.boolean(),
  object_match: z.boolean(),
  instruction_ok: z.boolean(),
  executable_ok: z.boolean(),
  safety_ok: z.boolean(),
  score: z.number(),
  notes: z.array(z.string())
});

const PromptMessageSchema = z.object({
  role: z.string(),
  content: z.string()
});

const PromptTraceSchema = z.object({
  model: z.string(),
  endpoint: z.string(),
  temperature: z.number(),
  user_text: z.string(),
  system_message: z.string(),
  final_user_prompt: z.string(),
  skill_registry_text: z.string(),
  messages: z.array(PromptMessageSchema),
  request_options: z.record(z.string(), z.any()).default({})
});

export type PromptTrace = z.infer<typeof PromptTraceSchema>;

const TraceResponseSchema = z.object({
  ok: z.boolean(),
  input: z.string(),
  model: z.string(),
  expected_skill: z.string(),
  prompt_trace: PromptTraceSchema,
  raw_output: z.string(),
  command: RobotCommandSchema,
  safety: SafetySchema,
  evaluation: TaskTraceEvaluationSchema,
  generated_command: z.string().nullable().optional(),
  metrics: TraceMetricsSchema,
  error: z.string().nullable().optional()
});

export type TraceResponse = z.infer<typeof TraceResponseSchema>;

export async function traceRobotCommand(
  text: string,
  expectedSkill: string,
  model: string
): Promise<TraceResponse> {
  return TraceResponseSchema.parse(
    await runJson([
      'trace-parse-json',
      text,
      '--expected-skill',
      expectedSkill,
      '--model',
      model
    ])
  );
}

// -- robot execution ---------------------------------------------------------

export async function executeRobotCommand(text: string): Promise<ExecuteResponse> {
  try {
    return ExecuteResponseSchema.parse(await runJson(['execute-json', text]));
  } catch (e) {
    return {ok: false, error: e instanceof Error ? e.message : String(e)};
  }
}
