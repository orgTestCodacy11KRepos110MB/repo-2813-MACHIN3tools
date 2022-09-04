from mathutils import Matrix, Vector
from math import log10, floor


# VALUE

def dynamic_format(value, decimal_offset=0):
    '''
    see https://stackoverflow.com/questions/8011017/python-find-first-non-zero-digit-after-decimal-point
    and https://stackoverflow.com/questions/658763/how-to-suppress-scientific-notation-when-printing-float-values

    decimal offset adds additional decimal places

    return formated string
    '''
    if round(value, 6) == 0:
        return '0'

    l10 = log10(abs(value))
    f = floor(abs(l10))

    if l10 < 0:
        precision = f + 1 + decimal_offset

    else:
        precision = decimal_offset
    return f"{'-' if value < 0 else ''}{abs(value):.{precision}f}"


# VECTOR

def get_center_between_points(point1, point2, center=0.5):
    return point1 + (point2 - point1) * center


def get_center_between_verts(vert1, vert2, center=0.5):
    return get_center_between_points(vert1.co, vert2.co, center=center)


def get_edge_normal(edge):
    return average_normals([f.normal for f in edge.link_faces])


def get_face_center(face, method='MEDIAN_WEIGHTED'):
    if method == 'BOUNDS':
        return face.calc_center_bounds()
    elif method == 'MEDIAN':
        return face.calc_center_median()
    elif method == 'MEDIAN_WEIGHTED':
        return face.calc_center_median_weighted()


def average_locations(locationslist, size=3):
    avg = Vector.Fill(size)

    for n in locationslist:
        avg += n

    return avg / len(locationslist)


def average_normals(normalslist):
    avg = Vector()

    for n in normalslist:
        avg += n

    return avg.normalized()


# MATRIX

def flatten_matrix(mx):
    dimension = len(mx)
    return [mx[j][i] for i in range(dimension) for j in range(dimension)]


def compare_matrix(mx1, mx2, precision=4):
    '''
    matrix comparison by rounding the individual values
    this is used for comparing cursor matrices,
    which if changed used set_cursor has the tendenciy to have float precission issues prevent proper comparison
    '''

    round1 = [round(i, precision) for i in flatten_matrix(mx1)]
    round2 = [round(i, precision) for i in flatten_matrix(mx2)]
    return round1 == round2


def get_loc_matrix(location):
    return Matrix.Translation(location)


def get_rot_matrix(rotation):
    return rotation.to_matrix().to_4x4()


def get_sca_matrix(scale):
    scale_mx = Matrix()
    for i in range(3):
        scale_mx[i][i] = scale[i]
    return scale_mx


def create_rotation_matrix_from_vertex(obj, vert):
    '''
    create world space rotation matrix from vertex
    supports loose vertices too
    '''
    mx = obj.matrix_world

    # get the vertex normal in world space
    normal = mx.to_3x3() @ vert.normal

    # get binormal from longest linked edge
    if vert.link_edges:
        longest_edge = max([e for e in vert.link_edges], key=lambda x: x.calc_length())
        binormal = (mx.to_3x3() @ (longest_edge.other_vert(vert).co - vert.co)).normalized()

        # the tangent is a simple cross product
        tangent = binormal.cross(normal).normalized()

        # recalculate the binormal, because it's not guarantieed the previous one is 90 degrees to the normal
        binormal = normal.cross(tangent).normalized()

    # without linked faces get a binormal from the objects up vector
    else:
        objup = (mx.to_3x3() @ Vector((0, 0, 1))).normalized()

        # use the x axis if the edge is already pointing in z
        dot = normal.dot(objup)
        if abs(round(dot, 6)) == 1:
            objup = (mx.to_3x3() @ Vector((1, 0, 0))).normalized()

        tangent = normal.cross(objup).normalized()
        binormal = normal.cross(tangent).normalized()

    # we want the normal, tangent and binormal to become Z, X and Y, in that order
    # see http://renderdan.blogspot.com/2006/05/rotation-matrix-from-axis-vectors.html
    rot = Matrix()
    rot[0].xyz = tangent
    rot[1].xyz = binormal
    rot[2].xyz = normal

    # transpose, because blender is column major
    return rot.transposed()


