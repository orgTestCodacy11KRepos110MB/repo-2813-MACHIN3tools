import bpy
import rna_keymap_ui


icons = None


def get_icon(name):
    global icons

    if not icons:
        from .. import icons

    return icons[name].icon_id


# CURSOR

def init_cursor(self, event):
    self.last_mouse_x = event.mouse_x
    self.last_mouse_y = event.mouse_y

    # region offsets
    self.region_offset_x = event.mouse_x - event.mouse_region_x
    self.region_offset_y = event.mouse_y - event.mouse_region_y


def wrap_cursor(self, context, event, x=False, y=False):
    if x:

        if event.mouse_region_x <= 0:
            context.window.cursor_warp(context.region.width + self.region_offset_x - 10, event.mouse_y)

        if event.mouse_region_x >= context.region.width - 1:  # the -1 is required for full screen, where the max region width is never passed
            context.window.cursor_warp(self.region_offset_x + 10, event.mouse_y)


        """
        if event.mouse_region_x > context.region.width - 2:
            context.window.cursor_warp(event.mouse_x - context.region.width + 2, event.mouse_y)
            self.last_mouse_x -= context.region.width

        elif event.mouse_region_x < 1:
            context.window.cursor_warp(event.mouse_x + context.region.width - 2, event.mouse_y)
            self.last_mouse_x += context.region.width
        """

    if y:
        if event.mouse_region_y <= 0:
            context.window.cursor_warp(event.mouse_x, context.region.height + self.region_offset_y - 10)

        if event.mouse_region_y >= context.region.height - 1:
            context.window.cursor_warp(event.mouse_x, self.region_offset_y + 100)

        """
        if event.mouse_region_y > context.region.height - 2:
            context.window.cursor_warp(event.mouse_x, event.mouse_y - context.region.height + 2)
            self.last_mouse_y -= context.region.height

        elif event.mouse_region_y < 1:
            context.window.cursor_warp(event.mouse_x, event.mouse_y + context.region.height - 2)
            self.last_mouse_y += context.region.height
        """


# POPUP

def popup_message(message, title="Info", icon="INFO", terminal=True):
    def draw_message(self, context):
        if isinstance(message, list):
            for m in message:
                self.layout.label(text=m)
        else:
            self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw_message, title=title, icon=icon)

    if terminal:
        if icon == "FILE_TICK":
            icon = "ENABLE"
        elif icon == "CANCEL":
            icon = "DISABLE"
        print(icon, title)

        if isinstance(message, list):
            print(" »", ", ".join(message))
        else:
            print(" »", message)


# KEYMAPS

def kmi_to_string(kmi):
    '''
    return keymap item as printable string
    '''
    return "%s, name: %s, active: %s, map type: %s, type: %s, value: %s, alt: %s, ctrl: %s, shift: %s, properties: %s" % (kmi.idname, kmi.name, kmi.active, kmi.map_type, kmi.type, kmi.value, kmi.alt, kmi.ctrl, kmi.shift, str(kmi.properties.items()))


def draw_keymap_items(kc, name, keylist, layout):
    drawn = []

    # index keeping track of SUCCESSFULL kmi iterations
    idx = 0

    for item in keylist:
        keymap = item.get("keymap")
        isdrawn = False

        if keymap:
            km = kc.keymaps.get(keymap)

            kmi = None
            if km:
                idname = item.get("idname")

                for kmitem in km.keymap_items:
                    if kmitem.idname == idname:
                        properties = item.get("properties")

                        if properties:
                            if all([getattr(kmitem.properties, name, None) == value for name, value in properties]):
                                kmi = kmitem
                                break

                        else:
                            kmi = kmitem
                            break

            # draw keymap item

            if kmi:
                # multi kmi tools, will share a single box, created for the first kmi
                if idx == 0:
                    box = layout.box()

                # single kmi tools, get their label from the title
                if len(keylist) == 1:
                    label = name.title().replace("_", " ")

                # multi kmi tools, get it from the label tag, while the title is printed once, before the first item
                else:
                    if idx == 0:
                        box.label(text=name.title().replace("_", " "))

                    label = item.get("label")

                row = box.split(factor=0.15)
                row.label(text=label)

                # layout.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, row, 0)

                # draw info, if available
                infos = item.get("info", [])
                for text in infos:
                    row = box.split(factor=0.15)
                    row.separator()
                    row.label(text=text, icon="INFO")

                isdrawn = True
                idx += 1

        drawn.append(isdrawn)
    return drawn
