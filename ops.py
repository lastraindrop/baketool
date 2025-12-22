import bpy
from bpy import props
import mathutils
import bmesh
import os
import numpy as np # optimizing custom bake
from .utils import *
from .constants import *

class BAKETOOL_OT_ResetChannels(bpy.types.Operator):
    """Clears and repopulates the channel list based on the current bake type."""
    bl_idname = "bake.reset_channels"
    bl_label = "Reset Bake Channels"
    bl_description = "Smart update of the channel list based on the current bake type"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        if not context.scene.BakeJobs.jobs:
            return {'CANCELLED'}
            
        job = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index]
        setting = job.setting
        bake_type = setting.bake_type
        
        desired_definitions = []
        if bake_type == 'BSDF':
            if bpy.app.version < (4, 0, 0):
                desired_definitions.extend(CHANNEL_DEFINITIONS['BSDF_3'])
            else:
                desired_definitions.extend(CHANNEL_DEFINITIONS['BSDF_4'])
        elif bake_type in CHANNEL_DEFINITIONS:
            desired_definitions.extend(CHANNEL_DEFINITIONS[bake_type])
        else:
            self.report({'WARNING'}, f"No channel definitions found for bake type: {bake_type}")
            return {'CANCELLED'}

        if setting.use_special_map:
             desired_definitions.extend(CHANNEL_DEFINITIONS['MESH'])
        
        desired_ids = [d['id'] for d in desired_definitions]

        for i in range(len(setting.channels) - 1, -1, -1):
            if setting.channels[i].id not in desired_ids:
                setting.channels.remove(i)
        
        existing_ids = {c.id for c in setting.channels}
        
        for i, def_item in enumerate(desired_definitions):
            if def_item['id'] not in existing_ids:
                new_channel = setting.channels.add()
                new_channel.id = def_item['id']
                new_channel.name = def_item['name']
                
                if 'defaults' in def_item:
                    for key, value in def_item['defaults'].items():
                        try:
                            setattr(new_channel, key, value)
                        except AttributeError:
                            logger.warning(f"Could not set default value for '{key}' on channel '{new_channel.name}'")
                            
        for target_idx, desired_id in enumerate(desired_ids):
            current_idx = -1
            for idx, c in enumerate(setting.channels):
                if c.id == desired_id:
                    current_idx = idx
                    break
            if current_idx != -1 and current_idx != target_idx:
                setting.channels.move(current_idx, target_idx)

        self.report({'INFO'}, f"Updated channels for {bake_type} bake type.")
        return {'FINISHED'}

class BAKETOOL_OT_SetSaveLocal(bpy.types.Operator):
    bl_idname="bake.set_save_local"
    bl_label="save local"
    bl_description="Set the path as local"
    
    save_location: props.IntProperty(name='Save Location',description='Save Location',default=0,min=0,max=3)
    
    def execute(self,context):
        if len(bpy.data.filepath)==0:
            return report_error(self, "File not save")
        path=bpy.data.filepath
        path=os.path.dirname(path)+'\\' 
        if self.save_location==0:
            context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting.save_path=path
        elif self.save_location==1:
            context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting.custom_file_path=path
        elif self.save_location==2:
            context.scene.BakeJobs.node_bake_save_path=path

        return{'FINISHED'}
        
class BAKETOOL_OT_RecordObjects(bpy.types.Operator):
    bl_idname="bake.record_objects"
    bl_label="Record Objects"
    bl_description="Record Objects"
    
    objecttype: props.IntProperty(name='Object type',description='Object type',default=0,min=0,max=2)
    allobjects: props.BoolProperty(name='All Objects',description='All Objects',default=False)
    
    def invoke(self,context,event):
        if event.shift==True:
            self.allobjects=True
        else:
            self.allobjects=False
        return self.execute(context)
    
    def execute(self,context):
        setting=context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting
        objs=context.selected_objects
        act=context.active_object
        
        if self.objecttype==0:
            setting.bake_objects.clear()
            if not self.allobjects:
                for i in range(len(objs)):
                    if objs[i].type=='MESH':
                        setting.bake_objects.add()
                        setting.bake_objects[len(setting.bake_objects)-1].bakeobject=objs[i]
            else:
                setting.active_object=act
                for i in range(len(objs)):
                    if objs[i].type=='MESH' and objs[i]!=act:
                        setting.bake_objects.add()
                        setting.bake_objects[len(setting.bake_objects)-1].bakeobject=objs[i]
                
        elif self.objecttype==1:
            setting.active_object=context.active_object
        elif self.objecttype==2:
            setting.cage_object=context.active_object
        return{'FINISHED'}
   
class BAKETOOL_OT_GenericChannelOperator(bpy.types.Operator):
    bl_idname = "bake.generic_channel_op"
    bl_label = "Channel Operation"
    bl_description = "Perform operations on specified channel collections"

    operation: bpy.props.EnumProperty(
        items=[
            ('ADD', "Add", "Add a new item to the collection", 'ADD', 0),
            ('DELETE', "Delete", "Delete the selected item", 'REMOVE', 1),
            ('UP', "Up", "Move the selected item up", 'TRIA_DOWN', 2),
            ('DOWN', "Down", "Move the selected item down", 'TRIA_UP', 3),
            ('CLEAR', "Clear", "Clear all items in the collection", 'BRUSH_DATA', 4),
        ],
        name="Operation"
    )

    target: bpy.props.StringProperty(name="Target", default="")

    TARGET_PROPERTIES = {
        "jobs_channel": {
            "collection": lambda c: c.scene.BakeJobs.jobs,
            "index": lambda c: c.scene.BakeJobs.job_index,
            "index_setter": lambda c, v: setattr(c.scene.BakeJobs, "job_index", v)
        },
        "job_custom_channel": {
            "collection": lambda c: c.scene.BakeJobs.jobs[c.scene.BakeJobs.job_index].Custombakechannels,
            "index": lambda c: c.scene.BakeJobs.jobs[c.scene.BakeJobs.job_index].Custombakechannels_index,
            "index_setter": lambda c, v: setattr(c.scene.BakeJobs.jobs[c.scene.BakeJobs.job_index], "Custombakechannels_index", v)
        }
    }

    @classmethod
    def poll(cls, context):
        return context.scene and context.scene.BakeJobs

    def execute(self, context):
        if self.target not in self.TARGET_PROPERTIES:
            return report_error(self, f"Unknown target: {self.target}", status='CANCELLED')

        props = self.TARGET_PROPERTIES[self.target]
        try:
            collection = props["collection"](context)
            index = props["index"](context)
            set_index = props["index_setter"]
        except (IndexError, AttributeError):
            return report_error(self, f"Invalid collection or index for target: {self.target}", status='CANCELLED')

        if self.operation == 'ADD':
            item = collection.add()
            item.name = self.target + str(len(collection))
            set_index(context, len(collection) - 1)
            if self.target == "jobs_channel":
                bpy.ops.bake.reset_channels()
        elif self.operation == 'DELETE' and len(collection) > 0 and 0 <= index < len(collection):
            collection.remove(index)
            set_index(context, min(index, len(collection) - 1))
        elif self.operation == 'UP' and len(collection) > 1 and index > 0:
            collection.move(index, index - 1)
            set_index(context, index - 1)
        elif self.operation == 'DOWN' and len(collection) > 1 and index < len(collection) - 1:
            collection.move(index, index + 1)
            set_index(context, index + 1)
        elif self.operation == 'CLEAR':
            collection.clear()
            set_index(context, -1)
        
        return {'FINISHED'}


