# 如何阅读参考项目

参考工程：Highlight-Lootable-Corpses。其用途是提供已存在的组织方式和具体实现案例，
不是目标项目的模块清单、不可修改的规范或逐文件同步源。

| 想解决的问题 | 阅读入口 | 提取的内容 |
| --- | --- | --- |
| 项目和元数据如何组织 | 根 CMakeLists、CMakePresets、cmake/plugin.h.in、main.cpp、pch.h | 构建顺序、生成文件位置、入口和命名空间约定。 |
| INI 如何分离职责 | src/config/ 及其调用方 | 配置模块接口和读写流程，不是原配置字段全集。 |
| 输入如何接入游戏 | src/input/ | 事件订阅和码值转换，按需求保留设备和触发行为。 |
| 菜单如何连接设置 | src/ui/ui_menu.* 与 extern/SKSE-MCP | 当且仅当需要该 UI 方案时参考。 |
| 图形代码如何拆分 | src/render/、dx11/、shader_manager.*、cmake/embed_shaders.cmake | 根据实际渲染规模选用层次、状态工具和生成流程。 |
| 某个工具是否可复用 | base/def.h、render_util.*、pulse_timer.* | 逐项检查消费者和依赖，选择有用途的函数/类。 |

不默认引入搜索、过滤、QuickLoot、轮廓/icon pass，也不默认引入上述“通用”模块。
它们只有在解决目标项目的具体需求时才进入目标项目。

旧版本 skill 的“固定通用骨架”“22 个文件必须相同”“哈希一致才算完成”约束已经移除。
check_reference.py、reference_model.py、reference.json 不再属于此 skill。维护标准改为：
当前功能是否有合理文件布局、CMake 是否只配置实际需要的内容、复用代码是否完成依赖裁剪与适配。
