//
// Created by AmazingBuff on 2026/9/19.
//

#pragma once

#include <REX/W32/D3D11.h>

PLUGIN_NAMESPACE_BEGIN

// One-shot shader compilation for every pass of the plugin. init(device) runs once when the
// D3D11 device is first available (renderer init); afterwards every pass's init only picks up
// the ready-made shader objects. The VS blobs stay alive here because CreateInputLayout needs
// the VS bytecode, which is not retrievable from an ID3D11VertexShader.
class ShaderManager
{
public:
    static ShaderManager& instance();

    ShaderManager(ShaderManager const&) = delete;
    ShaderManager& operator=(ShaderManager const&) = delete;

    // Compiles every embedded HLSL and creates the shader objects; returns false (and logs)
    // if any entry fails. Idempotent: a repeated call returns the previous verdict.
    [[nodiscard]] bool compile();

    // Generic overlay
    [[nodiscard]] REX::W32::ID3D11VertexShader* overlay_vs() const noexcept { return m_overlay_vs; }
    [[nodiscard]] REX::W32::ID3D11PixelShader* overlay_ps() const noexcept { return m_overlay_ps; }
    [[nodiscard]] REX::W32::ID3DBlob* overlay_vs_blob() const noexcept { return m_overlay_vs_blob; }

private:
    ShaderManager();
    ~ShaderManager();

    void release();

private:
    REX::W32::ID3D11VertexShader* m_overlay_vs;
    REX::W32::ID3D11PixelShader* m_overlay_ps;
    REX::W32::ID3DBlob* m_overlay_vs_blob;

    bool m_ready;
};

PLUGIN_NAMESPACE_END
