import bpy
from bpy.props import EnumProperty, BoolProperty
from .. utils.object import parent, unparent
from .. utils.group import group, ungroup, get_group_matrix, select_group_children, get_child_depth, clean_up_groups, fade_group_sizes
from .. utils.collection import get_collection_depth
from .. utils.registration import get_prefs
from .. utils.modifier import get_mods_as_dict, add_mods_from_dict
from .. utils.object import compensate_children
from .. items import group_location_items


# CREATE / DESTRUCT

class Group(bpy.types.Operator):
    bl_idname = "machin3.group"
    bl_label = "MACHIN3: Group"
    bl_description = "Group Objects by Parenting them to an Empty"
    bl_options = {'REGISTER', 'UNDO'}

    location: EnumProperty(name="Location", items=group_location_items, default='AVERAGE')
    rotation: EnumProperty(name="Rotation", items=group_location_items, default='WORLD')

    @classmethod
    def poll(cls, context):
        '''
        this poll ensures the operator isn't called when a single object is selected whos parent has at least one boolean mod using the object
        even without this poll, no group would be created here, due to the object being parented, but this poll prevents any keymap overlap too
        '''

        if context.mode == 'OBJECT':
            sel = [obj for obj in context.selected_objects]
            if len(sel) == 1:
                obj = sel[0]
                parent = obj.parent

                if parent:
                    booleans = [mod for mod in parent.modifiers if mod.type == 'BOOLEAN' and mod.object == obj]
                    if booleans:
                        return False
            return True

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row()
        row.label(text="Location")
        row.prop(self, 'location', expand=True)

        row = column.row()
        row.label(text="Rotation")
        row.prop(self, 'rotation', expand=True)

    def invoke(self, context, event):
        self.coords = (event.mouse_region_x, event.mouse_region_y)

        return self.execute(context)

    def execute(self, context):
        # get selection, but ignore objects that are regularly parented(as opposed to grouped)
        sel = {obj for obj in context.selected_objects if (obj.parent and obj.parent.M3.is_group_empty) or not obj.parent}

        if sel:
            self.group(context, sel)

            return {'FINISHED'}
        return {'CANCELLED'}

    def group(self, context, sel):
        debug = False
        # debug = True

        # fetch all the already grouped objects in the selection
        grouped = {obj for obj in sel if obj.parent and obj.parent.M3.is_group_empty}

        # get the selected empties from the selection
        selected_empties = {obj for obj in sel if obj.M3.is_group_empty}

        if debug:
            print()
            print("               sel", [obj.name for obj in sel])
            print("           grouped", [obj.name for obj in grouped])
            print("  selected empties", [obj.name for obj in selected_empties])

        # all objects are grouped, find out if they share a common parent group
        # if there is a common parent then the new group can become a child of it
        if grouped == sel:

            # get the unselected empties too
            unselected_empties = {obj.parent for obj in sel if obj not in selected_empties and obj.parent and obj.parent.M3.is_group_empty and obj.parent not in selected_empties}

            # find the top level empties of the union of both of these sets
            top_level = {obj for obj in selected_empties | unselected_empties if obj.parent not in selected_empties | unselected_empties}

            if debug:
                print("unselected empties", [obj.name for obj in unselected_empties])
                print("         top level", [obj.name for obj in top_level])


            # if there is a single top level, then this will be the parent of the new group
            if len(top_level) == 1:
                new_parent = top_level.pop()

            # otherwise find out if there is a single common parent, that the top level empties share
            else:
                # NOTE: it's important to include None as a parent possibility here, if there a group doesn't have a parent
                # parent_groups = {obj.parent for obj in top_level if obj.parent and obj.parent.M3.is_group_empty}
                parent_groups = {obj.parent for obj in top_level}

                if debug:
                    print("     parent_groups", [obj.name if obj else None for obj in parent_groups])

                new_parent = parent_groups.pop() if len(parent_groups) == 1 else None


        # not all objects are grouped, create a new separate group, not parented to anything
        else:
            new_parent = None

        if debug:
            print("        new parent", new_parent.name if new_parent else None)
            print(20 * "-")

        # get three kinds of objects:
        # 1. top level group empties, that are in the original/group sel
        # 2. grouped non-empty objects whose parents are not in selected_empties
        # 3. objects not grouped

        # get the ungrouped objects in the selection, note that there are no ungrouped objects when sel == grouped
        ungrouped = {obj for obj in sel - grouped if obj not in selected_empties}

        # get top level of only the selected empties, important to not take the unselected empties into account here NOTE: this is different from the initial top_level set
        top_level = {obj for obj in selected_empties if obj.parent not in selected_empties}

        # get grouped objects not part of any top_level hierarchy, NOTE: this is different from the initial grouped set
        grouped = {obj for obj in grouped if obj not in selected_empties and obj.parent not in selected_empties}

        # if you select a single sub group, then its empty will also be the parent, in that case, simply update the parent to the group's parent!
        if len(top_level) == 1 and new_parent in top_level:
            new_parent = list(top_level)[0].parent

            if debug:
                print("updated parent", new_parent.name)

        if debug:
            print("     top level", [obj.name for obj in top_level])
            print("       grouped", [obj.name for obj in grouped])
            print("     ungrouped", [obj.name for obj in ungrouped])

        # unparent the grouped objects and the top_level empties
        for obj in top_level | grouped:
            unparent(obj)

        # then group top_level, grouped and ungrouped
        empty = group(context, top_level | grouped | ungrouped, location=self.location, rotation=self.rotation)

        if new_parent:
            parent(empty, new_parent)
            empty.M3.is_group_object = True

        # NOTE: blender seems to collapse the hierarchy for newly created objects in the outliner, including for empties
        # ####: it may not be visible for empties as they don't have a mesh, but it will be obvious once you parent something to the empty
        # ####: so unfortunately, you can't see the entire hierarchy when grouping
        # ####: the outliner ops will run when overriden with the correct area, but nothing is happening

        # cleanup potential empty groups, also untag group objects that are no longer tagged properly
        clean_up_groups(context)

        # fade group sizes
        if get_prefs().group_fade_sizes:
            fade_group_sizes(context, init=True)

        # draw label
        bpy.ops.machin3.draw_label(text=f"{'Sub' if new_parent else 'Root'}: {empty.name}", coords=self.coords, color=(0.5, 1, 0.5) if new_parent else (1, 1, 1), time=get_prefs().HUD_fade_group, alpha=0.75)


