import bpy
from .. utils.math import average_locations, get_loc_matrix
from .. utils.object import parent, unparent


# TODO: remove from group
# TODO: add to group



def ungroup(empty):
    for obj in empty.children:
        unparent(obj)
        obj.M3.is_group_object = False

    bpy.data.objects.remove(empty, do_unlink=True)


class Group(bpy.types.Operator):
    bl_idname = "machin3.group"
    bl_label = "MACHIN3: Group"
    bl_description = "Group Objects by Parenting them to an Empty"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return len([obj for obj in context.selected_objects if not obj.parent]) > 1

    def execute(self, context):
        sel = [obj for obj in context.selected_objects if not obj.parent]

        avg_location = average_locations([obj.matrix_world.to_translation() for obj in sel])

        empty = bpy.data.objects.new(name="GROUP", object_data=None)
        empty.show_name = True
        empty.show_in_front = True
        empty.empty_display_type = 'CUBE'
        empty.empty_display_size = 0.1

        empty.matrix_world = get_loc_matrix(avg_location)
        context.scene.collection.objects.link(empty)
        empty.select_set(True)

        empty.M3.is_group_empty = True

        for obj in sel:
            parent(obj, empty)
            obj.M3.is_group_object = True

        return {'FINISHED'}


class UnGroup(bpy.types.Operator):
    bl_idname = "machin3.ungroup"
    bl_label = "MACHIN3: Un-Group"
    bl_description = "Un-Group selected top-level Groups\nALT: Un-Group all selected Groups"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return[obj for obj in context.selected_objects if obj.M3.is_group_empty]

    def invoke(self, context, event):
        all_empties = [obj for obj in context.selected_objects if obj.M3.is_group_empty]

        # by default only ungroup the top level groups
        empties = all_empties if event.alt else [e for e in all_empties if e.parent not in all_empties]

        # fetch potential higher level group empties
        upper_level = [e.parent for e in empties if e.parent and e.parent.M3.is_group_empty and e.parent not in all_empties]

        # ungroup
        for empty in empties:
            ungroup(empty)

        # clean up potential higher level groups that are now empty or only have a single child group
        for e in upper_level:
            # ungroup single child group of groups
            if len(e.children) == 1 and e.children[0].M3.is_group_empty and not e.parent:
                print("INFO: Un-Grouping single child group of groups", e.name)
                ungroup(e)
                continue

            # remove empty upper level groups
            if not e.children:
                print("INFO: Removing empty group", e.name)
                bpy.data.objects.remove(e, do_unlink=True)
                continue

        return {'FINISHED'}


class Add(bpy.types.Operator):
    bl_idname = "machin3.add_to_group"
    bl_label = "MACHIN3: add_to_group"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active_group = context.active_object if context.active_object and context.active_object.M3.is_group_empty and context.active_object.select_get() else None
            if active_group:
                return [obj for obj in context.selected_objects if not obj.M3.is_group_object and not obj.parent and not obj == active_group]

    def execute(self, context):
        active_group = context.active_object if context.active_object and context.active_object.M3.is_group_empty and context.active_object.select_get() else None
        objects = [obj for obj in context.selected_objects if not obj.M3.is_group_object and not obj.parent and not obj == active_group]

        for obj in objects:
            parent(obj, active_group)
            obj.M3.is_group_object = True

        return {'FINISHED'}


class Remove(bpy.types.Operator):
    bl_idname = "machin3.remove_from_group"
    bl_label = "MACHIN3: remove_from_group"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.M3.is_group_object]

    def execute(self, context):
        all_group_objects = [obj for obj in context.selected_objects if obj.M3.is_group_object]

        # only ever remove top level objects/groups from other groups
        group_objects = [obj for obj in all_group_objects if obj.parent not in all_group_objects]

        # fetch potential higher level group empties
        upper_level = {obj.parent for obj in group_objects if obj.parent and obj.parent.M3.is_group_empty and obj.parent not in all_group_objects}

        for obj in group_objects:
            unparent(obj)
            obj.M3.is_group_object = False

        # clean up potential higher level groups that are now empty or only have a single child group
        for e in upper_level:
            # ungroup single child group
            if len(e.children) == 1 and e.children[0].M3.is_group_object and not e.parent:
                print("INFO: Un-Grouping single child group", e.name)
                ungroup(e)
                continue

            # remove empty upper level groups
            if not e.children:
                print("INFO: Removing empty group", e.name)
                bpy.data.objects.remove(e, do_unlink=True)
                continue

        return {'FINISHED'}
