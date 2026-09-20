"""Feature selection, dependency closure and integration fragments."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parent.parent/'templates/features'


def catalog():
    return {p.parent.name:json.loads(p.read_text(encoding='utf-8')) for p in sorted(ROOT.glob('*/feature.json'))}


def resolve(raw):
    specs=catalog()
    if raw.strip() in ('','none'):
        return ()
    requested=list(specs) if raw.strip()=='all' else [v.strip() for v in raw.split(',')]
    if len(set(requested))!=len(requested):
        raise ValueError('Duplicate feature selection')
    result=[]
    active=set()
    def visit(name):
        if name not in specs:
            raise ValueError(f'Unknown feature: {name}; available: {", ".join(specs)}')
        if name in active:
            raise ValueError(f'Feature dependency cycle at {name}')
        if name in result:
            return
        active.add(name)
        for dependency in specs[name].get('requires',[]):
            visit(dependency)
        active.remove(name)
        result.append(name)
    for name in requested:
        visit(name)
    return tuple(result)


def entries(selected,key):
    specs=catalog()
    return list(dict.fromkeys(value for name in selected for value in specs[name].get(key,[])))


def submodules(selected):
    result={}
    specs=catalog()
    for name in selected:
        for module in specs[name].get('submodules',[]):
            path=module['path']
            if path in result and result[path]!=module['url']:
                raise ValueError(f'Conflicting submodule URL for {path}')
            result[path]=module['url']
    return tuple((url,path) for path,url in result.items())


def files(selected):
    result={}
    for name in selected:
        for folder in ('src','cmake'):
            for path in sorted((ROOT/name/folder).rglob('*')):
                if not path.is_file():
                    continue
                relative=path.relative_to(ROOT/name)
                if relative in result:
                    raise ValueError(f'Feature file collision: {relative}')
                result[relative]=path
    return result


def blocks(selected):
    data=entries(selected,'on_data_loaded')
    ready=entries(selected,'on_game_ready')
    save=entries(selected,'on_save')
    load=entries(selected,'on_load')
    handler=[]
    if data or ready or save:
        handler=['    void message_handler(SKSE::MessagingInterface::Message* message) noexcept',
                 '    {','        if (!message)','            return;','        try','        {',
                 '            switch (message->type)','            {']
        for labels,actions in ((['kDataLoaded'],data),(['kNewGame','kPostLoadGame'],ready),(['kSaveGame'],save)):
            if actions:
                handler.extend('            case SKSE::MessagingInterface::'+label+':' for label in labels)
                handler.extend('                '+action for action in actions)
                handler.append('                break;')
        handler.extend(['            default:','                break;','            }','        }',
                        '        catch (...)','        {',
                        '            try { logger::error("Feature message handler failed"); } catch (...) {}',
                        '        }','    }'])
    register=['auto* messaging = SKSE::GetMessagingInterface();',
              'if (!messaging || !messaging->RegisterListener(message_handler))',
              '    return false;'] if handler else []
    load_block=['try','{',*('    '+action for action in load),'}','catch (...)','{','    return false;','}'] if load else []
    return {
        'FEATURE_INCLUDES':['#include "'+p+'"' for p in entries(selected,'includes')],
        'FEATURE_MESSAGE_HANDLER':handler,
        'FEATURE_ON_LOAD':load_block,
        'FEATURE_REGISTER_LISTENER':register,
        'FEATURE_CMAKE_INCLUDES':['include('+p+')' for p in entries(selected,'cmake_includes')],
        'FEATURE_GENERATED_SOURCES':entries(selected,'generated_sources'),
        'FEATURE_SUBDIRECTORIES':['add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/'+path+')' for _,path in submodules(selected)],
        'FEATURE_FIND_PACKAGES':['find_package('+p+' CONFIG REQUIRED)' for p in entries(selected,'packages')],
        'FEATURE_LINK_LIBRARIES':entries(selected,'link_libraries'),
        'INPUT_MENU_INCLUDE':['#include "ui/ui_menu.h"'] if 'menu' in selected else [],
        'INPUT_MENU_GUARD':['if (Menu::is_menu_open())','    return RE::BSEventNotifyControl::kContinue;'] if 'menu' in selected else [],
    }


def expand_blocks(text,values):
    pattern=re.compile(r'(?m)^([ \t]*)\{\{([A-Z][A-Z0-9_]*)\}\}[ \t]*\n')
    def replace(match):
        if match[2] not in values:
            return match[0]
        return ''.join(match[1]+line+'\n' for line in values[match[2]])
    return pattern.sub(replace,text)
