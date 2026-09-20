//
// Created by AmazingBuff on 2026/9/19.
//

#include "shader_manager.h"

#include "render/shader_sources.h"
#include "render/dx11/d3d11_util.h"

PLUGIN_NAMESPACE_BEGIN

namespace
{
    // Compile + create one entry; on failure the outputs stay null and the caller aborts.
    // blob is optional: only the input layouts need the VS bytecode, so the VS without a layout
    // (fullscreen composite) passes nullptr and the blob is released right after creation.
    bool create_vertex_shader(
        REX::W32::ID3D11Device* device, char const* source, char const* entry, char const* name,
        REX::W32::ID3D11VertexShader** shader, REX::W32::ID3DBlob** blob)
    {
        REX::W32::ID3DBlob* compiled = compile_shader(source, entry, "vs_5_0", name, "shader manager");
        if (!compiled)
            return false;

        device->CreateVertexShader(compiled->GetBufferPointer(), compiled->GetBufferSize(), nullptr, shader);
        if (blob)
            *blob = compiled;
        else
            compiled->Release();

        return *shader != nullptr;
    }

    bool create_pixel_shader(
        REX::W32::ID3D11Device* device, char const* source, char const* entry, char const* name,
        REX::W32::ID3D11PixelShader** shader)
    {
        REX::W32::ID3DBlob* blob = compile_shader(source, entry, "ps_5_0", name, "shader manager");
        if (!blob)
            return false;
        device->CreatePixelShader(blob->GetBufferPointer(), blob->GetBufferSize(), nullptr, shader);
        blob->Release();
        return *shader != nullptr;
    }
}

ShaderManager& ShaderManager::instance()
{
    static ShaderManager s_instance;
    return s_instance;
}

ShaderManager::ShaderManager() :
    m_overlay_vs(nullptr),
    m_overlay_ps(nullptr),
    m_overlay_vs_blob(nullptr),
    m_ready(false) {}

ShaderManager::~ShaderManager()
{
    release();
}

bool ShaderManager::compile()
{
    if (!m_ready)
    {
        RE::BSGraphics::Renderer* renderer = RE::BSGraphics::Renderer::GetSingleton();
        if (!renderer)
        {
            logger::info("Shader precompile skipped, renderer not available at data-loaded");
            return false;
        }

        REX::W32::ID3D11Device* device = renderer->GetRuntimeData().forwarder;
        if (!device)
        {
            logger::info("Shader precompile skipped, D3D11 device not available at data-loaded");
            return false;
        }

        m_ready =
            create_vertex_shader(device, render_shaders::Overlay, "vs_main", "ui overlay", &m_overlay_vs, &m_overlay_vs_blob) &&
            create_pixel_shader(device, render_shaders::Overlay, "ps_main", "ui overlay", &m_overlay_ps);

        if (!m_ready)
        {
            release();
            logger::error("Shader compilation failed, overlay rendering disabled");
            return false;
        }

        logger::info("All overlay shaders compiled");
    }

    return true;
}

void ShaderManager::release()
{
    auto const release_ptr = [](auto& com_ptr) {
        if (com_ptr)
        {
            com_ptr->Release();
            com_ptr = nullptr;
        }
    };

    release_ptr(m_overlay_vs);
    release_ptr(m_overlay_ps);
    release_ptr(m_overlay_vs_blob);
}

PLUGIN_NAMESPACE_END