class UnGroup(bpy.types.Operator):
    bl_idname = "machin3.ungroup"
    bl_label = "MACHIN3: Un-Group"
    bl_options = {'REGISTER', 'UNDO'}

    ungroup_all_selected: BoolProperty(name="Un-Group all Selected Groups", default=False)
    ungroup_entire_hierarchy: BoolProperty(name="Un-Group entire Hierarchy down", default=False)

    @classmethod
    def description(cls, context, properties):
        if context.scene.M3.group_recursive_select and context.scene.M3.group_select:
            return "Un-Group selected top-level Groups\nALT: Un-Group all selected Groups"
        else:
            return "Un-Group selected top-level Groups\nALT: Un-Group all selected Groups\nCTRL: Un-Group entire Hierarchy down"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

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

        return self.execute(context)

    def execute(self, context):
        empties, all_empties = self.get_group_empties(context)

        if empties:
            self.ungroup(empties, all_empties)

            # cleanup
            clean_up_groups(context)

            # fade group sizes
            if get_prefs().group_fade_sizes:
                fade_group_sizes(context, init=True)

            return {'FINISHED'}
        return {'CANCELLED'}

    def get_group_empties(self, context):
        all_empties = [obj for obj in context.selected_objects if obj.M3.is_group_empty]

        # by default only ungroup the top level groups
        if self.ungroup_all_selected:
            empties = all_empties
        else:
            empties = [e for e in all_empties if e.parent not in all_empties]

        return empties, all_empties

    def collect_entire_hierarchy(self, empties):
        for e in empties:
            children = [obj for obj in e.children if obj.M3.is_group_empty]

            for c in children:
                self.empties.append(c)
                self.collect_entire_hierarchy([c])

    def ungroup(self, empties, all_empties):
        if self.ungroup_entire_hierarchy:
            self.empties = empties
            self.collect_entire_hierarchy(empties)
            empties = set(self.empties)

        # ungroup
        for empty in empties:
            ungroup(empty)


