# 构建、工具链与验证

## 1. 前置条件

- Visual Studio 2022（C++ 桌面开发），CMake ≥ 3.22，git。
- vcpkg：设置 `VCPKG_ROOT` 环境变量（本机为 `C:\env\vcpkg`）。
- 运行时 Address Library 由用户安装（Nexus 32444 / VR 版），构建不需要。

## 2. 标准构建流程

```powershell
# 1) 拉取 CommonLibSSE（及其嵌套 submodule，如 extern/openvr）
git submodule update --init --recursive

# 2) 配置（首次会经 vcpkg 安装依赖：fmt/spdlog/directxmath/directxtk/...）
cmake --preset "msvc release"

# 3) 构建（产物 "build/msvc release/src/Release/<Name>.dll"）
cmake --build --preset "msvc release"

# 4) 打 ZIP 包（可选，产物 build/packaging/<Name>-<ver>.zip）
cpack --config "build/msvc release/CPackConfig.cmake"
```

- 产物安装路径（install 规则）：`<Name>.dll` → `SKSE/Plugins/`，
  `<Name>.pdb` → 包根目录（component: pdbs）。
- 拷贝到游戏目录：设置 `CompiledPluginsPath` 环境变量 + `-DCOPY_OUTPUT=ON`，
  POST_BUILD 自动拷到 `<CompiledPluginsPath>/SKSE/Plugins/`。

## 3. 工具链对齐（重要，源项目踩过的坑）

- vcpkg 编译 spdlog 用的是最新 MSVC（如 14.44）；CMake 默认 `v143` 可能解析到较旧
  工具集（14.38），其 STL 缺少 14.44 的向量化符号，导致链接 `LNK2019`。
- 修复：在 `src/CMakeLists.txt` 设置
  `VS_GLOBAL_VCToolsVersion "14.44.35207"`，强制插件与 vcpkg 依赖同工具集。
- CMake ≥ 3.31 会丢弃 preset 中 `toolset` 的 `version=` 子句，因此必须保留上面的
  `VS_GLOBAL_VCToolsVersion` 兜底。

## 4. VR 构建前置

- 需要 CommonLibSSE 的 `extern/openvr` 子模块。缺失时：
  ```bash
  git -C extern/CommonLibSSE submodule update --init extern/openvr
  # 或手动 clone：git clone https://github.com/ValveSoftware/openvr.git extern/CommonLibSSE/extern/openvr
  ```
- 只构建 flatrim（SE+AE）时可在预设中关闭 `ENABLE_SKYRIM_VR`，避免 openvr 要求。

## 5. 离线 / 本机专用预设

- 复用已有工程构建好的依赖目录（`<Proj>\build\vcpkg_installed\x64-windows-static-md`）：
  在 `CMakeUserPresets.json` 定义 preset，设
  `CMAKE_PREFIX_PATH` 指向该目录，并按需关 `SKSE_SUPPORT_PATCH_SAFETY`（避免在线拉 hde64）。
- `CMakeUserPresets.json` 不提交（`.gitignore` 已排除）。

## 6. 验证清单（新建/修改插件后）

- [ ] `git submodule update --init --recursive` 成功，`extern/CommonLibSSE` 有内容。
- [ ] `cmake --preset "msvc release"` 成功（首次经 vcpkg 装依赖）。
- [ ] `cmake --build --preset "msvc release"` 成功，无 LNK2019 等链接错误。
- [ ] 产物存在于 `"build/msvc release/src/Release/<Name>.dll"`；`cpack` 产物含 `SKSE/Plugins/<Name>.dll`。
- [ ] 至少验证一个受支持运行时配置；涉及多运行时改动时扩大到 SE/AE/VR 矩阵。
- [ ] 插件日志：进入游戏后 `Documents\My Games\Skyrim Special Edition\SKSE\<Name>.log`
      显示 "loaded"；`kDataLoaded` 行为按预期触发。
- [ ] 新模块：头文件只声明稳定契约；`src/CMakeLists.txt` 登记；`vcpkg.json` 依赖按需追加；
      编码风格符合本 skill 内置的 `assets/coding-rules/small-project-cpp-rules` 组件。

## 7. 不声称未运行项

- 未实际编译的运行时/工具集组合不得在 README/文档中声称通过。
- 常见问题先看日志（插件日志 + SKSE 日志 `SKSE.log`）。
