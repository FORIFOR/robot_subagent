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