class Groupify(bpy.types.Operator):
    bl_idname = "machin3.groupify"
    bl_label = "MACHIN3: Groupify"
    bl_description = "Turn any Empty Hirearchy into Group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.type == 'EMPTY' and not obj.M3.is_group_empty and obj.children]

    def execute(self, context):
        all_empties = [obj for obj in context.selected_objects if obj.type == 'EMPTY' and not obj.M3.is_group_empty and obj.children]

        # only take the top level empties
        empties = [e for e in all_empties if e.parent not in all_empties]

        # groupify all the way down
        self.groupify(empties)

        # fade group sizes
        if get_prefs().group_fade_sizes:
            fade_group_sizes(context, init=True)

        return {'FINISHED'}

    def groupify(self, objects):
        for obj in objects:
            if obj.type == 'EMPTY' and not obj.M3.is_group_empty and obj.children:
                obj.M3.is_group_empty = True
                obj.M3.is_group_object = True if obj.parent and obj.parent.M3.is_group_empty else False
                obj.show_in_front = True
                obj.empty_display_type = 'CUBE'
                obj.empty_display_size = get_prefs().group_size
                obj.show_name = True

                if not any([s in obj.name.lower() for s in ['grp', 'group']]):
                    obj.name = f"{obj.name}_GROUP"

                # do it all the way down
                self.groupify(obj.children)

            else:
                obj.M3.is_group_object = True


# SELECT / DUPLICATE

class Select(bpy.types.Operator):
    bl_idname = "machin3.select_group"
    bl_label = "MACHIN3: Select Group"
    bl_description = "Select Group\nCTRL: Select entire Group Hierarchy down"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        if context.scene.M3.group_recursive_select:
            return "Select entire Group Hierarchies down"
        else:
            return "Select Top Level Groups\nCTRL: Select entire Group Hierarchy down"

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.M3.is_group_empty or obj.M3.is_group_object]

    def invoke(self, context, event):
        # cleanup all groups initially
        clean_up_groups(context)

        empties = {obj for obj in context.selected_objects if obj.M3.is_group_empty}
        objects = [obj for obj in context.selected_objects if obj.M3.is_group_object and obj not in empties]

        for obj in objects:
            if obj.parent and obj.parent.M3.is_group_empty:
                empties.add(obj.parent)

        # NOTE: only make the select and make empties active, if they are actually visible, it may not be visible when you are in local view with just some of the group objects
        # ####: if you would then make the empty active, you wouldn't be able to unsellect all until a new object is manually made active, because the group handler would keep the group selection alive

        for e in empties:
            if e.visible_get():
                e.select_set(True)

                if len(empties) == 1:
                    context.view_layer.objects.active = e

            select_group_children(context.view_layer, e, recursive=event.ctrl or context.scene.M3.group_recursive_select)

        # fade group sizes
        if get_prefs().group_fade_sizes:
            fade_group_sizes(context, init=True)

        return {'FINISHED'}


class Duplicate(bpy.types.Operator):
    bl_idname = "machin3.duplicate_group"
    bl_label = "MACHIN3: duplicate_group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        if context.scene.M3.group_recursive_select:
            return "Duplicate entire Group Hierarchies down\nALT: Create Instances"
        else:
            return "Duplicate Top Level Groups\nALT: Create Instances\nCTRL: Duplicate entire Group Hierarchies down"

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.M3.is_group_empty]

    def invoke(self, context, event):
        empties = [obj for obj in context.selected_objects if obj.M3.is_group_empty]

        # deselect everything, this ensures only the group will be duplicated, not any other non-group objects that may be selected
        bpy.ops.object.select_all(action='DESELECT')

        for e in empties:
            e.select_set(True)
            select_group_children(context.view_layer, e, recursive=event.ctrl or context.scene.M3.group_recursive_select)

        # fade group sizes
        if get_prefs().group_fade_sizes:
            fade_group_sizes(context, init=True)

        bpy.ops.object.duplicate_move_linked('INVOKE_DEFAULT') if event.alt else bpy.ops.object.duplicate_move('INVOKE_DEFAULT')

        return {'FINISHED'}


# ADD / REMOVE

