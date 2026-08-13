---
name: small-project-test-run
description: Execute an approved small-project test packet, preserve raw evidence, and return results for strong-model judgment. Use only after test planning is complete.
---

# Small Project Test Run

执行已批准的测试任务包；不重新设计测试标准，不把“命令成功启动”冒充功能正确。

## 进入条件

必须收到：测试 ID、关联验收标准、环境与前置条件、命令或人工步骤、输入数据、预期或完整性判据、容差、证据格式。缺项时返回测试规划者补充，不自行猜测。

## 执行规则

1. 记录环境、版本与实际执行命令。
2. 严格按任务包准备数据并执行；不得静默修改样本、预期或容差。
3. 保存原始输出、退出码、日志、产物路径，以及要求的截图或可视化证据。
4. 对每个测试标记 `PASS`、`FAIL`、`BLOCKED` 或 `NOT_RUN`，不得用整体印象替代逐项结果。
5. 不在测试执行阶段顺手修代码。发现产品问题时记录最小复现并交还强模型分类。
6. 任何外部写入、部署、真实消息、付费操作或破坏性测试仍需单独授权。

## 三类测试

### 无用户数据

至少执行导入或配置、构建或启动，以及一条最小代表路径。通过只证明当前环境下基本可运行，不证明业务结果正确。

### 有数据且有预期

按已确认的结果、容差和可视化要求比较；差异必须量化或给出可复现证据。

### 有数据但无明确预期

仅依据测试规划者定义的结构、范围、单位、缺失值、确定性或不变量判据执行。若没有可判定的 oracle，结果只能标记 `BLOCKED`，不得声称“准确”。

## 返回格式

```text
Test run: I01-TST-001
Environment: ...
Results:
- I01-TST-001 -> PASS|FAIL|BLOCKED|NOT_RUN
  command/step: ...
  evidence: I01-EVD-001, <path or raw excerpt>
  observed: ...
  expected/oracle: ...
Suspected class: product | test | environment | requirement
Unverified: ...
```

由强模型测试判定者确认 `G6 TEST_PASS`，执行者不得自批门禁。
