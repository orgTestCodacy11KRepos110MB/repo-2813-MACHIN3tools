import bpy
from .. utils.math import average_locations, get_loc_matrix
from .. utils.object import parent, unparent


# TODO: remove from group
# TODO: add to group


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
            self.ungroup(empty)

        # clean up potential higher level groups that are now empty or only have a single child group
        for e in upper_level:
            # ungroup single child group of groups
            if len(e.children) == 1 and e.children[0].M3.is_group_empty:
                print("INFO: Ungrouping single child group of groups", e.name)
                self.ungroup(e)
                continue

            # remove empty upper level groups
            if not e.children:
                print("INFO: Removing empty group", e.name)
                bpy.data.objects.remove(e, do_unlink=True)
                continue

        return {'FINISHED'}

    def ungroup(self, empty):
        for obj in empty.children:
            unparent(obj)
            obj.M3.is_group_object = False

        bpy.data.objects.remove(empty, do_unlink=True)