class BAKETOOL_OT_BakeOperator(bpy.types.Operator):
    bl_label = "Bake"
    bl_idname = "bake.bake_operator"
    bl_description="Start baking operator"
    
    objects = []
    act = None
    cage = None
    job = None
    setting = None
    UV = ''
    foldername = ''
    start = 0
    end = 0
    framerange = 1
    
    @classmethod
    def poll(self,context):
        if not context.scene.BakeJobs: return False
        for job in context.scene.BakeJobs.jobs:
            if len(job.setting.bake_objects)>0:
                return True
        if len(context.selected_objects)>0 and context.active_object!=None:
            if context.active_object.type!='MESH':
                return False
            return True
        return False
    
    def _create_imagemap(self):
        imagemap = []
        for channel in self.setting.channels:
            if not channel.enabled: continue

            bake_info = CHANNEL_BAKE_INFO.get(channel.id, {})
            map_item = {
                'id': channel.id,
                'name': channel.name,
                'bake_pass': bake_info.get('bake_pass', 'EMIT'),
                'node_socket': bake_info.get('node_socket'),
                'prefix': channel.prefix,
                'suffix': channel.suffix,
                'custom_cs': channel.custom_cs,
                'channel_prop': channel, 
                'image': None,
            }
            imagemap.append(map_item)
        return imagemap

    def _validate_job_settings(self, imagemap):
        setting = self.setting
        if not self.objects: return report_error(self, "No objects selected or specified for baking.")
        
        for obj in self.objects:
            obj.hide_render = False 
            if obj.type != 'MESH': return report_error(self, f"Object '{obj.name}' is not a mesh.")
            if not obj.data.materials and setting.bake_mode != 'SELECT_ACTIVE': return report_error(self, f"Object '{obj.name}' has no materials assigned.")

        if setting.bake_mode == 'SELECT_ACTIVE':
            if not self.act: return report_error(self, "No active object set for 'Selected to Active' bake mode.")
            if not self.act.data.materials: return report_error(self, f"Active object '{self.act.name}' has no materials assigned.")

        if setting.bake_type == 'BSDF' and not any(m['id'] == 'normal' for m in imagemap if m['channel_prop'].enabled):
            has_bsdf_node = False
            for matslot in self.act.material_slots:
                if matslot.material and matslot.material.node_tree:
                    for node in matslot.material.node_tree.nodes:
                        if node.bl_idname == 'ShaderNodeOutputMaterial' and node.is_active_output:
                            if node.inputs[0].links and node.inputs[0].links[0].from_node.bl_idname == 'ShaderNodeBsdfPrincipled':
                                has_bsdf_node = True; break
                    if has_bsdf_node: break
            if not has_bsdf_node: return report_error(self, "No valid Principled BSDF node found for BSDF bake.")
        
        if not imagemap: return report_error(self, "No bake channels are enabled.")

        if setting.special_bake_method == 'AUTOATLAS' and setting.bake_type == 'MULTIRES': return report_error(self, "Auto Atlas not supported with Multires bake.")
        
        if setting.bake_texture_apply and setting.bake_type == 'BSDF' and not any(m['id'] == 'color' for m in imagemap if m['channel_prop'].enabled):
            return report_error(self, "Applying textures requires 'Base Color' channel.")

        if setting.save_out and not setting.save_path and not setting.bake_motion: return report_error(self, "External saving is enabled but no save path is set.")
            
        if setting.bake_motion and not bpy.data.filepath: return report_error(self, "Animation bake requires the .blend file to be saved first.")
        
        if setting.special_bake_method not in ('VERTEXCOLOR', 'AUTOATLAS'):
            target_objs = [self.act] if setting.bake_mode == 'SELECT_ACTIVE' else self.objects
            for obj in target_objs:
                if not obj.data.uv_layers: return report_error(self, f"Object '{obj.name}' has no UV maps.")

        return True

    def _initialize_bake_parameters(self, context):
        setting = self.setting
        self.objects.clear()
        if setting.bake_objects:
            self.objects.extend([obj.bakeobject for obj in setting.bake_objects if obj.bakeobject])
        if not self.objects and context.selected_objects:
            self.objects.extend([obj for obj in context.selected_objects if obj.type == 'MESH'])
        
        self.act = setting.active_object or context.active_object
        self.cage = setting.cage_object

        if not setting.bake_motion_use_custom:
            self.framerange = (context.scene.frame_end - context.scene.frame_start) + 1
            self.start = context.scene.frame_start
            self.end = context.scene.frame_end
        else:
            self.framerange = setting.bake_motion_last
            self.start = setting.bake_motion_start
            self.end = setting.bake_motion_start + setting.bake_motion_last
        
    def execute(self,context):
        logger.info("Starting bake execution")
        self.objects = []; self.act = None; self.cage = None; self.job = None; self.setting = None
        self.UV = ''; self.foldername = ''; self.start = 0; self.end = 0; self.framerange = 1

        try:
            for job in context.scene.BakeJobs.jobs:
                self.job = job; self.setting = job.setting
                self._initialize_bake_parameters(context)

                # Context Managers for Settings
                scene_settings = {
                    'res_x': self.setting.res_x, 'res_y': self.setting.res_y, 'engine': 'CYCLES', 'samples': self.setting.sample
                }
                image_settings = {
                    'file_format': format_map[self.setting.save_format],
                    'color_depth': self.setting.color_depth,
                    'color_mode': 'RGBA' if self.setting.use_alpha else 'RGB',
                    'quality': self.setting.quality,
                    'exr_codec': self.setting.exr_code,
                }
                bake_settings = {'margin': self.setting.margin, 'normal_space': 'TANGENT'}

                with SceneSettingsContext('scene', scene_settings), \
                     SceneSettingsContext('image', image_settings), \
                     SceneSettingsContext('bake', bake_settings):
                    
                    imagemap = self._create_imagemap()
                    if not self._validate_job_settings(imagemap): return {'CANCELLED'}
                    
                    self._bake_objects(context, imagemap)

            if self.setting and self.setting.save_and_quit:
                bpy.ops.wm.save_mainfile(exit=True)
        except Exception as e:
            logger.error(f"Bake Error: {e}")
            return {'CANCELLED'}
            
        return {'FINISHED'}
        
    def _bake_objects(self, context, imagemap):
        setting = self.setting; objects = self.objects; act = self.act
        if setting.special_bake_method == 'AUTOATLAS': self._setup_auto_atlas(objects, act)

        main_imagemap = [m for m in imagemap if m['bake_pass'] not in ['SHADOW', 'ENVIRONMENT', 'BEVEL', 'AO', 'UV', 'WIREFRAME', 'BEVNOR', 'POSITION', 'SLOPE', 'THICKNESS', 'IDMAT', 'SELECT', 'IDELE', 'IDUVI', 'IDSEAM']]
        mesh_imagemap = [m for m in imagemap if m['bake_pass'] in ['SHADOW', 'ENVIRONMENT', 'BEVEL', 'AO', 'UV', 'WIREFRAME', 'BEVNOR', 'POSITION', 'SLOPE', 'THICKNESS', 'IDMAT', 'SELECT', 'IDELE', 'IDUVI', 'IDSEAM']]

        if setting.bake_mode == 'SINGLE_OBJECT' or setting.special_bake_method == 'VERTEXCOLOR':
            for obj in objects:
                set_active_and_selected(obj, objects)
                name = self._set_name(obj, setting.name_setting)
                self._process_bake([obj], name, main_imagemap, mesh_imagemap)
        elif setting.bake_mode == 'COMBINE_OBJECT':
            name = self._set_name(act, setting.name_setting)
            self._process_bake(objects, name, main_imagemap, mesh_imagemap)
        elif setting.bake_mode == 'SELECT_ACTIVE':
            name = self._set_name(act, setting.name_setting)
            target_objs = [act] if setting.bake_type == 'BASIC' else objects 
            self._process_bake(target_objs, name, main_imagemap, mesh_imagemap, activebake_object=act)
        elif setting.bake_mode == 'SPLIT_MATERIAL':
            for obj in objects:
                for matslot in obj.material_slots:
                    if matslot.material:
                        set_active_and_selected(obj, objects)
                        name = self._set_name(obj, setting.name_setting, material=matslot.material)
                        self._process_bake([obj], name, main_imagemap, mesh_imagemap, spematerial=matslot.material)
        elif setting.bake_type == 'MULTIRES':
            self._adjust_multires(context)
            if setting.bake_mode == 'SINGLE_OBJECT':
                for obj in objects:
                    set_active_and_selected(obj, objects)
                    name = self._set_name(obj, setting.name_setting)
                    self._process_bake([obj], name, main_imagemap, mesh_imagemap)
            elif setting.bake_mode == 'COMBINE_OBJECT':
                name = self._set_name(act, setting.name_setting)
                self._process_bake(objects, name, main_imagemap, mesh_imagemap)

    def _process_bake(self, target_objs, name, imagemap, mesh_imagemap, spematerial=None, activebake_object=None):
        setting = self.setting
        
        self._add_basic_image_and_bake_base(target_objs, imagemap, name, spematerial, activebake_object)
        
        if setting.use_special_map:
            self._bake_mesh_map(target_objs, name, mesh_imagemap, spematerial)
        
        if setting.use_custom_map and setting.special_bake_method != 'VERTEXCOLOR' and not setting.bake_motion:
            full_channel_map = {m['id']: m['image'] for m in imagemap if m['image']}
            full_channel_map.update({m['id']: m['image'] for m in mesh_imagemap if m['image']})
            self._bake_custom_channel(full_channel_map, name, obj=target_objs[0] if target_objs else None)

        if setting.bake_texture_apply and setting.bake_type == 'BSDF' and not setting.bake_motion and setting.special_bake_method != 'VERTEXCOLOR' and not setting.bake_mode == 'SPLIT_MATERIAL':
            for obj in target_objs:
                self._apply_bake(imagemap, obj)

        for map_item in imagemap: map_item['image'] = None
        for map_item in mesh_imagemap: map_item['image'] = None
            
    def _add_basic_image_and_bake_base(self, objects, imagemap, name='', spematerial=None, activebake_object=None):
        setting = self.setting
        mat_collection = []
        for obj in objects:
            obj.hide_render = False
            self.foldername = self._get_folder_name(obj, spematerial) if setting.create_new_folder else ''
            for matslot in obj.material_slots:
                mat_collection.append(create_matinfo(matslot.material, spematerial))

        for map_item in imagemap:
            channel_prop = map_item['channel_prop']
            if not channel_prop.enabled: continue

            # Use MaterialCleanupContext to automatically clean nodes/images
            with MaterialCleanupContext(mat_collection):
                mapname = map_item['prefix'] + name + map_item['suffix']
                
                if setting.special_bake_method == 'VERTEXCOLOR':
                    for obj in objects:
                        vc = obj.data.attributes.new(mapname, 'FLOAT_COLOR' if setting.float32 else 'BYTE_COLOR', 'POINT')
                        obj.data.attributes.active_color = vc
                else:
                    colorspace = channel_prop.custom_cs if setting.colorspace_setting else 'sRGB' 
                    if channel_prop.id == 'normal': colorspace = 'Non-Color' 
                    if setting.float32: colorspace = 'Linear' 
                    if bpy.app.version >= (4,0,0) and colorspace == 'Linear': colorspace = 'Linear Rec.709'

                    map_item['image'] = set_image(
                        mapname, setting.res_x, setting.res_y, alpha=setting.use_alpha,
                        full=setting.float32, space=colorspace, ncol=(colorspace == 'Non-Color'),
                        fake_user=setting.use_fake_user, clear=setting.clearimage, basiccolor=setting.colorbase
                    )

                if setting.bake_type == 'BSDF':
                    for matinfo in mat_collection:
                        if matinfo['bsdf_node'] and not matinfo['is_not_special']:
                            if setting.special_bake_method != 'VERTEXCOLOR':
                                imagenode = matinfo['material'].node_tree.nodes.new("ShaderNodeTexImage")
                                imagenode.image = map_item['image']
                                matinfo['material'].node_tree.nodes.active = imagenode
                                matinfo['extra_nodes'].append(imagenode)

                            if map_item['id'] != 'normal' and map_item['node_socket'] and matinfo['bsdf_node'].inputs.get(map_item['node_socket']):
                                input_socket = matinfo['bsdf_node'].inputs.get(map_item['node_socket'])
                                if input_socket.links:
                                    from_socket = input_socket.links[0].from_socket
                                    emi_node = matinfo['material'].node_tree.nodes.new('ShaderNodeEmission')
                                    matinfo['extra_nodes'].append(emi_node)
                                    
                                    if map_item['id'] == 'rough' and channel_prop.rough_inv:
                                        inv_node = matinfo['material'].node_tree.nodes.new('ShaderNodeInvert')
                                        matinfo['extra_nodes'].append(inv_node)
                                        matinfo['material'].node_tree.links.new(from_socket, inv_node.inputs[1])
                                        matinfo['material'].node_tree.links.new(inv_node.outputs[0], emi_node.inputs[0])
                                    else:
                                        matinfo['material'].node_tree.links.new(from_socket, emi_node.inputs[0])
                                    
                                    matinfo['material'].node_tree.links.new(emi_node.outputs[0], matinfo['output_node'].inputs[0])

                                elif map_item['node_socket']: 
                                    temp_image = bpy.data.images.new('TempPlace', 32, 32)
                                    temp_image_node = matinfo['material'].node_tree.nodes.new("ShaderNodeTexImage")
                                    temp_image_node.image = temp_image
                                    matinfo['temp_image'] = temp_image
                                    matinfo['extra_nodes'].append(temp_image_node)
                                    
                                    if input_socket.type == 'RGBA':
                                        temp_image.generated_color = input_socket.default_value
                                    else:
                                        v = input_socket.default_value
                                        temp_image.generated_color = (v, v, v, 1)
                                        
                                    emi_node = matinfo['material'].node_tree.nodes.new('ShaderNodeEmission')
                                    matinfo['extra_nodes'].append(emi_node)
                                    
                                    matinfo['material'].node_tree.links.new(temp_image_node.outputs[0], emi_node.inputs[0])
                                    matinfo['material'].node_tree.links.new(emi_node.outputs[0], matinfo['output_node'].inputs[0])

                if setting.special_bake_method == 'VERTEXCOLOR':
                    self._bake(map_item, vertex=True)
                else:
                    for obj in objects: obj.select_set(True)
                    if objects: bpy.context.view_layer.objects.active = objects[0]

                    if setting.bake_motion:
                        bpy.context.scene.frame_current = self.start
                        for i in range(self.framerange):
                            index = i + setting.bake_motion_startindex
                            self._bake(map_item, clear=setting.clearimage)
                            save_image(map_item['image'], setting.save_path, setting.create_new_folder, self.foldername, 
                                       setting.save_format, setting.color_depth, 'RGBA' if setting.use_alpha else 'RGB', 
                                       setting.quality, True, index, setting.exr_code, colorspace, setting.reload, 
                                       setting.bake_motion_digit, setting.use_denoise, setting.denoise_method, 
                                       setting.save_out or setting.bake_motion)
                            bpy.context.scene.frame_current += 1
                        if map_item['image']: bpy.data.images.remove(map_item['image'])
                    else:
                        self._bake(map_item, clear=setting.clearimage)
                        save_image(map_item['image'], setting.save_path, setting.create_new_folder, self.foldername, 
                                   setting.save_format, setting.color_depth, 'RGBA' if setting.use_alpha else 'RGB', 
                                   setting.quality, False, 0, setting.exr_code, colorspace, setting.reload, 
                                   0, setting.use_denoise, setting.denoise_method, setting.save_out)
                        self._write_result(map_item, map_item['image'])
        
    def _bake(self, map_item, clear=True, vertex=False):
        setting = self.setting; channel = map_item['channel_prop']
        cage_obj_name = self.cage.name if self.cage else ''

        pass_filter = set()
        if setting.bake_type == 'BASIC':
            if channel.id == 'diff':
                if channel.diff_dir: pass_filter.add('DIRECT')
                if channel.diff_ind: pass_filter.add('INDIRECT')
                if channel.diff_col: pass_filter.add('COLOR')
            elif channel.id == 'gloss':
                if channel.gloss_dir: pass_filter.add('DIRECT')
                if channel.gloss_ind: pass_filter.add('INDIRECT')
                if channel.gloss_col: pass_filter.add('COLOR')
            elif channel.id == 'tranb':
                if channel.tranb_dir: pass_filter.add('DIRECT')
                if channel.tranb_ind: pass_filter.add('INDIRECT')
                if channel.tranb_col: pass_filter.add('COLOR')
            elif channel.id == 'combine':
                if channel.com_dir: pass_filter.add('DIRECT')
                if channel.com_ind: pass_filter.add('INDIRECT')
                if channel.com_diff: pass_filter.add('DIFFUSE')
                if channel.com_gloss: pass_filter.add('GLOSSY')
                if channel.com_tran: pass_filter.add('TRANSMISSION')
                if channel.com_emi: pass_filter.add('EMIT')
        
        if not pass_filter and map_item['bake_pass'] not in ('NORMAL', 'ROUGHNESS', 'EMISSION'):
            pass_filter.add('COLOR')

        normal_type_val = channel.normal_type
        if normal_type_val == 'OPENGL': normal_r, normal_g, normal_b = 'POS_X', 'POS_Y', 'POS_Z'
        elif normal_type_val == 'DIRECTX': normal_r, normal_g, normal_b = 'POS_X', 'NEG_Y', 'POS_Z'
        else: normal_r, normal_g, normal_b = channel.normal_X, channel.normal_Y, channel.normal_Z
        
        if not vertex and setting.bake_type == 'MULTIRES':
             # ... Multires specific logic ...
             bpy.ops.object.bake_image()
             return

        params = {
            'type': map_item['bake_pass'],
            'pass_filter': pass_filter,
            'margin': setting.margin,
            'normal_r': normal_r, 'normal_g': normal_g, 'normal_b': normal_b,
            'normal_space': 'OBJECT' if channel.normal_obj else 'TANGENT',
            'use_clear': clear,
            'target': 'VERTEX_COLORS' if vertex else 'IMAGE_TEXTURES',
            'width': setting.res_x, 'height': setting.res_y,
            'margin_type': 'EXTEND', 
        }

        if not vertex and setting.bake_mode == 'SELECT_ACTIVE':
            params.update({
                'use_selected_to_active': True,
                'use_cage': True if self.cage else False,
                'cage_object': cage_obj_name,
                'cage_extrusion': setting.extrusion,
                'max_ray_distance': setting.ray_distance,
            })
        
        if not vertex and map_item['image']:
            current_active = bpy.context.active_object 
            if current_active and current_active.active_material and current_active.active_material.node_tree:
                tree = current_active.active_material.node_tree
                for node in tree.nodes:
                    if node.bl_idname == 'ShaderNodeTexImage' and node.image == map_item['image']:
                        tree.nodes.active = node
                        break
                else: 
                    image_node = tree.nodes.new('ShaderNodeTexImage')
                    image_node.image = map_item['image']
                    tree.nodes.active = image_node
            
        try:
            bpy.ops.object.bake(**params)
        except RuntimeError as e:
            logger.error(f"Bake failed for channel {map_item['name']}: {e}")
            raise 
        
    def _set_name(self,obj,method,material=None):
        if method=='OBJECT': return obj.name
        elif method=='MAT': return material.name if material else (obj.active_material.name if obj.active_material else "NoMaterial")
        elif method=='OBJ_MAT':
            mat_name = material.name if material else (obj.active_material.name if obj.active_material else "NoMaterial")
            return f"{obj.name}_{mat_name}"
        elif method=='CUSTOM': return self.setting.custom_name
        return "Bake" 
    
    def _bake_custom_channel(self, imagemap_dict, name, obj=None):
        try:
            import numpy as np
        except ImportError:
            logger.error("Numpy is required for optimized custom baking.")
            return

        width = self.setting.res_x
        height = self.setting.res_y
        num_pixels = width * height
        image_cache = {}

        def get_source_pixels(img_obj):
            if not img_obj: return None
            if img_obj.name in image_cache: return image_cache[img_obj.name]
            # 性能优化：确保 float32
            arr = np.empty(num_pixels * 4, dtype=np.float32)
            try: 
                img_obj.pixels.foreach_get(arr)
            except RuntimeError: 
                return None
            arr = arr.reshape((num_pixels, 4))
            image_cache[img_obj.name] = arr
            return arr

        def get_channel_data(channel_item, source_attr, sep_col, col_chan, invert, default_val):
            # 1. 获取所选源的 ID (现在直接从 Enum 属性获取，例如 'rough', 'diff')
            source_id = getattr(channel_item, source_attr, 'NONE')
            
            # 2. 从烘焙好的字典中查找图像
            src_img = imagemap_dict.get(source_id)
            
            if not src_img: 
                # 如果没有找到对应的图（可能是用户未开启该通道，或选择了None），返回默认值
                return np.full((num_pixels,), default_val, dtype=np.float32)
            
            src_arr = get_source_pixels(src_img)
            if src_arr is None: 
                return np.full((num_pixels,), default_val, dtype=np.float32)
            
            # 3. 提取通道
            idx = 0 
            # 如果启用了分离通道 (Separate Color)
            if sep_col: 
                idx = {'R':0, 'G':1, 'B':2, 'A':3}.get(col_chan, 0)
            # 如果源本身就是单通道图（如 Roughness），通常数据在所有通道都一样，或者在 R 通道
            # 这里假设如果是灰度图，取 R 通道也是安全的
            
            data = src_arr[:, idx]
            
            # 4. 反转
            if invert: 
                data = 1.0 - data
                
            return data

        # 开始处理每个自定义通道
        for custom_channel_item in self.job.Custombakechannels:
            res_arr = np.zeros((num_pixels, 4), dtype=np.float32)
            res_arr[:, 3] = 1.0 # Alpha 默认为 1
            
            folder_name = self._get_folder_name(obj, None)

            if not custom_channel_item.bw:
                # RGB 模式
                # 注意这里不再传递 map_suffix，直接传属性名 *_source
                if custom_channel_item.r_usemap:
                    res_arr[:, 0] = get_channel_data(custom_channel_item, "r_source", custom_channel_item.r_sepcol, custom_channel_item.r_colchan, custom_channel_item.r_invert, custom_channel_item.r)
                else: res_arr[:, 0] = custom_channel_item.r
                
                if custom_channel_item.g_usemap:
                    res_arr[:, 1] = get_channel_data(custom_channel_item, "g_source", custom_channel_item.g_sepcol, custom_channel_item.g_colchan, custom_channel_item.g_invert, custom_channel_item.g)
                else: res_arr[:, 1] = custom_channel_item.g
                
                if custom_channel_item.b_usemap:
                    res_arr[:, 2] = get_channel_data(custom_channel_item, "b_source", custom_channel_item.b_sepcol, custom_channel_item.b_colchan, custom_channel_item.b_invert, custom_channel_item.b)
                else: res_arr[:, 2] = custom_channel_item.b
                
                if custom_channel_item.a_usemap:
                    res_arr[:, 3] = get_channel_data(custom_channel_item, "a_source", custom_channel_item.a_sepcol, custom_channel_item.a_colchan, custom_channel_item.a_invert, custom_channel_item.a)
                else: res_arr[:, 3] = custom_channel_item.a
            else:
                # BW 模式
                val_arr = get_channel_data(custom_channel_item, "bw_source", custom_channel_item.bw_sepcol, custom_channel_item.bw_colchan, custom_channel_item.bw_invert, 0.0)
                res_arr[:, 0] = val_arr
                res_arr[:, 1] = val_arr
                res_arr[:, 2] = val_arr

            # 创建输出图像
            final_name = f"{custom_channel_item.prefix}{name}{custom_channel_item.suffix}"
            
            # 检查是否已有同名图像，避免内存泄漏
            out_img = bpy.data.images.get(final_name)
            if out_img:
                if out_img.size[0] != width or out_img.size[1] != height:
                    out_img.scale(width, height)
            else:
                out_img = bpy.data.images.new(name=final_name, width=width, height=height, alpha=True, float_buffer=True)
            
            # 写入像素
            out_img.pixels.foreach_set(res_arr.flatten())
            
            # 保存
            save_image(out_img, self.setting.custom_file_path, self.setting.custom_new_folder, 
                       folder_name, custom_channel_item.save_format, 
                       custom_channel_item.color_depth, custom_channel_item.color_mode, 
                       custom_channel_item.quality, False, 0, custom_channel_item.exr_code, 
                       custom_channel_item.color_space, True, save=True)
                       
            self._write_result(None, out_img, channel_name=custom_channel_item.name)
        
    def _apply_bake(self, imagemap, obj):
        setting = self.setting
        new_obj = obj.copy(); new_obj.name = obj.name + "_bake"
        coll = bpy.data.collections.get('bake') or bpy.data.collections.new('bake')
        if 'bake' not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(coll)
        if new_obj.name not in coll.objects: coll.objects.link(new_obj)
        mesh = obj.data.copy(); mesh.name = new_obj.name; new_obj.data = mesh
        new_mat = bpy.data.materials.new(obj.name + "_bake"); new_mat.use_nodes = True; new_mat.blend_method = 'HASHED'
        bsdf_node = new_mat.node_tree.nodes.get("Principled BSDF") or new_mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        output_node = get_output(new_mat.node_tree.nodes)
        if output_node: new_mat.node_tree.links.new(bsdf_node.outputs[0], output_node.inputs[0])

        index = 0
        for map_item in imagemap:
            channel = map_item['channel_prop']
            if map_item['image'] and map_item['bake_pass'] != 'NORMAL':
                index += 1
                socket_name = CHANNEL_BAKE_INFO.get(channel.id, {}).get('node_socket')
                if not socket_name or not bsdf_node.inputs.get(socket_name): continue
                outsocket = bsdf_node.inputs.get(socket_name)
                imagenode = new_mat.node_tree.nodes.new("ShaderNodeTexImage")
                imagenode.image = map_item['image']; imagenode.location = (-400, 1250 - (index * 300)); insocket = imagenode.outputs[0]
                if channel.id == 'rough' and channel.rough_inv:
                    inv1 = new_mat.node_tree.nodes.new("ShaderNodeInvert")
                    inv1.location = (imagenode.location.x - 300, imagenode.location.y)
                    new_mat.node_tree.links.new(insocket, inv1.inputs[1]); new_mat.node_tree.links.new(inv1.outputs[0], outsocket)
                else: new_mat.node_tree.links.new(insocket, outsocket)
                    
        normal_map_item = next((m for m in imagemap if m['id'] == 'normal' and m['image']), None)
        if normal_map_item:
            channel = normal_map_item['channel_prop']
            socket_name = CHANNEL_BAKE_INFO.get('normal', {}).get('node_socket')
            if socket_name and bsdf_node.inputs.get(socket_name):
                outsocket = bsdf_node.inputs.get(socket_name)
                norimagenode = new_mat.node_tree.nodes.new("ShaderNodeTexImage")
                norimagenode.image = normal_map_item['image']
                normalnode = new_mat.node_tree.nodes.new("ShaderNodeNormalMap")
                norimagenode.location = (-450, 1250 - ((index + 1) * 300)); normalnode.location = (-200, norimagenode.location.y)
                normal_r, normal_g, normal_b = 'POS_X', 'POS_Y', 'POS_Z'
                if channel.normal_type == 'DIRECTX': normal_g = 'NEG_Y'
                elif channel.normal_type == 'CUSTOM': normal_r, normal_g, normal_b = channel.normal_X, channel.normal_Y, channel.normal_Z
                if not (normal_r == 'POS_X' and normal_g == 'POS_Y' and normal_b == 'POS_Z'):
                    itemlist = ['POS_X', 'POS_Y', 'POS_Z', 'NEG_X', 'NEG_Y', 'NEG_Z']
                    spe = new_mat.node_tree.nodes.new("ShaderNodeSeparateColor")
                    com = new_mat.node_tree.nodes.new("ShaderNodeCombineColor")
                    new_mat.node_tree.links.new(norimagenode.outputs[0], spe.inputs[0])
                    new_mat.node_tree.links.new(com.outputs[0], normalnode.inputs[1])
                    for i, axis in enumerate([normal_r, normal_g, normal_b]):
                        idx = ['R', 'G', 'B'][itemlist.index(axis) % 3]
                        if axis.startswith('NEG'):
                            inv = new_mat.node_tree.nodes.new("ShaderNodeInvert")
                            new_mat.node_tree.links.new(spe.outputs[idx], inv.inputs[1]); new_mat.node_tree.links.new(inv.outputs[0], com.inputs[i])
                        else: new_mat.node_tree.links.new(spe.outputs[idx], com.inputs[i])
                else: new_mat.node_tree.links.new(norimagenode.outputs[0], normalnode.inputs[1])
                if channel.normal_obj: normalnode.space = 'OBJECT'
                new_mat.node_tree.links.new(normalnode.outputs[0], outsocket)
        mesh.materials.clear(); mesh.materials.append(new_mat); obj.hide_set(True); new_obj.hide_set(False)
        if setting.special_bake_method == 'AUTOATLAS':
            newUV = mesh.uv_layers.get('atlas_bake_UV')
            if newUV: newUV.active = True; newUV.active_render = True
        elif mesh.uv_layers.active: mesh.uv_layers.active.active_render = True
        if setting.export_model and setting.save_out:
            export_path = os.path.join(setting.save_path, self._get_folder_name(obj, None) if setting.create_new_folder else '', f"{new_obj.name}.{setting.export_format.lower()}")
            export_baked_model(new_obj, export_path, setting.export_format, logger)
        
    def _bake_mesh_map(self, objects, name, imagemap_mesh, spematerial=None):
        setting = self.setting
        logger.info(f"Baking mesh maps for {len(objects)} objects")
        self.foldername = self._get_folder_name(objects[0], spematerial) if setting.create_new_folder else ''
        target = 'IMAGE_TEXTURES' if setting.special_bake_method != 'VERTEXCOLOR' else 'VERTEX_COLORS'
        
        for map_item in imagemap_mesh:
            channel = map_item['channel_prop']
            if not channel.enabled: continue
            
            # Setup image or vertex color
            if target == 'IMAGE_TEXTURES':
                if ((setting.bake_mode == 'SELECT_ACTIVE' and setting.bake_type == 'BASIC') or setting.bake_mode == 'SPLIT_MATERIAL' or setting.bake_motion) and channel.id not in ('shadow', 'env'): continue
                colorspace = channel.custom_cs if setting.colorspace_setting else 'NONCOL'
                if channel.id == 'env': colorspace = 'SRGB'
                if setting.float32: colorspace = 'Linear'
                if bpy.app.version >= (4,0,0) and colorspace == 'Linear': colorspace = 'Linear Rec.709'
                map_item['image'] = set_image(channel.prefix + name + channel.suffix, setting.res_x, setting.res_y, alpha=False, full=setting.float32, space=colorspace, ncol=(colorspace == 'Non-Color'), fake_user=setting.use_fake_user, clear=setting.clearimage, basiccolor=setting.colorbase)
            else: 
                if channel.id not in ('shadow', 'env', 'vertex'): continue
                for obj in objects:
                    vername = channel.prefix + name + channel.suffix
                    vc = obj.data.attributes.new(vername, 'FLOAT_COLOR' if setting.float32 else 'BYTE_COLOR', 'POINT')
                    obj.data.attributes.active_color = vc

            # Setup nodes using MaterialCleanupContext
            mat_collection = []
            temp_objects = []
            if channel.id in ('select', 'idele', 'iduvi', 'idseam'): 
                mat_collection, temp_objects = self._prepare_special_map(objects, map_item, spematerial)
            else:
                for obj in objects:
                    for matslot in obj.material_slots:
                        if matslot.material:
                            matinfo = create_matinfo(matslot.material, spematerial); matinfo['owner'] = obj; mat_collection.append(matinfo)

            with MaterialCleanupContext(mat_collection):
                for matinfo in mat_collection:
                    if target == 'IMAGE_TEXTURES' and (spematerial is None or matinfo['material'] == spematerial):
                        imagenode = matinfo['material'].node_tree.nodes.new('ShaderNodeTexImage')
                        imagenode.image = map_item['image']; matinfo['material'].node_tree.nodes.active = imagenode; matinfo['extra_nodes'].append(imagenode)
                    
                    output_socket = self._setup_mesh_map_nodes(matinfo, channel)
                    if output_socket and matinfo['output_node']: matinfo['material'].node_tree.links.new(output_socket, matinfo['output_node'].inputs[0])
                
                try: bpy.ops.object.bake(type=map_item['bake_pass'], margin=setting.margin, target=target)
                except Exception as e: logger.error(f"Bake failed for mesh map {channel.name}: {e}")
            
            # Cleanup temp objects
            for obj in temp_objects:
                for mat in obj.data.materials:
                    if mat: bpy.data.materials.remove(mat)
                bpy.data.objects.remove(obj)
            for obj in objects: obj.select_set(True)

            if target == 'IMAGE_TEXTURES':
                save_image(map_item['image'], setting.save_path, setting.create_new_folder, self.foldername, 
                           setting.save_format, setting.color_depth, 'RGB', setting.quality, False, 0, 
                           setting.exr_code, colorspace, setting.reload, 0, setting.use_denoise, setting.denoise_method, setting.save_out)
                self._write_result(map_item, map_item['image'])
        return imagemap_mesh

    def _setup_mesh_map_nodes(self, matinfo, channel):
        # ... (Keep original node setup logic for mesh maps) ...
        nodes = matinfo['material'].node_tree.nodes
        links = matinfo['material'].node_tree.links
        if channel.id == 'vertex':
            if matinfo['owner'].data.vertex_colors:
                vernode = nodes.new('ShaderNodeVertexColor'); vernode.layer_name = matinfo['owner'].data.vertex_colors.active.name; matinfo['extra_nodes'].append(vernode); return vernode.outputs[0]
        elif channel.id == 'bevel':
            bevel = nodes.new('ShaderNodeBevel'); bevel.samples = channel.bevel_sample; bevel.inputs[0].default_value = channel.bevel_rad; vmc = nodes.new('ShaderNodeVectorMath'); vmc.operation = 'CROSS_PRODUCT'; vma = nodes.new('ShaderNodeVectorMath'); vma.operation = 'ABSOLUTE'; vml = nodes.new('ShaderNodeVectorMath'); vml.operation = 'LENGTH'; geo = nodes.new('ShaderNodeNewGeometry'); matinfo['extra_nodes'].extend([bevel, vmc, vma, vml, geo]); links.new(bevel.outputs[0], vmc.inputs[0]); links.new(geo.outputs[1], vmc.inputs[1]); links.new(vmc.outputs[0], vma.inputs[0]); links.new(vma.outputs[0], vml.inputs[0]); return vml.outputs[1]
        elif channel.id == 'ao':
            ao = nodes.new('ShaderNodeAmbientOcclusion'); ao.samples = channel.ao_sample; ao.inside = channel.ao_inside; ao.only_local = channel.ao_local; ao.inputs[1].default_value = channel.ao_dis; matinfo['extra_nodes'].append(ao); return ao.outputs[0]
        elif channel.id == 'uv':
            tex = nodes.new('ShaderNodeTexCoord'); sep = nodes.new('ShaderNodeSeparateColor'); com = nodes.new('ShaderNodeCombineColor'); matinfo['extra_nodes'].extend([tex, sep, com]); links.new(tex.outputs[2], sep.inputs[0]); links.new(sep.outputs[1], com.inputs[1]); return com.outputs[0]
        elif channel.id == 'wireframe':
            wf = nodes.new('ShaderNodeWireframe'); wf.inputs[0].default_value = channel.wireframe_dis; wf.use_pixel_size = channel.wireframe_use_pix; matinfo['extra_nodes'].append(wf); return wf.outputs[0]
        elif channel.id == 'bevnor':
            bevel = nodes.new('ShaderNodeBevel'); bevel.samples = channel.bevnor_sample; bevel.inputs[0].default_value = channel.bevnor_rad; bsdf = nodes.new('ShaderNodeBsdfPrincipled'); matinfo['extra_nodes'].extend([bevel, bsdf]); links.new(bevel.outputs[0], bsdf.inputs['Normal']); return bsdf.outputs[0]
        elif channel.id == 'position' or channel.id == 'slope':
            tex = nodes.new('ShaderNodeTexCoord'); sep = nodes.new('ShaderNodeSeparateColor'); math1 = nodes.new('ShaderNodeMath'); math1.operation = 'ABSOLUTE'; matinfo['extra_nodes'].extend([tex, sep, math1]); links.new(tex.outputs[0 if channel.id == 'position' else 1], sep.inputs[0])
            idx = {'X': 0, 'Y': 1, 'Z': 2}.get(channel.slope_directions if channel.id == 'slope' else 'Z', 2)
            links.new(sep.outputs[idx], math1.inputs[0])
            inv = channel.position_invg if channel.id == 'position' else channel.slope_invert
            if inv: math2 = nodes.new('ShaderNodeMath'); math2.operation = 'SUBTRACT'; math2.inputs[0].default_value = 1.0; matinfo['extra_nodes'].append(math2); links.new(math1.outputs[0], math2.inputs[1]); return math2.outputs[0]
            return math1.outputs[0]
        elif channel.id == 'thickness':
            ao = nodes.new('ShaderNodeAmbientOcclusion'); ao.samples = 32; ao.only_local = True; ao.inside = True; ao.inputs[1].default_value = channel.thickness_distance; inv = nodes.new('ShaderNodeInvert'); con = nodes.new('ShaderNodeBrightContrast'); con.inputs[2].default_value = channel.thickness_contrast; matinfo['extra_nodes'].extend([ao, inv, con]); links.new(ao.outputs[0], inv.inputs[1]); links.new(inv.outputs[0], con.inputs[0]); return con.outputs[0]
        elif channel.id == 'idmat' or channel.id == 'select' or channel.id in ('idele', 'iduvi', 'idseam'):
            colnode = nodes.new('ShaderNodeRGB'); matinfo['extra_nodes'].append(colnode)
            if channel.id == 'idmat':
                idx = sum(len(o.material_slots) for o in self.objects[:self.objects.index(matinfo['owner'])]) + [m.material for m in matinfo['owner'].material_slots].index(matinfo['material'])
                hue = idx / max(1, channel.ID_num); col = mathutils.Color((1.0, 0.0, 0.0)); col.h = hue; colnode.outputs[0].default_value = (col.r, col.g, col.b, 1.0)
            elif channel.id == 'select': colnode.outputs[0].default_value = matinfo.get('select_color', (1.0, 1.0, 1.0, 1.0))
            else: idx = matinfo.get(f"{channel.id}_index", 0); hue = idx / max(1, channel.ID_num); col = mathutils.Color((1.0, 0.0, 0.0)); col.h = hue; colnode.outputs[0].default_value = (col.r, col.g, col.b, 1.0)
            return colnode.outputs[0]
        return None

    def _prepare_special_map(self, objects, map_item, spematerial):
        # ... (Same as original) ...
        channel = map_item['channel_prop']; mat_collection = []; temp_objects = []
        if channel.id == 'select':
            sel_mat = bpy.data.materials.new('sel'); sel_mat.use_nodes = True; unsel_mat = bpy.data.materials.new('unsel'); unsel_mat.use_nodes = True
            for m, c in [(sel_mat, (1,1,1,1)), (unsel_mat, (0,0,0,1))]:
                n = m.node_tree.nodes; col = n.new('ShaderNodeRGB'); col.outputs[0].default_value = c; img = n.new('ShaderNodeTexImage'); img.image = map_item['image']; m.node_tree.links.new(col.outputs[0], get_output(n).inputs[0])
            for obj in objects:
                faces = {f.index for f in obj.data.polygons if f.select}; no = copy_object(obj, clear_material=True); temp_objects.append(no); obj.select_set(False); no.select_set(True); no.data.materials.append(sel_mat); no.data.materials.append(unsel_mat)
                for poly in no.data.polygons: poly.material_index = 0 if poly.index in faces else 1
                for m, c in [(sel_mat, (1,1,1,1)), (unsel_mat, (0,0,0,1))]: mi = create_matinfo(m, spematerial); mi['owner'] = no; mi['select_color'] = c; mat_collection.append(mi)
        elif channel.id in ('idele', 'iduvi', 'idseam'):
            for obj in objects:
                no = copy_object(obj, clear_material=True); temp_objects.append(no); obj.select_set(False); no.select_set(True); bm = bmesh.new(); bm.from_mesh(no.data); bm.faces.ensure_lookup_table(); delimit = {'UV'} if channel.id == 'iduvi' else {'SEAM'} if channel.id == 'idseam' else set()
                faces_list = []; used = set(); bpy.context.view_layer.objects.active = no; bpy.ops.object.mode_set(mode='EDIT')
                for i in range(len(bm.faces)):
                    if i in used: continue
                    bpy.ops.mesh.select_all(action='DESELECT'); bm.faces[i].select = True; bmesh.update_edit_mesh(no.data); bpy.ops.mesh.select_linked(delimit=delimit); group = [f.index for f in bm.faces if f.select]; used.update(group); faces_list.append(group)
                bpy.ops.object.mode_set(mode='OBJECT')
                for idx, faces in enumerate(faces_list):
                    mat = bpy.data.materials.new('grp'); mat.use_nodes = True; col = mat.node_tree.nodes.new('ShaderNodeRGB'); hue = idx / max(1, channel.ID_num); c = mathutils.Color((1,0,0)); c.h = hue; col.outputs[0].default_value = (c.r,c.g,c.b,1); img = mat.node_tree.nodes.new('ShaderNodeTexImage'); img.image = map_item['image']; mat.node_tree.nodes.active = img; mat.node_tree.links.new(col.outputs[0], get_output(mat.node_tree.nodes).inputs[0]); no.data.materials.append(mat)
                    for fi in faces: no.data.polygons[fi].material_index = idx
                    mi = create_matinfo(mat, spematerial); mi['owner'] = no; mi[f"{channel.id}_index"] = idx; mat_collection.append(mi)
        return mat_collection, temp_objects

    def _get_folder_name(self, obj, spematerial):
        s = self.setting
        if s.new_folder_name_setting == 'OBJECT': return obj.name
        if s.new_folder_name_setting == 'MAT': return spematerial.name if spematerial else (obj.active_material.name if obj.active_material else "NoMat")
        if s.new_folder_name_setting == 'OBJ_MAT': return f"{obj.name}_{spematerial.name if spematerial else (obj.active_material.name if obj.active_material else 'NoMat')}"
        if s.new_folder_name_setting == 'CUSTOM': return s.folder_name
        return ""

    def _write_result(self, map_item, image, channel_name=None):
        results = bpy.context.scene.baked_image_results
        res = next((r for r in results if r.image == image), None)
        if not res:
            res = results.add()
        res.image = image
        res.color_depth = self.setting.color_depth
        if map_item:
            res.color_space = map_item['custom_cs']
            res.channel_type = map_item['name']
        elif channel_name:
            res.color_space = 'sRGB' 
            res.channel_type = channel_name
        res.filepath = os.path.join(bpy.path.abspath(self.setting.save_path), self.foldername, f"{image.name}.{self.setting.save_format.lower()}") if self.setting.save_out else ""
        res.object_name = self.act.name if self.act else "Unknown"
        
    def _setup_auto_atlas(self, objects, act):
        bpy.ops.object.mode_set(mode='OBJECT'); ori = {o: o.data.uv_layers.active for o in objects}
        for o in objects:
            bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            uv = o.data.uv_layers.get('atlas_bake_UV') or o.data.uv_layers.new(name='atlas_bake_UV'); o.data.uv_layers.active = uv; uv.active_render = True
            if self.setting.atlas_pack_method == 'REPACK': bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=self.setting.atlas_margin)
            else:
                curr = bpy.context.area.type; bpy.context.area.type = 'IMAGE_EDITOR'
                bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin=self.setting.atlas_margin)
                bpy.context.area.type = curr
            bpy.ops.object.mode_set(mode='OBJECT')
        for o, l in ori.items():
            if l: o.data.uv_layers.active = l
        bpy.ops.object.mode_set(mode=act.mode)

    def _adjust_multires(self, context):
        for o in self.objects:
            for m in o.modifiers:
                if m.type == 'MULTIRES': m.levels = m.render_levels = self.setting.multires_divide; break