class Add(bpy.types.Operator):
    bl_idname = "machin3.add_to_group"
    bl_label = "MACHIN3: Add to Group"
    bl_description = "Add Selection to Group"
    bl_options = {'REGISTER', 'UNDO'}

    realign_group_empty: BoolProperty(name="Re-Align Group Empty", default=False)
    location: EnumProperty(name="Location", items=group_location_items, default='AVERAGE')
    rotation: EnumProperty(name="Rotation", items=group_location_items, default='WORLD')

    add_mirror: BoolProperty(name="Add Mirror Modifiers, if there are common ones among the existing Group's objects, that are missing from the new Objects", default=True)
    is_mirror: BoolProperty()

    add_color: BoolProperty(name="Add Object Color, from Group's Empty", default=True)
    is_color: BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        column.prop(self, 'realign_group_empty', toggle=True)

        row = column.row()
        row.active = self.realign_group_empty
        row.prop(self, 'location', expand=True)

        row = column.row()
        row.active = self.realign_group_empty
        row.prop(self, 'rotation', expand=True)

        row = column.row(align=True)

        if self.is_color:
            row.prop(self, 'add_color', text="Add Color", toggle=True)

        if self.is_mirror:
            row.prop(self, 'add_mirror', text="Add Mirror", toggle=True)

    def execute(self, context):
        debug = False
        # debug = True

        active_group = context.active_object if context.active_object and context.active_object.M3.is_group_empty and context.active_object.select_get() else None

        if not active_group:

            # the poll is nerfed for the redo panel, so ensure there actually is an active child
            active_group = context.active_object.parent if context.active_object and context.active_object.M3.is_group_object and context.active_object.select_get() else None

            if not active_group:
                return {'CANCELLED'}

        # get the addable objects, all objects that aren't the active group or among its direct children, so including selected objects of other groups, but not those children whose parents are also selected, bc you want to keeps those hierarchies
        objects = [obj for obj in context.selected_objects if obj != active_group and obj not in active_group.children and (not obj.parent or (obj.parent and obj.parent.M3.is_group_empty and not obj.parent.select_get()))]

        if debug:
            print("active group", active_group.name)
            print("     addable", [obj.name for obj in objects])

        if objects:

            # existing mesh object children, before any new objects are added (ignore stashes, by checking presence in view_layer)
            # NOTE: it's not quite clear how stashes can become group objects, so this needs to be investigaed and prevented
            children = [c for c in active_group.children if c.M3.is_group_object and c.type == 'MESH' and c.name in context.view_layer.objects]

            # set prop to determine how whether add_mirror is drawn
            self.is_mirror = any(obj for obj in children for mod in obj.modifiers if mod.type == 'MIRROR')

            self.is_color = any(obj.type == 'MESH' for obj in objects)

            for obj in objects:
                # unparent existing group objects
                if obj.parent:
                    unparent(obj)

                # parent to the new/active group
                parent(obj, active_group)

                obj.M3.is_group_object = True

                # optionally add mirror mods and colorize the new object, but not for group empties
                if obj.type == 'MESH':

                    # check if all group children have common mirror mods, and if so add those same mirros to the new objects!
                    if children and self.add_mirror:
                        self.mirror(obj, active_group, children)

                    # colorize
                    if self.add_color:
                        obj.color = active_group.color

            # optionally re-align the goup empty
            if self.realign_group_empty:

                # get the new group empties matrix
                gmx = get_group_matrix(context, [c for c in active_group.children], self.location, self.rotation)

                # compensate the children location, so they stay in place
                compensate_children(active_group, active_group.matrix_world, gmx)

                # align the group's empty
                active_group.matrix_world = gmx


            # clean up
            clean_up_groups(context)

            # fade group sizes
            if get_prefs().group_fade_sizes:
                fade_group_sizes(context, init=True)

            return {'FINISHED'}
        return {'CANCELLED'}

    def mirror(self, obj, active_group, children):
        '''
        check if all group children have common mirror mods, and if so add those same mirrors to the new objects!
        unless the object object also hase those same mods already
        '''

        all_mirrors = {}

        for c in children:
            if c.M3.is_group_object and not c.M3.is_group_empty and c.type == 'MESH':
                mirrors = get_mods_as_dict(c, types=['MIRROR'], skip_show_expanded=True)

                if mirrors:
                    all_mirrors[c] = mirrors

        # first check if all the children actually have mirror mods
        if all_mirrors and len(all_mirrors) == len(children):


            # get the mirror props of the object
            obj_props = [props for props in get_mods_as_dict(obj, types=['MIRROR'], skip_show_expanded=True).values()]

            # then find the common mirror props among all the groups children
            # if there's only a single object with mirrors in the group, no commonally needs to be checked of course
            if len(all_mirrors) == 1:

                common_props = [props for props in next(iter(all_mirrors.values())).values() if props not in obj_props]

            # for mutliple objects with mirrors, get all the mods shared by all the group's children
            else:
                common_props = []

                for c, mirrors in all_mirrors.items():
                    others = [obj for obj in all_mirrors if obj != c]

                    for name, props in mirrors.items():
                        if all(props in all_mirrors[o].values() for o in others) and props not in common_props:
                            if props not in obj_props:
                                common_props.append(props)


            # create proper mods dict from list of common props, using mod names as keys
            if common_props:
                common_mirrors = {f"Mirror{'.' + str(idx).zfill(3) if idx else ''}": props for idx, props in enumerate(common_props)}

                # add the mods
                add_mods_from_dict(obj, common_mirrors)


