import bpy
import bmesh
from mathutils.geometry import intersect_point_line, intersect_line_line
from bpy.props import EnumProperty, BoolProperty
from .. utils.graph import get_shortest_path
from .. utils.ui import init_cursor, wrap_cursor, popup_message
from .. utils.draw import draw_line, draw_lines, draw_point
from .. utils.raycast import cast_bvh_ray_from_mouse


modeitems = [("MERGE", "Merge", ""),
             ("CONNECT", "Connect Paths", "")]


mergetypeitems = [("LAST", "Last", ""),
                  ("CENTER", "Center", ""),
                  ("PATHS", "Paths", "")]

pathtypeitems = [("TOPO", "Topo", ""),
                 ("LENGTH", "Length", "")]


class SmartVert(bpy.types.Operator):
    bl_idname = "machin3.smart_vert"
    bl_label = "MACHIN3: Smart Vert"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(name="Mode", items=modeitems, default="MERGE")
    mergetype: EnumProperty(name="Merge Type", items=mergetypeitems, default="LAST")
    pathtype: EnumProperty(name="Path Type", items=pathtypeitems, default="TOPO")

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
        draw_lines(self.coords, self.edge_indices, color=(0.5, 1, 0.5), width=3, alpha=0.5)

        # for some reason event.alt doesn't update when passed in
        if self.snapping:
            draw_lines(self.snap_coords, color=(1, 0, 0), width=3, alpha=0.75)

    def modal(self, context, event):
        context.area.tag_redraw()

        # update mouse postion for HUD
        if event.type == "MOUSEMOVE":
            self.mouse_x = event.mouse_region_x
            self.mouse_y = event.mouse_region_y

        events = ["MOUSEMOVE"]

        # wrap mouse cursor
        if event.type == "MOUSEMOVE":
            wrap_cursor(self, context, event, x=True)

        if event.type in events:
            if event.type == 'MOUSEMOVE':

                if self.passthrough:
                    self.passthrough = False

                else:
                    divisor = 5000 if event.shift else 50 if event.ctrl else 500

                    delta_x = event.mouse_x - self.last_mouse_x
                    delta_distance = delta_x / divisor

                    self.distance += delta_distance

                    # modal slide to edge
                    if event.ctrl:
                        mousepos = (event.mouse_region_x, event.mouse_region_y)
                        hitobj, hitloc, _, hitindex, _ = cast_bvh_ray_from_mouse(mousepos, candidates=[self.active_copy], debug=False)

                        self.snapping = True
                        self.slide_to_edge(context, event, hitloc, hitindex)

                    # modal slide
                    else:
                        self.snapping = False
                        self.slide(context, self.distance)


        # VIEWPORT control

        elif event.type in {'MIDDLEMOUSE'}:
            self.passthrough = True
            return {'PASS_THROUGH'}

        # FINISH

        elif event.type in {'LEFTMOUSE', 'SPACE'}:
            bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
            bpy.data.meshes.remove(self.active_copy.data, do_unlink=True)
            return {'FINISHED'}

        # CANCEL

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel_modal()
            bpy.data.meshes.remove(self.active_copy.data, do_unlink=True)
            return {'CANCELLED'}

        self.last_mouse_x = event.mouse_x

        return {'RUNNING_MODAL'}

    def cancel_modal(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        bpy.ops.object.mode_set(mode='OBJECT')
        self.initbm.to_mesh(self.active.data)
        bpy.ops.object.mode_set(mode='EDIT')

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

                # make sure the current edit mode state is saved to obj.data
                self.active.update_from_editmode()

                # create copy to raycast on, this prevents an issue where the raycast flips from one face to the other because moving a vert changes the topology
                self.active_copy = self.active.copy()
                self.active_copy.data = self.active.data.copy()

                # save this initial mesh state, this will be used when canceling the modal and to reset it for each mousemove event
                self.initbm = bmesh.new()
                self.initbm.from_mesh(self.active.data)

                # mouse positions
                self.last_mouse_x = event.mouse_region_x
                self.distance = 1

                # initialize
                self.coords = []
                self.edge_indices = []
                self.snapping = False
                self.snap_coords = []

                # initialize mouse
                init_cursor(self, event)

                self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (), 'WINDOW', 'POST_VIEW')

                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}

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

        # MERGE

        if self.mode == "MERGE":

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

    def slide(self, context, distance):
        mx = self.active.matrix_world

        bpy.ops.object.mode_set(mode='OBJECT')

        bm = self.initbm.copy()
        bm.normal_update()

        selected = [v for v in bm.verts if v.select]
        history = list(bm.select_history)

        self.coords = []
        self.edge_indices = []

        # multi target sliding
        if len(selected) > 3 and len(selected) % 2 == 0 and set(history) == set(selected):
            pairs = [(history[i], history[i + 1]) for i in range(0, len(history), 2)]

            for v, target in pairs:
                v.co = target.co + (v.co - target.co) * distance

                self.coords.append(mx @ v.co)
                self.coords.append(mx @ target.co)

        # single target sliding
        else:
            last = history[-1]
            verts = [v for v in selected if v != last]

            self.coords.append(mx @ last.co)

            for idx, v in enumerate(verts):
                v.co = last.co + (v.co - last.co) * distance

                self.coords.append(mx @ v.co)
                self.edge_indices.append((0, idx + 1))

        bm.to_mesh(self.active.data)

        bpy.ops.object.mode_set(mode='EDIT')

    def slide_to_edge(self, context, event, location, index):
        mx = self.active.matrix_world

        bpy.ops.object.mode_set(mode='OBJECT')

        bm = self.initbm.copy()
        bm.normal_update()
        bm.faces.ensure_lookup_table()

        self.coords = []
        self.edge_indices = []
        self.snap_coords = []

        if location and index is not None:
            selected = [v for v in bm.verts if v.select]
            history = list(bm.select_history)

            face = bm.faces[index]

            closest = min([((intersect_point_line(location, mx @ e.verts[0].co, mx @ e.verts[1].co)[0] - location).length, [mx @ e.verts[0].co, mx @ e.verts[1].co], e) for e in face.edges])
            self.snap_coords = closest[1]

            # multi target sliding
            if len(selected) > 3 and len(selected) % 2 == 0 and set(history) == set(selected):
                pairs = [(history[i], history[i + 1]) for i in range(0, len(history), 2)]

                for v, target in pairs:
                    intersect = intersect_line_line(mx @ target.co, mx @ v.co, *self.snap_coords)
                    i = intersect[1 if event.alt else 0] if intersect else mx @ v.co
                    v.co = mx.inverted_safe() @ i

                    self.coords.append(i)
                    self.coords.append(mx @ target.co)


            # single target sliding
            else:
                last = history[-1]
                verts = [v for v in bm.verts if v.select and v != last]

                self.coords.append(mx @ last.co)

                for idx, v in enumerate(verts):
                    intersect = intersect_line_line(mx @ last.co, mx @ v.co, *self.snap_coords)
                    i = intersect[1 if event.alt else 0] if intersect else mx @ v.co
                    v.co = mx.inverted_safe() @ i

                    self.coords.append(i)
                    self.edge_indices.append((0, idx + 1))

        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=0.001)

        bm.to_mesh(self.active.data)

        bpy.ops.object.mode_set(mode='EDIT')
