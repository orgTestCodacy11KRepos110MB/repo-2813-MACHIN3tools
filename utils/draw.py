import bpy
from mathutils import Vector, Matrix
import gpu
from gpu_extras.batch import batch_for_shader
import blf
from . wm import get_last_operators
from . registration import get_prefs
from . ui import require_header_offset
from .. colors import red, green, blue, black, white


def add_object_axes_drawing_handler(dns, context, objs, draw_cursor):
    handler = bpy.types.SpaceView3D.draw_handler_add(draw_object_axes, ([context, objs, draw_cursor],), 'WINDOW', 'POST_VIEW')
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
    context, objs, draw_cursor = args

    if context.space_data.overlay.show_overlays:
        axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]

        size = context.scene.M3.object_axes_size
        alpha = context.scene.M3.object_axes_alpha

        for axis, color in axes:
            coords = []

            # draw object(s)
            for obj in objs:
                mx = obj.matrix_world
                origin = mx.decompose()[0]

                # coords.append(origin)
                coords.append(origin + mx.to_3x3() @ axis * size * 0.1)
                coords.append(origin + mx.to_3x3() @ axis * size)

            # cursor
            if draw_cursor and context.space_data.overlay.show_cursor:
                cmx = context.scene.cursor.matrix
                corigin = cmx.decompose()[0]

                coords.append(corigin + cmx.to_3x3() @ axis * size * 0.1 * 0.5)
                coords.append(corigin + cmx.to_3x3() @ axis * size * 0.5)

            """
            # debuging stash + stashtargtmx for object origin changes
            for stash in obj.MM.stashes:
                if s tash.obj:
                    smx = sta sh.obj.MM.stashmx
                    sorigin = smx.decompose()[0]

                    coords.append(sorigin + smx.to_3x3() @ axis * size * 0.1)
                    coords.append(sorigin + smx.to_3x3() @ axis * size)


                    stmx = stash.obj.MM.stashtargetmx
                    storigin = stmx.decompose()[0]

                    coords.append(storigin + stmx.to_3x3() @ axis * size * 0.1)
                    coords.append(storigin + stmx.to_3x3() @ axis * size)
            """

            if coords:
                indices = [(i, i + 1) for i in range(0, len(coords), 2)]

                shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
                shader.bind()
                shader.uniform_float("color", (*color, alpha))

                gpu.state.depth_test_set('NONE')
                gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
                gpu.state.line_width_set(2)

                use_legacy_line_smoothing(alpha, 2)

                batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
                batch.draw(shader)


def draw_focus_HUD(context, color=(1, 1, 1), alpha=1, width=2):
    if context.space_data.overlay.show_overlays:
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

            gpu.state.depth_test_set('NONE')
            gpu.state.blend_set('ALPHA' if (alpha / 4) < 1 else 'NONE')
            gpu.state.line_width_set(width)

            batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
            batch.draw(shader)

            # draw title

            scale = context.preferences.view.ui_scale * get_prefs().HUD_scale
            offset = 4

            # add additional offset if necessary
            if require_header_offset(context, top=True):
                offset += int(25)

            title = "Focus Level: %d" % len(context.scene.M3.focus_history)

            stashes = True if context.active_object and getattr(context.active_object, 'MM', False) and getattr(context.active_object.MM, 'stashes') else False
            center = (region.width / 2) + (scale * 100) if stashes else region.width / 2

            font = 1
            fontsize = int(12 * scale)

            blf.size(font, fontsize, 72)
            blf.color(font, *color, alpha)
            blf.position(font, center - int(60 * scale), region.height - offset - int(fontsize), 0)

            blf.draw(font, title)


def draw_surface_slide_HUD(context, color=(1, 1, 1), alpha=1, width=2):
    if context.space_data.overlay.show_overlays:
        region = context.region

        scale = context.preferences.view.ui_scale * get_prefs().HUD_scale
        offset = 0

        if require_header_offset(context, top=False):
            offset += int(20)

        title = "Surface Sliding"

        font = 1
        fontsize = int(12 * scale)

        blf.size(font, fontsize, 72)
        blf.color(font, *color, alpha)
        blf.position(font, (region.width / 2) - int(60 * scale), 0 + offset + int(fontsize), 0)

        blf.draw(font, title)


