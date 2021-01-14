import bpy
from bpy.props import IntProperty, FloatProperty
import bmesh
from math import pi, cos, sin, sqrt
from mathutils import Vector
from .. utils.draw import draw_points


class Threads(bpy.types.Operator):
    bl_idname = "machin3.add_threads"
    bl_label = "MACHIN3: Threads"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    segments: IntProperty(name="Segments", min=5, default=12)
    loops: IntProperty(name="Loops", min=1, default=2)

    depth: FloatProperty(name="Depth", min=0, max=100, default=20, description="Depth in Percentage of minor Diamater", subtype='PERCENTAGE')
    fade: FloatProperty(name="Fade", description="Percentage of Segments fading into inner Diameter", min=1, max=50, default=25, subtype='PERCENTAGE')

    h1: FloatProperty(name="Under Side", min=0, default=0.3, step=0.1)
    h2: FloatProperty(name="Width", min=0, default=0.0, step=0.1)
    h3: FloatProperty(name="Upper Side", min=0, default=0.1, step=0.1)
    h4: FloatProperty(name="Space", min=0, default=0.0, step=0.1)

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(context.active_object.data)
            # return [f for f in bm.faces if f.select]
            return True

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(self, 'segments')
        row.prop(self, 'loops')

        row = column.row(align=True)
        row.prop(self, 'depth')
        row.prop(self, 'fade')

        row = column.row(align=True)
        row.prop(self, 'h1', text='')
        row.prop(self, 'h3', text='')
        row.prop(self, 'h2', text='')
        row.prop(self, 'h4', text='')


    def execute(self, context):
        active = context.active_object
        mxi = active.matrix_world.inverted_safe()

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()

        # faces = [f for f in bm.faces if f.select]

        # coords, indices = thread_generator()
        # draw_points(coords, size=6, color=(1, 0, 0), alpha=0.5, modal=False)


        threads, bottom, top = thread_generator2(segments=self.segments, loops=self.loops, radius=1, depth=self.depth / 100, h1=self.h1, h2=self.h2, h3=self.h3, h4=self.h4, fade=self.fade / 100)


        # draw_points(coords, size=3, color=(0, 1, 0), modal=False)

        # """
        verts = []

        for co in threads[0]:
            v = bm.verts.new(mxi @ co)
            verts.append(v)


        faces = []

        for ids in threads[1]:
            f = bm.faces.new([verts[idx] for idx in ids])
            faces.append(f)

            # v.select_set(True)


        bottom_verts = []

        for co in bottom[0]:
            v = bm.verts.new(mxi @ co)
            bottom_verts.append(v)

        bottom_faces = []

        for ids in bottom[1]:
            # print(ids)

            f = bm.faces.new([bottom_verts[idx] for idx in ids])
            bottom_faces.append(f)


        top_verts = []

        for co in top[0]:
            v = bm.verts.new(mxi @ co)
            top_verts.append(v)

        top_faces = []

        for ids in top[1]:
            f = bm.faces.new([top_verts[idx] for idx in ids])
            top_faces.append(f)


        bmesh.ops.remove_doubles(bm, verts=verts + bottom_verts + top_verts, dist=0.0001)



        # """

        bm.normal_update()

        bmesh.update_edit_mesh(active.data)



        context.area.tag_redraw()
        return {'FINISHED'}


def thread_generator(verts_per_loop=12, loops=2, outer_radius=1.2, inner_radius=1, h1=0.3, h2=0.05, h3=0.1, h4=0.05, falloff_rate=5):
    '''
    thread profile
    # |   h4
    #  \  h3
    #  |  h2
    #  /  h1
    '''

    height = h1 + h2 + h3 + h4

    # create profile coords
    profile = []
    profile.append([inner_radius, 0, 0])
    profile.append([outer_radius, 0, h1])

    # the profile can have 3-5 coords, depending on the h2 and h4 "spacer values"
    if h2 > 0:
        profile.append([outer_radius, 0, h1 + h2])

    profile.append([inner_radius, 0, h1 + h2 + h3])

    if h4 > 0:
        profile.append([inner_radius, 0, h1 + h2 + h3 + h4])

    profile_count = len(profile)

    # init list of coords and indices
    coords = [[0, 0, 0] for _ in range(profile_count * (verts_per_loop + 1) * loops)]
    indices = [[0, 0, 0, 0] for _ in range((profile_count - 1) * verts_per_loop * loops)]

    # go around a cirle. for each point in ProfilePoints array, create a vertex
    angle = 0


    for i in range(verts_per_loop * loops + 1):
        angle = i * 2 * pi / verts_per_loop

        for j in range(profile_count):

            # falloff applies to outer rings only
            u = i / (verts_per_loop * loops)
            radius = inner_radius + (outer_radius - inner_radius) * (1 - 6 * (pow(2 * u - 1, falloff_rate * 4) / 2 - pow(2 * u - 1, falloff_rate * 6) / 3)) if profile[j][0] == outer_radius else inner_radius

            x = radius * cos(angle)
            y = radius * sin(angle)
            z = profile[j][2] + i / verts_per_loop * height

            coords[profile_count * i + j][0] = x
            coords[profile_count * i + j][1] = y
            coords[profile_count * i + j][2] = z


    # now build face array
    for i in range(verts_per_loop * loops):
        for j in range(profile_count - 1):
            indices[(profile_count - 1) * i + j][0] = profile_count * i + j
            indices[(profile_count - 1) * i + j][1] = profile_count * i + 1 + j
            indices[(profile_count - 1) * i + j][2] = profile_count * (i + 1) + 1 + j
            indices[(profile_count - 1) * i + j][3] = profile_count * (i + 1) + j

    return coords, indices


def thread_generator2(segments=12, loops=1, radius=1, depth=0.2, h1=0.3, h2=0.05, h3=0.1, h4=0.05, fade=0.25):
    '''
    thread profile
    # |   h4
    #  \  h3
    #  |  h2
    #  /  h1
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

    return (coords, indices), (bottom_coords, bottom_indices), (top_coords, top_indices)
