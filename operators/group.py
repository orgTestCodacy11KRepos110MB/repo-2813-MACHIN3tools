import bpy
from bpy.props import EnumProperty, BoolProperty
from mathutils import Vector
from .. utils.math import average_locations, get_loc_matrix
from .. utils.object import parent, unparent
from .. items import group_location_items


# TODO: groupify (turn empty hierarchy in to group)


def ungroup(empty):
    for obj in empty.children:
        unparent(obj)
        obj.M3.is_group_object = False

    bpy.data.objects.remove(empty, do_unlink=True)


def get_group_matrix(context, location_type, objects):
    if location_type == 'AVERAGE':
        location = average_locations([obj.matrix_world.to_translation() for obj in objects])

    elif location_type == 'ACTIVE':
        if context.active_object:
            return context.active_object.matrix_world

        # fallback to average if no active object is present
        else:
            location = average_locations([obj.matrix_world.to_translation() for obj in objects])

    elif location_type == 'CURSOR':
        location = context.scene.cursor.location

    elif location_type == 'WORLD':
        location = Vector()

    return get_loc_matrix(location)


def select_group_children(empty, recursive=False):
    children = [c for c in empty.children if c.M3.is_group_object]

    for obj in children:
        obj.select_set(True)

        if obj.M3.is_group_empty and recursive:
            select_group_children(obj, recursive=True)


class Group(bpy.types.Operator):
    bl_idname = "machin3.group"
    bl_label = "MACHIN3: Group"
    bl_description = "Group Objects by Parenting them to an Empty"
    bl_options = {'REGISTER', 'UNDO'}

    location: EnumProperty(name="Location", items=group_location_items, default='AVERAGE')

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            # return len([obj for obj in context.selected_objects if not obj.parent]) > 1
            return True

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row()
        row.label(text="Location")
        row.prop(self, 'location', expand=True)

    def execute(self, context):
        sel = [obj for obj in context.selected_objects if not obj.parent]

        if len(sel) > 1:

            # get collection
            col = self.get_collection(context, sel)

            empty = bpy.data.objects.new(name="GROUP.001", object_data=None)
            empty.M3.is_group_empty = True
            empty.matrix_world = get_group_matrix(context, self.location, sel)
            col.objects.link(empty)

            context.view_layer.objects.active = empty
            empty.select_set(True)
            empty.show_in_front = True
            empty.empty_display_type = 'CUBE'

            if context.scene.M3.group_hide:
                empty.show_name = False
                empty.empty_display_size = 0

            else:
                empty.show_name = True
                empty.empty_display_size = 0.1

            for obj in sel:
                parent(obj, empty)
                obj.M3.is_group_object = True

            return {'FINISHED'}
        else:
            return {'CANCELLED'}

    def get_collection(self, context, sel):
        '''
        if all the objects in sel are in the same collection, return it
        otherwise return the master collection
        '''

        collections = set()

        for obj in sel:
            for col in obj.users_collection:
                collections.add(col)

        if len(collections) == 1:
            return collections.pop()

        else:
            return context.scene.collection


class UnGroup(bpy.types.Operator):
    bl_idname = "machin3.ungroup"
    bl_label = "MACHIN3: Un-Group"
    bl_description = "Un-Group selected top-level Groups\nALT: Un-Group all selected Groups\nCTRL: Un-Group entire Hierarchy down"
    bl_options = {'REGISTER', 'UNDO'}

    ungroup_all_selected: BoolProperty(name="Un-Group all Selected Groups", default=False)
    ungroup_entire_hierarchy: BoolProperty(name="Un-Group entire Hierarchy down", default=False)

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            # return [obj for obj in context.selected_objects if obj.M3.is_group_empty]
            return True

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row(align=True)
        row.label(text="Un-Group")
        row.prop(self, 'ungroup_all_selected', text='All Selected', toggle=True)
        row.prop(self, 'ungroup_entire_hierarchy', text='Entire Hierarchy', toggle=True)

    def invoke(self, context, event):
        self.ungroup_all_selected = event.alt
        self.ungroup_entire_hierarchy = event.ctrl

        self.execute(context)
        return {'FINISHED'}

    def execute(self, context):
        all_empties = [obj for obj in context.selected_objects if obj.M3.is_group_empty]

        # by default only ungroup the top level groups
        if self.ungroup_all_selected:
            empties = all_empties
        else:
            empties = [e for e in all_empties if e.parent not in all_empties]

        if self.ungroup_entire_hierarchy:
            self.empties = empties
            self.collect_entire_hierarchy(empties)
            empties = set(self.empties)

        # fetch potential higher level group empties
        upper_level = [e.parent for e in empties if e.parent and e.parent.M3.is_group_empty and e.parent not in all_empties]

        # ungroup
        for empty in empties:
            ungroup(empty)


        # clean up potential higher level groups that are now empty or only have a single child group
        for e in upper_level:
            if str(e) != '<bpy_struct, Object invalid>':
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

    def collect_entire_hierarchy(self, empties):
        for e in empties:
            children = [obj for obj in e.children if obj.M3.is_group_empty]

            for c in children:
                self.empties.append(c)
                self.collect_entire_hierarchy([c])


