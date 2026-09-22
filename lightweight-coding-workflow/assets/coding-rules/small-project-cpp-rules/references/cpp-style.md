# C++ 编码规则

## 目录

- 适配原则
- 文件与命名
- 文件结构、include 与命名空间
- 格式
- 类型与接口
- 多后端、friend 与配置结构体
- 所有权与错误
- 注释与禁止项

## 适配原则

先读取 `.clang-format`、`.clang-tidy`、`.editorconfig`、编译选项、CI 和受影响模块的至少两个第一方样本。已有机器可执行规则、公共 ABI、框架约定和局部稳定惯例优先；不要为了符合本文件批量改写稳定旧代码。

以下规则是用户指定的 C++ 规范基线，默认用于绿地项目以及新增或实际触及的代码。既有项目需要兼容时，按 `decision-policy.md` 记录例外、保持修改面最小，并只格式化本次触及范围。

## 文件与命名

### 文件命名

- 文件名使用全小写和下划线分隔：`render_driver.h`、`dx12_device.cpp`。
- 绿地项目的头文件使用 `.h`，实现文件使用 `.cpp`；既有项目只有在兼容性要求下沿用其他扩展名。
- 每个 `.h` / `.cpp` 文件以以下头注释开头：

```cpp
//
// Created by AmazingBuff on YYYY/MM/DD.
//
```

新增文件填写实际日期；已有文件不因本规范而批量补写或重排头注释。

### 代码命名

| 类别 | 规则 | 示例 |
|---|---|---|
| 类 / 结构体 | `PascalCase` | `Device`, `RenderSystem`, `GraphicsContext` |
| 枚举类型名 | `PascalCase` | `Backend`, `ShaderStage` |
| 枚举值 | `e_` + `snake_case` | `e_graphics`, `e_vulkan` |
| 成员变量 | `m_` + `snake_case` | `m_device`, `m_allocator` |
| 外部借用成员指针 | `m_ref_` + `snake_case` | `m_ref_adapter` |
| 全局常量（`const`/`constexpr`） | `Upper_Snake_Case` | `Max_Allowable_Error`, `Default_Timeout` |
| 全局变量 | `g_` + `snake_case` | `g_render_engine`, `g_swap_chain` |
| 函数 / 方法 | `snake_case` | `fetch_queue()`, `import_scene()` |
| 局部变量（含局部 `const`） | `snake_case` | `queue_desc`, `render_node` |
| 局部静态变量 / `static`（含 `static constexpr`） | `s_` + `snake_case` | `s_queue_count`, `s_node_index` |
| 宏 | `ALL_CAPS` + `_` | `CHECK_RESULT`, `SAFE_FREE` |
| 模板参数 | 单大写字母或 `PascalCase` | `T`, `F`, `Args`, `Key`, `Value` |
| 头文件保护 | 统一使用 `#pragma once` | `#pragma once` |

- `m_ref_` 表示成员指向外部对象且本类不拥有该对象；生命周期必须由接口或类型关系保证。
- 常量与变量按作用域判定：全局空间（含命名空间，不含函数内）的 `const`/`constexpr` 变量均按常量命名；局部空间（函数内）中，`constexpr` 变量一般会额外加 `static`，按局部静态 `s_` 命名，`const` 变量按普通变量命名。
- 常量使用 `Upper_Snake_Case`（首字母大写 + 下划线，如 `Max_Allowable_Error`）；与宏 `ALL_CAPS`（全大写）的区别仅在于首字母是否大写。
- 工厂函数使用模块缩写前缀，例如 `GPU_create_device()`、`GFX_create_context()`。
- 第一方代码放在项目根命名空间中；实现细节可放入项目既有的 `detail` 或 `Internal` 命名空间。
- `const` 放在类型右侧，统一使用 east const：`Type const* ptr`、`Type const& ref`。
- 尽可能写出精确类型；`auto` 仅允许用于无法具名的类型（lambda、结构化绑定、转发引用），且不得借 `auto` 引入隐式转换（如 `auto x = some_int;`）。

## 文件结构、include 与命名空间

### 文件头、保护与 include

头文件统一使用 `#pragma once` 进行保护，同一子模块内保持一致：

```cpp
#pragma once

// declarations

```

`.cpp` 的 include 严格按以下顺序分组，组间空一行；每组内部保持稳定排序：

```cpp
// 对应头文件
#include "my_class.h"

// 同目录下其他文件
#include "other_class.h"

// 同项目内部上一级头文件
#include "render/core/base.h"
#include "render/core/math.h"

// 同项目内部上一级不同目录下头文件
#include "render/util/cache/cache_type.h"
#include "render/util/utl.h"

// 同项目内部上上一级头文件
#include "render/render_type.h"

// 第三方库
#include <Eigen/Eigen>
#include <assimp/Importer.hpp>

// 系统库
#include <windows.h>

// 标准库
#include <algorithm>
#include <fstream>
```

