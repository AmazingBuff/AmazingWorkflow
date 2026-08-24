# SKSE Plugin Template Spec

状态：已确认
版本：0.1
日期：2026-08-23

## 1. 定位

本套件是 **Skyrim SKSE 插件工程模板** 的宿主中立源包，与 `small-project-workflow-spec`、
`lightweight-coding-agent-workflow-spec` 并列。它不是一个编排型工作流，而是一个
**单 skill 工具套件**：任何具备「原生 skill 加载 + 文件读写 + 运行 python」能力的
agent 都可以部署并使用，无需子代理、沙箱或其他宿主特性。

功能概要：以 CorpseESP 与 FollowerSummonAllyFix 两个真实项目验证过的工程结构为蓝本，
脚手架生成支持 Skyrim SE / AE / VR 多运行时（CommonLibSSE）的 C++ DLL 插件项目，
可选 INI 配置、热键、D3D11 Present 钩子、vtable 钩子、事件监听模块。

## 2. 套件布局

```text
skse-plugin-template-spec/
└── skills/
    └── skse-plugin-template/
        ├── SKILL.md                  # 使用入口（触发描述、执行流程、内置参考索引）
        ├── assets/
        │   └── coding-rules/         # 编码规范组件（内嵌，随套件分发）
        │       ├── small-project-code-contract/SKILL.md
        │       └── small-project-cpp-rules/   # 含 references/ 五份细则与检查脚本
        ├── references/               # structure / patterns / multi-runtime / build-and-verify
        ├── scripts/
        │   └── scaffold.py           # 脚手架生成器（仅标准库）
        └── templates/                # 生成的工程模板（C++ / CMake / 清单 / 功能模块）
```

## 3. 来源与溯源

| 内容 | 来源 | 说明 |
|---|---|---|
| 工程模板与脚手架 | CorpseESP / FollowerSummonAllyFix 验证结构 | 经 DSH 部署版迭代（规范对齐 + bug 修复）后收入 |
| `assets/coding-rules/` | `small-project-workflow-spec` @ git `5fb6ec0` | 经 lightweight-coding-workflow 组合适配（编排词汇调整）；**只取 code-contract 与 cpp-rules 两组件**，python-rules 与本套件无关 |

SPW 上游更新时，重新对照 `assets/coding-rules/` 增量同步；组件头部的溯源块
标明了基线版本。编码风格的**单一权威来源就是这套内嵌组件**——生成的项目不携带
`.clang-format` / `.editorconfig` 等本地格式器配置。

## 4. 部署与适配（各 agent）

通用原则：把 `skills/skse-plugin-template/` 整目录复制到目标 agent 的 skills 根
（项目级或用户级均可）。skill 只依赖原生加载器、文件工具和 python3 运行
scaffold；组件文档按 skill 根的相对路径解析，无任何宿主绝对路径。

| Agent | 部署位置 | 备注 |
|---|---|---|
| DeepSeek Harness (DSH) | `~/.dsh/skills/skse-plugin-template/` | provider 监视自动生效，免重启 |
| Codex | 用户级 skill 安装目录 | 纯 skill 调用即可，不需要 `lightweight_implementer` 类自定义 agent |
| OpenCode | 项目 `.opencode/skill/...` 或全局 skills | 显式 `/skse-plugin-template` 调用 |
| Pi | 项目 skills 目录（隐藏隐式触发、保留显式调用） | 无内置 subagent 需求 |
| Claude Code 及其他 | 对应 skills 根（如 `.claude/skills/`） | 同通用原则 |

适配 checklist：

- [ ] skills 根中出现 `skse-plugin-template/SKILL.md` 且被加载器识别。
- [ ] `scripts/scaffold.py --help` 可运行（python3，仅标准库）。
- [ ] 从该 agent 会话内读取 `assets/coding-rules/small-project-cpp-rules/SKILL.md`
      成功（验证组件路径解析）。
- [ ] 试生成一个插件目录并核对：文件头日期注入、preset 名 `msvc release`、
      无 Tab、无未解析占位符。

## 5. 非目标

不提供编译工具链本身（VS2022 / vcpkg 由使用者自备，见 build-and-verify.md）；
不做多插件批量管理；不引入网络依赖（`--git-init` 的 submodule 拉取除外，
且需用户显式选择）。
