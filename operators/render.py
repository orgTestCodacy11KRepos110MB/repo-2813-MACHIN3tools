import bpy
from bpy.props import BoolProperty
from .. utils.registration import get_prefs
from .. utils.system import makedir
from .. utils.math import dynamic_format
from random import randint
import os
import datetime
import time


class Render(bpy.types.Operator):
    bl_idname = "machin3.render"
    bl_label = "MACHIN3: Render"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    quarter_qual: BoolProperty(name="Quarter Quality", default=False)
    half_qual: BoolProperty(name="Half Quality", default=False)
    double_qual: BoolProperty(name="Double Quality", default=False)
    quad_qual: BoolProperty(name="Quadruple Quality", default=False)

    seed: BoolProperty(name="Seed Render", default=False)

    def draw(self, context):
        layout = self.layout
        column = layout.column()

    @classmethod
    def description(cls, context, properties):
        currentblend = bpy.data.filepath
        currentfolder = os.path.dirname(currentblend)
        outpath = makedir(os.path.join(currentfolder, get_prefs().render_folder_name))

        if properties.seed:
            return f"Seed render {get_prefs().seed_render_count}x, combine all, and save to {outpath + os.sep}\n\nALT: Half Quality\nSHIFT: Double Quality\nALT + CTRL: Quarter Quality\nSHIFT + CTRL: Quadruple Quality"
        else:
            return f"Quickly render and save to {outpath + os.sep}\n\nALT: Half Quality\nSHIFT: Double Quality\nALT + CTRL: Quarter Quality\nSHIFT + CTRL: Quadruple Quality"

    @classmethod
    def poll(cls, context):
        return context.scene.camera

    def invoke(self, context, event):
        self.half_qual = event.alt
        self.double_qual = event.shift
        self.quarter_qual = event.alt and event.ctrl
        self.quad_qual = event.shift and event.ctrl
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        render = scene.render
        cycles = scene.cycles

        # fetch initial time
        starttime = time.time()

        # adjust render quality when modifier keys have been pressed
        orig_res, orig_samples, orig_threshold, orig_seed = self.set_render_settings(render, cycles)

        # get output path and blend file name while at it
        outpath, blendname = self.get_output_path()

        # quality setup
        qualityhint = ' (Quarter Quality)' if self.quarter_qual else ' (Half Quality)' if self.half_qual else ' (Double Quality)' if self.double_qual else ' (Quadruple Quality)' if self.quad_qual else ''
        resolution, samples, thresholdhint = self.get_render_setting_strings(render, cycles, orig_res, orig_samples, orig_threshold)

        # prepare seed render
        if self.seed:
            # fetch seed count
            count = get_prefs().seed_render_count
            
            # disable compositing
            scene.render.use_compositing = False

            # collect seeeds and file paths
            seedpaths = []

            print(f"\nSeed Rendering{qualityhint} {count} times at {resolution} with {samples} samples{thresholdhint}")

        # prepare quick render
        else:
            print(f"\nQuick Rendering{qualityhint} at {resolution} with {samples} samples{thresholdhint}")


        # open the render view
        bpy.ops.render.view_show('INVOKE_DEFAULT')

        # seed render
        if self.seed:
            for i in range(count):
                cycles.seed = i

                print(" Seed:", cycles.seed)
                bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

                # save seed render
                save_path = self.get_save_path(render, cycles, outpath, blendname, seed=i)

                img = bpy.data.images.get('Render Result')
                img.save_render(filepath=save_path)
                seedpaths.append((i, save_path))

                # temporaryily change the Render Result image name and update the UI as simple progress indication
                img.name = f"Render Seed {i} ({i + 1}/{count})"
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                img.name = f"Render Result"

            # enable compositing and comp nodes
            scene.render.use_compositing = True
            scene.use_nodes = True

            tree = scene.node_tree

            # clear all existing nodes
            for node in tree.nodes:

                # remove any previous seed renderings
                if node.type == 'IMAGE' and node.image:
                    if "Render Seed " in node.image.name:
                        bpy.data.images.remove(node.image)

                tree.nodes.remove(node)

            # load the renderings
            images = []

            for idx, (seed, path) in enumerate(seedpaths):
                loadimg = bpy.data.images.load(filepath=path)
                loadimg.name = f"Render Seed {seed} ({idx + 1}/{count})"

                images.append(loadimg)

            imgnodes = []
            mixnodes = []

            # setup the compositor tree to combine the renderings, removing the fireflies
            for idx, img in enumerate(images):
                imgnode = tree.nodes.new('CompositorNodeImage')
                imgnode.image = img
                imgnodes.append(imgnode)

                imgnode.location.x = idx * 200

                if idx < count - 1:
                    mixnode = tree.nodes.new('CompositorNodeMixRGB')
                    mixnode.blend_type = 'DARKEN'
                    mixnodes.append(mixnode)

                    mixnode.location.x = 400 + idx * 200
                    mixnode.location.y = 300


                if idx == 0:
                    tree.links.new(imgnode.outputs[0], mixnode.inputs[1])
                else:
                    tree.links.new(imgnode.outputs[0], mixnodes[idx - 1].inputs[2])

                    if idx < count - 1:
                        tree.links.new(mixnodes[idx - 1].outputs[0], mixnodes[idx].inputs[1])


                if idx == count - 1:
                    compnode = tree.nodes.new('CompositorNodeComposite')

                    compnode.location.x = imgnode.location.x + 500
                    compnode.location.y = 150

                    viewnode = tree.nodes.new('CompositorNodeViewer')
                    viewnode.location.x = imgnode.location.x + 500
                    viewnode.location.y = 300

                    tree.links.new(mixnodes[-1].outputs[0], compnode.inputs[0])
                    tree.links.new(mixnodes[-1].outputs[0], viewnode.inputs[0])

            print(f"\nCompositing {count} Renders")
            # render compositor
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            save_path = self.get_save_path(render, cycles, outpath, blendname, seed=-1)
            img = bpy.data.images.get('Render Result')
            img.save_render(filepath=save_path)


        # quick render
        else:
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            # save quick render
            save_path = self.get_save_path(render, cycles, outpath, blendname)

            img = bpy.data.images.get('Render Result')
            img.save_render(filepath=save_path)

        # final terminal output
        rendertime = datetime.timedelta(seconds=int(time.time() - starttime))
        print(f"\nRendering finished after {rendertime}")
        print(f"       saved to {save_path}")

        # reset to initial quality
        self.reset_render_settings(render, cycles, orig_res, orig_samples, orig_threshold, seed=orig_seed if self.seed else None)

        return {'FINISHED'}

    def get_output_path(self):
        '''
        from the import location of the current blend file get the output path, as well as the blend file's name
        '''

        currentblend = bpy.data.filepath
        currentfolder = os.path.dirname(currentblend)

        outpath = makedir(os.path.join(currentfolder, get_prefs().render_folder_name))
        blendname = os.path.basename(currentblend).split('.')[0]

        return outpath, blendname

    def get_save_path(self, render, cycles, outpath, blendname, seed=None):
        '''
        create filename to save render to
        note that when composing seed renders (seed == -1), a tiny delay is created, to ensure the composed images is saved after(not using the same time code) as the last seed render
        '''

        if seed == -1:
            time.sleep(0.5)

        fileformat = render.image_settings.file_format
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        if cycles.use_adaptive_sampling:
            basename = os.path.join(outpath, f"{blendname}_{now}_{render.resolution_x}x{render.resolution_y}_{cycles.samples}_{dynamic_format(cycles.adaptive_threshold)}")
        else:
            basename = os.path.join(outpath, f"{blendname}_{now}_{render.resolution_x}x{render.resolution_y}_{cycles.samples}.{fileformat.lower()}")

        if seed is not None:
            basename += "_composed" if seed == -1 else f"_seed_{seed}"

        return f"{basename}.{fileformat.lower()}"

    def set_render_settings(self, render, cycles):
        '''
        adjust render quality when mod keys are pressed
        '''

        orig_res = (render.resolution_x, render.resolution_y)
        orig_samples = cycles.samples
        orig_threshold = cycles.adaptive_threshold

        if self.quarter_qual:
            render.resolution_x /= 4
            render.resolution_y /= 4

            if render.engine == 'CYCLES':
                cycles.samples = int(cycles.samples / 4)

                if cycles.use_adaptive_sampling:
                    cycles.adaptive_threshold = cycles.adaptive_threshold * 4

        elif self.half_qual:
            render.resolution_x /= 2
            render.resolution_y /= 2

            if render.engine == 'CYCLES':
                cycles.samples = int(cycles.samples / 2)

                if cycles.use_adaptive_sampling:
                    cycles.adaptive_threshold = cycles.adaptive_threshold * 2

        elif self.double_qual:
            render.resolution_x *= 2
            render.resolution_y *= 2

        elif self.quad_qual:
            render.resolution_x *= 4
            render.resolution_y *= 4

        return orig_res, orig_samples, orig_threshold, cycles.seed

    def reset_render_settings(self, render, cycles, res, samples, threshold, seed=None):
        '''
        reset to the initially used render settings
        '''

        if any([self.quarter_qual, self.half_qual, self.double_qual, self.quad_qual]):
            render.resolution_x = res[0]
            render.resolution_y = res[1]

            cycles.samples = samples

            if cycles.use_adaptive_sampling:
                cycles.adaptive_threshold = threshold

        # reset the seed to it's initial value
        if seed is not None:
            cycles.seed = seed

    def get_render_setting_strings(self, render, cycles, orig_res, orig_samples, orig_threshold):
        '''
        create strings for terminal output of render settings
        '''

        if any([self.quarter_qual, self.half_qual, self.double_qual, self.quad_qual]):
            resolution = f"{render.resolution_x}x{render.resolution_y}/{orig_res[0]}x{orig_res[1]}"
            samples = f"{cycles.samples}/{orig_samples}"
            thresholdhint = f" and a noise threshold of {dynamic_format(cycles.adaptive_threshold)}/{dynamic_format(orig_threshold)}" if cycles.use_adaptive_sampling else ''
        else:
            resolution = f"{render.resolution_x}x{render.resolution_y}"
            samples = cycles.samples
            thresholdhint = f" and a noise threshold of {dynamic_format(cycles.adaptive_threshold)}" if cycles.use_adaptive_sampling else ''

        return resolution, samples, thresholdhint
