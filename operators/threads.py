import bpy
from bpy.props import IntProperty, FloatProperty
import bmesh
from math import pi, cos, sin, sqrt
from mathutils import Vector, Matrix
from .. utils.draw import draw_points, draw_point, draw_vector
from .. utils.selection import get_boundary_edges, get_edges_vert_sequences
from .. utils.math import average_locations


class Threads(bpy.types.Operator):
    bl_idname = "machin3.add_threads"
    bl_label = "MACHIN3: Threads"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    radius: FloatProperty(name="Radius", min=0, default=1)
    segments: IntProperty(name="Segments", min=5, default=32)
    loops: IntProperty(name="Loops", min=1, default=4)

    depth: FloatProperty(name="Depth", description="Depth in Percentage of minor Diamater", min=0, max=100, default=10, subtype='PERCENTAGE')
    fade: FloatProperty(name="Fade", description="Percentage of Segments fading into inner Diameter", min=1, max=50, default=15, subtype='PERCENTAGE')

    h1: FloatProperty(name="Under Side", min=0, default=0.2, step=0.1)
    h2: FloatProperty(name="Width", min=0, default=0.05, step=0.1)
    h3: FloatProperty(name="Upper Side", min=0, default=0.2, step=0.1)
    h4: FloatProperty(name="Space", min=0, default=0.05, step=0.1)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(self, 'loops')
        row.prop(self, 'depth')
        row.prop(self, 'fade')

        row = column.row(align=True)
        row.prop(self, 'h1', text='')
        row.prop(self, 'h3', text='')
        row.prop(self, 'h2', text='')
        row.prop(self, 'h4', text='')

    def execute(self, context):
        active = context.active_object

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()

        selverts = [v for v in bm.verts if v.select]
        selfaces = [f for f in bm.faces if f.select]

        if selfaces:
            boundary = get_boundary_edges(selfaces)
            sequences = get_edges_vert_sequences(selverts, boundary, debug=False)

            # if there are 2 sequences
            if len(sequences) == 2:
                seq1, seq2 = sequences

                verts1, cyclic1 = seq1
                verts2, cyclic2 = seq2

                # if they are both cyclic and have the same amount of verts,and at least 5
                if cyclic1 == cyclic2 and cyclic1 is True and len(verts1) == len(verts2) and len(verts1) >= 5:
                    smooth = selfaces[0].smooth

                    if smooth:
                        active.data.use_auto_smooth = True

                    # deselect verts
                    for v in verts1 + verts2:
                        v.select_set(False)

                    bm.select_flush(False)

                    # set amount of segments
                    self.segments = len(verts1)

                    # get selection mid points
                    center1 = average_locations([v.co for v in verts1])
                    center2 = average_locations([v.co for v in verts2])

                    # get the radii, and set the radius as an average
                    radius1 = (center1 - verts1[0].co).length
                    radius2 = (center2 - verts2[0].co).length
                    self.radius = (radius1 + radius2) / 2

                    # create point coordinates and face indices
                    threads, bottom, top, height = generate_threads(segments=self.segments, loops=self.loops, radius=self.radius, depth=self.depth / 100, h1=self.h1, h2=self.h2, h3=self.h3, h4=self.h4, fade=self.fade / 100)

                    # build the faces from those coords and indices
                    verts, faces = self.build_faces(bm, threads, bottom, top, smooth=smooth)

                    # scale the thread geometry to fit the selection height
                    selheight = (center1 - center2).length
                    bmesh.ops.scale(bm, vec=Vector((1, 1, selheight / height)), space=Matrix(), verts=verts)

                    # move the thread geometry into alignment with the first selection center
                    bmesh.ops.translate(bm, vec=center1, space=Matrix(), verts=verts)

                    # then rotate it into alignment too, this is done in two steps, first the up vectors are aligned
                    selup = (center2 - center1).normalized()

                    selrot = Vector((0, 0, 1)).rotation_difference(selup)
                    bmesh.ops.rotate(bm, cent=center1, matrix=selrot.to_matrix(), verts=verts, space=Matrix())

                    # then the first verts are aligned too
                    threadvec = verts[0].co - center1
                    selvec = verts1[0].co - center1

                    matchrot = threadvec.rotation_difference(selvec)
                    bmesh.ops.rotate(bm, cent=center1, matrix=matchrot.to_matrix(), verts=verts, space=Matrix())

                    # remove doubles
                    bmesh.ops.remove_doubles(bm, verts=verts + verts1 + verts2, dist=0.00001)

                    # remove the initially selected faces
                    bmesh.ops.delete(bm, geom=selfaces, context='FACES')

                    bmesh.ops.recalc_face_normals(bm, faces=faces)

                    bmesh.update_edit_mesh(active.data)

                    return {'FINISHED'}
        return {'CANCELLED'}

    def build_faces(self, bm, threads, bottom, top, smooth=False):
        verts = []

        for co in threads[0]:
            v = bm.verts.new(co)
            verts.append(v)

        faces = []

        for ids in threads[1]:
            f = bm.faces.new([verts[idx] for idx in ids])
            f.smooth = smooth
            faces.append(f)

            if smooth:
                f.edges[0].smooth = False
                f.edges[-2].smooth = False

        bottom_verts = []

        for co in bottom[0]:
            v = bm.verts.new(co)
            bottom_verts.append(v)

        bottom_faces = []

        for ids in bottom[1]:
            f = bm.faces.new([bottom_verts[idx] for idx in ids])
            f.smooth = smooth
            bottom_faces.append(f)

            if smooth:
                if len(ids) == 4:
                    f.edges[-2].smooth = False
                else:
                    f.edges[-1].smooth = False

        top_verts = []

        for co in top[0]:
            v = bm.verts.new(co)
            top_verts.append(v)

        top_faces = []

        for ids in top[1]:
            f = bm.faces.new([top_verts[idx] for idx in ids])
            f.smooth = smooth
            top_faces.append(f)

            if smooth:
                if len(ids) == 4:
                    f.edges[0].smooth = False
                else:
                    f.edges[-1].smooth = False

        return [v for v in verts + bottom_verts + top_verts if v.is_valid], faces + bottom_faces + top_faces


