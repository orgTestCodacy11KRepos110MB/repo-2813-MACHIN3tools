from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as view3d_tools


def get_tools_from_context(context):
    tools = {}

    for tool in view3d_tools.tools_from_context(context):
        if tool:

            # tuple tool
            if type(tool) is tuple:
                for subtool in tool:
                    tools[subtool.idname] = {'label': subtool.label,
                                             'icon_value': view3d_tools._icon_value_from_icon_handle(subtool.icon)}
            # single tool
            else:
                tools[tool.idname] = {'label': tool.label,
                                      'icon_value': view3d_tools._icon_value_from_icon_handle(tool.icon)}

    return tools
