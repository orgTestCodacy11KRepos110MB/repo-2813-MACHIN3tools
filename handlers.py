import bpy
from bpy.app.handlers import persistent
from . utils.draw import remove_object_axes_drawing_handler, draw_focus_HUD


focusHUD = None


@persistent
def update_object_axes_drawing(none):
    remove_object_axes_drawing_handler()


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
