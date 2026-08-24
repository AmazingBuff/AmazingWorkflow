# 项目结构与代码抽象

## 目录

- 项目编排
- 依赖方向
- 抽象选择
- 所有权与生命周期
- 数据流与状态
- 错误边界
- 变更粒度

## 项目编排

### 既有项目

保留稳定目录、目标和安装布局。新增文件跟随受影响模块的现有入口；不要仅为符合模板而移动代码。

### 绿地项目

从最小结构开始，按需求增加目录：

```text
project/
├── CMakeLists.txt
├── CMakePresets.json       # 需要可重复本地配置时
├── cmake/                  # 可复用 CMake 模块
├── include/<project>/      # 库的公共头
├── src/                    # 私有实现
├── apps/ 或 tools/         # 可执行入口
├── tests/                  # 自动化测试
├── examples/               # 面向使用者的示例
└── docs/                   # 需要独立文档时
```

- 仅库需要稳定公共头时创建 `include/`；纯可执行项目可把头放在 `src/`。
- 仅组件可以独立构建、测试或复用时拆成独立 CMake 目标。
- 测试和示例职责不同：测试验证行为，示例展示用法。
- 外部依赖优先交给包管理器；确需源码内置时使用项目既有的第三方目录名称。
- 按领域或能力纵向组织复杂模块，避免把所有类仅按文件类型横向堆放。

## 依赖方向

保持依赖由易变外层指向稳定内层：

```text
application / composition root
                ↓
use-case orchestration
                ↓
domain API and stable contracts
                ↓
adapters and concrete implementations
                ↓
operating system / external libraries
```

- 让公共接口使用领域类型，不泄漏具体实现或外部库细节。
- 把实现选择集中到 composition root、工厂或依赖注入点。
- 公共头能前向声明时避免包含私有实现头。
- 禁止内层模块反向调用应用层；跨模块协作通过稳定契约。
- 循环依赖出现时先检查职责划分，不用全局注册表掩盖结构问题。

## 抽象选择

### 直接实现

单一路径、单一调用方且没有稳定变化轴时，使用函数或具体类型。不要为“以后可能需要”预建接口。

### 运行时替换

存在多实现、插件、外部边界或测试替身时，定义小型契约：

```cpp
class Storage
{
public:
    virtual ~Storage() = default;
    virtual Result load(Key const& key) = 0;
};

class FileStorage final : public Storage
{
public:
    Result load(Key const& key) override;
};
```

- 接口表达调用者需要的行为，不镜像实现类全部方法。
- 具体实现使用 `final`，重写使用 `override`。
- 把后端选择留在装配点，不让调用方到处进行类型分支。
- 空实现只满足契约定义的最小语义，不自行发明状态变化或诊断。

### 编译期策略

类型、allocator、比较器、序列化策略或无运行时替换需求的算法变体，优先使用 concepts、traits、policy 或 callable。

- 把约束写成 concept/`requires`，使错误靠近调用点。
- 让容器或算法主体依赖窄 policy，不复制整套实现。
- 先实现 iterator/range 核心，再添加容器便利重载。
- 不把模板用于隐藏普通控制流或规避清晰接口。

### 参数对象、Builder 与 Graph

- 参数超过少量稳定值、存在可选组合或需要向后兼容扩展时，使用 `Options`、`Config` 或 descriptor。
- Builder 应负责建立不变量、校验或分阶段构造；只包装 setter 时直接使用参数对象。
- 只有执行顺序由声明式依赖决定时使用 graph：先收集读写关系，再验证、排序、编译并执行。
- 简单顺序流程保持显式函数调用，不为假设中的并行引入图结构。

### Pimpl 与类型擦除

- 需要稳定 ABI、隔离重型依赖或缩短公共头编译影响时考虑 Pimpl。
- 需要保存任意实现且调用方不应见到具体类型时使用 type erasure。
- type erasure 必须定义空状态、复制、移动、析构和异常保证。
- 不因隐藏实现而牺牲所有权和失败语义。

## 所有权与生命周期

- 默认使用值语义和 RAII。
- 唯一所有权使用对象成员或 `std::unique_ptr`；共享所有权只用于真实共享生命周期。
- 裸指针和引用默认表示借用，不负责销毁；生命周期必须由接口或类型关系保证。
- 资源包装器明确 copy/move/destructor/swap 语义，并按创建逆序释放。
- C ABI、插件或自定义 allocator 边界可使用成对 create/destroy，但必须共享同一分配域：

```cpp
LibraryHandle* library_create(LibraryOptions const* options);
void library_destroy(LibraryHandle* handle) noexcept;
```

- 不在内部偷偷加入全局锁；线程安全模型应成为类型或 API 合同的一部分。

## 数据流与状态

- 公共 API 使用稳定输入/输出类型；阶段间临时数据留在私有实现。
- 可替换阶段通过小接口或 callable 注入，固定阶段直接调用。
- 便利重载转发到一个 canonical implementation，不复制校验和转换。
- 对昂贵且可由稳定键唯一标识的资源才建立缓存；同时定义失效和释放条件。
- 先创建并验证新状态，再替换现有状态，避免失败后破坏可用数据。
- 将外部类型与领域类型的转换集中在适配层，并处理未知值。

## 错误边界

- 使用项目既有的错误模型；不要在同一层混用状态码、异常和空值表达同一失败。
- 在外部边界添加操作、输入和资源上下文，再转换为领域错误。
- 内部不变量使用 assertion；可恢复输入错误返回可检查结果。
- 不吞掉返回值，不记录无上下文的笼统失败。
- 异常不得穿越不支持异常的 ABI 边界。

## 变更粒度

- 一次修改处理一个可描述的行为单元。
- 改接口前搜索声明、实现、调用方、测试、序列化和安装导出。
- 先复用现有扩展点；只有现有结构无法表达需求时增加抽象。
- 不顺带升级工具链、重排目录或格式化无关文件。
- 将机械重命名与行为修改拆开，保持 diff 可审查。