def draw_screen_cast_HUD(context):
    p = get_prefs()
    operators = get_last_operators(context, debug=False)[-p.screencast_operator_count:]

    font = 0
    scale = context.preferences.view.ui_scale * get_prefs().HUD_scale

    # initiate the horizontal offset based on the presence of the tools bar
    tools = [r for r in context.area.regions if r.type == 'TOOLS']
    offset_x = tools[0].width if tools else 0

    # then add some more depending on wether the addon prefix is used
    offset_x += 7 if p.screencast_show_addon else 15

    # initiate the vertical offset based on the height of the redo panel, use a 50px base offset
    redo = [r for r in context.area.regions if r.type == 'HUD']
    offset_y = redo[0].height + 50 if redo else 50

    # emphasize the last op
    emphasize = 1.25

    # get addon prefix offset, based on widest possiblestring 'MM', and based on empasized last op's size
    if p.screencast_show_addon:
        blf.size(font, round(p.screencast_fontsize * scale * emphasize), 72)
        addon_offset_x = blf.dimensions(font, 'MM')[0]
    else:
        addon_offset_x = 0

    y = 0
    hgap = 10

    for idx, (addon, label, idname, prop) in enumerate(reversed(operators)):
        size = round(p.screencast_fontsize * scale * (emphasize if idx == 0 else 1))
        vgap = round(size / 2)

        color = green if idname.startswith('machin3.') and p.screencast_highlight_machin3 else white
        alpha = (len(operators) - idx) / len(operators)

        # enable shadowing for the last op and idname
        if idx == 0:
            blf.enable(font, blf.SHADOW)

            blf.shadow_offset(font, 3, -3)
            blf.shadow(font, 5, *black, 1.0)


        # label

        text = f"{label}: {prop}" if prop else label

        x = offset_x + addon_offset_x
        y = offset_y * scale if idx == 0 else y + (blf.dimensions(font, text)[1] + vgap)

        blf.size(font, size, 72)
        blf.color(font, *color, alpha)
        blf.position(font, x, y, 0)

        blf.draw(font, text)


        # idname

        if p.screencast_show_idname:
            x += blf.dimensions(font, text)[0] + hgap

            blf.size(font, size - 2, 72)
            blf.color(font, *color, alpha * 0.3)
            blf.position(font, x, y, 0)

            blf.draw(font, f"{idname}")

            # reset size
            blf.size(font, size, 72)


        # diable shadowing, we don't want to use it for the addon prefix or for the other ops
        if idx == 0:
            blf.disable(font, blf.SHADOW)


        # addon prefix

        if addon and p.screencast_show_addon:
            blf.size(font, size, 72)

            x = offset_x + addon_offset_x - blf.dimensions(font, addon)[0] - (hgap / 2)

            blf.color(font, *white, alpha * 0.3)
            blf.position(font, x, y, 0)

            blf.draw(font, addon)

        if idx == 0:
            y += blf.dimensions(font, text)[1]


def draw_label(context, title='', coords=None, center=True, color=(1, 1, 1), alpha=1):

    # centered, but slighly below
    if not coords:
        region = context.region
        width = region.width / 2
        height = region.height / 2
    else:
        width, height = coords

    scale = context.preferences.view.ui_scale * get_prefs().HUD_scale

    font = 1
    fontsize = int(12 * scale)

    blf.size(font, fontsize, 72)
    blf.color(font, *color, alpha)

    if center:
        blf.position(font, width - (int(len(title) * scale * 7) / 2), height + int(fontsize), 0)
    else:
        blf.position(font, *(coords), 1)

    # blf.position(font, 10, 10, 0)

    blf.draw(font, title)


# BASIC

def use_legacy_line_smoothing(alpha, width):
    '''
    legacy line smoothing using the depreciated bgl module
    be prepared for blg no longer being available
    '''

    if get_prefs().use_legacy_line_smoothing and alpha < 1:
        try:
            import bgl

            bgl.glEnable(bgl.GL_BLEND)
            bgl.glLineWidth(width)
            bgl.glEnable(bgl.GL_LINE_SMOOTH)
        except:
            pass


def draw_point(co, mx=Matrix(), color=(1, 1, 1), size=6, alpha=1, xray=True, modal=True):
    def draw():
        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.point_size_set(size)

        batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co]})
        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_points(coords, indices=None, mx=Matrix(), color=(1, 1, 1), size=6, alpha=1, xray=True, modal=True):
    def draw():
        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.point_size_set(size)

        if indices:
            if mx != Matrix():
                batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co for co in coords]}, indices=indices)
            else:
                batch = batch_for_shader(shader, 'POINTS', {"pos": coords}, indices=indices)

        else:
            if mx != Matrix():
                batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co for co in coords]})
            else:
                batch = batch_for_shader(shader, 'POINTS', {"pos": coords})

        batch.draw(shader)


    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_line(coords, indices=None, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    """
    takes coordinates and draws a single line
    can optionally take an indices argument to specify how it should be drawn
    """
    def draw():
        nonlocal indices

        if not indices:
            indices = [(i, i + 1) for i in range(0, len(coords)) if i < len(coords) - 1]

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.line_width_set(width)

        use_legacy_line_smoothing(alpha, width)

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_lines(coords, indices=None, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    """
    takes an even amount of coordinates and draws half as many 2-point lines
    """
    def draw():
        nonlocal indices

        if not indices:
            indices = [(i, i + 1) for i in range(0, len(coords), 2)]

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.line_width_set(width)

        use_legacy_line_smoothing(alpha, width)

        if mx != Matrix():
            batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)

        else:
            batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)

        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_vector(vector, origin=Vector((0, 0, 0)), mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    def draw():
        coords = [mx @ origin, mx @ origin + mx.to_3x3() @ vector]

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.line_width_set(width)

        use_legacy_line_smoothing(alpha, width)

        batch = batch_for_shader(shader, 'LINES', {"pos": coords})
        batch.draw(shader)


    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_vectors(vectors, origins, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    def draw():
        coords = []

        for v, o in zip(vectors, origins):
            coords.append(mx @ o)
            coords.append(mx @ o + mx.to_3x3() @ v)

        indices = [(i, i + 1) for i in range(0, len(coords), 2)]

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.line_width_set(width)

        use_legacy_line_smoothing(alpha, width)

        batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
        batch.draw(shader)


    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_mesh_wire(batch, color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    """
    takes tupple of (coords, indices) and draws a line for each edge index
    """
    def draw():
        nonlocal batch
        coords, indices = batch

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.line_width_set(width)

        use_legacy_line_smoothing(alpha, width)

        b = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
        b.draw(shader)

        del shader
        del b

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_tris(coords, indices=None, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    def draw():
        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.line_width_set(width)

        if mx != Matrix():
            batch = batch_for_shader(shader, 'TRIS', {"pos": [mx @ co for co in coords]}, indices=indices)

        else:
            batch = batch_for_shader(shader, 'TRIS', {"pos": coords}, indices=indices)

        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')
