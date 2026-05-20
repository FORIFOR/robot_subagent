import React, {useEffect, useState} from 'react';
import {Box, Text, useApp, useInput} from 'ink';
import {
  executeRobotCommand,
  loadSkills,
  parseRobotCommand,
  type ParseResponse,
  type Skill
} from './pythonBridge.js';
import type {LogItem} from './types.js';
import {SkillList} from './components/SkillList.js';
import {ChatLog} from './components/ChatLog.js';
import {CommandInput} from './components/CommandInput.js';
import {StatusBar} from './components/StatusBar.js';

export function App() {
  const {exit} = useApp();

  const [skills, setSkills] = useState<Skill[]>([]);
  const [logs, setLogs] = useState<LogItem[]>([
    {type: 'system', text: 'Robot Agent Ink UI started. mode=DRY-RUN'}
  ]);
  const [executeMode, setExecuteMode] = useState(false);
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
      log({
        type: 'error',
        text: error instanceof Error ? error.message : String(error)
      });
    }
  }

  useEffect(() => {
    void refreshSkills();
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
      log({type: 'error', text: 'Execute mode OFFです。/mode (F9) で切替してください。'});
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
      log({
        type: 'error',
        text: error instanceof Error ? error.message : String(error)
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;

    if (trimmed === '/quit' || trimmed === '/exit' || trimmed === 'q' || trimmed === 'exit' || trimmed === 'quit') {
      exit();
      return;
    }
    if (trimmed === '/help') {
      log({
        type: 'system',
        text:
          '/run    直前のコマンドを実行 (execute mode のみ)\n' +
          '/mode   dry-run <-> execute 切替\n' +
          '/skills skill_registry.yaml を再読込\n' +
          '/clear  ログクリア\n' +
          '/quit   終了\n\n' +
          '例: キューブをつかんで / りんごを取って / ばいばい'
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
    if (trimmed === '/mode' || trimmed === '/toggle') {
      setExecuteMode(prev => {
        log({type: 'system', text: `Mode -> ${!prev ? 'EXECUTE' : 'DRY-RUN'}`});
        return !prev;
      });
      return;
    }
    if (trimmed === '/run') {
      await runLast();
      return;
    }
    if (trimmed.startsWith('/')) {
      log({type: 'error', text: `Unknown command: ${trimmed}. /help を確認してください。`});
      return;
    }

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
      log({
        type: 'error',
        text: error instanceof Error ? error.message : String(error)
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Box flexDirection="column">
      <Box marginBottom={1} paddingX={1}>
        <Text bold>Robot Agent Ink UI</Text>
      </Box>

      <Box flexDirection="row" gap={1}>
        <SkillList skills={skills} executeMode={executeMode} />
        <Box flexDirection="column" flexGrow={1}>
          <ChatLog items={logs} />
          <CommandInput onSubmit={handleSubmit} isLoading={isLoading} />
        </Box>
      </Box>

      <StatusBar executeMode={executeMode} />
    </Box>
  );
}
