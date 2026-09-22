#include "ui_menu.h"
#include "config/config.h"

#pragma warning(push)
#pragma warning(disable: 4996 5054 4099 4267 4244 4061 4062)
#include <SKSEMCP/utils.hpp>
#pragma warning(pop)

PLUGIN_NAMESPACE_BEGIN

namespace
{
    void render_settings()
    {
        Config config = Setting::instance().get_config();
        if (ImGuiMCP::Checkbox("Enabled", &config.enabled))
            Setting::instance().toggle();
        if (ImGuiMCP::Button("Save"))
            Setting::instance().save();
    }
}

bool Menu::is_menu_open()
{
    return SKSEMenuFramework::IsInstalled() && SKSEMenuFramework::IsAnyBlockingWindowOpened();
}

void Menu::register_menu()
{
    static bool s_registered = false;
    if (s_registered || !SKSEMenuFramework::IsInstalled())
        return;
    SKSEMenuFramework::SetSection(Plugin::Plugin_Name.data());
    SKSEMenuFramework::AddSectionItem("Settings", render_settings);
    s_registered = true;
}
PLUGIN_NAMESPACE_END