- 禁止使用 `../` 相对 include；始终从项目配置的 include 根路径引用。
- 公共头能前向声明时不要 include 私有实现头或不必要的依赖。
- 预编译头可以包含标准库、稳定且广泛使用的第三方库头、平台宏和全局配置宏，不包含项目内部除版本/元数据生成头之外的其他实现头。第三方库头按实际使用选择，不为潜在功能预先引入依赖。
-  `pch.h` 这种预编译头由项目自动调配，不应加入 `.cpp` 的 include 文件当中。

### 命名空间

所有第一方声明和定义都包裹在项目根命名空间中：

```cpp
namespace project_name
{

// declarations and definitions

} // namespace project_name
```

保留外部 ABI、框架 override、生成代码和协议要求的名称；不要用这些名称反推项目内部命名风格。源文件私有的函数、类型和变量可以放入匿名命名空间；匿名命名空间应置于项目根命名空间内部；对于基本类型 `size_t` ,  `uint32_t`, `int32_t` 等基本类型，在不需要使用 `std` 命名空间的情况下，直接去除。

## 格式

- 每级缩进 4 个空格，禁止 Tab；禁止行尾空格。
- 逻辑段落之间留一行空行。
- 绿地代码使用 Allman 大括号，并在同一文件内保持一致。多语句控制流必须使用大括号；单语句控制流可以省略大括号，但不得在同一逻辑分支中无理由混用两种形式。

```cpp
class Device
{
public:
    Device() : m_ref_adapter(nullptr) {}
    virtual ~Device() = default;
};

void process()
{
    if (condition)
        do_onething();
    else
    {
        do_something();
        do_other();
    }
}
```

`switch` 中 `case` 需要局部变量时，块起始大括号单独占下一行，并与 `case` 标签保持同级缩进：

```cpp
switch (value)
{
case 0:
    handle_zero();
    break;
case 1:
{
    int temp = compute();
    handle_one(temp);
    break;
}
default:
    break;
}
```

- 访问修饰符使用 `public:`, `protected:`, `private:`，不缩进并与 `class` 对齐；默认顺序为 `public` → `protected` → `private`；同一修饰符可以重复出现，用于分组相关成员。
-  `class` 中，同一访问修饰符下的成员变量和成员函数，通过添加一个额外的访问修饰符分隔开。
- 初始化列表放在构造函数签名同一行，冒号紧跟参数列表右括号：

```cpp
MyClass::MyClass(Arg const* arg, Info const& info) : m_arg(nullptr), m_handle(nullptr)
{
}
```

- 使用 `Type const*`、`Type* const`、`Type const&`，不要在同一模块混用 east/west const。

## 类型与接口

- 抽象接口只定义调用者需要的契约，不包含具体实现细节；纯虚接口提供虚析构函数。
- 继承虚基类的具体类必须标记 `final`，重写必须标记 `override`。
- 能由编译器生成或禁止的特殊成员使用 `= default` / `= delete`；不要把可 default 的特殊成员写成空函数体。
- 可能被调用方忽略而造成错误的结果使用 `[[nodiscard]]`；无抛出保证成立时使用 `noexcept`。
- 避免裸 `new` / `delete`，优先使用值语义、RAII 和智能指针。
- 使用 `nullptr`、named cast 和作用域枚举，避免 C 风格转换与无类型宏。
- 公共 API 不泄漏具体后端、私有类型或不必要的第三方库类型。
- 容量、索引和字节数使用合适的尺寸类型；协议和持久化字段使用固定宽度整数。
- 对于可以通过前向声明处理的依赖，优先使用前向声明，避免因引入不必要的头文件增加编译复杂度。
- 遵循最小作用域原则：仅供单个类使用的类型优先放在该类的私有区域或私有实现中；仅供源文件使用的类型、函数和变量应放在源文件的匿名命名空间中，不应暴露在公共头文件中。
- 严格区分 `struct` 和 `class` 。 `struct` 中的字段均不初始化，与C风格保持一致，且除特殊情况下绝不包含成员函数，其值须在使用时填充； `class` 中的字段的初始化通过构造函数完成，而非类内赋值。

接口与实现的最小形态如下：

#### `system.h`

```cpp
//
// Created by AmazingBuff on YYYY/MM/DD.
//

#pragma once

namespace project_name
{

class ISystem
{
public:
    virtual ~ISystem() = default;

    virtual Entity import(Scene const& scene) = 0;
    virtual Entity create_pipeline(PipelineInfo const& info) = 0;
};

namespace Base
{
    class Driver;
}

class Pipeline;

class SystemImpl final : public ISystem
{
public:
    explicit SystemImpl(SystemInfo const& info);
    ~SystemImpl() override;

    Entity import(Scene const& scene) override;
    Entity create_pipeline(PipelineInfo const& info) override;

private:
    Base::Driver* m_ref_driver;
    Pipeline* m_ref_pipeline;
};

} // namespace project_name
```