class Remove(bpy.types.Operator):
    bl_idname = "machin3.remove_from_group"
    bl_label = "MACHIN3: Remove from Group"
    bl_description = "Remove Selection from Group"
    bl_options = {'REGISTER', 'UNDO'}

    realign_group_empty: BoolProperty(name="Re-Align Group Empty", default=False)
    location: EnumProperty(name="Location", items=group_location_items, default='AVERAGE')
    rotation: EnumProperty(name="Rotation", items=group_location_items, default='WORLD')

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

        row = column.row()
        row.active = self.realign_group_empty
        row.prop(self, 'rotation', expand=True)

    def execute(self, context):
        debug = False
        # debug = True

        all_group_objects = [obj for obj in context.selected_objects if obj.M3.is_group_object]

        # skip group objects, whose parents are also selected, so only ever remove top level objects/groups from other groups
        # this allows removing sub groups with auto-select enabled
        group_objects = [obj for obj in all_group_objects if obj.parent not in all_group_objects]

        if debug:
            print()
            print("all group objects", [obj.name for obj in all_group_objects])
            print("    group objects", [obj.name for obj in group_objects])

        if group_objects:

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
                        gmx = get_group_matrix(context, children, self.location, self.rotation)

                        # compensate the children location, so they stay in place
                        compensate_children(e, e.matrix_world, gmx)

                        # align the group's empty
                        e.matrix_world = gmx

            # clean up
            clean_up_groups(context)

            return {'FINISHED'}
        return {'CANCELLED'}


# OUTLINER

class ToggleChildren(bpy.types.Operator):
    bl_idname = "machin3.toggle_outliner_children"
    bl_label = "MACHIN3: Toggle Outliner Children"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'OUTLINER'

    def execute(self, context):
        area = context.area
        space = area.spaces[0]

        space.use_filter_children = not space.use_filter_children

        return {'FINISHED'}


class ToggleGroupMode(bpy.types.Operator):
    bl_idname = "machin3.toggle_outliner_group_mode"
    bl_label = "MACHIN3: Toggle Outliner Group Mode"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'OUTLINER'

    def execute(self, context):
        area = context.area
        space = area.spaces[0]

        if space.use_filter_object_mesh:
            space.use_filter_collection = False
            space.use_filter_object_mesh = False
            space.use_filter_object_content = False
            space.use_filter_object_armature = False
            space.use_filter_object_light = False
            space.use_filter_object_camera = False
            space.use_filter_object_others = False
            space.use_filter_children = True

        else:
            space.use_filter_collection = True
            space.use_filter_object_mesh = True
            space.use_filter_object_content = True
            space.use_filter_object_armature = True
            space.use_filter_object_light = True
            space.use_filter_object_camera = True
            space.use_filter_object_others = True

        return {'FINISHED'}


class CollapseOutliner(bpy.types.Operator):
    bl_idname = "machin3.collapse_outliner"
    bl_label = "MACHIN3: Collapse Outliner"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'OUTLINER'

    def execute(self, context):

        # get collection depth
        col_depth = get_collection_depth(self, [context.scene.collection], init=True)
        # print("collection depth", col_depth)

        # get child depth
        child_depth = get_child_depth(self, [obj for obj in context.scene.objects if obj.children], init=True)
        # print("child depth", child_depth)

        # collapse the max amount of the two, plus once more, in case meshes are expanded too
        for i in range(max(col_depth, child_depth) + 1):
            bpy.ops.outliner.show_one_level(open=False)

        return {'FINISHED'}


class ExpandOutliner(bpy.types.Operator):
    bl_idname = "machin3.expand_outliner"
    bl_label = "MACHIN3: Expand Outliner"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'OUTLINER'

    def execute(self, context):

        # expand parent-child hierarchies completely
        bpy.ops.outliner.show_hierarchy()

        # get collection depth
        depth = get_collection_depth(self, [context.scene.collection], init=True)

        # expand collections
        for i in range(depth):
            bpy.ops.outliner.show_one_level(open=True)

        return {'FINISHED'}
