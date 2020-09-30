import bpy
from mathutils import Vector, Matrix
import gpu
from gpu_extras.batch import batch_for_shader
import bgl
import blf
from .. colors import red, green, blue


def add_object_axes_drawing_handler(dns, args):
    # print("adding object axes drawing handler")

    handler = bpy.types.SpaceView3D.draw_handler_add(draw_object_axes, (args,), 'WINDOW', 'POST_VIEW')
    dns['draw_object_axes'] = handler


def remove_object_axes_drawing_handler(handler=None):
    # print("attempting to remove object axes drawing handler")

    if not handler:
        handler = bpy.app.driver_namespace.get('draw_object_axes')


    if handler:
        # print(" REMOVING object axes drawing handler")

        bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
        del bpy.app.driver_namespace['draw_object_axes']


def draw_object_axes(args):
    context, objs = args

    if context.space_data.overlay.show_overlays:
        axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]

        size = context.scene.M3.object_axes_size
        alpha = context.scene.M3.object_axes_alpha

        for axis, color in axes:
            coords = []

            for obj in objs:
                mx = obj.matrix_world
                origin, _, _ = mx.decompose()

                # coords.append(origin)
                coords.append(origin + mx.to_3x3() @ axis * size * 0.1)
                coords.append(origin + mx.to_3x3() @ axis * size)

            indices = [(i, i + 1) for i in range(0, len(coords), 2)]

            shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
            shader.bind()
            shader.uniform_float("color", (*color, alpha))

            bgl.glEnable(bgl.GL_BLEND)
            bgl.glDisable(bgl.GL_DEPTH_TEST)

            bgl.glLineWidth(2)

            batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
            batch.draw(shader)


def draw_focus_HUD(context, color=(1, 1, 1), alpha=1, width=2):
    region = context.region
    view = context.space_data

    # only draw when actually in local view, this prevents it being drawn when switing workspace, which doesn't sync local view
    if view.local_view:

        # draw border

        coords = [(width, width), (region.width - width, width), (region.width - width, region.height - width), (width, region.height - width)]
        indices =[(0, 1), (1, 2), (2, 3), (3, 0)]

        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha / 4))

        bgl.glEnable(bgl.GL_BLEND)

        bgl.glLineWidth(width)

        batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
        batch.draw(shader)

        # draw title

        # check if title needs to be offset down due to the header position
        area = context.area
        headers = [r for r in area.regions if r.type == 'HEADER']

        scale = context.preferences.view.ui_scale
        offset = 4

        if headers:
            header = headers[0]

            # only offset when the header is on top and when show_region_tool_header is disabled
            if area.y - header.y and not view.show_region_tool_header:
                offset += int(25 * scale)

        title = "Focus Level: %d" % len(context.scene.M3.focus_history)

        stashes = True if context.active_object and getattr(context.active_object, 'MM', False) and getattr(context.active_object.MM, 'stashes') else False
        center = (region.width / 2) + (scale * 100) if stashes else region.width / 2

        font = 1
        fontsize = int(12 * scale)

        blf.size(font, fontsize, 72)
        blf.color(font, *color, alpha)
        blf.position(font, center - int(60 * scale), region.height - offset - int(fontsize), 0)

        blf.draw(font, title)
