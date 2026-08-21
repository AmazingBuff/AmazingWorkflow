# Git 提交与 Changelog 规范

状态：正式规范

版本：1.0

适用范围：本仓库及其子项目的新提交。既有 Git 历史不要求重写。

本规范中的“必须（MUST）”表示硬要求，“应该（SHOULD）”表示默认做法，“可以（MAY）”表示按项目情况选择。

## 1. 目标

每个提交必须满足三个结果：

1. **可理解**：评审者不依赖作者口头说明也能知道改了什么、为什么改。
2. **可验证**：提交包含证明改动正确所需的测试、文档和配置。
3. **可回退**：撤销该提交时，不会意外撤销另一个无关功能。

提交数量不是目标。正确的粒度是“一个完整、独立、可验证的逻辑变更”。

## 2. 什么时候提交

### 2.1 必须提交的时点

满足以下全部条件时，必须形成提交：

- 一个逻辑变更已经完成，例如一个功能、缺陷修复、重构步骤或文档变更。
- 相关代码、测试、文档、配置和 Changelog 已保持一致。
- 与本次变更相关的格式化、静态检查、构建和测试已经通过；无法执行的检查已明确记录原因。
- 已检查暂存区，确认不存在无关修改、调试代码、临时文件或敏感信息。
- 该提交可以独立解释，并能在不破坏其他无关工作的情况下独立回退。

以下场景也应该先形成一个干净提交，再继续工作：

- 准备切换到另一个无关任务。
- 准备把工作交给其他开发者或 Agent。
- 准备开始高风险重构，而当前逻辑单元已经完整且验证通过。
- 准备执行可能产生大量机械改动的升级、格式化或代码生成。

### 2.2 不得提交的状态

以下内容不得作为普通提交进入共享分支：

- 无法构建、相关测试失败或已知行为不完整的中间状态。
- 多个互不相关的功能、修复和重构混在同一提交中。
- 仅为了“保存一下”而产生、没有稳定含义的快照。
- 密钥、令牌、密码、私有证书、真实个人数据或内部临时地址。
- 编辑器缓存、构建目录、运行日志、崩溃转储和其他应被忽略的临时产物。
- 被注释掉的旧实现、未说明用途的调试输出或无追踪信息的临时 TODO。

### 2.3 WIP 提交

`WIP` 提交只允许用于个人分支上的临时备份或跨会话交接，并必须满足：

- 不得合并到受保护分支。
- 消息以 `WIP:` 开头，并说明当前状态和剩余工作。
- 在创建 Pull Request 或合并前，必须通过 rebase、squash 或重新提交整理为符合本规范的提交。
- 不得用 WIP 提交规避失败测试、Review 或 Changelog 要求。

## 3. 一个提交应包含什么

### 3.1 原子提交边界

一个提交必须包含完成同一逻辑变更所需的全部内容，并排除无关内容。

通常应放在同一提交中的内容：

- 功能或修复的实现代码。
- 直接证明该行为的新增或更新测试。
- 因公共接口、配置、命令或用户行为变化而需要更新的文档。
- 与本次变更直接相关的配置、迁移文件、生成清单或依赖锁文件。
- 符合第 4 节条件的 Changelog 条目。

通常应拆成独立提交的内容：

- 与功能无关的重命名、目录移动或全仓格式化。
- 为未来工作准备、当前变更并不需要的抽象或重构。
- 多个可以独立发布、独立验证或独立回退的功能。
- 工具链升级与业务功能修改，除非两者无法安全分离。

### 3.2 内容对应关系

| 变更类型 | 同一提交必须包含 | 不应混入 |
| --- | --- | --- |
| 新功能 | 实现、测试、用户文档、必要 Changelog | 无关重构、顺手修复 |
| 缺陷修复 | 修复、可复现或回归测试、必要 Changelog | 其他缺陷、全局清理 |
| 重构 | 等价行为证明、相关测试 | 新功能、行为变化 |
| 依赖升级 | 清单、锁文件、兼容修改、验证证据、必要 Changelog | 无关依赖升级 |
| 数据或配置迁移 | 迁移、兼容代码、验证和回退说明 | 无关结构调整 |
| 纯文档 | 完整文档改动及有效链接 | 产品代码修改 |
| 机械格式化 | 仅格式变化 | 逻辑变化、重命名 |

### 3.3 暂存要求

- 应按明确路径暂存文件，或使用 `git add -p` 逐块选择。
- 不应在没有检查工作树的情况下直接使用 `git add .` 或 `git add -A`。
- 文件中同时包含相关和无关修改时，必须拆分暂存或先整理文件。
- 提交前必须检查 `git diff --cached`，暂存区内容才是即将提交的真实边界。

## 4. Changelog 规范

### 4.1 Changelog 与提交历史的区别

`CHANGELOG.md` 面向使用者和发布维护者，回答“升级后会发生什么变化”。Git 提交历史面向开发者，记录“代码如何演进”。

因此：

- 不是每个提交都需要 Changelog。
- 需要 Changelog 的变更，条目必须与实现放在同一逻辑提交中。
- 不得把提交消息逐条复制到 Changelog。
- Changelog 应描述用户影响，而不是内部函数、文件或重构过程。

