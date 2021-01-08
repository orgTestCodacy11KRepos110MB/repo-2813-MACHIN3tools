import bpy
from bpy.props import EnumProperty, BoolProperty
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
from bl_ui.space_statusbar import STATUSBAR_HT_header as statusbar
import bmesh
from mathutils import Vector
from mathutils.geometry import intersect_point_line, intersect_line_line
from .. utils.graph import get_shortest_path
from .. utils.ui import popup_message
from .. utils.draw import draw_line, draw_lines, draw_point
from .. utils.raycast import cast_bvh_ray_from_mouse
from .. utils.math import average_locations, get_center_between_verts
from .. items import smartvert_mode_items, smartvert_merge_type_items, smartvert_path_type_items


def draw_slide_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text=f"Slide Extend")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if not op.is_snapping:
            row.label(text="", icon='EVENT_CTRL')
            row.label(text="Snap")

        if op.is_snapping and not op.is_diverging:
            row.label(text="", icon='EVENT_ALT')
            row.label(text="Diverge")

    return draw


class SmartVert(bpy.types.Operator):
    bl_idname = "machin3.smart_vert"
    bl_label = "MACHIN3: Smart Vert"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(name="Mode", items=smartvert_mode_items, default="MERGE")
    mergetype: EnumProperty(name="Merge Type", items=smartvert_merge_type_items, default="LAST")
    pathtype: EnumProperty(name="Path Type", items=smartvert_path_type_items, default="TOPO")

    slideoverride: BoolProperty(name="Slide Override", default=False)

    # hidden
    wrongselection = False
    snapping = False
    passthrough = False

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH' and tuple(context.scene.tool_settings.mesh_select_mode) == (True, False, False):
            bm = bmesh.from_edit_mesh(context.active_object.data)
            return [v for v in bm.verts if v.select]

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        if self.slideoverride:
            row = column.split(factor=0.3)
            row.label(text="Mode")
            r = row.row()
            r.label(text='Slide Extend')

        else:
            row = column.split(factor=0.3)
            row.label(text="Mode")
            r = row.row()
            r.prop(self, "mode", expand=True)

            if self.mode == "MERGE":
                row = column.split(factor=0.3)
                row.label(text="Merge")
                r = row.row()
                r.prop(self, "mergetype", expand=True)

            if self.mode == "CONNECT" or (self.mode == "MERGE" and self.mergetype == "PATHS"):
                if self.wrongselection:
                    column.label(text="You need to select exactly 4 vertices for paths.", icon="INFO")

                else:
                    row = column.split(factor=0.3)
                    row.label(text="Shortest Path")
                    r = row.row()
                    r.prop(self, "pathtype", expand=True)

    def draw_VIEW3D(self):
        # draw_point(self.target_avg, color=(1, 1, 0))
        # draw_point(self.origin, color=(1, 0, 0))

        # draw_point(self.init_loc, color=(1, 1, 1), alpha=0.5)
        # draw_point(self.loc, color=(1, 1, 0), alpha=0.5)
        # draw_line([self.init_loc, self.loc], width=2, alpha=0.2)

        # draw slide vectors
        if self.coords:
            draw_lines(self.coords, mx=self.mx, color=(0.5, 1, 0.5), width=3, alpha=0.5)

        # draw snap coords
        if self.is_snapping:
            if self.snap_coords:
                draw_lines(self.snap_coords, color=(1, 0, 0), width=3, alpha=0.75)

            if self.snap_proximity_coords:
                draw_lines(self.snap_proximity_coords, mx=self.mx, color=(1, 0, 0), width=1, alpha=0.3)

            if self.snap_ortho_coords:
                draw_lines(self.snap_ortho_coords, mx=self.mx, color=(1, 0.7, 0), width=1, alpha=0.3)


    def modal(self, context, event):
        context.area.tag_redraw()

        # update mouse
        self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))

        # set snapping
        self.is_snapping = event.ctrl
        self.is_diverging = self.is_snapping and event.alt

        if not self.is_snapping:
            self.snap_coords = []
            self.snap_proximity_coords = []
            self.snap_ortho_coords = []

        events = ['MOUSEMOVE', 'LEFT_CTRL', 'LEFT_ALT', 'RIGHT_CTRL', 'RIGHT_ALT']

        if event.type in events:
            if self.passthrough:
                self.passthrough = False

                # update the init_loc to compensate for the viewport change
                self.loc = self.get_slide_vector_intersection(context)
                self.init_loc = self.init_loc + self.loc - self.offset_loc

            # snap to edge
            elif event.ctrl:
                hitobj, hitlocation, hitnormal, hitindex, hitdistance, cache = cast_bvh_ray_from_mouse(self.mousepos, candidates=self.snappable, bmeshes=self.snap_bms, bvhs=self.snap_bvhs, debug=False)

                # cache bmeshes
                if cache['bmesh']:
                    for name, bm in cache['bmesh'].items():
                        if name not in self.snap_bms:
                            bm.faces.ensure_lookup_table()

                            self.snap_bms[name] = bm

                # cache bvhs
                if cache['bvh']:
                    for name, bvh in cache['bvh'].items():
                        if name not in self.snap_bvhs:
                            self.snap_bvhs[name] = bvh

                # snap to geometry
                if hitobj:
                    self.slide_snap(context, hitobj, hitlocation, hitindex)

                # side normally if nothing is hit
                else:
                    self.snap_coords = []
                    self.snap_proximity_coords = []
                    self.snap_ortho_coords = []

                    self.loc = self.get_slide_vector_intersection(context)

                    self.slide(context)

            # slide
            else:
                self.is_snapping = False
                self.loc = self.get_slide_vector_intersection(context)

                self.slide(context)


        # VIEWPORT control

        if event.type in {'MIDDLEMOUSE'}:
            # store the current location, so the view change can be taken into account
            self.offset_loc = self.get_slide_vector_intersection(context)

            self.passthrough = True
            return {'PASS_THROUGH'}

        # FINISH

        elif event.type in {'LEFTMOUSE', 'SPACE'}:

            # dissolve edges when snapping
            if self.is_snapping:

                # get the average distance that was moved
                avg_dist = sum((v.co - data['co']).length for v, data in self.verts.items()) / len(self.verts)

                # use it for dissolveing to ensure it works on very small scales as you'd expect
                bmesh.ops.dissolve_degenerate(self.bm, edges=self.bm.edges, dist=avg_dist / 100)
                self.bm.normal_update()
                bmesh.update_edit_mesh(self.active.data)

            self.finish()

            return {'FINISHED'}

        # CANCEL

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            # reset original vert locations
            for v, data in self.verts.items():
                v.co = data['co']

            self.bm.normal_update()
            bmesh.update_edit_mesh(self.active.data)

            self.finish()

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        # reset the statusbar
        statusbar.draw = self.bar_orig

        # remove snap copy of active
        bpy.data.meshes.remove(self.snap_copy.data, do_unlink=True)

        # remove snap bmeshes and bhs
        del self.snap_bms, self.snap_bvhs

    def invoke(self, context, event):

        # SLIDE EXTEND
        if self.slideoverride:
            bm = bmesh.from_edit_mesh(context.active_object.data)
            verts = [v for v in bm.verts if v.select]
            history = list(bm.select_history)

            if len(verts) == 1:
                popup_message("Select more than 1 vertex.")
                return {'CANCELLED'}

            elif not history:
                popup_message("Select the last vertex without Box or Circle Select.")
                return {'CANCELLED'}

            else:
                self.active = context.active_object
                self.mx = self.active.matrix_world

                self.bm = bmesh.from_edit_mesh(self.active.data)
                self.bm.normal_update()

                # get selected verts
                selected = [v for v in bm.verts if v.select]
                history = list(self.bm.select_history)

                # get each vert that is slid and the target it pushed away from or towards
                # also store the initial location of the moved verts

                # multi target sliding
                if len(selected) > 3 and len(selected) % 2 == 0 and set(history) == set(selected):
                    self.verts = {history[i]: {'co': history[i].co.copy(), 'target': history[i + 1]} for i in range(0, len(history), 2)}

                # single target sliding
                else:
                    last = history[-1]
                    self.verts = {v: {'co': v.co.copy(), 'target': last} for v in selected if v != last}

                # get average target and slid vert locations in world space
                self.target_avg = self.mx @ average_locations([data['target'].co for _, data in self.verts.items()])
                self.origin = self.mx @ average_locations([v.co for v, _ in self.verts.items()])

                # init mouse
                self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))

                # create first intersection of the view dir with the origin-to-targetavg vector
                self.init_loc = self.get_slide_vector_intersection(context)

                if self.init_loc:

                    # init
                    self.loc = self.init_loc
                    self.offset_loc = self.init_loc
                    self.distance = 0
                    self.coords = []

                    # init snapping
                    self.is_snapping = False
                    self.is_diverging = False
                    self.snap_bms = {}
                    self.snap_bvhs = {}
                    self.snap_coords = []
                    self.snap_proximity_coords = []
                    self.snap_ortho_coords = []

                    # create copy of the active to raycast on, this prevents an issue where the raycast flips from one face to the other because moving a vert changes the topology
                    self.active.update_from_editmode()
                    self.snap_copy = self.active.copy()
                    self.snap_copy.data = self.active.data.copy()

                    # snappable objects are all edit mesh object nicluding the the active's copy
                    edit_mesh_objects = [obj for obj in context.visible_objects if obj.mode == 'EDIT' and obj != self.active]
                    self.snappable = edit_mesh_objects + [self.snap_copy]

                    # handlers
                    self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (), 'WINDOW', 'POST_VIEW')

                    # draw statusbar info
                    self.bar_orig = statusbar.draw
                    statusbar.draw = draw_slide_status(self)

                    context.window_manager.modal_handler_add(self)
                    return {'RUNNING_MODAL'}

                return {'CANCELLED'}

        # MERGE and CONNECT
        else:
            self.smart_vert(context)

        return {'FINISHED'}

    def execute(self, context):
        self.smart_vert(context)
        return {'FINISHED'}

    def smart_vert(self, context):
        active = context.active_object
        topo = True if self.pathtype == "TOPO" else False

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        verts = [v for v in bm.verts if v.select]


        # VERT BEVEL

        if len(verts) == 1:
            bpy.ops.mesh.bevel('INVOKE_DEFAULT', affect='VERTICES')


        # MERGE

        elif self.mode == "MERGE":

            if self.mergetype == "LAST":
                if len(verts) >= 2:
                    if self.validate_history(active, bm, lazy=True):
                        bpy.ops.mesh.merge(type='LAST')

            elif self.mergetype == "CENTER":
                if len(verts) >= 2:
                    bpy.ops.mesh.merge(type='CENTER')

            elif self.mergetype == "PATHS":
                self.wrongselection = False

                if len(verts) == 4:
                    history = self.validate_history(active, bm)

                    if history:
                        path1, path2 = self.get_paths(bm, history, topo)

                        self.weld(active, bm, path1, path2)
                        return

                self.wrongselection = True

        # CONNECT

        elif self.mode == "CONNECT":
            self.wrongselection = False

            if len(verts) == 4:
                history = self.validate_history(active, bm)

                if history:
                    path1, path2 = self.get_paths(bm, history, topo)

                    self.connect(active, bm, path1, path2)
                    return

            self.wrongselection = True

    def get_paths(self, bm, history, topo):
        pair1 = history[0:2]
        pair2 = history[2:4]
        pair2.reverse()

        path1 = get_shortest_path(bm, *pair1, topo=topo, select=True)
        path2 = get_shortest_path(bm, *pair2, topo=topo, select=True)

        return path1, path2

    def validate_history(self, active, bm, lazy=False):
        verts = [v for v in bm.verts if v.select]
        history = list(bm.select_history)

        # just check for the prence of any element in the history
        if lazy:
            return history

        if len(verts) == len(history):
            return history
        return None

    def weld(self, active, bm, path1, path2):
        targetmap = {}
        for v1, v2 in zip(path1, path2):
            targetmap[v1] = v2

        bmesh.ops.weld_verts(bm, targetmap=targetmap)

        bmesh.update_edit_mesh(active.data)

    def connect(self, active, bm, path1, path2):
        for verts in zip(path1, path2):
            if not bm.edges.get(verts):
                bmesh.ops.connect_vert_pair(bm, verts=verts)

        bmesh.update_edit_mesh(active.data)

    def get_slide_vector_intersection(self, context):
        view_origin = region_2d_to_origin_3d(context.region, context.region_data, self.mousepos)
        view_dir = region_2d_to_vector_3d(context.region, context.region_data, self.mousepos)

        i = intersect_line_line(view_origin, view_origin + view_dir, self.origin, self.target_avg)

        return i[1]

    def slide(self, context):
        origin_dir = (self.target_avg - self.origin).normalized()
        move_dir = (self.loc - self.init_loc).normalized()

        # get distance in local space
        self.distance = (self.mx.to_3x3().inverted_safe() @ (self.init_loc - self.loc)).length * origin_dir.dot(move_dir)

        self.coords = []

        for v, data in self.verts.items():
            init_co = data['co']
            target = data['target']

            slidedir = (target.co - init_co).normalized()
            v.co = init_co + slidedir * self.distance

            self.coords.extend([v.co, target.co])

        self.bm.normal_update()
        bmesh.update_edit_mesh(self.active.data)

    def slide_snap(self, context, hitobj, hitlocation, hitindex):
        '''
        slide snap to edges of all edit mode objects
        '''

        # get hitface from the cached bmesh
        hitbm = self.snap_bms[hitobj.name]
        hitface = hitbm.faces[hitindex]

        # hit location in hitobj's local space
        hitmx = hitobj.matrix_world
        hit = hitmx.inverted() @ hitlocation

        # get closest edge
        edge = min([(e, (hit - intersect_point_line(hit, e.verts[0].co, e.verts[1].co)[0]).length, (hit - get_center_between_verts(*e.verts)).length) for e in hitface.edges], key=lambda x: (x[1] * x[2]) / x[0].calc_length())[0]

        # set snap coords for view3d drawing
        self.snap_coords = [hitmx @ v.co for v in edge.verts]

        # get snap coords in active's local space
        snap_coords = [self.mx.inverted_safe() @ co for co in self.snap_coords]

        # init proximity and ortho coords for view3d drawing
        self.snap_proximity_coords = []
        self.snap_ortho_coords = []

        # get intersection of individual slide dirs and snap coords
        for v, data in self.verts.items():
            init_co = data['co']
            target = data['target']

            snap_dir = (snap_coords[0] - snap_coords[1]).normalized()
            slide_dir = (init_co - target.co).normalized()

            # check for parallel and almost parallel snap edges, do nothing in this case
            if abs(slide_dir.dot(snap_dir)) > 0.999:
                v.co = init_co

            # with a smaller dot product, interseect_line_line will produce a guaranteed hit
            else:
                i = intersect_line_line(init_co, target.co, *snap_coords)

                v.co = i[1 if self.is_diverging else 0] if i else init_co

                # add coords to draw the slide 'edges'
                if v.co != target.co:
                    self.coords.extend([v.co, target.co])

                # add proximity coords
                if i[1] != snap_coords[0]:
                    self.snap_proximity_coords.extend([i[1], snap_coords[0]])

                # add ortho coords
                if v.co != i[1]:
                    self.snap_ortho_coords.extend([v.co, i[1]])


        self.bm.normal_update()
        bmesh.update_edit_mesh(self.active.data)