class BAKETOOL_OT_BakeSelectedNode(bpy.types.Operator):
    bl_label = "Selected Node Bake"
    bl_idname = "bake.selected_node_bake"
    bl_description = "Bake selected material nodes to image"

    @classmethod
    def poll(cls, context):
        if not context.active_object or not context.selected_objects: return False
        if not context.selected_nodes or not context.active_node: return False
        active_mat = context.active_object.active_material
        if not active_mat or not active_mat.node_tree: return False
        if not next((n for n in active_mat.node_tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output), None): return False
        if not context.scene.BakeJobs.node_bake_auto_find_socket:
            if context.scene.BakeJobs.node_bake_socket_index >= len(context.active_node.outputs): return False
        return True

    def execute(self, context):
        bj = context.scene.BakeJobs
        if bj.node_bake_save_outside and not bj.node_bake_save_path: return report_error(self, "Please set a valid save path")
        material = context.active_object.active_material; nt = material.node_tree
        out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output)
        sock = out.inputs[0]; orig = sock.links[0].from_socket if sock.links else None
        
        scene_settings = {'res_x': bj.node_bake_res_x, 'res_y': bj.node_bake_res_y, 'engine': 'CYCLES', 'samples': bj.node_bake_sample}
        image_settings = {'file_format': format_map[bj.node_bake_save_format], 'color_depth': bj.node_bake_color_depth, 'color_mode': bj.node_bake_color_mode, 'quality': bj.node_bake_quality, 'exr_codec': bj.node_bake_exr_code}
        bake_settings = {'margin': bj.node_bake_margin}

        with SceneSettingsContext('scene', scene_settings), \
             SceneSettingsContext('image', image_settings), \
             SceneSettingsContext('bake', bake_settings):
            
            t_mats = [make_temp_node(s.material) for s in context.active_object.material_slots if s.material != material]
            
            for node in [n for n in nt.nodes if n.select]:
                s = self.get_output_socket(node, bj)
                if not s: continue
                img = self.create_bake_image(f"{material.name} {node.label or node.name}", bj)
                in_node = nt.nodes.new("ShaderNodeTexImage"); in_node.image = img; nt.nodes.active = in_node
                nt.links.new(s, sock); bpy.ops.object.bake(type='EMIT', margin=bj.node_bake_margin, margin_type='EXTEND', target='IMAGE_TEXTURES')
                if bj.node_bake_save_outside: 
                    # Use save_image utility if possible, but keeping original logic for node bake for now or adapting
                    img.filepath_raw = bj.node_bake_save_path; img.file_format = format_map[bj.node_bake_save_format]; img.save()
                else: img.pack()
                if bj.node_bake_delete_node: nt.nodes.remove(in_node)
            
            if orig: nt.links.new(orig, sock)
            for t in t_mats: clear_temp_node(t)
            
        return {'FINISHED'}

    def get_output_socket(self, node, bj):
        if not bj.node_bake_auto_find_socket: return node.outputs[bj.node_bake_socket_index]
        return next((s for s in node.outputs if s.is_linked), next((s for s in node.outputs if s.enabled), None))

    def create_bake_image(self, name, bj):
        cs = ('sRGB' if bj.node_bake_color_space == 'SRGB' else 'Linear' if bj.node_bake_color_space == 'LINEAR' else 'Non-Color')
        return bpy.data.images.new(name=name, width=bj.node_bake_res_x, height=bj.node_bake_res_y, alpha=True, float_buffer=bj.node_bake_float32, is_data=(cs == 'Non-Color'))

