import React from 'react';
import {Box, Text} from 'ink';

export function StatusBar({executeMode}: {executeMode: boolean}) {
  return (
    <Box justifyContent="space-between" paddingX={1}>
      <Text dimColor>
        /help /run /mode /skills /clear /quit · Ctrl+L clear · Ctrl+C quit
      </Text>
      <Text color={executeMode ? 'red' : 'yellow'}>
        {executeMode ? 'EXECUTE' : 'DRY-RUN'}
      </Text>
    </Box>
  );
}
