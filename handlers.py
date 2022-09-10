import bpy
from bpy.app.handlers import persistent
from . utils.draw import draw_axes_HUD, draw_focus_HUD, draw_surface_slide_HUD, draw_screen_cast_HUD
from . utils.registration import get_prefs, reload_msgbus, get_addon
from . utils.group import update_group_name, select_group_children
from . utils.light import adjust_lights_for_rendering, get_area_light_poll
from . utils.view import sync_light_visibility

# import time


axesHUD = None
prev_axes_objects = []
focusHUD = None
surfaceslideHUD = None
screencastHUD = None


@persistent
def update_msgbus(none):
    reload_msgbus()


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
def update_asset(none):
    context = bpy.context
    # return

    if context.mode == 'OBJECT':

        # avoid AttributeError: 'Context' object has no attribute 'active_object'
        active = getattr(context, 'active_object', None)

        operators = context.window_manager.operators

        if operators and active and active.type == 'EMPTY' and active.instance_collection and active.instance_type == 'COLLECTION':
            lastop = operators[-1]

            if lastop.bl_idname == 'OBJECT_OT_transform_to_mouse':
                # print("inserting an asset")
                # start = time.time()

                for obj in context.scene.objects:
                    if obj.MM.isstashobj:
                        # print(" STASH!")

                        for col in obj.users_collection:
                            # print(f"  unlinking {obj.name} from {col.name}")
                            col.objects.unlink(obj)

                    if obj.DM.isbackup:
                        # print(" DECAL BACKUP!")

                        for col in obj.users_collection:
                            # print(f"  unlinking {obj.name} from {col.name}")
                            col.objects.unlink(obj)

                # print(f" done, after {time.time() - start:.20f} seconds")


@persistent
def axes_HUD(scene):
    global axesHUD, prev_axes_objects

    # if you unregister the addon, the handle will somehow stay arround as a capsule object with the following name
    # despite that, the object will return True, and so we need to check for this or no new handler will be created when re-registering
    if axesHUD and "RNA_HANDLE_REMOVED" in str(axesHUD):
        axesHUD = None

    axes_objects = [obj for obj in bpy.context.visible_objects if obj.M3.draw_axes]
    active = getattr(bpy.context, 'active_object', None)

    if scene.M3.draw_active_axes and active and active not in axes_objects:
        axes_objects.append(active)

    # print()

    if axes_objects:
        # print("axes objects present")

        if axes_objects != prev_axes_objects:
            # print(" axes objects changed")
            prev_axes_objects = axes_objects

            # the objects have changed, remove the previous handler if one exists
            if axesHUD:
                # print("  removing previous draw handler")
                bpy.types.SpaceView3D.draw_handler_remove(axesHUD, 'WINDOW')

            # create a new handler
            # print("  adding new draw handler")
            axesHUD = bpy.types.SpaceView3D.draw_handler_add(draw_axes_HUD, (bpy.context, axes_objects), 'WINDOW', 'POST_VIEW')

    # remove the handler when no axes objects are present anymore
    elif axesHUD:
        bpy.types.SpaceView3D.draw_handler_remove(axesHUD, 'WINDOW')
        # print("removing old draw handler")
        axesHUD = None
        prev_axes_objects = []


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


debug = False
# debug = True


@persistent
def decrease_lights_on_render_start(scene):
    m3 = scene.M3

    if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_adjust_lights_on_render and get_area_light_poll() and m3.adjust_lights_on_render:
        if scene.render.engine == 'CYCLES':
            last = m3.adjust_lights_on_render_last
            divider = m3.adjust_lights_on_render_divider

            # decrease on start of rendering
            if last in ['NONE', 'INCREASE'] and divider > 1:
                if debug:
                    print()
                    print("decreasing lights for cycles when starting render")

                m3.adjust_lights_on_render_last = 'DECREASE'
                m3.is_light_decreased_by_handler = True

                adjust_lights_for_rendering(mode='DECREASE')

    if get_prefs().activate_render and get_prefs().render_sync_light_visibility:
        sync_light_visibility(scene)


@persistent
def increase_lights_on_render_end(scene):
    m3 = scene.M3

    if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_adjust_lights_on_render and get_area_light_poll() and m3.adjust_lights_on_render:
        if scene.render.engine == 'CYCLES':
            last = m3.adjust_lights_on_render_last

            # increase again when finished
            if last == 'DECREASE' and m3.is_light_decreased_by_handler:
                if debug:
                    print()
                    print("increasing lights for cycles when finshing/aborting render")

                m3.adjust_lights_on_render_last = 'INCREASE'
                m3.is_light_decreased_by_handler = False

                adjust_lights_for_rendering(mode='INCREASE')
