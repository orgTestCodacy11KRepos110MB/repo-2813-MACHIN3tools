import bpy
from bpy.app.handlers import persistent
from . utils.draw import remove_object_axes_drawing_handler, draw_focus_HUD, draw_surface_slide_HUD


focusHUD = None
surfaceslideHUD = None


@persistent
def update_object_axes_drawing(none):
    remove_object_axes_drawing_handler()


@persistent
def update_group(none):
    context = bpy.context

    if context.mode == 'OBJECT':
        active = context.active_object if context.active_object and context.active_object.M3.is_group_empty else None
        inactive = [obj for obj in context.visible_objects if obj.M3.is_group_empty and obj != active]


        # auto select active group's children
        if context.scene.M3.group_select and active:
            if active.select_get():
                for obj in active.children:
                    if not obj.select_get():
                        obj.select_set(True)

            else:
                for obj in active.children:
                    if obj.select_get():
                        obj.select_set(False)

        # auto "hide" group empties, except the active one
        if context.scene.M3.group_hide:
            if active:
                active.show_name = True
                active.empty_display_size = 0.1

            if inactive:
                for e in inactive:
                    e.show_name = False
                    e.empty_display_size = 0


@persistent
def focus_HUD(scene):
    global focusHUD

    # if you unregister the addon, the handle will somehow stay arround as a capsule object with the following name
    # despite that, the object will return True, and so we need to check for this or no new handler will be created when re-registering
    if focusHUD and "RNA_HANDLE_REMOVED" in str(focusHUD):
        focusHUD = None

    history = scene.M3.focus_history

    if history:
        if not focusHUD:
            focusHUD = bpy.types.SpaceView3D.draw_handler_add(draw_focus_HUD, (bpy.context, (1, 1, 1), 1, 2), 'WINDOW', 'POST_PIXEL')

    elif focusHUD:
        bpy.types.SpaceView3D.draw_handler_remove(focusHUD, 'WINDOW')
        focusHUD = None


@persistent
def surface_slide_HUD(scene):
    global surfaceslideHUD

    # if you unregister the addon, the handle will somehow stay arround as a capsule object with the following name
    # despite that, the object will return True, and so we need to check for this or no new handler will be created when re-registering
    if surfaceslideHUD and "RNA_HANDLE_REMOVED" in str(surfaceslideHUD):
        surfaceslideHUD = None

    active = bpy.context.active_object if bpy.context.active_object else None

    if active:
        surfaceslide = [mod for mod in active.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

        if surfaceslide and not surfaceslideHUD:
            surfaceslideHUD = bpy.types.SpaceView3D.draw_handler_add(draw_surface_slide_HUD, (bpy.context, (0, 1, 0), 1, 2), 'WINDOW', 'POST_PIXEL')

        elif surfaceslideHUD and not surfaceslide:
            bpy.types.SpaceView3D.draw_handler_remove(surfaceslideHUD, 'WINDOW')
            surfaceslideHUD = None
