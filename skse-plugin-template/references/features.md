# 可选模块

默认只生成最小插件。模块存放在 templates/features，不直接出现在未选择的生成结果中。
引用关系是依赖关系，不是建议“全部启用”。只选择当前功能需要的入口 feature。

| Feature | 自动依赖 | 文件与用途 |
| --- | --- | --- |
| config | 无 | src/config；Setting + INI，示例 Enabled/Hotkey 字段。 |
| input | config | src/input；键盘事件热键，不依赖 Present 或菜单。 |
| menu | config | src/ui/ui_menu.*；可选 MCP 的 Enabled/Save 设置页。 |
| present_hook | 无 | src/render/present_hook.*；独立的 REX PresentHook，不自动安装回调。 |
| render | present_hook | src/render/renderer.*；显式选用的 Renderer/OverlayDirector 扩展点，无默认绘图。 |
| dx11 | 无 | src/render/dx11；CommonStates、D3D11StateCapture、compile_shader。 |
| shaders | dx11 | ShaderManager、通用 HLSL、嵌入脚本和 cmake/shaders.cmake。 |
| render_util | 无 | Color、坐标转换和投影函数。 |
| pulse_timer | 无 | 独立 PulseTimer，不生成触发策略。 |
| hash | 无 | src/base/def.h 中的 hash 函数，不生成业务调用。 |

例如 `--features input` 输出 config 和 input；不带 menu、render 或 shaders。
`--features menu` 才增加 SKSE-MCP 子模块和链接。选 shaders 才生成 HLSL 构建步骤。
底层 present_hook、dx11、render_util、pulse_timer、hash 可单独选择，供已有逻辑调用。
render 与 shaders 可以分别选取；真正的绘图 pass 由使用者接入，不伪装成现成功能。

## 包格式

```text
templates/features/config/
  feature.json
  src/config/config.h
  src/config/config.cpp
templates/features/shaders/
  feature.json
  cmake/shaders.cmake
  cmake/embed_shaders.cmake
  src/render/shader_manager.h
  src/render/shader_manager.cpp
  src/render/shaders/overlay.hlsl
```

src/ 与 cmake/ 的内容按相对路径合并到输出项目；feature.json 本身不复制到项目。
重复目标路径被拒绝，不会静默覆盖基础模板或另一 feature。未知 feature、重复选择和循环依赖
在写入前报错。默认不运行网络操作；只有 --add-submodules 才获取实际所选的子模块。

feature.json 的字段：

- description、requires：用途和依赖 feature。
- includes：main.cpp 使用的模块头文件。
- ports、packages、link_libraries：分别补齐 vcpkg、find_package 和目标链接。
- submodules：url/path 配对，同时补齐 .gitmodules 和 add_subdirectory。
- cmake_includes、generated_sources：生成文件步骤和插件 target 的生成输入。
- on_load、on_data_loaded、on_game_ready、on_save：实际需要的生命周期调用。

添加 feature 时声明最小依赖；不要因为多个模块经常一起使用就互相绑定。
模块头自行包含所需标准库/API 头，不依靠“全集一起编译时恰好有某个头文件”。

## 当前适配行为

config::Setting 使用加锁快照和 toggle 接口，load/save 在游戏入口/SaveGame 调用；
示例键值是 VK F7 (0x76)，不是扫描码。配置不存在时使用示例默认值，保存时创建 INI。
input 在 DataLoaded 和 game-ready 消息上尝试幂等注册，只处理键盘 IsDown；menu 同时选中时
额外检查 Menu::is_menu_open，没选 menu 就没有该 include/调用。
menu 仅提供已经接入的 Enabled/Save 控件，不包含未实现的重绑按钮。

render 在同样的时机幂等安装 Present 回调；present_hook 保留原函数并封闭插件回调异常。
shaders 在 DataLoaded 尝试编译；设备尚未就绪时，后续实际使用者需要按其设备生命周期调用 compile。
state capture 的捕获范围、设备重建、窗口 resize、事件/线程和运行时兼容性仍需按新插件需求验证。
工具 feature 不会自动获得业务消费者，也不会自动把所有工具绑定进 Renderer。

## 手动复用与验证

已有项目可以只复制一个 feature 的所需文件，但必须一并检查 manifest 中的构建和生命周期
接入点；不要把 generator 用作覆盖已有项目的升级命令。裁剪模块仍遵循 reuse-guide.md。

回归测试检查默认最小输出、依赖补齐、每个 feature、所有两两组合和全集的文件/include
一致性。真实 Release 编译验证全集，另外区分游戏内行为、Debug/VR 和依赖获取是否经过验证。

本次验证：默认生成仍为 12 个文件；10 个独立选择、45 个两两组合及全集通过生成检查。
全集已用 MSVC 19.44.35228 / Windows SDK 10.0.26100.0 配置并编译链接为 DLL，复用匹配的
CommonLib 静态库和已有 vcpkg 缓存。游戏内运行、Debug/VR 构建和全新网络依赖获取未验证。
