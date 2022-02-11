import bpy
from bpy.props import BoolProperty
from .. utils.registration import get_prefs
from .. utils.system import makedir
from .. utils.math import dynamic_format
import os
import datetime
import time


# TODO: final render
# ####: produces renderings for the usualy passes

# TODO: redo fetching initial settings, do it via a single dict
# ####:  and then restore it again properly, currently scene.use_nodes, use compositing, and cryptomatte aren't really taking into account


class Render(bpy.types.Operator):
    bl_idname = "machin3.render"
    bl_label = "MACHIN3: Render"
    bl_options = {'REGISTER', 'UNDO'}

    quarter_qual: BoolProperty(name="Quarter Quality", default=False)
    half_qual: BoolProperty(name="Half Quality", default=False)
    double_qual: BoolProperty(name="Double Quality", default=False)
    quad_qual: BoolProperty(name="Quadruple Quality", default=False)

    seed: BoolProperty(name="Seed Render", default=False)
    final: BoolProperty(name="Final Render", default=False)

    def draw(self, context):
        layout = self.layout
        column = layout.column()

    @classmethod
    def description(cls, context, properties):
        currentblend = bpy.data.filepath
        currentfolder = os.path.dirname(currentblend)
        outpath = makedir(os.path.join(currentfolder, get_prefs().render_folder_name))

        if properties.seed:
            desc = f"Render {get_prefs().seed_render_count} seeds, combine all, and save to {outpath + os.sep}"
        else:
            desc = f"Render and save to {outpath + os.sep}"

        if properties.final:
            desc += "\nAdditionally force EXR, render Cryptomatte, and set up the Compositor"

        desc += f"\n\nALT: Half Quality\nSHIFT: Double Quality\nALT + CTRL: Quarter Quality\nSHIFT + CTRL: Quadruple Quality"

        return desc

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
        view_layer = context.view_layer

        # fetch initial time
        starttime = time.time()

        # adjust render quality when modifier keys have been pressed
        orig_res, orig_samples, orig_threshold, orig_seed, orig_format = self.set_render_settings(render, cycles)

        # get output path and blend file name while at it
        outpath, blendname, ext = self.get_output_path(render)

        # quality setup
        qualityhint = ' (Quarter Quality)' if self.quarter_qual else ' (Half Quality)' if self.half_qual else ' (Double Quality)' if self.double_qual else ' (Quadruple Quality)' if self.quad_qual else ''
        resolution, samples, thresholdhint = self.get_render_setting_strings(render, cycles, orig_res, orig_samples, orig_threshold)

        # prepare rendering terminial output and disable compositing
        count = self.prepare_rendering(scene, qualityhint, resolution, samples, thresholdhint, ext)

        # open the render view
        bpy.ops.render.view_show('INVOKE_DEFAULT')

        # seed render
        if self.seed:

            # clear out compositing nodes, and remove potential previous seed renderings
            tree = self.prepare_compositing(scene)

            # do count renderings, each with a different seed
            seedpaths = self.seed_render(render, cycles, outpath, blendname, ext, count)

            # TODO: for the first or last seed render, setup and save out the cryptomatte


            # load previously saved seed renderings
            images = self.load_seed_renderings(seedpaths, count)

            # setup the compositor for firefly removal by mixing the seed renderings
            basename = self.get_save_path(render, cycles, None, blendname, None, suffix='composed')
            self.setup_compositor_for_firefly_removal(scene, render, tree, images, count, outpath, basename)

            # render compositor
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            # remove the frame number from the composed image
            save_path = self.rename_file_output(scene, ext, outpath, basename)

        # quick render
        else:

            if self.final:

                # setup the compositor for cryptomatte export
                basename = self.get_save_path(render, cycles, None, blendname, None, suffix='clownmatte')
                self.setup_compositor_for_cryptomatte_export(scene, view_layer, outpath, basename)

            # render
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            # remove the frame number from the composed cryptomatte
            if self.final:
                self.rename_file_output(scene, ext, outpath, basename)

            # save render result
            save_path = self.get_save_path(render, cycles, outpath, blendname, ext)

            img = bpy.data.images.get('Render Result')
            img.save_render(filepath=save_path)


        if self.final:
            pass

            # TODO: bring cryptomattei into compositor


        # final terminal output
        rendertime = datetime.timedelta(seconds=int(time.time() - starttime))
        print(f"\nRendering finished after {rendertime}")
        print(f"       saved to {save_path}")

        # reset to initial quality
        self.reset_render_settings(render, cycles, orig_res, orig_samples, orig_threshold, orig_format, seed=orig_seed if self.seed else None)

        return {'FINISHED'}


    # GENERAL

    def get_output_path(self, render):
        '''
        from the import location of the current blend file get the output path, as well as the blend file's name and the extension based on the image format
        '''

        currentblend = bpy.data.filepath
        currentfolder = os.path.dirname(currentblend)

        outpath = makedir(os.path.join(currentfolder, get_prefs().render_folder_name))
        blendname = os.path.basename(currentblend).split('.')[0]

        fileformat = render.image_settings.file_format

        if fileformat == 'TIFF':
            ext = 'tif'
        elif fileformat in ['TARGA', 'TARGA_RAW']:
            ext = 'tga'
        elif fileformat in ['OPEN_EXR', 'OPEN_EXR_MULTILAYER']:
            ext = 'exr'
        elif fileformat == 'JPEG':
            ext = 'jpg'
        elif fileformat == 'JPEG2000':
            ext = 'jp2' if render.image_settings.jpeg2k_codec == 'JP2' else 'j2c'
        else:
            ext = fileformat.lower()

        return outpath, blendname, ext

    def get_save_path(self, render, cycles, outpath, blendname, ext, seed=None, suffix=None):
        '''
        create filename to save render to
        note that when composing seed renders, a tiny delay is created, to ensure the composed images is saved after(not using the same time code) as the last seed render
        when a suffix is passed in, return the basename only instead of the entire path, as the compositor's output node will be used to save the render result, and it expects the path to be split
        '''

        if suffix == 'composed':
            time.sleep(1)

        now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        if cycles.use_adaptive_sampling:
            basename = f"{blendname}_{now}_{render.resolution_x}x{render.resolution_y}_{cycles.samples}_{dynamic_format(cycles.adaptive_threshold)}"
        else:
            basename = f"{blendname}_{now}_{render.resolution_x}x{render.resolution_y}_{cycles.samples}"

        if seed is not None:
            basename += f"_seed_{seed}"

        if suffix:
            basename += "_" + suffix
            return basename

        return os.path.join(outpath, f"{basename}.{ext}")

    def set_render_settings(self, render, cycles):
        '''
        adjust render quality when mod keys are pressed
        force  OPEN_EXR if it's a final render
        '''

        orig_res = (render.resolution_x, render.resolution_y)
        orig_samples = cycles.samples
        orig_threshold = cycles.adaptive_threshold
        orig_format = (render.image_settings.file_format, render.image_settings.color_depth) if self.final and render.image_settings.file_format != 'OPEN_EXR' else None

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

        if self.final:
            render.image_settings.file_format = 'OPEN_EXR'

        return orig_res, orig_samples, orig_threshold, cycles.seed, orig_format

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

    def prepare_rendering(self, scene, qualityhint, resolution, samples, thresholdhint, ext):
        '''
        disable compositing and prepare terminal output
        '''

        # disable compositing
        scene.render.use_compositing = False

        prefix = "\n"

        if self.final:
            prefix += 'Final'

            if self.seed:
                prefix += ' Seed'
        else:
            if self.seed:
                prefix += 'Seed'
            else:
                prefix += 'Quick'


        # prepare seed render
        if self.seed:
            # fetch seed count
            count = get_prefs().seed_render_count

            print(f"{prefix} Rendering{qualityhint} {count} times at {resolution} with {samples} samples{thresholdhint} to .{ext}")
            return count

        # prepare quick render
        else:
            print(f"{prefix} Rendering{qualityhint} at {resolution} with {samples} samples{thresholdhint} to .{ext}")

    def reset_render_settings(self, render, cycles, res, samples, threshold, format, seed=None):
        '''
        reset to the initially used render settings
        '''

        if any([self.quarter_qual, self.half_qual, self.double_qual, self.quad_qual]):
            render.resolution_x = res[0]
            render.resolution_y = res[1]

            cycles.samples = samples

            if cycles.use_adaptive_sampling:
                cycles.adaptive_threshold = threshold

        if format:
            render.image_settings.file_format = format[0]
            render.image_settings.color_depth = format[1]

        # reset the seed to it's initial value
        if seed is not None:
            cycles.seed = seed


    # SEED

    def seed_render(self, render, cycles, outpath, blendname, ext, count):
        '''
        render out count images, each with a new seed
        '''

        # collect seeeds and file paths
        seedpaths = []

        for i in range(count):
            cycles.seed = i

            print(" Seed:", cycles.seed)
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            # save seed render
            save_path = self.get_save_path(render, cycles, outpath, blendname, ext, seed=i)

            img = bpy.data.images.get('Render Result')
            img.save_render(filepath=save_path)
            seedpaths.append((i, save_path))

            # temporaryily change the Render Result image name and update the UI as simple progress indication
            img.name = f"Render Seed {i} ({i + 1}/{count})"
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            img.name = f"Render Result"

        return seedpaths

    def prepare_compositing(self, scene):
        '''  '
        clear out compositing nodes
        remove potential previous seed renderings too
        '''

        # ensure comp nodes are used
        scene.use_nodes = True

        tree = scene.node_tree

        # clear all existing nodes
        for node in tree.nodes:

            # remove any previous seed renderings
            if node.type == 'IMAGE' and node.image:
                if "Render Seed " in node.image.name:
                    bpy.data.images.remove(node.image)

            tree.nodes.remove(node)

        return tree

    def load_seed_renderings(self, seedpaths, count):
        '''
        load the previously saved seed renderings
        '''

        images = []

        for idx, (seed, path) in enumerate(seedpaths):
            loadimg = bpy.data.images.load(filepath=path)
            loadimg.name = f"Render Seed {seed} ({idx + 1}/{count})"

            images.append(loadimg)

        return images

    def setup_compositor_for_firefly_removal(self, scene, render, tree, images, count, outpath, basename):
        '''
        setup compositing node tree, combining the individual seed renderings using darke mix mode to remove fireflies
        '''

        print(f"\nCompositing {count} Renders")

        scene.render.use_compositing = True

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


        # add file output node
        outputnode = tree.nodes.new('CompositorNodeOutputFile')
        outputnode.location.x = compnode.location.x

        tree.links.new(mixnodes[-1].outputs[0], outputnode.inputs[0])

        if render.image_settings.file_format == 'OPEN_EXR_MULTILAYER':
            outputnode.base_path = os.path.join(outpath, basename)
        else:
            outputnode.base_path = outpath

        output = outputnode.file_slots[0]
        output.path = basename
        output.save_as_render = False

    def rename_file_output(self, scene, ext, outpath, basename):
        '''
        we are using the file ouput node in the compositor to save the result, because it allows us to disable "save_as_render"
        not doing this, or using img.save_render() again would result in a slight color change, likely because some color shit is applied a second time
        unfortunately, the file output node, also always adds the frame number at the end, so we'll have to remove that
        '''

        comp_path = os.path.join(outpath, f"{basename}{str(scene.frame_current).zfill(4)}.{ext}")
        save_path = os.path.join(outpath, f"{basename}.{ext}")
        os.rename(comp_path, save_path)

        return save_path


    # FINAL

    def setup_compositor_for_cryptomatte_export(self, scene, view_layer, outpath, basename):
        '''
        save out the 9 cryptomatte passes
        call "cryptomatte" "clownmatte", because https://twitter.com/machin3io/status/1491819866961190914 and because "clown maps" > "id maps"
        '''

        # enable compositing, to save out the cryptomatte pass using the file output node
        scene.render.use_compositing = True

        # remove any existing nodes
        self.prepare_compositing(scene)

        # enable cryptomatte rendering
        view_layer.use_pass_cryptomatte_object = True
        view_layer.use_pass_cryptomatte_material = True
        view_layer.use_pass_cryptomatte_asset = True

        tree = scene.node_tree

        rndrnode = tree.nodes.new('CompositorNodeRLayers')

        compnode = tree.nodes.new('CompositorNodeComposite')
        compnode.location.x = 400

        tree.links.new(rndrnode.outputs[0], compnode.inputs[0])

        # add file output node
        outputnode = tree.nodes.new('CompositorNodeOutputFile')
        outputnode.format.file_format = 'OPEN_EXR_MULTILAYER'

        # set up cryptomatte layers as inputs on the file output nodes and connect them
        Imageslot = outputnode.inputs.get('Image')
        outputnode.layer_slots.remove(Imageslot)

        for name in ['CryptoObject00', 'CryptoObject01', 'CryptoObject02', 'CryptoMaterial00', 'CryptoMaterial01', 'CryptoMaterial02', 'CryptoAsset00', 'CryptoAsset01', 'CryptoAsset02']:
            clownname = name.replace('Crypto', 'Clown')

            outputnode.layer_slots.new(clownname)
            tree.links.new(rndrnode.outputs[name], outputnode.inputs[clownname])

        outputnode.location.x = 400
        outputnode.location.y = -200

        outputnode.base_path = os.path.join(outpath, basename)
