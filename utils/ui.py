import bpy

icons = None


def get_icon(name):
    global icons

    if not icons:
        from .. import icons

    return icons[name].icon_id


def wrap_mouse(self, context, event, x=False, y=False):
    if x:
        if event.mouse_region_x > context.region.width - 2:
            context.window.cursor_warp(event.mouse_x - context.region.width + 2, event.mouse_y)
            self.last_mouse_x -= context.region.width

        elif event.mouse_region_x < 1:
            context.window.cursor_warp(event.mouse_x + context.region.width - 2, event.mouse_y)
            self.last_mouse_x += context.region.width

    if y:
        if event.mouse_region_y > context.region.height - 2:
            context.window.cursor_warp(event.mouse_x, event.mouse_y - context.region.height + 2)
            self.last_mouse_y -= context.region.height

        elif event.mouse_region_y < 1:
            context.window.cursor_warp(event.mouse_x, event.mouse_y + context.region.height - 2)
            self.last_mouse_y += context.region.height


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
