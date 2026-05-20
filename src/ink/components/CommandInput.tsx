import React from 'react';
import {Box, Text} from 'ink';
import {TextInput} from '@inkjs/ui';

export function CommandInput({
  onSubmit,
  isLoading
}: {
  onSubmit: (value: string) => void;
  isLoading: boolean;
}) {
  return (
    <Box borderStyle="round" borderColor="yellow" paddingX={1}>
      <Text color="yellow">{isLoading ? '… ' : '> '}</Text>
      <TextInput
        placeholder="ロボット命令を入力。/help /run /mode /skills /clear /quit"
        onSubmit={onSubmit}
      />
    </Box>
  );
}
