# dependency-map/group-2/n-robot-agent-skills-py-d3a3e6

[解析トップへ戻る](../../../README.md)

確認済みファイル: `robot_agent/skills.py`

解析: Python AST。静的なimport／export参照です。関数の実行順序やHTTP通信は表していません。

宣言: `load_skill_registry`, `save_skill_registry`, `_skill_to_yaml_dict`, `render_skill_list`, `find_skill`, `add_skill`, `remove_skill`

- `__future__` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `pathlib` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `typing` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `yaml` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `schemas` → `robot_agent/schemas.py`（内容確認済み）


```mermaid
graph TD
    source["ソース\nrobot_agent/skills.py"]
    n-future-05a733["__future__\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-future-05a733
    n-pathlib-4471f7["pathlib\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-pathlib-4471f7
    n-typing-02d7d3["typing\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-typing-02d7d3
    n-yaml-c94c08["yaml\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-yaml-c94c08
    n-schemas-c20018["schemas\nrobot_agent/schemas.py"]
    source -->|"Python AST: import／export"| n-schemas-c20018
```

## 要素の説明

### n-future-05a733

参照名: `__future__`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-pathlib-4471f7

参照名: `pathlib`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-schemas-c20018

参照名: `schemas`

対応する実在ソース: `robot_agent/schemas.py`。内容確認済み。

### n-typing-02d7d3

参照名: `typing`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-yaml-c94c08

参照名: `yaml`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### source

`robot_agent/skills.py` の内容を確認しました。

