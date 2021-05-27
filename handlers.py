import bpy
from bpy.app.handlers import persistent
from . utils.draw import remove_object_axes_drawing_handler, draw_focus_HUD, draw_surface_slide_HUD, draw_screen_cast_HUD
from . utils.registration import get_prefs, reload_msgbus, get_addon
from . utils.group import update_group_name, select_group_children


focusHUD = None
surfaceslideHUD = None
screencastHUD = None


@persistent
def update_msgbus(none):
    reload_msgbus()


@persistent
def update_object_axes_drawing(none):
    remove_object_axes_drawing_handler()


@persistent
def update_group(none):
    context = bpy.context

    if context.mode == 'OBJECT':

        # avoid AttributeError: 'Context' object has no attribute 'active_object'
        active = context.active_object if getattr(context, 'active_object', None) and context.active_object.M3.is_group_empty and context.active_object.select_get() else None

        # AUTO SELECT

        if context.scene.M3.group_select and active:
            select_group_children(context.view_layer, active, recursive=context.scene.M3.group_recursive_select)


        # STORE USER-SET EMPTY SIZE

        if active:
            # without this you can't actually set a new empty size, because it would be immediately reset to the stored value, if group_hide is enabled
            if round(active.empty_display_size, 4) != 0.0001 and active.empty_display_size != active.M3.group_size:
                active.M3.group_size = active.empty_display_size


        # HIDE / UNHIDE

        if context.scene.M3.group_hide and getattr(context, 'visible_objects', None):
            selected = [obj for obj in context.visible_objects if obj.M3.is_group_empty and obj.select_get()]
            unselected = [obj for obj in context.visible_objects if obj.M3.is_group_empty and not obj.select_get()]

            if selected:
                for group in selected:
                    group.show_name = True
                    group.empty_display_size = group.M3.group_size

            if unselected:
                for group in unselected:
                    group.show_name = False

                    # store existing non-zero size
                    if round(group.empty_display_size, 4) != 0.0001:
                        group.M3.group_size = group.empty_display_size

                    group.empty_display_size = 0.0001


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

    # avoid AttributeError: 'Context' object has no attribute 'active_object'
    active = getattr(bpy.context, 'active_object', None)

    if active:
        surfaceslide = [mod for mod in active.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

        if surfaceslide and not surfaceslideHUD:
            surfaceslideHUD = bpy.types.SpaceView3D.draw_handler_add(draw_surface_slide_HUD, (bpy.context, (0, 1, 0), 1, 2), 'WINDOW', 'POST_PIXEL')

        elif surfaceslideHUD and not surfaceslide:
            bpy.types.SpaceView3D.draw_handler_remove(surfaceslideHUD, 'WINDOW')
            surfaceslideHUD = None


@persistent
def screencast_HUD(scene):
    global screencastHUD

    wm = bpy.context.window_manager

    # if you unregister the addon, the handle will somehow stay arround as a capsule object with the following name
    # despite that, the object will return True, and so we need to check for this or no new handler will be created when re-registering
    if screencastHUD and "RNA_HANDLE_REMOVED" in str(screencastHUD):
        screencastHUD = None

    # if bpy.context.window_manager.operators and scene.M3.screen_cast:
    if getattr(wm, 'M3_screen_cast', False):
        if not screencastHUD:
            screencastHUD = bpy.types.SpaceView3D.draw_handler_add(draw_screen_cast_HUD, (bpy.context, ), 'WINDOW', 'POST_PIXEL')

    elif screencastHUD:
        bpy.types.SpaceView3D.draw_handler_remove(screencastHUD, 'WINDOW')
        screencastHUD = None
