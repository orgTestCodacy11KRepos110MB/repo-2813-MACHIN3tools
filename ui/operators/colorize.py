import bpy
import random
from bpy.props import FloatProperty, EnumProperty
from ... utils.registration import get_addon
from ... utils.material import get_last_node, lighten_color


# TODO: unique preset colors for decal types

class ColorizeMaterials(bpy.types.Operator):
    bl_idname = "machin3.colorize_materials"
    bl_label = "MACHIN3: Colorize Materials"
    bl_description = "Set Material Viewport Colors from last Node in Material"
    bl_options = {'REGISTER', 'UNDO'}

    lighten_amount: FloatProperty(name="Lighten", default=0.05, min=0, max=1)

    @classmethod
    def poll(cls, context):
        return bpy.data.materials

    def execute(self, context):
        for mat in bpy.data.materials:
            node = get_last_node(mat)

            if node:
                color = node.inputs.get("Base Color")

                if not color:
                    color = node.inputs.get("Color")

                if color:
                    mat.diffuse_color = lighten_color(color=color.default_value, amount=self.lighten_amount)

        return {'FINISHED'}


class ColorizeObjectsFromMaterials(bpy.types.Operator):
    bl_idname = "machin3.colorize_objects_from_materials"
    bl_label = "MACHIN3: Colorize Objects from Materials"
    bl_description = "Set Object Viewport Colors of selected Objects from their active Materials"
    bl_options = {'REGISTER', 'UNDO'}

    lighten_amount: FloatProperty(name="Lighten", default=0.05, min=0, max=1)

    @classmethod
    def poll(cls, context):
        return [obj for obj in context.selected_objects if obj.type != 'EMPTY']

    def execute(self, context):
        objects = [obj for obj in context.selected_objects if obj.type != 'EMPTY']

        for obj in objects:
            mat = obj.active_material

            if mat:
                node = get_last_node(mat)

                if node:
                    color = node.inputs.get("Base Color")

                    if not color:
                        color = node.inputs.get("Color")

                    if color:
                        obj.color = lighten_color(color=color.default_value, amount=self.lighten_amount)

        return {'FINISHED'}


class ColorizeObjectsFromActive(bpy.types.Operator):
    bl_idname = "machin3.colorize_objects_from_active"
    bl_label = "MACHIN3: Colorize Objects from Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.selected_objects

    @classmethod
    def description(cls, context, properties):
        if context.active_object and context.active_object.M3.is_group_empty:
            return"Set Object Viewport Colors from Active Object\nALT: Only set Color for active top-level Group\nCTRL: Set Group Colors recursively from each Group's Empty"
        else:
            return"Set Object Viewport Colors from Active Object"

    def invoke(self, context, event):

        # colorize the active group's objects only, when ALT is pressed, also ignore any child empties, as they may be used to colorize their own object
        if context.active_object and context.active_object.M3.is_group_empty and event.alt:
            objects = [obj for obj in context.active_object.children if obj.M3.is_group_object and not obj.M3.is_group_empty]
            self.colorize(context, objects)

        # colorize group recursively, and use each group's empty as the source, instead of the active object
        elif context.active_object and context.active_object.M3.is_group_empty and event.ctrl:
            self.colorize_group_recursively(context, context.active_object)
        else:
            objects = context.selected_objects
            self.colorize(context, objects)

        return {'FINISHED'}

    def colorize(self, context, objects, color=None):
        if not color:
            color = context.active_object.color

        for obj in objects:
            obj.color = color

    def colorize_group_recursively(self, context, empty):
        objects = [c for c in empty.children if c.M3.is_group_object and not c.M3.is_group_empty]
        groups = [c for c in empty.children if c.M3.is_group_empty]

        self.colorize(context, objects, color=empty.color)

        for group in groups:
            self.colorize_group_recursively(context, group)


multi_collection_items = [("LEAST", "Least", ""),
                          ("MOST", "Most", "")]


decal_collection_items = [("TYPE", "Type", ""),
                          ("PARENT", "Parent", ""),
                          ("IGNORE", "Ignore", "")]


# TODO: colorize objects from Groups

class ColorizeObjectsFromCollections(bpy.types.Operator):
    bl_idname = "machin3.colorize_objects_from_collections"
    bl_label = "MACHIN3: Colorize Objects from Collections"
    bl_description = "Set Object Viewport Colors of selected Objects based on Collections"
    bl_options = {'REGISTER', 'UNDO'}

    multiple: EnumProperty(name="Multiple Collections", items=multi_collection_items, default="MOST")

    decalmachine: EnumProperty(name="DECALmachine Collections", items=decal_collection_items, default="TYPE")


    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.split(factor=0.5)
        row.label(text="Multi-Collection Objects")
        r = row.row()
        r.prop(self, "multiple", expand=True)

        if self.dm:
            row = column.split(factor=0.5)
            row.label(text="Decal Collections")
            r = row.row()
            r.prop(self, "decalmachine", expand=True)

        column.label(text=self.msg, icon='INFO')


    @classmethod
    def poll(cls, context):
        return context.selected_objects


    def execute(self, context):
        self.dm, _, _, _ = get_addon("DECALmachine")


        collectiondict = {}

        for obj in context.selected_objects:
            cols = sorted([col for col in obj.users_collection], key=lambda c: len(c.objects), reverse=True if self.multiple == "MOST" else False)
            # print(obj.name, [col.name for col in cols], [col.DM.isdecaltypecol for col in cols])

            if self.dm:
                if obj.DM.isdecal:
                    if self.decalmachine == "TYPE":
                        cols = [col for col in cols if col.DM.isdecaltypecol]

                    if self.decalmachine == "PARENT":
                        cols = [col for col in cols if col.DM.isdecalparentcol]

                    if self.decalmachine == "IGNORE" and obj.parent:
                        cols = sorted([col for col in obj.parent.users_collection], key=lambda c: len(c.objects), reverse=True if self.multiple == "MOST" else False)


            if cols:
                col = cols[0]
            else:
                col = context.scene.collection


            if col in collectiondict:
                collectiondict[col]["objects"].append(obj)

            else:
                collectiondict[col] = {}
                collectiondict[col]["objects"] = [obj]
                collectiondict[col]["color"] = (random.random(), random.random(), random.random(), 1)


        for col in collectiondict:
            objects = collectiondict[col]["objects"]
            color = collectiondict[col]["color"]

            # print(col.name, color, len(objects))

            for obj in objects:
                obj.color = color

        self.msg = "Assigned %d unique colors." % (len(collectiondict))

        # print(self.msg)

        return {'FINISHED'}


class ColorizeObjectsFromGroups(bpy.types.Operator):
    bl_idname = "machin3.colorize_objects_from_groups"
    bl_label = "MACHIN3: Colorize Objects from Groups"
    bl_description = "Set Object Viewport Colors of selected Objects based on Group Membership"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.M3.is_group_empty

    def execute(self, context):
        group = context.active_object

        self.colorize_group_recursively(group)
        return {'FINISHED'}

    def colorize_group_recursively(self, empty):
        children = [c for c in empty.children if c.M3.is_group_object]

        empty.color = (random.random(), random.random(), random.random(), 1)

        for c in children:
            if c.M3.is_group_empty:
                self.colorize_group_recursively(c)
            else:
                c.color = empty.color
