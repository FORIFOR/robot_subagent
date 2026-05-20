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
