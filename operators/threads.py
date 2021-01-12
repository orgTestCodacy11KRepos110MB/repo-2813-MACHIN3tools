import bpy
import bmesh
from math import pi, cos, sin
from mathutils import Vector
from .. utils.draw import draw_points


class Threads(bpy.types.Operator):
    bl_idname = "machin3.add_threads"
    bl_label = "MACHIN3: Threads"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(context.active_object.data)
            # return [f for f in bm.faces if f.select]
            return True

    def execute(self, context):
        active = context.active_object
        mxi = active.matrix_world.inverted_safe()

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()

        # faces = [f for f in bm.faces if f.select]

        # coords, indices = thread_generator()
        # draw_points(coords, size=6, color=(1, 0, 0), alpha=0.5, modal=False)


        coords, indices = thread_generator2()
        # draw_points(coords, size=3, color=(0, 1, 0), modal=False)

        # """
        verts = []

        for co in coords:
            v = bm.verts.new(mxi @ co)
            verts.append(v)

        for ids in indices:
            bm.faces.new([verts[idx] for idx in ids])
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
            # radius = inner_radius + (outer_radius - inner_radius) * (1 - 6 * (pow(2 * u - 1, falloff_rate * 4) / 2 - pow(2 * u - 1, falloff_rate * 6) / 3)) if profile[j][0] == outer_radius else inner_radius

            # radius = inner_radius + (outer_radius - inner_radius) * 1 if profile[j][0] == outer_radius else inner_radius
            radius = profile[j][0]


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


def thread_generator2(segments=12, loops=1, outer_radius=1.2, inner_radius=1, h1=0.3, h2=0.05, h3=0.1, h4=0.05, falloff_rate=5):
    '''
    thread profile
    # |   h4
    #  \  h3
    #  |  h2
    #  /  h1
    '''

    height = h1 + h2 + h3 + h4

    # create profile coords, there are 3-5 coords, depending on the h2 and h4 "spacer values"
    profile = [Vector((inner_radius, 0, 0))]
    profile.append(Vector((outer_radius, 0, h1)))

    if h2 > 0:
        profile.append(Vector((outer_radius, 0, h1 + h2)))

    profile.append(Vector((inner_radius, 0, h1 + h2 + h3)))

    if h4 > 0:
        profile.append(Vector((inner_radius, 0, h1 + h2 + h3 + h4)))

    # based on the profile create the thread coords and indices
    pcount = len(profile)

    coords = []
    indices = []

    for loop in range(loops):
        for segment in range(segments + 1):
            angle = segment * 2 * pi / segments

            # create the thread coords
            for co in profile:

                # the radius is always the x coord
                radius = co.x

                # slightly increase each profile coords height per segment, and offset it per loop too
                z = co.z + (segment / segments) * height + (height * loop)

                coords.append(Vector((radius * cos(angle), radius * sin(angle), z)))

            # create the indices
            if segment > 0:

                # create pcount - 1 rows of face indices
                for p in range(pcount - 1):
                    indices.append([len(coords) + i + p for i in [-pcount * 2, -pcount, -pcount + 1, -pcount * 2 + 1]])

    return coords, indices
