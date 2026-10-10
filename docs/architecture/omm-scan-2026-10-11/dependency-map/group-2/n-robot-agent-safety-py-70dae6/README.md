# dependency-map/group-2/n-robot-agent-safety-py-70dae6

[解析トップへ戻る](../../../README.md)

確認済みファイル: `robot_agent/safety.py`

解析: Python AST。静的なimport／export参照です。関数の実行順序やHTTP通信は表していません。

宣言: `safety_check`

- `__future__` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `schemas` → `robot_agent/schemas.py`（内容確認済み）
- `skills` → `robot_agent/skills.py`（内容確認済み）


```mermaid
graph TD
    source["ソース\nrobot_agent/safety.py"]
    n-future-05a733["__future__\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-future-05a733
    n-schemas-c20018["schemas\nrobot_agent/schemas.py"]
    source -->|"Python AST: import／export"| n-schemas-c20018
    n-skills-816f2b["skills\nrobot_agent/skills.py"]
    source -->|"Python AST: import／export"| n-skills-816f2b
```

## 要素の説明

### n-future-05a733

参照名: `__future__`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-schemas-c20018

参照名: `schemas`

対応する実在ソース: `robot_agent/schemas.py`。内容確認済み。

### n-skills-816f2b

参照名: `skills`

対応する実在ソース: `robot_agent/skills.py`。内容確認済み。

### source

`robot_agent/safety.py` の内容を確認しました。

