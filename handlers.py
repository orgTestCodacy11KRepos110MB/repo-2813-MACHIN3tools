import bpy
from bpy.app.handlers import persistent
from . utils.draw import remove_object_axes_drawing_handler, draw_focus_HUD, draw_surface_slide_HUD
from . utils.registration import get_prefs
from . utils.group import update_group_name, select_group_children


focusHUD = None
surfaceslideHUD = None


@persistent
def update_object_axes_drawing(none):
    remove_object_axes_drawing_handler()


@persistent
def update_group(none):
    context = bpy.context

    if context.mode == 'OBJECT':
        active = context.active_object if context.active_object and context.active_object.M3.is_group_empty and context.active_object.select_get() else None

        # AUTO SELECT

        if context.scene.M3.group_select and active:
            select_group_children(active, recursive=context.scene.M3.group_recursive_select)


        # STORE USER-SET EMPTY SIZE

        if active:
            # without this you can't actually set a new empty size, because it would be immediately reset to the stored value, if group_hide is enabled
            if round(active.empty_display_size, 4) != 0.0001 and active.empty_display_size != active.M3.group_size:
                active.M3.group_size = active.empty_display_size


        # HIDE / UNHIDE

        if context.scene.M3.group_hide:
            if active:
                active.show_name = True
                active.empty_display_size = active.M3.group_size

            inactive = [obj for obj in context.visible_objects if obj.M3.is_group_empty and obj != active]

            if inactive:
                for e in inactive:
                    e.show_name = False

                    # store existing non-zero size
                    if round(e.empty_display_size, 4) != 0.0001:
                        e.M3.group_size = e.empty_display_size

                    e.empty_display_size = 0.0001


        # AUTO NAME

        if active and get_prefs().group_auto_name:
            update_group_name(active)


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
