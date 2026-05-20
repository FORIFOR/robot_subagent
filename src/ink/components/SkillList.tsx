import React from 'react';
import {Box, Text} from 'ink';
import type {Skill} from '../pythonBridge.js';

export function SkillList({
  skills,
  executeMode
}: {
  skills: Skill[];
  executeMode: boolean;
}) {
  return (
    <Box
      flexDirection="column"
      width={40}
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
              {skill.object_required ? 'object req' : 'object opt'}
              {' / '}
              {skill.color_required ? 'color req' : 'color opt'}
            </Text>
          </Box>
        ))}
      </Box>

      <Text bold>Examples</Text>
      <Box flexDirection="column" marginTop={1}>
        {skills.slice(0, 6).map(skill => {
          const aliases = skill.aliases ?? [];
          if (aliases.length === 0) return null;
          return (
            <Box key={`ex-${skill.id}`} flexDirection="column" marginBottom={1}>
              <Text color="cyan">{skill.id}</Text>
              {aliases.slice(0, 2).map(alias => (
                <Text key={alias} dimColor>
                  {`  - ${alias}`}
                </Text>
              ))}
            </Box>
          );
        })}
      </Box>

      <Box marginTop={1} flexDirection="column">
        <Text bold>Mode</Text>
        <Text color={executeMode ? 'red' : 'yellow'}>
          {executeMode ? 'EXECUTE' : 'DRY-RUN'}
        </Text>
      </Box>
    </Box>
  );
}
