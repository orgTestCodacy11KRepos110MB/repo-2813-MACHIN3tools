import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty, FloatProperty
import bmesh
from .. items import bridge_interpolation_items, smartedge_sharp_mode_items, smartedge_select_mode_items
from .. utils.modifier import add_bevel
from .. utils.ui import popup_message


# TODO: why does bridging require custom props on this op, that are passe through, but bevel or offset edges doesn't???


class SmartEdge(bpy.types.Operator):
    bl_idname = "machin3.smart_edge"
    bl_label = "MACHIN3: Smart Edge"
    bl_options = {'REGISTER', 'UNDO'}

    sharp: BoolProperty(name="Toggle Sharp", default=False)
    sharp_mode: EnumProperty(name="Sharp Mode", items=smartedge_sharp_mode_items, default='SHARPEN')
    bevel_weight: FloatProperty(name="Weight", default=1, min=0.01, max=1)
    bevel_amount: FloatProperty(name="Amount", default=0.1, min=0, step=0.3, precision=4)
    bevel_clamp: BoolProperty(name="Clamp Overlap", default=False)
    bevel_loop: BoolProperty(name="Loop Slide", default=False)
    is_unbevel: BoolProperty(name="Is Unbevel")

    offset: BoolProperty(name="Offset Edge Slide", default=False)

    bridge_cuts: IntProperty(name="Cuts", default=0, min=0)
    bridge_interpolation: EnumProperty(name="Interpolation", items=bridge_interpolation_items, default='SURFACE')

    is_knife_projectable: BoolProperty(name="Can be Knife Projected", default=False)
    is_knife_project: BoolProperty(name="Is Knife Project", default=False)
    cut_through: BoolProperty(name="Cut Trough", default=False)

    select_mode: EnumProperty(name="Select Mode", items=smartedge_select_mode_items, default='BOUNDS')

    # screen cast
    is_knife = False
    is_connect = False
    is_starconnect = False
    is_select = False
    is_region = False
    is_loop_cut = False
    is_turn = False


    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)
        row = column.row(align=True)

        if self.is_knife_projectable:
            row.prop(self, 'is_knife_project', text='Knife Project', toggle=True)

            r = row.row(align=True)
            r.active = self.is_knife_project
            r.prop(self, "cut_through", toggle=True)

        elif self.draw_sharp_props:
            row.prop(self, "sharp_mode", expand=True)

            if self.sharp_mode in ['CHAMFER', 'KOREAN'] and not self.is_unbevel:
                row = column.row(align=True)
                row.prop(self, "bevel_amount")
                row.prop(self, "bevel_weight")

                row = column.row(align=True)
                row.prop(self, "bevel_clamp", toggle=True)
                row.prop(self, "bevel_loop", toggle=True)

        elif self.draw_bridge_props:
            row.prop(self, "bridge_cuts")
            row.prop(self, "bridge_interpolation", text="")

        elif self.is_select:
            row.label(text="Select")
            row.prop(self, "select_mode", expand=True)

    @classmethod
    def poll(cls, context):
        mode = tuple(context.scene.tool_settings.mesh_select_mode)
        return any(mode == m for m in [(True, False, False), (False, True, False), (False, False, True)])

    def invoke(self, context, event):
        self.draw_bridge_props = False
        self.draw_sharp_props = False
        self.is_knife_projectable = False
        self.do_knife_project = False
        self.is_unbevel = False
        self.is_knife = False
        self.is_connect = False
        self.is_starconnect = False
        self.is_select = False
        self.is_region = False
        self.is_loop_cut = False
        self.is_turn = False

        active = context.active_object
        self.show_wire = active.show_wire

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        verts = [v for v in bm.verts if v.select]
        faces = [f for f in bm.faces if f.select]
        edges = [e for e in bm.edges if e.select]

        # check if selection is isolated and can be knife projected
        if self.is_selection_separated(bm, verts, edges, faces):
            self.is_knife_projectable = True
            self.is_knife_project = True

        if self.sharp and self.sharp_mode in ['CHAMFER', 'KOREAN']:
            bevels = [mod for mod in active.modifiers if mod.type == 'BEVEL' and mod.limit_method == 'WEIGHT' and mod.name in ['Chamfer', 'Korean Bevel']]

            if bevels:
                bevel = bevels[-1]

                self.bevel_amount = bevel.width
                self.bevel_clamp = bevel.use_clamp_overlap
                self.bevel_loop = bevel.loop_slide


        return self.execute(context)

    def execute(self, context):
        active = context.active_object

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        bw = bm.edges.layers.bevel_weight.verify()

        verts = [v for v in bm.verts if v.select]
        faces = [f for f in bm.faces if f.select]
        edges = [e for e in bm.edges if e.select]


        # KNIFE PROJECT

        if self.is_knife_projectable and self.is_knife_project and not self.offset and not self.sharp:
            self.knife_project(context, active, cut_through=self.cut_through)
            return {'FINISHED'}

        # disable the prop for screen casting
        self.is_knife_project = False


        # TOGGLE SHARP

        if self.sharp and edges:
            self.draw_sharp_props = True

            if self.sharp_mode == 'SHARPEN':
                self.toggle_sharp(active, edges)

            else:
                self.set_bevel_weight(active, bw, edges)
                self.bevel(active, bw, edges)

            self.clean_up_bevels(active, bm, bw, edges)

            if not self.show_wire:
                active.show_wire = self.sharp_mode == 'KOREAN'


        # OFFSET EDGES

        elif self.offset and edges:
            self.offset_edges(active, edges)


        # SMART

        else:

            # vert mode
            if tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (True, False, False):
                verts = [v for v in bm.verts if v.select]

                # KNIFE
                if len(verts) <= 1:
                    self.is_knife = True
                    bpy.ops.mesh.knife_tool('INVOKE_DEFAULT')

                # PATH / STAR CONNECT
                else:

                    # star connects when appropriate, fall back to path connect otherwise
                    connected = self.star_connect(active, bm)

                    if connected:
                        self.is_starconnect = True

                    else:
                        try:
                            bpy.ops.mesh.vert_connect_path()
                            self.is_connect = True
                        except:
                            self.report({'ERROR'}, "Could not connect vertices")
                            return {'CANCELLED'}

            # edge mode
            elif tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, True, False):

                # LOOPCUT

                if len(edges) == 0:
                    self.is_loop_cut = True
                    bpy.ops.mesh.loopcut_slide('INVOKE_DEFAULT')


                # BRIDGE

                elif all([not e.is_manifold for e in edges]):
                    try:
                        bpy.ops.mesh.bridge_edge_loops(number_cuts=self.bridge_cuts, interpolation=self.bridge_interpolation)
                        self.draw_bridge_props = True
                    except:
                        popup_message("SmartEdge in Bridge mode requires two separate, non-manifold edge loops.")
                        return {'CANCELLED'}


                # TURN EDGE

                elif 1 <= len(edges) < 4:
                    self.is_turn = True
                    bpy.ops.mesh.edge_rotate(use_ccw=False)


                # SELECT

                elif len(edges) >= 4:
                    self.is_select = True

                    # LOOP TO REGION

                    if self.select_mode == 'BOUNDS':
                        self.is_region = True
                        bpy.ops.mesh.loop_to_region()
                        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')

                    # ADJACENT FACES

                    elif self.select_mode == 'ADJACENT':
                        self.select_adjacent_faces(active, edges)


            # face mode:
            elif tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, False, True):
                faces = [f for f in bm.faces if f.select]

                # LOOPCUT

                if not faces:
                    self.is_loop_cut = True
                    bpy.ops.mesh.loopcut_slide('INVOKE_DEFAULT')


                # SELECT

                else:
                    self.is_select = True

                    # REGION TO LOOP

                    if self.select_mode == 'BOUNDS':
                        bpy.ops.mesh.region_to_loop()

                    # ADJACENT EDGES

                    elif self.select_mode == 'ADJACENT':
                        self.select_adjacent_edges(active, edges, faces)


        return {'FINISHED'}


    # KNIFE PROJECT

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

    def knife_project(self, context, active, cut_through=False):
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')

        sel = [obj for obj in context.selected_objects if obj != active]

        if sel:
            for obj in sel:
                obj.select_set(False)

            # starting with 2.93.4 only the to-be-cut object has to be in edit mode
            # so select the cutter only after entire edit mode
            bpy.ops.object.mode_set(mode='EDIT')

            cutter = sel[0]
            cutter.select_set(True)

            try:
                bpy.ops.mesh.knife_project(cut_through=cut_through)

            except RuntimeError:
                pass

            # the 2.93.4 knife project changes allows us to skip a mode change too, when removing the cutter
            bpy.data.meshes.remove(cutter.data, do_unlink=True)


    # SHARP / CHAMFER / KOREAN BEVEL (mod)

    def toggle_sharp(self, active, edges):
        '''
        sharpen or unsharpen selected edges
        '''

        # existing sharp edges among selection: unsharpen
        if any([not e.smooth for e in edges]):
            smooth = True

        # no sharp edges found: sharpen
        else:
            smooth = False

        # (un)sharpen
        for e in edges:
            e.smooth = smooth

        bmesh.update_edit_mesh(active.data)

    def set_bevel_weight(self, active, bw, edges):
        '''
        add or remove bevel weight on selected edges
        '''

        # existing bevelled edges among selection: remove weigts
        if any([e[bw] > 0 for e in edges]):
            self.bevel_weight = max(e[bw] for e in edges)
            weight = 0

            self.is_unbevel = True

        # no weighted edges found: set weights
        else:
            weight = self.bevel_weight

        # bevel weighing
        for e in edges:
            e[bw] = weight

        bmesh.update_edit_mesh(active.data)

    def bevel(self, active, bw, edges):
        '''
        add bevel mod and name it according to the "sharp_method"
        '''

        bevels = [mod for mod in active.modifiers if mod.type == 'BEVEL' and mod.limit_method == 'WEIGHT' and mod.name in ['Chamfer', 'Korean Bevel']]

        # add new mod
        if not bevels:
            bevel = add_bevel(active)

        # use the existing mod
        else:
            bevel = bevels[-1]

        bevel.width = self.bevel_amount
        bevel.use_clamp_overlap = self.bevel_clamp
        bevel.loop_slide = self.bevel_loop

        if self.sharp_mode == 'CHAMFER':
            bevel.name = 'Chamfer'
            bevel.profile = 0.5
            bevel.segments = 1

        else:
            bevel.name = 'Korean Bevel'
            bevel.profile = 1
            bevel.segments = 2

    def clean_up_bevels(self, active, bm, bw, edges):
        '''
        remove chamfer/korean bevel mods if no weighted edges are found anymore
        '''

        if all([e[bw] == 0 for e in bm.edges]):
            bevels = [mod for mod in active.modifiers if mod.type == 'BEVEL' and mod.limit_method == 'WEIGHT' and mod.name in ['Chamfer', 'Korean Bevel']]

            for bevel in bevels:
                active.modifiers.remove(bevel)


    # KOREAN BEVEL (mesh)

    def offset_edges(self, active, edges):
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


    # STAR CONNECT

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


    # SELECT

    def select_adjacent_edges(self, active, edges, faces):
        '''
        selecting unselected edges, connected to the selected faces
        '''

        adjacent = {e for f in faces for v in f.verts for e in v.link_edges if e not in edges}

        bpy.ops.mesh.select_all(action='DESELECT')

        for e in adjacent:
            e.select_set(True)

        bmesh.update_edit_mesh(active.data)
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')


    def select_adjacent_faces(self, active, edges):
        '''
        select unselected faces, connected to the selected edges
        '''

        adjacent = {f for e in edges for f in e.link_faces}

        bpy.ops.mesh.select_all(action='DESELECT')

        for f in adjacent:
            f.select_set(True)

        bmesh.update_edit_mesh(active.data)
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
