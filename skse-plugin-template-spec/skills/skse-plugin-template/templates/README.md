# {{PROJECT_NAME}}

{{DESCRIPTION}}

多运行时（Skyrim SE / AE / VR）的 SKSE 插件，基于 CommonLibSSE。

## 安装

1. 安装 [SKSE64](https://skse.silverlock.org/)（或 SKSEVR，与游戏版本匹配）。
2. 安装 [Address Library for SKSE Plugins](https://www.nexusmods.com/skyrimspecialedition/mods/32444)（VR 用 VR 版）。
3. 将 `{{PROJECT_NAME}}.dll` 放入游戏目录的 `Data\SKSE\Plugins\` 下。

> 日志：`Documents\My Games\Skyrim Special Edition\SKSE\{{PROJECT_NAME}}.log`

## 构建

需要：Visual Studio 2022（含 C++ 桌面开发）、CMake 3.22+、git、vcpkg（设置 `VCPKG_ROOT`）。

```powershell
# 首次克隆拉取 CommonLibSSE 子模块
git submodule update --init --recursive

cmake --preset "msvc release"           # 配置（首次会经 vcpkg 安装依赖）
cmake --build --preset "msvc release"   # 产物 "build/msvc release/src/Release/{{PROJECT_NAME}}.dll"

# 打 ZIP 包（可选）
cpack --config "build/msvc release/CPackConfig.cmake"
```

- VR 构建前置：CommonLibSSE 的 `extern/openvr` 子模块需就绪，见
  `git submodule update --init --recursive`（会带入嵌套子模块）。
- 拷贝到游戏目录：设置 `CompiledPluginsPath` 环境变量后 `-DCOPY_OUTPUT=ON`。

## 配置

（按需填写：INI 路径 `Data\SKSE\Plugins\{{PROJECT_NAME}}.ini`、热键等。）

## 许可证

MIT