### 4.2 什么时候必须更新 Changelog

| 变更 | 是否更新 | 推荐分类 |
| --- | --- | --- |
| 用户可见的新功能 | 必须 | `Added` |
| 用户可见的缺陷修复 | 必须 | `Fixed` |
| 破坏兼容性的变化 | 必须 | `Changed` 或 `Removed`，并标注迁移方法 |
| 安全修复 | 必须 | `Security`；披露程度遵循安全策略 |
| 可观察的性能变化 | 应该 | `Changed` |
| 安装、配置、部署或构建方式变化 | 影响使用者时必须 | `Changed` |
| 公共 API 废弃 | 必须 | `Deprecated` |
| 内部重构且行为不变 | 不需要 | 无 |
| 测试、格式、注释或内部清理 | 不需要 | 无 |
| 仅修正文档错别字 | 不需要 | 无 |
| 发布文档本身是产品能力 | 应该 | `Changed` |

### 4.3 文件结构

项目默认使用仓库根目录下的 `CHANGELOG.md`。未发布内容写入 `Unreleased`：

如果项目尚无 `CHANGELOG.md`，第一个需要 Changelog 的变更必须按本节模板创建该文件，不得因文件不存在而跳过记录。

```markdown
# Changelog

## [Unreleased]

### Added

- Add project-level host adapter validation before implementation starts.

### Changed

- Require implementation contracts to record protocol and adapter versions.

### Fixed

- Preserve uncommitted user changes when an implementation task is blocked.
```

发布时把已发布条目移动到带版本和日期的章节：

```markdown
## [1.2.0] - 2026-08-21
```

只保留有内容的分类。分类顺序为：

1. `Added`
2. `Changed`
3. `Deprecated`
4. `Removed`
5. `Fixed`
6. `Security`

### 4.4 条目写法

Changelog 条目必须：

- 默认使用英文；同一仓库不得混用语言。
- 使用主动语态和现在时，以 `Add`、`Change`、`Fix`、`Deprecate`、`Remove` 或 `Prevent` 等动词开头。
- 一条只描述一个使用者可以观察或需要采取行动的变化。
- 说明结果和影响，不复述实现细节。
- 以句号结尾。
- 在有正式 Issue 或 Pull Request 时，可以在末尾添加引用。

推荐：

```markdown
- Add CSV export for filtered report results. (#123)
- Fix duplicate notifications after reconnecting. (#127)
```

不推荐：

```markdown
- Update export_manager.py.
- Refactor notification code.
- Various fixes.
```

### 4.5 Breaking Change

破坏兼容性的条目必须同时说明：

- 原行为。
- 新行为。
- 受影响对象。
- 迁移方法。
- 必要时的回退方式。

示例：

```markdown
### Changed

- **BREAKING:** Require `host_adapter` in implementation contracts. Existing approved v0.1 contracts must continue with v0.1 resources or be replanned as v0.2.
```

## 5. 提交消息规范

### 5.1 格式

提交消息采用 Conventional Commits 风格：

```text
<type>(<scope>)!?: <summary>

<body>

<footer>
```

只有标题是必需的。`scope`、`!`、正文和页脚按情况使用。

### 5.2 Type

| Type | 用途 | 通常需要 Changelog |
| --- | --- | --- |
| `feat` | 新增用户或开发者可用能力 | 是 |
| `fix` | 修复错误行为 | 用户可见时是 |
| `refactor` | 不改变行为的代码结构调整 | 否 |
| `perf` | 性能优化 | 可观察时是 |
| `docs` | 仅文档变化 | 通常否 |
| `test` | 仅测试变化 | 否 |
| `build` | 构建系统、依赖或打包变化 | 影响使用时是 |
| `ci` | CI/CD 配置变化 | 影响交付时是 |
| `style` | 不改变语义的格式调整 | 否 |
| `chore` | 不能归入以上类型的维护工作 | 通常否 |
| `revert` | 撤销已有提交 | 取决于被撤销内容 |

安全修复使用 `fix(security)`，不要为了安全变更自定义不兼容的 Type。

当一个逻辑提交同时包含实现、测试、文档和 Changelog 时，Type 按主要交付结果选择。例如新增功能仍使用 `feat`，不能因为同时修改测试和文档而改成 `test` 或 `docs`。

### 5.3 Scope

- Scope 表示稳定的模块、组件或领域，例如 `workflow`、`adapter`、`cmake`、`docs`。
- Scope 必须使用小写英文，可包含数字、点、斜杠或连字符。
- Scope 不应是临时文件名、人员姓名、Issue 编号或笼统的 `misc`。
- 变更横跨多个模块且不存在自然主模块时，可以省略 Scope。

### 5.4 Summary

- 默认使用英文；同一仓库必须保持语言一致。
- 使用祈使语气和现在时，例如 `add`、`fix`、`prevent`、`remove`。
- 首字母小写，末尾不加句号。
- 描述结果，不写过程，不使用 `update stuff`、`fix bug` 等模糊词。
- 完整标题建议不超过 72 个字符。

