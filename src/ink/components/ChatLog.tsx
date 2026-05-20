import React from 'react';
import {Box, Text} from 'ink';
import type {LogItem} from '../types.js';

export function ChatLog({items}: {items: LogItem[]}) {
  const visible = items.slice(-20);

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor="blue"
      paddingX={1}
      flexGrow={1}
      minHeight={20}
    >
      {visible.map((item, index) => {
        if (item.type === 'system') {
          return (
            <Text key={index} color="yellow">
              {item.text}
            </Text>
          );
        }

        if (item.type === 'user') {
          return (
            <Box key={index} marginTop={1} flexDirection="column">
              <Text color="green">user</Text>
              <Text>{item.text}</Text>
            </Box>
          );
        }

        if (item.type === 'error') {
          return (
            <Text key={index} color="red">
              {`Error: ${item.text}`}
            </Text>
          );
        }

        if (item.type === 'trace') {
          const r = item.result;
          const e = r.evaluation;
          const m = r.metrics;
          return (
            <Box key={index} marginTop={1} flexDirection="column">
              <Text color={r.ok ? 'green' : 'red'}>
                {`task trace / ${r.expected_skill} / ${r.model}`}
              </Text>
              <Text>{`input: ${r.input}`}</Text>

              <Box marginTop={1} flexDirection="column">
                <Text color="yellow">Prompt Trace</Text>
                <Text>{`model: ${r.prompt_trace.model}`}</Text>
                <Text>{`temperature: ${r.prompt_trace.temperature}`}</Text>
                <Text>{`endpoint: ${r.prompt_trace.endpoint}`}</Text>
                <Text color="cyan">  system message</Text>
                <Text dimColor>{r.prompt_trace.system_message}</Text>
                <Text color="cyan">  user text</Text>
                <Text>{r.prompt_trace.user_text}</Text>
                <Text dimColor>
                  {`  (full user prompt: ${r.prompt_trace.final_user_prompt.length} chars — type /prompt to dump)`}
                </Text>
              </Box>

              <Box marginTop={1} flexDirection="column">
                <Text color="cyan">LLM Raw Output</Text>
                <Text dimColor>{r.raw_output}</Text>
              </Box>

              <Box marginTop={1} flexDirection="column">
                <Text color="cyan">Parsed RobotCommand</Text>
                <Text>{`skill: ${r.command.skill_id}`}</Text>
                <Text>{`object: ${r.command.object ?? 'none'}`}</Text>
                <Text>{`color: ${r.command.color ?? 'none'}`}</Text>
                <Text>{`instruction: ${r.command.vla_instruction}`}</Text>
                <Text>{`confidence: ${r.command.confidence.toFixed(2)}`}</Text>
                <Text dimColor>{`reason: ${r.command.reason}`}</Text>
              </Box>

              <Box marginTop={1} flexDirection="column">
                <Text color="cyan">Evaluation</Text>
                <Text>{`score: ${(e.score * 100).toFixed(0)}%`}</Text>
                <Text>{`skill_match:    ${e.skill_match ? 'OK' : 'NG'}`}</Text>
                <Text>{`object_match:   ${e.object_match ? 'OK' : 'NG'}`}</Text>
                <Text>{`instruction_ok: ${e.instruction_ok ? 'OK' : 'NG'}`}</Text>
                <Text>{`executable_ok:  ${e.executable_ok ? 'OK' : 'NG'}`}</Text>
                <Text>{`safety_ok:      ${e.safety_ok ? 'OK' : 'NG'}`}</Text>
                {e.notes.map((note, ni) => (
                  <Text key={`${index}-note-${ni}`} color="yellow">{`- ${note}`}</Text>
                ))}
              </Box>

              <Box marginTop={1} flexDirection="column">
                <Text color="magenta">Performance</Text>
                <Text>{`total: ${m.total_time_s.toFixed(2)}s`}</Text>
                <Text>
                  {`first_token: ${m.first_token_time_s == null ? 'n/a' : m.first_token_time_s.toFixed(2) + 's'}`}
                </Text>
                <Text>
                  {`tokens/sec: ${m.tokens_per_second == null ? 'n/a' : m.tokens_per_second.toFixed(2)}`}
                </Text>
                <Text>
                  {`cpu peak/avg: ${m.cpu_peak_percent == null ? 'n/a' : m.cpu_peak_percent.toFixed(1) + '% / ' + (m.cpu_avg_percent ?? 0).toFixed(1) + '%'}`}
                </Text>
                <Text>
                  {`gpu peak/avg: ${m.gpu_peak_percent == null ? 'n/a' : m.gpu_peak_percent.toFixed(1) + '% / ' + (m.gpu_avg_percent ?? 0).toFixed(1) + '%'}`}
                </Text>
                <Text>
                  {`vram peak: ${m.vram_peak_mb == null ? 'n/a' : (m.vram_peak_mb / 1024).toFixed(2) + ' GB / ' + ((m.vram_total_mb ?? 0) / 1024).toFixed(2) + ' GB'}`}
                </Text>
              </Box>

              {r.generated_command ? (
                <Box marginTop={1} flexDirection="column">
                  <Text color="magenta">Generated command</Text>
                  <Text dimColor>{r.generated_command}</Text>
                </Box>
              ) : null}
            </Box>
          );
        }

        if (item.type === 'llm') {
          const r = item.result;
          const m = r.metrics;
          return (
            <Box key={index} marginTop={1} flexDirection="column">
              <Text color={r.ok ? 'cyan' : 'red'}>{`llm / ${r.model}`}</Text>
              {r.ok ? (
                <>
                  <Text>{r.response}</Text>
                  <Box marginTop={1} flexDirection="column">
                    <Text color="magenta">Metrics</Text>
                    <Text>{`total: ${r.total_time_s.toFixed(2)}s`}</Text>
                    <Text>
                      {`first_token: ${r.first_token_time_s == null ? 'n/a' : r.first_token_time_s.toFixed(2) + 's'}`}
                    </Text>
                    <Text>
                      {`tokens/sec: ${r.tokens_per_second == null ? 'n/a' : r.tokens_per_second.toFixed(2)}`}
                    </Text>
                    <Text>{`eval_count: ${r.eval_count ?? 'n/a'}`}</Text>
                    <Text>
                      {`cpu peak/avg: ${m.cpu_peak_percent.toFixed(1)}% / ${m.cpu_avg_percent.toFixed(1)}%`}
                    </Text>
                    <Text>
                      {`ram peak: ${(m.ram_peak_mb / 1024).toFixed(2)} GB (${m.ram_peak_percent.toFixed(1)}%)`}
                    </Text>
                    <Text>
                      {`gpu peak/avg: ${m.gpu_peak_percent == null ? 'n/a' : m.gpu_peak_percent.toFixed(1) + '% / ' + (m.gpu_avg_percent ?? 0).toFixed(1) + '%'}`}
                    </Text>
                    <Text>
                      {`vram peak: ${m.vram_peak_mb == null ? 'n/a' : (m.vram_peak_mb / 1024).toFixed(2) + ' GB / ' + ((m.vram_total_mb ?? 0) / 1024).toFixed(2) + ' GB'}`}
                    </Text>
                  </Box>
                </>
              ) : (
                <Text color="red">{r.error ?? 'LLM call failed'}</Text>
              )}
            </Box>
          );
        }

        const r = item.result;
        return (
          <Box key={index} marginTop={1} flexDirection="column">
            <Text color={r.ok ? 'green' : 'red'}>
              {`agent / ${r.safety.level}`}
            </Text>
            <Text>{`skill: ${r.command.skill_id}`}</Text>
            <Text>{`object: ${r.command.object ?? 'none'}`}</Text>
            <Text>{`color: ${r.command.color ?? 'none'}`}</Text>
            <Text>{`instruction: ${r.command.vla_instruction}`}</Text>
            <Text>{`confidence: ${r.command.confidence.toFixed(2)}`}</Text>
            <Text dimColor>{`reason: ${r.command.reason}`}</Text>

            {r.shell_command ? (
              <Box marginTop={1} flexDirection="column">
                <Text color="magenta">generated command:</Text>
                <Text dimColor>{r.shell_command}</Text>
              </Box>
            ) : null}

            {!r.ok ? <Text color="red">{`blocked: ${r.safety.reason}`}</Text> : null}
          </Box>
        );
      })}
    </Box>
  );
}
