import React, {useEffect, useState} from 'react';
import {Box, Text, useApp, useInput} from 'ink';
import {
  executeRobotCommand,
  llmChatMeasured,
  loadOllamaModels,
  loadSkills,
  parseRobotCommand,
  traceRobotCommand,
  type ParseResponse,
  type Skill
} from './pythonBridge.js';
import type {LogItem} from './types.js';
import {SkillList} from './components/SkillList.js';
import {ChatLog} from './components/ChatLog.js';
import {CommandInput} from './components/CommandInput.js';
import {StatusBar} from './components/StatusBar.js';

const BENCH_PROMPTS: readonly string[] = [
  '日本語で短く自己紹介してください。',
  '「りんごを取って」をロボット命令の英語に変換してください。',
  '次の文を {skill_id, vla_instruction} のJSONにしてください: キューブをつかんで',
  'こんにちは。今日の作業を一言で励ましてください。'
];

const TASK_BENCH_PROMPTS: Record<string, readonly string[]> = {
  grab_cube: [
    'キューブをつかんで',
    'cubeをつかんで',
    'ブロックを掴んで',
    'Grab the cube',
    '赤いキューブをつかんで',
    '四角いやつを取って',
    'これを取って'
  ],
  pick_apple: [
    'りんごを取って',
    'リンゴをつかんで',
    'Pick the apple',
    '赤いりんごを取って'
  ],
  place_on_plate: [
    'カップを皿に置いて',
    'cubeをプレートに置いて',
    'place on plate',
    '青いカップを皿に置いて'
  ],
  wave_hand: [
    'ばいばい',
    'バイバイ',
    '手を振って',
    'wave your hand'
  ],
  move_to_home: ['ホームに戻って', 'home pose', '初期姿勢に戻して']
};