class BAKETOOL_OT_DeleteResult(bpy.types.Operator):
    bl_idname = "baketool.delete_result"
    bl_label = "Delete Selected Result"
    @classmethod
    def poll(cls, context): return context.scene.baked_image_results_index >= 0
    def execute(self, context):
        idx = context.scene.baked_image_results_index; res = context.scene.baked_image_results
        if res[idx].image: bpy.data.images.remove(res[idx].image)
        res.remove(idx); context.scene.baked_image_results_index = min(max(0, idx - 1), len(res) - 1); return {'FINISHED'}

class BAKETOOL_OT_DeleteAllResults(bpy.types.Operator):
    bl_idname = "baketool.delete_all_results"
    bl_label = "Delete All Results"
    def execute(self, context):
        res = context.scene.baked_image_results
        for r in res:
            if r.image: bpy.data.images.remove(r.image)
        res.clear(); context.scene.baked_image_results_index = -1; return {'FINISHED'}

class BAKETOOL_OT_ExportResult(bpy.types.Operator):
    bl_idname = "baketool.export_result"
    bl_label = "Export Selected Result"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    @classmethod
    def poll(cls, context): return (context.scene.baked_image_results_index >= 0 and context.scene.baked_image_results[context.scene.baked_image_results_index].image is not None)
    def invoke(self, context, event):
        self.filepath = bpy.path.abspath(context.scene.BakeJobs.bake_result_save_path or "//"); context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, context):
        r = context.scene.baked_image_results[context.scene.baked_image_results_index]; bj = context.scene.BakeJobs
        if not r.image: return {'CANCELLED'}
        save_image(image=r.image, path=os.path.dirname(self.filepath), folder=False, folder_name="", file_format=bj.bake_result_save_format, color_depth=bj.bake_result_color_depth, color_mode=bj.bake_result_color_mode, quality=bj.bake_result_quality, exr_codec=bj.bake_result_exr_code, color_space='sRGB' if bj.bake_result_color_space == 'DEFAULT' else bj.bake_result_color_space, reload=False, denoise=bj.bake_result_use_denoise, denoise_method=bj.bake_result_denoise_method, save=True)
        return {'FINISHED'}

class BAKETOOL_OT_ExportAllResults(bpy.types.Operator):
    bl_idname = "baketool.export_all_results"
    bl_label = "Export All Results"
    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    @classmethod
    def poll(cls, context): return (context.scene.baked_image_results_index >= 0)
    def invoke(self, context, event):
        self.directory = bpy.path.abspath(context.scene.BakeJobs.bake_result_save_path or "//"); context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, context):
        res = context.scene.baked_image_results; bj = context.scene.BakeJobs
        if not res: return {'CANCELLED'}
        for r in res:
            if r.image: save_image(image=r.image, path=self.directory, folder=False, folder_name="", file_format=bj.bake_result_save_format, color_depth=bj.bake_result_color_depth, color_mode=bj.bake_result_color_mode, quality=bj.bake_result_quality, exr_codec=bj.bake_result_exr_code, color_space='sRGB' if bj.bake_result_color_space == 'DEFAULT' else bj.bake_result_color_space, reload=False, denoise=bj.bake_result_use_denoise, denoise_method=bj.bake_result_denoise_method, save=True)
        return {'FINISHED'}