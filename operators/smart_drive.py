import bpy


class SmartDrive(bpy.types.Operator):
    bl_idname = "machin3.smart_drive"
    bl_label = "MACHIN3: Smart Drive"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        m3 = context.scene.M3

        driver_start = m3.driver_start
        driver_end = m3.driver_end

        driven_start = m3.driven_start
        driven_end = m3.driven_end

        if driver_start != driver_end and driven_start != driven_end and context.active_object:
            driven = context.active_object
            sel = [obj for obj in context.selected_objects if obj != driven]

            return len(sel) == 1

    def execute(self, context):
        m3 = context.scene.M3

        driver_start = m3.driver_start
        driver_end = m3.driver_end

        driven_start = m3.driven_start
        driven_end = m3.driven_end

        driven = context.active_object
        driver = [obj for obj in context.selected_objects if obj != driven][0]

        range_driver = abs(driver_end - driver_start)
        range_driven = abs(driven_end - driven_start)

        print()
        print("driver:", driver.name)
        print(" range:", range_driver)

        print()
        print("driven:", driven.name)
        print(" range:", range_driven)

        fcurve = driven.driver_add('location', 1)

        drv = fcurve.driver
        drv.type = 'SCRIPTED'

        var = drv.variables.new()
        var.name = 'loc'
        var.type = 'TRANSFORMS'

        target = var.targets[0]
        target.id = driver
        target.transform_type = 'LOC_X'
        target.transform_space = 'WORLD_SPACE'

        # driven end value is bigger than end value!
        if driven_end > driven_start:
            expr = f'((({var.name} - {driver_start}) / {range_driver}) * {range_driven}) + {driven_start}'

        # driven start value is bigger than end value!
        else:
            expr = f'{driven_start} - ((({var.name} - {driver_start}) / {range_driver}) * {range_driven})'

        drv.expression = expr

        # TODO: cap using min and max

        return {'FINISHED'}
