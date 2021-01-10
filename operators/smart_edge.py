import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty
import bmesh
from .. items import bridge_interpolation_items
from .. utils.ui import popup_message


# TODO: why does bridging require custom props on this op, that are passe through, but bevel or offset edges doesn't???


class SmartEdge(bpy.types.Operator):
    bl_idname = "machin3.smart_edge"
    bl_label = "MACHIN3: Smart Edge"
    bl_options = {'REGISTER', 'UNDO'}

    sharp: BoolProperty(name="Toggle Sharp", default=False)
    offset: BoolProperty(name="Offset Edge Slide", default=True)

    bridge_cuts: IntProperty(name="Cuts", default=0, min=0)
    bridge_interpolation: EnumProperty(name="Interpolation", items=bridge_interpolation_items, default='SURFACE')

    cut_through: BoolProperty(name="Cut Trough", default=False)

    draw_bridge_props = False
    draw_knife_props_props = False

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        if self.draw_bridge_props:
            row = column.row(align=True)
            row.prop(self, "bridge_cuts")
            row.prop(self, "bridge_interpolation", text="")

        elif self.draw_knife_props:
            row = column.row(align=True)
            row.prop(self, "cut_through")

    @classmethod
    def poll(cls, context):
        mode = tuple(context.scene.tool_settings.mesh_select_mode)
        return any(mode == m for m in [(True, False, False), (False, True, False), (False, False, True)])

    def execute(self, context):
        self.draw_bridge_props = False
        self.draw_knife_props = False

        active = context.active_object

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        verts = [v for v in bm.verts if v.select]
        faces = [f for f in bm.faces if f.select]
        edges = [e for e in bm.edges if e.select]


        # KNIFE PROJECT

        if self.is_selection_separated(bm, verts, edges, faces):
            self.knife_project(context, active, cut_through=self.cut_through)
            return {'FINISHED'}


        # TOGGLE SHARP

        if self.sharp and edges:
            self.toggle_sharp(active, bm, edges)

        elif self.offset and edges:
            self.offset_edges(active, bm, edges)

        # SMART

        else:
            ts = context.scene.tool_settings
            mode = tuple(ts.mesh_select_mode)

            # vert mode
            if mode[0]:
                verts = [v for v in bm.verts if v.select]

                # KNIFE
                if len(verts) <= 1:
                    bpy.ops.mesh.knife_tool('INVOKE_DEFAULT')

                # PATH / STAR CONNECT
                else:

                    # star connects when appropriate, fall back to path connect otherwise
                    connected = self.star_connect(active, bm)

                    if not connected:
                        bpy.ops.mesh.vert_connect_path()

            # edge mode
            elif mode[1]:

                # LOOPCUT
                if len(edges) == 0:
                    bpy.ops.mesh.loopcut_slide('INVOKE_DEFAULT')

                # BRIDGE
                elif all([not e.is_manifold for e in edges]):
                    try:
                        bpy.ops.mesh.bridge_edge_loops(number_cuts=self.bridge_cuts, interpolation=self.bridge_interpolation)
                        self.draw_bridge_props = True
                    except:
                        popup_message("SmartEdge in Bridge mode requires two separate, non-manifold edge loops.")

                # TURN EDGE
                elif 1 <= len(edges) < 4:
                    bpy.ops.mesh.edge_rotate(use_ccw=False)

                # LOOP TO REGION
                elif len(edges) >= 4:
                    bpy.ops.mesh.loop_to_region()
                    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')

            # face mode
            elif mode[2]:
                faces = [f for f in bm.faces if f.select]

                # REGION TO LOOP
                if faces:
                    bpy.ops.mesh.region_to_loop()

                # LOOPCUT
                else:
                    bpy.ops.mesh.loopcut_slide('INVOKE_DEFAULT')

        return {'FINISHED'}

    def knife_project(self, context, active, cut_through=False):
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')

        sel = [obj for obj in context.selected_objects if obj != active]

        if sel:
            cutter = sel[0]
            cutter.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')

            try:
                bpy.ops.mesh.knife_project(cut_through=cut_through)
                self.draw_knife_props = True

            except RuntimeError:
                self.draw_knife_props = False

            # remove cutter
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.meshes.remove(cutter.data, do_unlink=True)
            bpy.ops.object.mode_set(mode='EDIT')

    def is_selection_separated(self, bm, verts, edges, faces):
        '''
        figure out of selecting is separated from the rest of the mesh
        '''

        # abort if nothing is selected or the entire mesh is selected
        if not verts or len(faces) == len(bm.faces):
            return False

        # check for each selected vert, if every connected edge or face is also selected
        for v in verts:
            if not all(e in edges for e in v.link_edges):
                return False

            if not all(f in faces for f in v.link_faces):
                return False
        return True

    def toggle_sharp(self, active, bm, edges):
        '''
        sharpen or unsharpen selected edges
        '''

        # existing sharp edges among selection unsharpen
        if any([not e.smooth for e in edges]):
            smooth = True

        # no sharp edges found - sharpen
        else:
            smooth = False

        # (un)sharpen
        for e in edges:
            e.smooth = smooth

        bmesh.update_edit_mesh(active.data)

    def offset_edges(self, active, bm, edges):
        '''
        offset parallel edges creating a "korean bevel", choosing either the bevel tool or the offset_edge_loop_slide tool to do so, depending on the circumstances, remove sharps too
        '''
        verts = {v for e in edges for v in e.verts}

        connected_edge_counts = [len([e for e in v.link_edges if e not in edges]) for v in verts]

        for e in edges:
            e.smooth = True

        # if at least one of the verts doesn't have at least 2 conencted edges use bevel!
        if any(count < 2 for count in connected_edge_counts):
            bpy.ops.mesh.bevel('INVOKE_DEFAULT', segments=2, profile=1)

        # other wise use edge offset slide
        else:
            bpy.ops.mesh.offset_edge_loops_slide('INVOKE_DEFAULT',
                                                 MESH_OT_offset_edge_loops={"use_cap_endpoint": False},
                                                 TRANSFORM_OT_edge_slide={"value": -1, "use_even": True, "flipped": False, "use_clamp": True, "correct_uv": True})
        bmesh.update_edit_mesh(active.data)

    def star_connect(self, active, bm):
        '''
        verify the selection and star connect if it fits, otherwise return False
        '''

        def star_connect(bm, last, verts):
            verts.remove(last)

            for v in verts:
                bmesh.ops.connect_verts(bm, verts=[last, v])

        verts = [v for v in bm.verts if v.select]
        history = list(bm.select_history)
        last = history[-1] if history else None

        # check if there's a common face shared by all the verts, a good indicator for star connect
        faces = [f for v in verts for f in v.link_faces]

        common = None
        for f in faces:
            if all([v in f.verts for v in verts]):
                common = f

        # with only two verts, only a path connect makes sence, unless the verts are connected already, then nothing should be done, it works even without a history in the case of just 2
        if len(verts) == 2 and not bm.edges.get([verts[0], verts[1]]):
            return False

        # with 3 verts the base assumption is, you want to make a path connect, common face or not
        elif len(verts) == 3:
            # nothing goes without an active vert
            if last:

                # for path connect you need to have a complete history
                if len(verts) == len(history):
                    return False

                # without a complete history the only option is star connect, but that works only with a common face
                elif common:
                    star_connect(bm, last, verts)


        # with more than 3 verts, the base assumption is, you want to make a star connect, complete history or not
        elif len(verts) > 3:
            # nothing goes without an active vert
            if last:

                # for star connect, you need to have a common face
                if common:
                    star_connect(bm, last, verts)


                # without a common face, the only option is path connect but that needs a complete history
                elif len(verts) == len(history):
                    return False

        bmesh.update_edit_mesh(active.data)
        return True
