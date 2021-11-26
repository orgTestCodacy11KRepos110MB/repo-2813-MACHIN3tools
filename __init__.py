bl_info = {
    "name": "MACHIN3tools",
    "author": "MACHIN3, TitusLVR",
    "version": (0, 9, 0),
    "blender": (2, 93, 0),
    "location": "",
    "description": "Streamlining Blender 2.93 and beyond.",
    "warning": "",
    "doc_url": "https://machin3.io/MACHIN3tools/docs",
    "category": "Mesh"}


def reload_modules(name):
    '''
    This makes sure all modules are reloaded from new files, when the addon is removed and a new version is installed in the same session,
    or when Blender's 'Reload Scripts' operator is run manually.
    It's important, that utils modules are reloaded first, as operators and menus import from them
    '''

    import os
    import importlib


    # first update the classes and keys dicts, the properties, items, colors
    from . import registration, items, colors

    for module in [registration, items, colors]:
        print("reloading", module.__name__)
        importlib.reload(module)

    # then fetch and reload all utils modules
    utils_modules = sorted([name[:-3] for name in os.listdir(os.path.join(__path__[0], "utils")) if name.endswith('.py')])

    for module in utils_modules:
        impline = "from . utils import %s" % (module)

        print("reloading %s" % (".".join([name] + ['utils'] + [module])))

        exec(impline)
        importlib.reload(eval(module))


    from . import handlers
    print("reloading", handlers.__name__)
    importlib.reload(handlers)

    # and based on that, reload the modules containing operator and menu classes
    modules = []

    for label in registration.classes:
        entries = registration.classes[label]
        for entry in entries:
            path = entry[0].split('.')
            module = path.pop(-1)

            if (path, module) not in modules:
                modules.append((path, module))

    for path, module in modules:
        if path:
            impline = "from . %s import %s" % (".".join(path), module)
        else:
            impline = "from . import %s" % (module)

        print("reloading %s" % (".".join([name] + path + [module])))

        exec(impline)
        importlib.reload(eval(module))


if 'bpy' in locals():
    reload_modules(bl_info['name'])

import bpy
from bpy.props import PointerProperty, BoolProperty
from . properties import M3SceneProperties, M3ObjectProperties
from . utils.registration import get_core, get_tools, get_pie_menus
from . utils.registration import register_classes, unregister_classes, register_keymaps, unregister_keymaps, register_icons, unregister_icons, register_msgbus, unregister_msgbus
from . ui.menus import object_context_menu, mesh_context_menu, add_object_buttons, material_pick_button, outliner_group_toggles, cursor_spin
from . handlers import update_object_axes_drawing, focus_HUD, surface_slide_HUD, update_group, update_msgbus, screencast_HUD


def register():
    global classes, keymaps, icons, owner

    # CORE

    core_classes = register_classes(get_core())


    # PROPERTIES

    bpy.types.Scene.M3 = PointerProperty(type=M3SceneProperties)
    bpy.types.Object.M3 = PointerProperty(type=M3ObjectProperties)

    bpy.types.WindowManager.M3_screen_cast = BoolProperty()


    # TOOLS, PIE MENUS, KEYMAPS, MENUS

    tool_classlists, tool_keylists, tool_count = get_tools()
    pie_classlists, pie_keylists, pie_count = get_pie_menus()

    classes = register_classes(tool_classlists + pie_classlists) + core_classes
    keymaps = register_keymaps(tool_keylists + pie_keylists)

    bpy.types.VIEW3D_MT_object_context_menu.prepend(object_context_menu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(mesh_context_menu)

    bpy.types.VIEW3D_MT_edit_mesh_extrude.append(cursor_spin)
    bpy.types.VIEW3D_MT_mesh_add.prepend(add_object_buttons)
    bpy.types.VIEW3D_MT_editor_menus.append(material_pick_button)
    bpy.types.OUTLINER_HT_header.prepend(outliner_group_toggles)



    # ICONS

    icons = register_icons()


    # MSGBUS

    owner = object()
    register_msgbus(owner)


    # HANDLERS

    bpy.app.handlers.load_post.append(update_msgbus)

    bpy.app.handlers.undo_pre.append(update_object_axes_drawing)
    bpy.app.handlers.redo_pre.append(update_object_axes_drawing)
    bpy.app.handlers.load_pre.append(update_object_axes_drawing)

    bpy.app.handlers.depsgraph_update_post.append(focus_HUD)
    bpy.app.handlers.depsgraph_update_post.append(surface_slide_HUD)
    bpy.app.handlers.depsgraph_update_post.append(update_group)
    bpy.app.handlers.depsgraph_update_post.append(screencast_HUD)


    # REGISTRATION OUTPUT

    print(f"Registered {bl_info['name']} {'.'.join([str(i) for i in bl_info['version']])} with {tool_count} {'tool' if tool_count == 1 else 'tools'}, {pie_count} pie {'menu' if pie_count == 1 else 'menus'}")


def unregister():
    global classes, keymaps, icons, owner

    # HANDLERS

    bpy.app.handlers.load_post.remove(update_msgbus)

    bpy.app.handlers.undo_pre.remove(update_object_axes_drawing)
    bpy.app.handlers.redo_pre.remove(update_object_axes_drawing)
    bpy.app.handlers.load_pre.remove(update_object_axes_drawing)

    from . handlers import focusHUD, surfaceslideHUD, screencastHUD

    if focusHUD and "RNA_HANDLE_REMOVED" not in str(focusHUD):
        bpy.types.SpaceView3D.draw_handler_remove(focusHUD, 'WINDOW')

    if surfaceslideHUD and "RNA_HANDLE_REMOVED" not in str(surfaceslideHUD):
        bpy.types.SpaceView3D.draw_handler_remove(surfaceslideHUD, 'WINDOW')

    if screencastHUD and "RNA_HANDLE_REMOVED" not in str(screencastHUD):
        bpy.types.SpaceView3D.draw_handler_remove(screencastHUD, 'WINDOW')

    bpy.app.handlers.depsgraph_update_post.remove(focus_HUD)
    bpy.app.handlers.depsgraph_update_post.remove(surface_slide_HUD)
    bpy.app.handlers.depsgraph_update_post.remove(update_group)
    bpy.app.handlers.depsgraph_update_post.remove(screencast_HUD)


    # MSGBUS

    unregister_msgbus(owner)


    # TOOLS, PIE MENUS, KEYMAPS, MENUS

    bpy.types.VIEW3D_MT_object_context_menu.remove(object_context_menu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(mesh_context_menu)

    bpy.types.VIEW3D_MT_edit_mesh_extrude.remove(cursor_spin)
    bpy.types.VIEW3D_MT_mesh_add.remove(add_object_buttons)
    bpy.types.VIEW3D_MT_editor_menus.remove(material_pick_button)
    bpy.types.OUTLINER_HT_header.remove(outliner_group_toggles)

    unregister_keymaps(keymaps)
    unregister_classes(classes)


    # PROPERTIES

    del bpy.types.Scene.M3
    del bpy.types.Object.M3


    # ICONS

    unregister_icons(icons)

    print(f"Unregistered {bl_info['name']} {'.'.join([str(i) for i in bl_info['version']])}.")
