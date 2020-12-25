import bpy
from mathutils import Vector, Quaternion


def set_cursor(matrix=None, location=Vector(), rotation=Quaternion()):
    '''
    NOTE: setting the cursor rotation will result in tiny float imprecision issues and so the cursor matrix will differ very slightly afterwards
    '''

    cursor = bpy.context.scene.cursor

    # setting cursor.matrix has no effect unless a selection event occurs, so set location and rotation individually
    if matrix:
        cursor.location = matrix.to_translation()
        cursor.rotation_quaternion = matrix.to_quaternion()
        cursor.rotation_mode = 'QUATERNION'

    # use passed in location and rotation
    else:
        cursor.location = location

        if cursor.rotation_mode == 'QUATERNION':
            cursor.rotation_quaternion = rotation

        elif cursor.rotation_mode == 'AXIS_ANGLE':
            cursor.rotation_axis_angle = rotation.to_axis_angle()

        else:
            cursor.rotation_euler = rotation.to_euler(cursor.rotation_mode)
