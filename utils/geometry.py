from math import cos, sin, pi
from mathutils import Vector


def calculate_thread(segments=12, loops=2, radius=1, depth=0.1, h1=0.2, h2=0.0, h3=0.2, h4=0.0, fade=0.15):
    '''
    create thread coordinates and face indices using the folowing profile
    thread profile
    # |   h4
    #  \  h3
    #  |  h2
    #  /  h1
    also ceate coordinates and indices for faces at the bottom and top of the thread, creating a full cylinder
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