def generate_threads(segments=32, loops=4, radius=1, depth=0.1, h1=0.2, h2=0.0, h3=0.2, h4=0.0, fade=0.15):
    '''
    thread profile
    # |   h4
    #  \  h3
    #  |  h2
    #  /  h1
    return coords and indices tuples for thread, bottom and top faces, as well as the total height of the thread
    '''

    height = h1 + h2 + h3 + h4

    # fade determines how many of the segments falloff
    falloff = segments * fade

    # create profile coords, there are 3-5 coords, depending on the h2 and h4 "spacer values"
    profile = [Vector((radius, 0, 0))]
    profile.append(Vector((radius + depth, 0, h1)))

    if h2 > 0:
        profile.append(Vector((radius + depth, 0, h1 + h2)))

    profile.append(Vector((radius, 0, h1 + h2 + h3)))

    if h4 > 0:
        profile.append(Vector((radius, 0, h1 + h2 + h3 + h4)))

    # based on the profile create the thread coords and indices
    pcount = len(profile)

    coords = []
    indices = []

    bottom_coords = []
    bottom_indices = []

    top_coords = []
    top_indices = []


    for loop in range(loops):
        for segment in range(segments + 1):
            angle = segment * 2 * pi / segments

            # create the thread coords
            for pidx, co in enumerate(profile):

                # the radius for individual points is always the x coord, except when adjusting the falloff for the first or last segments
                if loop == 0 and segment <= falloff and pidx in ([1, 2] if h2 else [1]):
                    r = radius + depth * segment / falloff
                elif loop == loops - 1 and segments - segment <= falloff and pidx in ([1, 2] if h2 else [1]):
                    r = radius + depth * (segments - segment) / falloff
                else:
                    r = co.x

                # slightly increase each profile coords height per segment, and offset it per loop too
                z = co.z + (segment / segments) * height + (height * loop)

                # add thread coords
                coords.append(Vector((r * cos(angle), r * sin(angle), z)))

                # add bottom coords, to close off the thread faces into a full cylinder
                if loop == 0 and pidx == 0:

                    # the last segment, has coords for all the verts of the profile!
                    if segment == segments:
                        bottom_coords.extend([Vector((radius, 0, co.z)) for co in profile])

                    # every other segment has a point at z == 0 and the first point in the profile
                    else:
                        bottom_coords.extend([Vector((r * cos(angle), r * sin(angle), 0)), Vector((r * cos(angle), r * sin(angle), z))])

                elif loop == loops - 1 and pidx == len(profile) - 1:

                    # the first segment, has coords for all the verts of the profile!
                    if segment == 0:
                        top_coords.extend([Vector((radius, 0, co.z + height + height * loop)) for co in profile])

                    # every other segment has a point at max height and the last point in the profile
                    else:
                        # top_coords.extend([Vector((r * cos(angle), r * sin(angle), 2 * height + height * loop)), Vector((r * cos(angle), r * sin(angle), z))])
                        top_coords.extend([Vector((r * cos(angle), r * sin(angle), z)), Vector((r * cos(angle), r * sin(angle), 2 * height + height * loop))])


            # for each segment - starting with the second one - create the face indices
            if segment > 0:

                # create thread face indices, pcount - 1 rows of them
                for p in range(pcount - 1):
                    indices.append([len(coords) + i + p for i in [-pcount * 2, -pcount, -pcount + 1, -pcount * 2 + 1]])

                # create bottom face indices
                if loop == 0:
                    if segment < segments:
                        bottom_indices.append([len(bottom_coords) + i for i in [-4, -2, -1, -3]])

                    # the last face will have 5-7 verts, depending on h2 and h4
                    else:
                        bottom_indices.append([len(bottom_coords) + i for i in [-1 - pcount, -2 - pcount] + [i - pcount for i in range(pcount)]])

                # create bottom face indices
                if loop == loops - 1:
                    # the first face will have 5-7 verts, depending on h2 and h4
                    if segment == 1:
                        top_indices.append([len(top_coords) + i for i in [-2, -1] + [-3 - i for i in range(pcount)]])
                    else:
                        top_indices.append([len(top_coords) + i for i in [-4, -2, -1, -3]])

    return (coords, indices), (bottom_coords, bottom_indices), (top_coords, top_indices), height + height * loops
