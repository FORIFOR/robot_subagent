import React from 'react';
import {Box, Text} from 'ink';
import type {Skill} from '../pythonBridge.js';

export function SkillList({
  skills,
  executeMode,
  llmTestMode,
  models,
  selectedModel
}: {
  skills: Skill[];
  executeMode: boolean;
  llmTestMode: boolean;
  models: string[];
  selectedModel: string;
}) {
  return (
    <Box
      flexDirection="column"
      width={42}
      borderStyle="round"
      borderColor="cyan"
      paddingX={1}
    >
      <Text bold>Skills</Text>

      <Box marginTop={1} flexDirection="column">
        {skills.map(skill => (
          <Box key={skill.id} flexDirection="column" marginBottom={1}>
            <Text color="cyan">{skill.id}</Text>
            <Text dimColor>{skill.template ?? ''}</Text>
            <Text dimColor>
              {`${skill.object_required ? 'object req' : 'object opt'} / ${skill.color_required ? 'color req' : 'color opt'}`}
            </Text>
          </Box>
        ))}
      </Box>

      <Text bold>LLM Models</Text>
      <Box marginTop={1} flexDirection="column">
        {models.length === 0 ? (
          <Text dimColor>(none loaded — /models)</Text>
        ) : (
          models.slice(0, 10).map(model => {
            const selected = model === selectedModel;
            return (
              <Text
                key={model}
                color={selected ? 'green' : undefined}
                dimColor={!selected}
              >
                {`${selected ? '▶ ' : '  '}${model}`}
              </Text>
            );
          })
        )}
      </Box>

      <Box marginTop={1} flexDirection="column">
        <Text bold>Mode</Text>
        <Text color={executeMode ? 'red' : 'yellow'}>
          {executeMode ? 'EXECUTE' : 'DRY-RUN'}
        </Text>
        <Text color={llmTestMode ? 'cyan' : undefined} dimColor={!llmTestMode}>
          {`LLM_TEST: ${llmTestMode ? 'ON' : 'OFF'}`}
        </Text>
      </Box>
    </Box>
  );
}
