import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty
import bmesh
from mathutils.geometry import distance_point_to_plane
import math
from .. items import cleanup_select_items


class CleanUp(bpy.types.Operator):
    bl_idname = "machin3.clean_up"
    bl_label = "MACHIN3: Clean Up"
    bl_options = {'REGISTER', 'UNDO'}

    remove_doubles: BoolProperty(name="Remove Doubles", default=True)
    dissolve_degenerate: BoolProperty(name="Dissolve Degenerate", default=True)
    distance: FloatProperty(name="Merge Distance", default=0.0001, min=0, step=0.01, precision=4)

    recalc_normals: BoolProperty(name="Recalculate Normals", default=True)
    flip_normals: BoolProperty(name="Flip Normals", default=False)

    delete_loose: BoolProperty(name="Delete Loose", default=True)
    delete_loose_verts: BoolProperty(name="Delete Loose Verts", default=True)
    delete_loose_edges: BoolProperty(name="Delete Loose Edges", default=True)
    delete_loose_faces: BoolProperty(name="Delete Loose Faces", default=False)

    dissolve_redundant: BoolProperty(name="Dissolve Redundant", default=True)
    dissolve_redundant_verts: BoolProperty(name="Dissolve Redundant Verts", default=True)
    dissolve_redundant_edges: BoolProperty(name="Dissolve Redundant Edges", default=False)
    dissolve_redundant_angle: FloatProperty(name="Dissolve Redundnat Angle", default=179.999, min=0, max=180, step=0.01, precision=6)

    select: BoolProperty(name="Select", default=True)
    select_type: EnumProperty(name="Select", items=cleanup_select_items, default="NON-MANIFOLD")
    planar_threshold: FloatProperty(name="Non-Planar Face Threshold", default=0.001, min=0, step=0.0001, precision=6)

    view_selected: BoolProperty(name="View Selected", default=False)

    def draw(self, context):
        layout = self.layout
        box = layout.box()

        col = box.column()

        row = col.split(factor=0.3, align=True)
        row.prop(self, "remove_doubles", text="Doubles")
        row.prop(self, "dissolve_degenerate", text="Degenerate")
        r = row.row()
        r.active = any([self.remove_doubles, self.dissolve_degenerate])
        r.prop(self, "distance", text="")

        row = col.split(factor=0.3, align=True)
        row.prop(self, "delete_loose", text="Loose")
        r = row.row(align=True)
        r.active = self.delete_loose
        r.prop(self, "delete_loose_verts", text="Verts", toggle=True)
        r.prop(self, "delete_loose_edges", text="Edges", toggle=True)
        r.prop(self, "delete_loose_faces", text="Faces", toggle=True)

        row = col.split(factor=0.3, align=True)
        row.prop(self, "dissolve_redundant", text="Redundant")
        r = row.row(align=True)
        r.active = self.dissolve_redundant
        r.prop(self, "dissolve_redundant_verts", text="Verts", toggle=True)
        r.prop(self, "dissolve_redundant_edges", text="Edges", toggle=True)
        rr = r.row(align=True)
        rr.active = any([self.dissolve_redundant_verts, self.dissolve_redundant_edges])
        rr.prop(self, "dissolve_redundant_angle", text="Angle")

        row = col.row()
        row.prop(self, "recalc_normals")
        r = row.row()
        r.active = self.recalc_normals
        r.prop(self, "flip_normals", text="Flip", toggle=True)

        box = layout.box()
        col = box.column(align=True)

        row = col.row()
        row.prop(self, "select")
        r = row.row()
        r.active = self.select
        r.prop(self, "view_selected")

        row = col.row(align=True)
        row.active = self.select
        row.prop(self, "select_type", expand=True)

        if self.select_type == 'NON-PLANAR':
            row = col.row(align=True)
            row.active = self.select
            row.prop(self, "planar_threshold", text='Threshold')


    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        active = context.active_object

        bm = self.clean_up(active)

        if self.select:
            self.select_geometry(bm)

        bmesh.update_edit_mesh(active.data)

        if self.select and self.view_selected:
            bpy.ops.view3d.view_selected(use_all_regions=False)

        return {'FINISHED'}

    def clean_up(self, active):
        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        if self.remove_doubles:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=self.distance)

        if self.dissolve_degenerate:
            bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=self.distance)

        if self.delete_loose:
            self.delete_loose_geometry(bm)

        if self.dissolve_redundant:
            self.dissolve_redundant_geometry(bm)

        if self.recalc_normals:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

            if self.flip_normals:
                for f in bm.faces:
                    f.normal_flip()
        return bm

    def delete_loose_geometry(self, bm):
        if self.delete_loose_verts:
            loose_verts = [v for v in bm.verts if not v.link_edges]
            bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")

        if self.delete_loose_edges:
            loose_edges = [e for e in bm.edges if not e.link_faces]
            bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")

        if self.delete_loose_faces:
            loose_faces = [f for f in bm.faces if all([not e.is_manifold for e in f.edges])]
            bmesh.ops.delete(bm, geom=loose_faces, context="FACES")

    def dissolve_redundant_geometry(self, bm):
        '''
        dissolve redundant verts on straight edges
        dissolve redundant edges on flat faces
        '''

        if self.dissolve_redundant_edges:
            manifold_edges = [e for e in bm.edges if e.is_manifold]

            redundant_edges = []

            for e in manifold_edges:
                angle = math.degrees(e.calc_face_angle(0))

                if angle < 180 - self.dissolve_redundant_angle:
                    redundant_edges.append(e)

            bmesh.ops.dissolve_edges(bm, edges=redundant_edges, use_verts=False)

            # dissolving with use_verts enabled can cause problems in som cases, so it's better to check the left over edges for 2 edged verts, and remove those in a separate step
            two_edged_verts = {v for e in redundant_edges if e.is_valid for v in e.verts if len(v.link_edges) == 2}
            bmesh.ops.dissolve_verts(bm, verts=list(two_edged_verts))

        # also run vert removal after edge removal to ensure verts from symmetry center lines get removed properly
        if self.dissolve_redundant_verts:
            two_edged_verts = [v for v in bm.verts if len(v.link_edges) == 2]

            redundant_verts = []

            for v in two_edged_verts:
                e1 = v.link_edges[0]
                e2 = v.link_edges[1]

                vector1 = e1.other_vert(v).co - v.co
                vector2 = e2.other_vert(v).co - v.co

                angle = min(math.degrees(vector1.angle(vector2)), 180)

                if self.dissolve_redundant_angle < angle:
                    redundant_verts.append(v)

            bmesh.ops.dissolve_verts(bm, verts=redundant_verts)

    def select_geometry(self, bm):
        for f in bm.faces:
            f.select = False

        bm.select_flush(False)

        if self.select_type == "NON-MANIFOLD":
            edges = [e for e in bm.edges if not e.is_manifold]

            for e in edges:
                e.select = True

        elif self.select_type == "NON-PLANAR":
            faces = [f for f in bm.faces if len(f.verts) > 3]

            for f in faces:
                distances = [distance_point_to_plane(v.co, f.calc_center_median(), f.normal) for v in f.verts]

                if any([d for d in distances if abs(d) > self.planar_threshold]):
                    f.select_set(True)

        elif self.select_type == "TRIS":
            faces = [f for f in bm.faces if len(f.verts) == 3]

            for f in faces:
                f.select = True

        elif self.select_type == "NGONS":
            faces = [f for f in bm.faces if len(f.verts) > 4]

            for f in faces:
                f.select = True