export function App() {
  const {exit} = useApp();

  const [skills, setSkills] = useState<Skill[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>(
    process.env.ROBOT_AGENT_MODEL ?? 'qwen3:14b'
  );
  const [logs, setLogs] = useState<LogItem[]>([
    {type: 'system', text: 'Robot Agent Ink UI started. mode=DRY-RUN, LLM_TEST=OFF'}
  ]);
  const [executeMode, setExecuteMode] = useState(false);
  const [llmTestMode, setLlmTestMode] = useState(false);
  const [traceMode, setTraceMode] = useState(false);
  const [traceSkill, setTraceSkill] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastText, setLastText] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ParseResponse | null>(null);

  const log = (item: LogItem) => setLogs(prev => [...prev, item]);

  async function refreshSkills() {
    try {
      const loaded = await loadSkills();
      setSkills(loaded);
      log({type: 'system', text: 'Skills loaded.'});
    } catch (error) {
      log({type: 'error', text: error instanceof Error ? error.message : String(error)});
    }
  }

  async function refreshModels() {
    try {
      const loaded = await loadOllamaModels();
      setModels(loaded);
      if (loaded.length > 0 && !loaded.includes(selectedModel)) {
        setSelectedModel(loaded[0]);
      }
      log({type: 'system', text: `Ollama models loaded (${loaded.length}).`});
    } catch (error) {
      log({type: 'error', text: error instanceof Error ? error.message : String(error)});
    }
  }

  useEffect(() => {
    void refreshSkills();
    void refreshModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useInput((inputKey, key) => {
    if (key.ctrl && inputKey === 'c') {
      exit();
    }
    if (key.ctrl && inputKey === 'l') {
      setLogs([{type: 'system', text: 'Log cleared.'}]);
    }
  });

  async function runLast() {
    if (!lastText || !lastResult) {
      log({type: 'error', text: '実行できる直前コマンドがありません。'});
      return;
    }
    if (!executeMode) {
      log({type: 'error', text: 'Execute mode OFFです。/mode で切替してください。'});
      return;
    }
    if (!lastResult.ok) {
      log({type: 'error', text: '直前コマンドはSafety Gateでblockedです。'});
      return;
    }
    setIsLoading(true);
    log({type: 'system', text: 'Executing last command...'});
    try {
      const result = await executeRobotCommand(lastText);
      log({
        type: result.ok ? 'system' : 'error',
        text:
          `Execution: ok=${result.ok}` +
          (result.error ? `\nerror=${result.error}` : '') +
          (result.result ? `\nresult=${JSON.stringify(result.result)}` : '')
      });
    } catch (error) {
      log({type: 'error', text: error instanceof Error ? error.message : String(error)});
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLlmChat(text: string) {
    log({type: 'user', text});
    setIsLoading(true);
    try {
      const result = await llmChatMeasured(text, selectedModel);
      log({type: 'llm', result});
    } catch (error) {
      log({type: 'error', text: error instanceof Error ? error.message : String(error)});
    } finally {
      setIsLoading(false);
    }
  }

  async function runBenchmark() {
    log({type: 'system', text: `Benchmark started: ${selectedModel}`});
    for (const prompt of BENCH_PROMPTS) {
      await handleLlmChat(prompt);
    }
    log({type: 'system', text: `Benchmark finished: ${selectedModel}`});
  }

  async function handleTrace(text: string, skill: string) {
    log({type: 'user', text});
    setIsLoading(true);
    try {
      const result = await traceRobotCommand(text, skill, selectedModel);
      log({type: 'trace', result});
    } catch (error) {
      log({type: 'error', text: error instanceof Error ? error.message : String(error)});
    } finally {
      setIsLoading(false);
    }
  }

  async function runTaskBench(skill: string) {
    const prompts = TASK_BENCH_PROMPTS[skill];
    if (!prompts) {
      log({type: 'error', text: `Unknown bench task: ${skill}. 候補: ${Object.keys(TASK_BENCH_PROMPTS).join(', ')}`});
      return;
    }
    log({type: 'system', text: `Task bench started: ${skill} / ${selectedModel}`});
    for (const prompt of prompts) {
      await handleTrace(prompt, skill);
    }
    log({type: 'system', text: `Task bench finished: ${skill}`});
  }

  async function handleSubmit(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;

    if (
      trimmed === '/quit' ||
      trimmed === '/exit' ||
      trimmed === 'q' ||
      trimmed === 'exit' ||
      trimmed === 'quit'
    ) {
      exit();
      return;
    }
    if (trimmed === '/help') {
      log({
        type: 'system',
        text:
          'Robot:\n' +
          '  /robot                ロボット命令モードへ\n' +
          '  /run                  直前コマンドを実行 (executeモード)\n' +
          '  /mode                 dry-run <-> execute\n' +
          '  /skills               skill_registry.yaml 再読込\n' +
          'LLM Test:\n' +
          '  /llm                  LLM Test Mode ON/OFF\n' +
          '  /models               Ollama モデル一覧再読込\n' +
          '  /model <name>         使用モデル変更\n' +
          '  /bench                定型プロンプトを連投して比較\n' +
          'Task Trace:\n' +
          '  /trace <skill_id>     対象スキルのTrace Modeへ (例: /trace grab_cube)\n' +
          '  /trace-off            Trace Mode終了\n' +
          '  /bench-task <skill>   想定プロンプト一括評価\n' +
          'Misc:\n' +
          '  /clear                ログクリア\n' +
          '  /help                 このヘルプ\n' +
          '  /quit                 終了'
      });
      return;
    }
    if (trimmed === '/clear') {
      setLogs([{type: 'system', text: 'Log cleared.'}]);
      return;
    }
    if (trimmed === '/skills') {
      await refreshSkills();
      return;
    }
    if (trimmed === '/models') {
      await refreshModels();
      return;
    }
    if (trimmed === '/mode' || trimmed === '/toggle') {
      setExecuteMode(prev => {
        log({type: 'system', text: `Mode -> ${!prev ? 'EXECUTE' : 'DRY-RUN'}`});
        return !prev;
      });
      return;
    }
    if (trimmed === '/llm') {
      setLlmTestMode(prev => {
        log({type: 'system', text: `LLM Test Mode -> ${!prev ? 'ON' : 'OFF'}`});
        return !prev;
      });
      setTraceMode(false);
      setTraceSkill(null);
      return;
    }
    if (trimmed === '/robot') {
      setLlmTestMode(false);
      setTraceMode(false);
      setTraceSkill(null);
      log({type: 'system', text: 'Robot Command Mode'});
      return;
    }
    if (trimmed.startsWith('/trace ')) {
      const skill = trimmed.slice('/trace '.length).trim();
      if (!skill) {
        log({type: 'error', text: '使い方: /trace grab_cube'});
        return;
      }
      setTraceSkill(skill);
      setTraceMode(true);
      setLlmTestMode(false);
      log({
        type: 'system',
        text: `Task Trace Mode ON. expected_skill=${skill}, model=${selectedModel}`
      });
      return;
    }
    if (trimmed === '/trace-off') {
      setTraceMode(false);
      setTraceSkill(null);
      log({type: 'system', text: 'Task Trace Mode OFF'});
      return;
    }
    if (trimmed.startsWith('/bench-task ')) {
      const skill = trimmed.slice('/bench-task '.length).trim();
      if (!skill) {
        log({type: 'error', text: '使い方: /bench-task grab_cube'});
        return;
      }
      await runTaskBench(skill);
      return;
    }
    if (trimmed.startsWith('/model ')) {
      const model = trimmed.slice('/model '.length).trim();
      if (!model) {
        log({type: 'error', text: '/model <name> を指定してください。例: /model qwen3:14b'});
        return;
      }
      setSelectedModel(model);
      log({type: 'system', text: `Selected model: ${model}`});
      return;
    }
    if (trimmed === '/run') {
      await runLast();
      return;
    }
    if (trimmed === '/bench') {
      await runBenchmark();
      return;
    }
    if (trimmed.startsWith('/')) {
      log({type: 'error', text: `Unknown command: ${trimmed}. /help を確認してください。`});
      return;
    }

    if (traceMode && traceSkill) {
      await handleTrace(trimmed, traceSkill);
      return;
    }
    if (llmTestMode) {
      await handleLlmChat(trimmed);
      return;
    }

    // Robot command path
    log({type: 'user', text: trimmed});
    setIsLoading(true);
    try {
      const result = await parseRobotCommand(trimmed);
      setLastText(trimmed);
      setLastResult(result);
      log({type: 'agent', result});
      log({
        type: 'system',
        text: executeMode
          ? 'Command prepared. /run で実行。'
          : 'Dry-run. /mode で execute に切替後、/run。'
      });
    } catch (error) {
      log({type: 'error', text: error instanceof Error ? error.message : String(error)});
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Box flexDirection="column">
      <Box marginBottom={1} paddingX={1}>
        <Text bold>Robot Agent Ink UI</Text>
        <Text dimColor>
          {`   model: ${selectedModel}   llm_test: ${llmTestMode ? 'ON' : 'OFF'}   trace: ${traceMode && traceSkill ? traceSkill : 'OFF'}`}
        </Text>
      </Box>

      <Box flexDirection="row" gap={1}>
        <SkillList
          skills={skills}
          executeMode={executeMode}
          llmTestMode={llmTestMode}
          models={models}
          selectedModel={selectedModel}
        />
        <Box flexDirection="column" flexGrow={1}>
          <ChatLog items={logs} />
          <CommandInput onSubmit={handleSubmit} isLoading={isLoading} />
        </Box>
      </Box>

      <StatusBar executeMode={executeMode} />
    </Box>
  );
}