推荐：

```text
feat(adapter): add verified host capability gate
fix(cmake): preserve the selected toolchain file
docs(git): define commit and changelog policy
```

不推荐：

```text
update code
fix bug
feat: added some changes.
chore: new user feature
```

### 5.5 Body

出现以下任一情况时，应编写正文：

- 标题无法说明修改原因。
- 存在非显然的设计决策或取舍。
- 需要说明验证方式、限制或兼容性。
- 提交包含迁移、回退或运维影响。

正文应解释“为什么”和“产生什么影响”，不要逐文件复述 diff。标题与正文之间必须空一行，正文建议每行不超过 100 个字符。

示例：

```text
feat(workflow): add host adapter validation

Reject non-verified adapters before contract approval so unsupported
hosts cannot start product-code writes. Keep the existing Codex path
unchanged.
```

### 5.6 Footer

页脚用于结构化元数据：

```text
Refs: #123
Closes: #127
Co-authored-by: Name <email@example.com>
```

- `Refs` 表示关联但不自动关闭。
- `Closes` 只在提交合入目标分支后应关闭 Issue 时使用。
- 不得引用不存在或与提交无关的 Issue。

### 5.7 Breaking Change 消息

破坏兼容性必须同时使用标题中的 `!` 和正文后的 `BREAKING CHANGE:`：

```text
feat(contract)!: require host adapter metadata

Bind every implementation task to one verified adapter and version.

BREAKING CHANGE: New contracts must include protocol_version,
host_adapter, and adapter_version.
Migration: replan an old task or continue it with matching v0.1 resources.
```

### 5.8 Revert 消息

撤销提交应使用：

```text
revert(workflow): revert host adapter validation

This reverts commit <full-sha>.
```

如果撤销会重新引入已知风险，正文必须说明风险和后续计划。

## 6. 标准提交流程

### 6.1 检查工作树

```bash
git status --short
git diff
```

确认哪些修改属于本次逻辑变更，哪些必须保留到后续提交。

### 6.2 运行验证

运行与变更相关的格式化、静态检查、构建和测试。不得用无关测试成功替代相关验证。

### 6.3 精确暂存

```bash
git add path/to/file1 path/to/file2
```

存在混合修改时使用：

```bash
git add -p
```

### 6.4 检查暂存内容

```bash
git diff --cached --stat
git diff --cached
```

检查：

- 逻辑边界是否单一。
- 测试、文档和 Changelog 是否齐全。
- 是否存在密钥、调试输出、临时文件或无关格式变化。

### 6.5 提交并复核

```bash
git commit
git show --stat --oneline HEAD
```

确认最终消息和文件列表与预期一致。未经明确授权，不得自动推送。

## 7. 特殊场景

### 7.1 纯重构

- 使用 `refactor`。
- 必须证明外部行为保持不变。
- 不得在同一提交中增加功能或改变接口。
- 若重构是功能实现的必要组成且无法独立验证，可以与功能同提交，但正文必须解释原因。

### 7.2 大规模格式化或生成代码

- 应作为独立提交。
- 提交中不得包含逻辑变化。
- 生成文件只有在仓库策略要求版本控制时才提交，并必须与源输入保持同步。

### 7.3 依赖升级

- 一次提交只处理一个依赖或一个必须同步升级的依赖组。
- 同时提交清单和锁文件。
- 记录兼容修改、构建和测试结果。
- 影响安装、运行或安全时更新 Changelog。

### 7.4 数据迁移

- 迁移文件、兼容代码、验证和回退说明必须形成一个可部署逻辑单元。
- 不可逆迁移必须在提交前获得专项批准，不得仅依靠提交消息授权。

### 7.5 多提交功能

一个较大功能可以拆成多个提交，但每个提交都必须独立可理解和可验证。推荐顺序：

1. 无行为变化的准备性重构。
2. 核心实现和测试。
3. 独立的适配层或迁移。
4. 文档和 Changelog；若它们是功能完整性的必要部分，应与对应实现同提交。

合并前必须整理掉 `WIP`、`fixup!`、`squash!` 和无意义的试错提交。

## 8. 提交前检查清单

- [ ] 本提交只包含一个逻辑变更。
- [ ] 相关实现、测试、文档、配置和迁移保持一致。
- [ ] 相关格式化、静态检查、构建和测试已通过。
- [ ] 需要 Changelog 的变更已更新 `Unreleased`。
- [ ] 暂存区不含密钥、调试代码、临时文件和无关修改。
- [ ] 提交可以独立解释、验证和回退。
- [ ] Type 与 Scope 正确。
- [ ] Summary 使用祈使语气，清晰且不超过建议长度。
- [ ] Breaking Change 同时包含 `!`、正文说明和迁移方法。
- [ ] 已检查 `git diff --cached`。

## 9. 完整消息模板

```text
<type>(<scope>)!?: <imperative summary>

<why this change is needed and what behavior it produces>

<verification, compatibility, migration, or rollback notes when relevant>

Refs: #<issue>
BREAKING CHANGE: <impact and migration steps>
```

删除不适用的可选段落，不得保留占位符。
