import bpy
from bpy.props import BoolProperty
from .. utils.registration import get_prefs
from .. utils.system import makedir, printd
from .. utils.math import dynamic_format
import os
import datetime
import time
import platform


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
            desc = f"Render {get_prefs().render_seed_count} seeds, combine all, and save to {outpath + os.sep}"
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

        self.settings = {'scene': context.scene,
                         'render': context.scene.render,
                         'cycles': context.scene.cycles,
                         'view_layer': context.view_layer,

                         'resolution': (context.scene.render.resolution_x, context.scene.render.resolution_y),
                         'samples': context.scene.cycles.samples,
                         'threshold': context.scene.cycles.adaptive_threshold,
                         'format': context.scene.render.image_settings.file_format,
                         'depth': context.scene.render.image_settings.color_depth,
                         'seed': context.scene.cycles.seed,
                         'seed_count': get_prefs().render_seed_count,

                         'tree': None,
                         'use_nodes': context.scene.use_nodes,
                         'use_compositing': context.scene.render.use_compositing,

                         'outpath': None,
                         'blendname': None,
                         'ext': None,
                         }

        self.strings = {'quality': ' (Quarter Quality)' if self.quarter_qual else ' (Half Quality)' if self.half_qual else ' (Double Quality)' if self.double_qual else ' (Quadruple Quality)' if self.quad_qual else '',

                        'resolution_terminal': None,
                        'samples_terminal': None,
                        'threshold_terminal': None,

                        'resolution_file': None,
                        'samples_file': None,
                        'threshold_file': None,
                        }

        return self.execute(context)

    def execute(self, context):

        # fetch initial time
        starttime = time.time()

        # adjust render quality when modifier keys have been pressed
        self.set_render_settings()

        # get output path and blend file name while at it
        self.get_output_path()

        # quality setup
        self.get_strings()

        # prepare rendering terminial output, disable compositing open render view
        self.prepare_rendering()

        # seed render
        if self.seed:

            # clear out compositing nodes, and remove potential previous seed renderings
            self.clear_out_compositor()

            # do count renderings, each with a different seed
            seedpaths, matte_path = self.seed_render()

            # load previously saved seed renderings
            images = self.load_seed_renderings(seedpaths)

            # setup the compositor for firefly removal by mixing the seed renderings
            basename = self.get_save_path(suffix='seed')
            self.setup_compositor_for_firefly_removal(images, basename)

            # render compositor
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            # remove the frame number from the composed image, and properly set the datetime
            save_path = self.rename_file_output(basename)

            # remove individual seed renderings
            if not get_prefs().render_keep_seed_renderings:
                for _, path in seedpaths:
                    os.remove(path)

                # clear out the compositor too, but note that when final is enabled this happens anyway
                if not self.final:
                    self.clear_out_compositor()

        # quick render
        else:

            if self.final:

                # setup the compositor for cryptomatte export
                basename = self.get_save_path(suffix='clownmatte' if get_prefs().render_use_clownmatte_naming else 'cryptomatte')
                self.setup_compositor_for_cryptomatte_export(basename)

            # render
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            # save render result
            save_path = self.get_save_path()

            # remove the frame number from the composed cryptomatte and properly set the datetime, important to do it after the saving out the render, to ensure a later time code
            if self.final:
                matte_path = self.rename_file_output(basename)

            img = bpy.data.images.get('Render Result')
            img.save_render(filepath=save_path)

        # final terminal output
        rendertime = datetime.timedelta(seconds=int(time.time() - starttime))
        print(f"\nRendering finished after {rendertime}")
        print(f"          saved to {save_path}")

        # reset to initial quality
        self.reset_render_settings()

        # bring cryptomatte into compositor
        if self.final:
            self.setup_compositor_for_final_composing(save_path, matte_path)

        return {'FINISHED'}


    # GENERAL

    def set_render_settings(self):
        '''
        adjust render quality when mod keys are pressed
        force  OPEN_EXR if it's a final render
        '''

        render = self.settings['render']
        cycles = self.settings['cycles']

        if self.quarter_qual:
            render.resolution_x = round(render.resolution_x / 4)
            render.resolution_y = round(render.resolution_y / 4)

            if render.engine == 'CYCLES':
                cycles.samples = round(cycles.samples / 4)

                if cycles.use_adaptive_sampling:
                    cycles.adaptive_threshold = cycles.adaptive_threshold * 4

        elif self.half_qual:
            render.resolution_x = round(render.resolution_x / 2)
            render.resolution_y = round(render.resolution_y / 2)

            if render.engine == 'CYCLES':
                cycles.samples = round(cycles.samples / 2)

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

    def get_output_path(self):
        '''
        from the import location of the current blend file get the output path, as well as the blend file's name and the extension based on the image format
        '''

        currentblend = bpy.data.filepath
        currentfolder = os.path.dirname(currentblend)

        render = self.settings['render']
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

        self.settings['outpath'] = makedir(os.path.join(currentfolder, get_prefs().render_folder_name))
        self.settings['blendname'] = os.path.basename(currentblend).split('.')[0]
        self.settings['ext'] = ext

    def get_strings(self):
        '''
        create strings for terminal output of render settings and for file names
        '''

        render = self.settings['render']
        cycles = self.settings['cycles']

        resolution = self.settings['resolution']
        samples = self.settings['samples']
        threshold = self.settings['threshold']

        if any([self.quarter_qual, self.half_qual, self.double_qual, self.quad_qual]):
            self.strings['resolution_terminal'] = f"{render.resolution_x}x{render.resolution_y} ({resolution[0]}x{resolution[1]})"
            self.strings['samples_terminal'] = f"{cycles.samples} ({samples})"
            self.strings['threshold_terminal'] = f" and a noise threshold of {dynamic_format(cycles.adaptive_threshold)} ({dynamic_format(threshold)})" if cycles.use_adaptive_sampling else ''

        else:
            self.strings['resolution_terminal'] = f"{render.resolution_x}x{render.resolution_y}"
            self.strings['samples_terminal'] = str(cycles.samples)
            self.strings['threshold_terminal'] = f" and a noise threshold of {dynamic_format(cycles.adaptive_threshold)}" if cycles.use_adaptive_sampling else ''

        self.strings['resolution_file'] = f"{render.resolution_x}x{render.resolution_y}"
        self.strings['samples_file'] = str(cycles.samples)
        self.strings['threshold_file'] = dynamic_format(cycles.adaptive_threshold)

    def prepare_rendering(self):
        '''
        disable compositing and prepare terminal output
        then open the render view
        '''

        # disable compositing
        self.settings['render'].use_compositing = False

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

        quality = self.strings['quality']
        resolution = self.strings['resolution_terminal']
        samples = self.strings['samples_terminal']
        threshold = self.strings['threshold_terminal']

        ext = self.settings['ext']

        # prepare seed render
        if self.seed:
            count = self.settings['seed_count']

            print(f"{prefix} Rendering{quality} {count} times at {resolution} with {samples} samples{threshold} to .{ext}")

        # prepare quick render
        else:
            print(f"{prefix} Rendering{quality} at {resolution} with {samples} samples{threshold} to .{ext}")

        # open the render view
        bpy.ops.render.view_show('INVOKE_DEFAULT')

    def clear_out_compositor(self):
        '''
        clear out compositing nodes
        remove potential previous seed renderings too
        '''

        scene = self.settings['scene']

        # ensure comp nodes are used
        scene.use_nodes = True
        tree = scene.node_tree

        # clear all existing nodes
        for node in tree.nodes:

            # remove any previous seed renderings, as well as final (Seed) Renders
            if node.type == 'IMAGE' and node.image:
                if "Render Seed " in node.image.name or node.image.name in ['Render', 'Seed Render']:
                    bpy.data.images.remove(node.image)

            # remove previous cryptomattes as well
            elif node.type == 'CRYPTOMATTE_V2':
                if node.image.name in ['Clownmatte', 'Cryptomatte']:
                    bpy.data.images.remove(node.image)

            tree.nodes.remove(node)

        self.settings['tree'] = tree

    def get_save_path(self, seed=None, suffix=None):
        '''
        create filename to save render to
        note that when composing seed renders, a tiny delay is created, to ensure the composed images is saved after(not using the same time code) as the last seed render
        when a suffix is passed in, return the basename only instead of the entire path, as the compositor's output node will be used to save the render result, and it expects the path to be split
        '''

        cycles = self.settings['cycles']

        outpath = self.settings['outpath']
        blendname = self.settings['blendname']
        ext = self.settings['ext']

        resolution = self.strings['resolution_file']
        samples = self.strings['samples_file']
        threshold = self.strings['threshold_file']


        # if you pass in a suffix, the filepath and so the datetime is set before rendering/compositing, this is undesired
        # so instead use a placeholder string and set the correct datetime when renaming the file, which is always done for suffix renders, which are saved from the compositors file output node
        now = 'DATETIME' if suffix else datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        if platform.system() == "Windows":
            now = now.replace(':', '-')

        basename = f"{blendname}_{now}_{resolution}_{samples}"

        if cycles.use_adaptive_sampling:
            basename += f"_{threshold}"

        if seed is not None:
            basename += f"_seed_{seed}"

        if suffix:
            basename += "_" + suffix
            return basename

        return os.path.join(outpath, f"{basename}.{ext}")

    def reset_render_settings(self):
        '''
        reset to the initially used render settings
        '''

        scene = self.settings['scene']
        render = self.settings['render']
        cycles = self.settings['cycles']

        if any([self.quarter_qual, self.half_qual, self.double_qual, self.quad_qual]):
            render.resolution_x = self.settings['resolution'][0]
            render.resolution_y = self.settings['resolution'][1]

            cycles.samples = self.settings['samples']

            if cycles.use_adaptive_sampling:
                cycles.adaptive_threshold = self.settings['threshold']

        render.image_settings.file_format = self.settings['format']
        render.image_settings.color_depth = self.settings['depth']

        # reset the seed to it's initial value too
        if self.seed:
            cycles.seed = self.settings['seed']

        # as well as compositing settings
        scene.use_nodes = self.settings['use_nodes']
        render.use_compositing = self.settings['use_compositing']

        # for seed rendings, but non-final ones, where the seed renderings are kept, and where use_nodes was disabled initially, enable it, otherwise the previews in the compositor won't work
        if get_prefs().render_keep_seed_renderings and self.seed and not self.final and not scene.use_nodes:
            scene.use_nodes = True

    def rename_file_output(self, basename):
        '''
        we are using the file ouput node in the compositor to save the result, because it allows us to disable "save_as_render"
        not doing this, or using img.save_render() again would result in a slight color change, likely because some color shit is applied a second time
        unfortunately, the file output node, also always adds the frame number at the end, so we'll have to remove that
        also, the datetime couldn't be set earlier or it would denote the pre-rendering/pre-compositing time
        '''

        scene = self.settings['scene']

        outpath = self.settings['outpath']
        ext = self.settings['ext']

        comp_path = os.path.join(outpath, f"{basename}{str(scene.frame_current).zfill(4)}.{ext}")

        time.sleep(1)
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        if platform.system() == "Windows":
            now = now.replace(':', '-')

        basename = basename.replace('DATETIME', now)

        save_path = os.path.join(outpath, f"{basename}.{ext}")
        os.rename(comp_path, save_path)

        return save_path


    # SEED

    def seed_render(self):
        '''
        render out count images, each with a new seed
        '''

        count = self.settings['seed_count']
        cycles = self.settings['cycles']

        matte_path = None

        # collect seeeds and file paths
        seedpaths = []

        for i in range(count):
            cycles.seed = i

            # for the final seed rendering, setup the compositor for cryptomatte export
            if i == count - 1 and self.final:
                basename = self.get_save_path(suffix='clownmatte' if get_prefs().render_use_clownmatte_naming else 'cryptomatte')
                self.setup_compositor_for_cryptomatte_export(basename)

            print(" Seed:", cycles.seed)
            bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, layer='', scene='')

            # save seed render
            save_path = self.get_save_path(seed=i)

            # remove the frame number from the composed cryptomatte and properly set the datetime, important to do it after the seed render is saved, to ensure a later time code
            if i == count - 1 and self.final:
                matte_path = self.rename_file_output(basename)

                # clear out compositing
                self.clear_out_compositor()

            img = bpy.data.images.get('Render Result')
            img.save_render(filepath=save_path)
            seedpaths.append((i, save_path))

            # temporaryily change the Render Result image name and update the UI as simple progress indication
            img.name = f"Render Seed {i} ({i + 1}/{count})"
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            img.name = f"Render Result"

        return seedpaths, matte_path

    def load_seed_renderings(self, seedpaths):
        '''
        load the previously saved seed renderings
        '''

        count = self.settings['seed_count']

        images = []

        for idx, (seed, path) in enumerate(seedpaths):
            loadimg = bpy.data.images.load(filepath=path)
            loadimg.name = f"Render Seed {seed} ({idx + 1}/{count})"

            images.append(loadimg)

        return images

    def setup_compositor_for_firefly_removal(self, images, basename):
        '''
        setup compositing node tree, combining the individual seed renderings using darke mix mode to remove fireflies
        '''

        count = self.settings['seed_count']
        scene = self.settings['scene']
        render = self.settings['render']
        tree = self.settings['tree']
        outpath = self.settings['outpath']

        print(f"\nCompositing {count} Renders")

        # enable compositing, to save out the combined pass using the file output node
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


    # FINAL

    def setup_compositor_for_cryptomatte_export(self, basename):
        '''
        save out the 9 cryptomatte passes
        call "cryptomatte" "clownmatte", because https://twitter.com/machin3io/status/1491819866961190914 and because "clown maps" > "id maps"
        '''

        scene = self.settings['scene']
        view_layer = self.settings['view_layer']
        outpath = self.settings['outpath']

        # remove any existing nodes
        self.clear_out_compositor()

        # fetch the tree now
        tree = self.settings['tree']

        # enable compositing, to save out the cryptomatte pass using the file output node
        scene.render.use_compositing = True

        # enable cryptomatte rendering
        view_layer.use_pass_cryptomatte_object = True
        view_layer.use_pass_cryptomatte_material = True
        view_layer.use_pass_cryptomatte_asset = True

        # create render con composite nodes
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
            inputname = name.replace('Crypto', 'Clown') if get_prefs().render_use_clownmatte_naming else name

            outputnode.layer_slots.new(inputname)
            tree.links.new(rndrnode.outputs[name], outputnode.inputs[inputname])

        outputnode.location.x = 400
        outputnode.location.y = -200

        outputnode.base_path = os.path.join(outpath, basename)

    def setup_compositor_for_final_composing(self, img_path, matte_path):
        '''
        setup the compositro for final compositing
        so bring in the render and the cryptomatte
        '''

        self.clear_out_compositor()

        render = self.settings['render']
        tree = self.settings['tree']

        render.use_compositing = True

        imgname = 'Seed Render' if self.seed else 'Render'
        mattename = 'Clownmatte' if get_prefs().render_use_clownmatte_naming else 'Cryptomatte'

        # load images
        img = bpy.data.images.load(img_path)
        img.name = imgname

        matte = bpy.data.images.load(matte_path)
        matte.name = mattename

        # create nodes
        imgnode = tree.nodes.new('CompositorNodeImage')
        imgnode.image = img

        imgnode.name = imgname
        imgnode.label = imgname

        mattenode = tree.nodes.new('CompositorNodeCryptomatteV2')
        mattenode.source = 'IMAGE'
        mattenode.image = matte
        mattenode.layer_name = 'ClownObject' if get_prefs().render_use_clownmatte_naming else 'CryptoObject'

        mattenode.name = mattename
        mattenode.label = mattename

        mattenode.location.x = 300
        mattenode.location.y = -150

        # connect them
        tree.links.new(imgnode.outputs[0], mattenode.inputs[0])

        # add a viewer node too as a render preview
        viewernode = tree.nodes.new('CompositorNodeViewer')
        viewernode.location.x = 600

        tree.links.new(imgnode.outputs[0], viewernode.inputs[0])


class DuplicateNodes(bpy.types.Operator):
    bl_idname = "machin3.duplicate_nodes"
    bl_label = "MACHIN3: Duplicate Nodes"
    bl_description = "Duplicate Nodes normaly, except for Cryptomatte V2 nodes, in that case keep the inputs and clear out the matte ids"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR' and context.scene.use_nodes

    def execute(self, context):
        active = context.scene.node_tree.nodes.active

        if active and active.type == 'CRYPTOMATTE_V2':
            bpy.ops.node.duplicate_move_keep_inputs('INVOKE_DEFAULT')
            context.scene.node_tree.nodes.active.matte_id = ''
            return {'FINISHED'}
        return {'PASS_THROUGH'}
