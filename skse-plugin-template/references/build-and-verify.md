# CMake：沿用组织方式，按功能配置内容

## 根文件顺序

参考 Highlight-Lootable-Corpses 的根 CMake 编排：

1. project 及版本、命名空间、作者、运行时选项。
2. cmake 模块路径；需要的生成材料和源文件集合。
3. configure_file 生成 build/src/plugin.h 和版本资源。
4. add_library(SHARED)，设置 C++23、编译/链接参数、包含目录。
5. 添加实际依赖、find_package、target_link_libraries、PCH。

默认保留根目录统一管理 target 的模式，不需要 src/CMakeLists.txt。
main.cpp 已定义 Load/Query/Version 导出，不能同时再用会生成同名导出的 helper。

模板沿用参考项目的 Release configure preset 和 build/ 目录：

```powershell
cmake --preset Release
cmake --build build --config Release
```

没有 buildPresets 时不能使用 --build --preset Release。Visual Studio 是多配置生成器，
实际构建配置由 --config 指定。原参考环境使用 MSVC 14.44.35207、x64-windows-static-md；
模板保留该环境示例。移植到别的机器时，统一调整 preset 和 target 的工具集选择，匹配
依赖的 CRT/STL，不把精确补丁版本当成所有 SKSE 项目的普遍要求。

## 依赖分层

默认 target 只直接依赖 CommonLib、fmt、spdlog。vcpkg 中 DirectXMath、DirectXTK、rapidcsv
用于当前 CommonLib 构建，不能仅因第一方没有调用就随意删除。反过来，参考工程的
SimpleIni、SKSE-MCP 等也不能在没有功能需求时全部加入。

每次增加功能，同时检查：根 manifest 中是否需要新增 port、CMake 是否需要 find_package
或 add_subdirectory、哪个 target 应链接它、运行时是否还有用户需安装的插件。

| 功能 | 必要增量示例 |
| --- | --- |
| INI | 使用 SimpleIni 时，manifest 增加 simpleini；find_package(simpleini CONFIG REQUIRED)；目标链接 SimpleIni::SimpleIni。 |
| MCP 菜单 | 只有选择此 UI 方案时，新增 extern/SKSE-MCP 子模块、add_subdirectory 和 SKSE-MCP::SKSE-MCP 链接。 |
| 自定义 D3D 渲染 | 根据实际 API 增加 d3d11/dxgi；运行时编译 HLSL 才需要 d3dcompiler。 |
| 纯游戏事件 | 通常复用 CommonLib 即可，不需要 UI 或渲染依赖。 |

不能仅在 CMake 链接库却遗漏 vcpkg/submodule，也不能只复制 manifest 而没有实际消费者。
新依赖版本按选定 CommonLib/工具链验证；基线是项目选择，不是必须照抄的业务属性。

## 源文件与 shader

模板沿用参考的 GLOB_RECURSE；新增源文件后重新 configure。若目标项目需要自动感知新增文件，
可以有意识地采用 CONFIGURE_DEPENDS 或显式清单，说明其行为，保持一种清晰策略。

只有需要自定义 shader 时才引入参考的 cmake/embed_shaders.cmake。将真正使用的 HLSL 放在
src/render/shaders，显式列出“文件:符号名”，输出到 build/src/render/shader_sources.h；
custom command 的 DEPENDS 应包含 HLSL 和生成脚本，生成头加入插件 target。
检查消费者的 include 和构建依赖，确认 shader 修改会触发生成及相关编译。没有 shader 时，
不要保留空映射、生成命令或 ShaderManager。

## 发布和验证

packaging.cmake 只是参考的 CPack 组织示例，当前最小模板没有插件 install 规则。
用户要求发布包时再定义 DLL、配置、资源、符号的安装布局并检查 ZIP；不要声称空配置
已经产生可安装 mod 包。COPY_OUTPUT、部署脚本和本机路径也只在有需求时加入。

验证范围跟随变更：默认最小插件应配置、编译、链接并检查导出和生成元数据；新增配置
检查默认值/非法值/读写；新增输入或 hook 需要实际游戏验证；新增 shader 检查依赖重建与
编译入口。复用本地依赖缓存时明确记录，不等同于全新依赖安装成功。

## 使用 feature 的构建接入

`--features` 通过各包的 feature.json 将上述增量接入根 CMake，而不是复制一份完整根配置。
未选择 feature 时，条件占位块被移除，基础模板不添加对应源码和依赖。
shaders 使用 include(cmake/shaders.cmake) 声明生成头，该头加入根 target；menu 单独添加
SKSE-MCP；config 单独添加 SimpleIni。依赖 feature 自动按先后顺序展开并去重。
不要只手动复制 feature 源码而忽略这些构建步骤。