def create_rotation_matrix_from_edge(obj, edge):
    '''
    create world space rotation matrix from edge
    supports loose edges too
    '''
    mx = obj.matrix_world

    # call the direction, the binormal, we want this to be the y axis at the end
    binormal = (mx.to_3x3() @ (edge.verts[1].co - edge.verts[0].co)).normalized()

    # get normal from linked faces
    if edge.link_faces:
        normal = (mx.to_3x3() @ get_edge_normal(edge)).normalized()
        tangent = binormal.cross(normal).normalized()

        # recalculate the normal, that's because the one calculated from the neighbouring faces may not actually be perpendicular to the binormal, if the faces are not planar
        normal = tangent.cross(binormal).normalized()

    # without linked faces get a normal from the objects up vector
    else:
        objup = (mx.to_3x3() @ Vector((0, 0, 1))).normalized()

        # use the x axis if the edge is already pointing in z
        dot = binormal.dot(objup)
        if abs(round(dot, 6)) == 1:
            objup = (mx.to_3x3() @ Vector((1, 0, 0))).normalized()

        tangent = (binormal.cross(objup)).normalized()
        normal = tangent.cross(binormal)

    # we want the normal, tangent and binormal to become Z, X and Y, in that order
    rotmx = Matrix()
    rotmx[0].xyz = tangent
    rotmx[1].xyz = binormal
    rotmx[2].xyz = normal

    # transpose, because blender is column major
    return rotmx.transposed()


def create_rotation_matrix_from_face(mx, face):
    '''
    create world space rotation matrix from face
    '''

    # get the face normal in world space
    normal = (mx.to_3x3() @ face.normal).normalized()

    # tangent = (mx.to_3x3() @ face.calc_tangent_edge()).normalized()
    tangent = (mx.to_3x3() @ face.calc_tangent_edge_pair()).normalized()

    # the binormal is a simple cross product
    binormal = normal.cross(tangent)

    # we want the normal, tangent and binormal to become Z, X and Y, in that order
    rot = Matrix()
    rot[0].xyz = tangent
    rot[1].xyz = binormal
    rot[2].xyz = normal

    # transpose, because blender is column major
    return rot.transposed()


def create_rotation_difference_matrix_from_quat(v1, v2):
    q = v1.rotation_difference(v2)
    return q.to_matrix().to_4x4()


def create_selection_bbox(coords):
    minx = min(coords, key=lambda x: x[0])
    maxx = max(coords, key=lambda x: x[0])

    miny = min(coords, key=lambda x: x[1])
    maxy = max(coords, key=lambda x: x[1])

    minz = min(coords, key=lambda x: x[2])
    maxz = max(coords, key=lambda x: x[2])

    midx = get_center_between_points(minx, maxx)
    midy = get_center_between_points(miny, maxy)
    midz = get_center_between_points(minz, maxz)

    mid = Vector((midx[0], midy[1], midz[2]))

    bbox = [Vector((minx.x, miny.y, minz.z)), Vector((maxx.x, miny.y, minz.z)),
            Vector((maxx.x, maxy.y, minz.z)), Vector((minx.x, maxy.y, minz.z)),
            Vector((minx.x, miny.y, maxz.z)), Vector((maxx.x, miny.y, maxz.z)),
            Vector((maxx.x, maxy.y, maxz.z)), Vector((minx.x, maxy.y, maxz.z))]

    return bbox, mid


def get_right_and_up_axes(context, mx):
    r3d = context.space_data.region_3d

    # get view right (and up) vectors in 3d space
    view_right = r3d.view_rotation @ Vector((1, 0, 0))
    view_up = r3d.view_rotation @ Vector((0, 1, 0))

    # get the right and up axes depending on the matrix that was passed in (object's local space, world space, etc)
    axes_right = []
    axes_up = []

    for idx, axis in enumerate([Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]):
        dot = view_right.dot(mx.to_3x3() @ axis)
        axes_right.append((dot, idx))

        dot = view_up.dot(mx.to_3x3() @ axis)
        axes_up.append((dot, idx))

    axis_right = max(axes_right, key=lambda x: abs(x[0]))
    axis_up = max(axes_up, key=lambda x: abs(x[0]))

    # determine flip
    flip_right = True if axis_right[0] < 0 else False
    flip_up = True if axis_up[0] < 0 else False

    return axis_right[1], axis_up[1], flip_right, flip_up