class Add(bpy.types.Operator):
    bl_idname = "machin3.add_to_group"
    bl_label = "MACHIN3: Add to Group"
    bl_description = "Add Selection to Group"
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
    bl_label = "MACHIN3: Remove from Group"
    bl_description = "Remove Selection from Group"
    bl_options = {'REGISTER', 'UNDO'}

    realign_group_empty: BoolProperty(name="Re-Align Group Empty", default=False)

    location: EnumProperty(name="Location", items=group_location_items, default='AVERAGE')


    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            # return [obj for obj in context.selected_objects if obj.M3.is_group_object]
            return True

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        column.prop(self, 'realign_group_empty', toggle=True)

        row = column.row()
        row.active = self.realign_group_empty
        row.prop(self, 'location', expand=True)


    def execute(self, context):
        all_group_objects = [obj for obj in context.selected_objects if obj.M3.is_group_object]

        # only ever remove top level objects/groups from other groups
        group_objects = [obj for obj in all_group_objects if obj.parent not in all_group_objects]

        # fetch potential higher level group empties
        upper_level = {obj.parent for obj in group_objects if obj.parent and obj.parent.M3.is_group_empty and obj.parent not in all_group_objects}

        # collect group empties
        empties = set()

        for obj in group_objects:
            empties.add(obj.parent)

            unparent(obj)
            obj.M3.is_group_object = False

        # optionally re-align the goup empty
        if self.realign_group_empty:
            for e in empties:
                children = [c for c in e.children]

                if children:
                    gmx = get_group_matrix(context, self.location, children)

                    # get the matrix difference, aka the old mx expressed in the new ones local space
                    deltamx = gmx.inverted_safe() @ e.matrix_world

                    # align the group's empty
                    e.matrix_world = gmx

                    # compensate the children location, so they stay in place
                    for c in children:
                        pmx = c.matrix_parent_inverse
                        c.matrix_parent_inverse = pmx @ deltamx


        # clean up potential higher level groups that are now empty or only have a single child group
        for e in upper_level:
            if str(e) != '<bpy_struct, Object invalid>':

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


class Select(bpy.types.Operator):
    bl_idname = "machin3.select_group"
    bl_label = "MACHIN3: Select Group"
    bl_description = "Select Group\nCTRL: Select entire Group Hierarchy down"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.M3.is_group_empty or obj.M3.is_group_object]

    def invoke(self, context, event):
        empties = {obj for obj in context.selected_objects if obj.M3.is_group_empty}
        objects = [obj for obj in context.selected_objects if obj.M3.is_group_object and obj not in empties]

        for obj in objects:
            if obj.parent and obj.parent.M3.is_group_empty:
                empties.add(obj.parent)

        for e in empties:
            e.select_set(True)

            select_group_children(e, recursive=event.ctrl)

        return {'FINISHED'}


class Duplicate(bpy.types.Operator):
    bl_idname = "machin3.duplicate_group"
    bl_label = "MACHIN3: duplicate_group"
    bl_description = "Duplicate a Group\nALT: Create Instances\nCTRL: Duplicate entire Hierarchy down"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.M3.is_group_empty]

    def invoke(self, context, event):
        empties = [obj for obj in context.selected_objects if obj.M3.is_group_empty]

        for e in empties:
            select_group_children(e, recursive=event.ctrl)

        bpy.ops.object.duplicate_move_linked('INVOKE_DEFAULT') if event.alt else bpy.ops.object.duplicate_move('INVOKE_DEFAULT')

        return {'FINISHED'}
