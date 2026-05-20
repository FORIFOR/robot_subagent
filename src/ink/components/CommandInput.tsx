import React, {useState} from 'react';
import {Box, Text} from 'ink';
import {TextInput} from '@inkjs/ui';

export function CommandInput({
  onSubmit,
  isLoading
}: {
  onSubmit: (value: string) => void;
  isLoading: boolean;
}) {
  // @inkjs/ui v2 TextInput is uncontrolled. Remount it after every submit
  // (by bumping `resetKey`) so the typed text disappears.
  const [resetKey, setResetKey] = useState(0);

  return (
    <Box borderStyle="round" borderColor="yellow" paddingX={1}>
      <Text color="yellow">{isLoading ? '… ' : '> '}</Text>
      <TextInput
        key={resetKey}
        placeholder="ロボット命令を入力。/help /run /mode /skills /clear /quit"
        onSubmit={value => {
          onSubmit(value);
          setResetKey(k => k + 1);
        }}
      />
    </Box>
  );
}