示例中的 `m_ref_driver` 和 `m_ref_pipeline` 表示借用指针，`SystemImpl` 不负责销毁其指向的对象；如果实现类拥有这些对象，应改用明确的 RAII 所有权类型。

#### `system.cpp`

```cpp
//
// Created by AmazingBuff on YYYY/MM/DD.
//

#include "system.h"

#include "base/driver.h"

namespace project_name
{

class Pipeline
{
public:
    explicit Pipeline(PipelineInfo const& info);
};

} // namespace project_name

```

## 多后端、friend 与配置结构体

### 多后端 / 策略

多后端或策略模式应抽象稳定的公共接口，各后端独立实现；把后端选择集中在 composition root、工厂或依赖注入点，不让调用方到处进行类型分支。

```cpp
class Device
{
public:
    Device() : m_ref_adapter(nullptr) {}
    virtual ~Device() = default;

    virtual Queue const* fetch_queue(QueueType type, uint32_t index) const = 0;

protected:
    Adapter const* m_ref_adapter;
};

class D3D12Device final : public Device
{
public:
    D3D12Device(Adapter const* adapter, DeviceInfo const& info);
    ~D3D12Device() override;

    Queue const* fetch_queue(QueueType type, uint32_t index) const override;

private:
    void* m_native_handle;

    friend class D3D12Buffer;
};
```

`friend` 只允许用于紧密关联的后端或实现类；声明放在 `private` 区域末尾，禁止跨模块或跨后端的 `friend`。

### 枚举

使用 `enum class` 并显式指定底层类型，尽量选择满足 ABI、协议或存储需求的最小宽度；枚举值使用 `e_` 前缀，集合型枚举以 `e_count` 结尾：

```cpp
enum class Backend : uint8_t
{
    e_d3d12 = 0,
    e_vulkan = 1,
};

enum class Format : uint8_t
{
    e_undefined,
    e_r8g8b8a8_unorm,
    e_r32_sfloat,
    e_count
};
```

### 配置结构体

创建参数通过命名结构体传递。使用 C++20 designated initializers；字段顺序为 `bool` → 基本类型 → 容器/结构体 → 指针；配置结构体与目标类放在同一头文件：

```cpp
struct DeviceInfo
{
    bool disable_cache;
    uint32_t frame_count;
    std::vector<QueueGroup> queue_groups;
};

DeviceInfo info{
    .disable_cache = false,
    .frame_count = 2,
    .queue_groups = {}
};
```

## 所有权与错误

- 默认使用值语义和 RAII；唯一所有权使用对象成员或 `std::unique_ptr`。
- 只有确实存在跨所有者共享生命周期时才使用 `std::shared_ptr`。
- 裸指针和引用默认表示借用，不负责销毁；资源 wrapper 明确复制、移动、析构和 swap 语义，并按创建逆序释放。
- C ABI、插件或自定义 allocator 边界可以使用成对 `create` / `destroy`，但必须共享同一分配域：

```cpp
LibraryHandle* library_create(LibraryOptions const* options);
void library_destroy(LibraryHandle* handle) noexcept;
```

- 使用项目既有的错误模型；不要在同一层用状态码、异常和空值表达同一失败。
- 在外部边界为错误补充操作、输入和资源上下文，再转换为领域错误；内部不变量使用 assertion。
- 不吞掉返回值，不用无上下文日志代替错误传播；异常不得穿过不支持异常的 ABI 边界。
- 避免使用 try / catch 的异常处理行为：失败通过返回值、`std::error_code` 或 assertion 传播，I/O 与系统调用优先选用不抛出的重载；声明为 `noexcept` 的边界内的整条调用链必须保证不抛出。
- 只有第三方库在既有调用路径上强制抛出异常、且同一操作没有不抛出的替代接口时，才允许在该调用点局部使用 try / catch；捕获后必须转换为项目错误模型，禁止吞掉异常、禁止跨层捕获。
- 不在内部偷偷加入全局锁；线程安全、线程亲和性和调用方同步责任必须成为类型或 API 合同的一部分。

## 注释与禁止项

- 禁止添加注释，除非功能极度复杂；优先通过清晰命名、提取函数/类型和简化结构消除注释需求。
- 必须保留或新增注释时，只解释不变量、原因、单位、坐标、ABI、线程或生命周期限制，并在代码变化后同步更新。
- 必要的注释需要使用英文进行描述。
- 禁止 `using namespace std;`。
- 禁止父目录相对 include、无必要的公共头依赖和不成对的资源释放。
- 禁止跨模块 `friend`、公共 API 泄漏具体适配器、静默忽略失败或未初始化返回值。
- 禁止在项目内部新增 try / catch 异常处理流程（第三方强制抛出且无替代接口的边界调用除外）。
- 禁止从 vendor、生成代码、构建产物、复制示例或机械 API 表复制第一方风格。
- 禁止为了符合本 skill 批量重写未触及代码。
