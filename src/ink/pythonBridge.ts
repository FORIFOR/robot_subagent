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
  throw new Error(`No JSON object found in stdout: ${stdout}`);
}

export async function loadSkills(): Promise<Skill[]> {
  const {stdout} = await execa(PYTHON_BIN, ['skills-json'], {env: process.env});
  return SkillsResponseSchema.parse(pickStdoutJson(stdout)).skills;
}

export async function parseRobotCommand(text: string): Promise<ParseResponse> {
  const {stdout} = await execa(PYTHON_BIN, ['parse-json', text], {env: process.env});
  return ParseResponseSchema.parse(pickStdoutJson(stdout));
}

export async function executeRobotCommand(text: string): Promise<ExecuteResponse> {
  const {stdout} = await execa(PYTHON_BIN, ['execute-json', text], {
    env: process.env,
    reject: false
  });
  try {
    return ExecuteResponseSchema.parse(pickStdoutJson(stdout));
  } catch {
    return {ok: false, error: stdout};
  }
}
