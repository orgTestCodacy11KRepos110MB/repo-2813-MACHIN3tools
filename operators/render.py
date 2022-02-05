import bpy
from bpy.props import BoolProperty
from .. utils.registration import get_prefs
from .. utils.system import makedir
from random import randint
import os


class SeedRender(bpy.types.Operator):
    bl_idname = "machin3.seed_render"
    bl_label = "MACHIN3: Seed Render"
    bl_options = {'REGISTER', 'UNDO'}

    random: BoolProperty(name="Use Random Seeds", default=False)

    @classmethod
    def description(cls, context, properties):
        desc = f"Render {get_prefs().seed_render_count} Images with different seeds and combine them, to get rid of fireflies"

        if context.scene.render.engine != 'CYCLES':
            desc += "\nNOTE: You need to enable Cycles as the Render Engine"

        if not context.scene.camera:
            desc += "\nNOTE: You need to have an active Camera in the Scene"

        return desc

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'CYCLES' and context.scene.camera

    def invoke(self, context, event):
        self.random = event.alt
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        cycles = scene.cycles
        init_seed = cycles.seed

        currentblend = bpy.data.filepath
        currentfolder = os.path.dirname(currentblend)

        outfolder = makedir(os.path.join(currentfolder, 'out'))
        blendname = os.path.basename(currentblend).split('.')[0]

        resolution = f"{scene.render.resolution_x}x{scene.render.resolution_y}"
        fileformat = scene.render.image_settings.file_format

        count = get_prefs().seed_render_count

        # disable compositing
        scene.render.use_compositing = False

        # collect seeeds and file paths
        seedpaths = []

        # """
        print()
        print(f"Seed Rendering {count}x{' (random)' if self.random else ''}, Resolution: {resolution}, Format: {fileformat}")

        # openthe render view
        bpy.ops.render.view_show('INVOKE_DEFAULT')

        for i in range(count):

            # use a predictable, reproducable or random seed
            seed = randint(0, 999) if self.random else i

            cycles.seed = seed

            print(" Rendering Seed:", seed)
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            # TODO: date time instead of index?
            if self.random:
                save_path = os.path.join(outfolder, f"{blendname}_{resolution}_{i + 1}_{str(seed).zfill(3)}.{fileformat.lower()}")
            else:
                save_path = os.path.join(outfolder, f"{blendname}_{resolution}_{str(seed).zfill(3)}.{fileformat.lower()}")

            img = bpy.data.images.get('Render Result')
            img.save_render(filepath=save_path)
            seedpaths.append((seed, save_path))

            # temporaryily change the Render Result image name and update the UI as progress indication
            img.name = f"Render Seed {str(seed).zfill(3)} ({i + 1}/{count})"
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            img.name = f"Render Result"


        # load the renderings
        renders = []

        for idx, (seed, path) in enumerate(seedpaths):
            loadimg = bpy.data.images.load(filepath=path)
            loadimg.name = f"Render Seed {str(seed).zfill(3)} ({idx + 1}/{count})"

            renders.append(loadimg)

        # enable compositing and comp nodes
        scene.render.use_compositing = True
        scene.use_nodes = True

        tree = scene.node_tree

        # clear all existing nodes
        for node in tree.nodes:
            tree.nodes.remove(node)

        imgnodes = []
        mixnodes = []

        # renders = range(get_prefs().seed_render_count)

        for idx, render in enumerate(renders):
            imgnode = tree.nodes.new('CompositorNodeImage')
            imgnode.image = render
            imgnodes.append(imgnode)

            imgnode.location.x = idx * 200

            if idx < len(renders) - 1:
                mixnode = tree.nodes.new('CompositorNodeMixRGB')
                mixnode.blend_type = 'DARKEN'
                mixnodes.append(mixnode)

                mixnode.location.x = 400 + idx * 200
                mixnode.location.y = 300


            if idx == 0:
                tree.links.new(imgnode.outputs[0], mixnode.inputs[1])
            else:
                tree.links.new(imgnode.outputs[0], mixnodes[idx - 1].inputs[2])

                if idx < len(renders) - 1:
                    tree.links.new(mixnodes[idx - 1].outputs[0], mixnodes[idx].inputs[1])


            if idx == len(renders) - 1:
                compnode = tree.nodes.new('CompositorNodeComposite')

                compnode.location.x = imgnode.location.x + 500
                compnode.location.y = 150

                viewnode = tree.nodes.new('CompositorNodeViewer')
                viewnode.location.x = imgnode.location.x + 500
                viewnode.location.y = 300

                tree.links.new(mixnodes[-1].outputs[0], compnode.inputs[0])
                tree.links.new(mixnodes[-1].outputs[0], viewnode.inputs[0])

        print(f"Compositing {len(renders)} Renders")
        # render compositor
        bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

        save_path = os.path.join(outfolder, f"{blendname}_{resolution}_composed.{fileformat.lower()}")
        img = bpy.data.images.get('Render Result')
        img.save_render(filepath=save_path)


        # reset the seed to it's initial value
        cycles.seed = init_seed
        return {'FINISHED'}
