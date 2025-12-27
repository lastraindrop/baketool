import bpy
from bpy import props
import mathutils
import bmesh
import os
from pathlib import Path
from collections import namedtuple
try:
    import numpy as np
except ImportError:
    np = None
from .utils import *
from .constants import *

BakeTask = namedtuple('BakeTask', ['objects', 'materials', 'active_obj', 'base_name', 'folder_name'])

class TaskBuilder:
    @staticmethod
    def build(context, setting, objects, active_obj):
        mode = setting.bake_mode
        tasks = []
        
        if mode == 'SINGLE_OBJECT':
            for obj in objects:
                n = TaskBuilder._get_name(setting, obj)
                tasks.append(BakeTask(
                    objects=[obj],
                    materials=[ms.material for ms in obj.material_slots if ms.material],
                    active_obj=obj,
                    base_name=n,
                    folder_name=n
                ))
        elif mode == 'COMBINE_OBJECT':
            n = TaskBuilder._get_name(setting, active_obj)
            all_mats = {ms.material for obj in objects for ms in obj.material_slots if ms.material}
            tasks.append(BakeTask(
                objects=objects,
                materials=list(all_mats),
                active_obj=active_obj,
                base_name=n,
                folder_name=n
            ))
        elif mode == 'SELECT_ACTIVE':
            if not active_obj: return []
            n = TaskBuilder._get_name(setting, active_obj)
            tasks.append(BakeTask(
                objects=objects,
                materials=[ms.material for ms in active_obj.material_slots if ms.material],
                active_obj=active_obj,
                base_name=n,
                folder_name=n
            ))
        elif mode == 'SPLIT_MATERIAL':
            for obj in objects:
                for ms in obj.material_slots:
                    if not ms.material: continue
                    n = TaskBuilder._get_name(setting, obj, ms.material)
                    tasks.append(BakeTask(
                        objects=[obj],
                        materials=[ms.material],
                        active_obj=obj,
                        base_name=n,
                        folder_name=n
                    ))
        return tasks

    @staticmethod
    def _get_name(setting, obj, mat=None):
        m = setting.name_setting
        if m == 'OBJECT': return obj.name
        if m == 'MAT': return mat.name if mat else (obj.active_material.name if obj.active_material else "NoMat")
        if m == 'OBJ_MAT':
            mn = mat.name if mat else (obj.active_material.name if obj.active_material else "NoMat")
            return f"{obj.name}_{mn}"
        if m == 'CUSTOM': return setting.custom_name
        return "Bake"

class BAKETOOL_OT_BakeOperator(bpy.types.Operator):
    bl_label = "Bake"
    bl_idname = "bake.bake_operator"
    
    @classmethod
    def poll(cls, context):
        return context.scene.BakeJobs and context.scene.BakeJobs.jobs
        
    def execute(self, context):
        try:
            for job in context.scene.BakeJobs.jobs:
                self.process_job(context, job)
            
            if context.scene.BakeJobs.jobs[0].setting.save_and_quit:
                bpy.ops.wm.save_mainfile(exit=True)
                
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            self.report({'ERROR'}, f"Bake Error: {str(e)}")
            return {'CANCELLED'}
            
        self.report({'INFO'}, "Baking Finished")
        return {'FINISHED'}

    def process_job(self, context, job):
        s = job.setting
        objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]
        if not objs and context.selected_objects:
            objs = [o for o in context.selected_objects if o.type == 'MESH']
        if not objs: return
        
        act = s.active_object or context.active_object
        tasks = TaskBuilder.build(context, s, objs, act)
        
        chans = self._get_enabled_channels(s)
        if s.use_custom_map:
            chans.extend(self._get_custom_channels(job))
        if not chans: return
        
        # Sort custom channels to end (optional, depending on logic)
        chans.sort(key=lambda c: 1 if c['id'] == 'CUSTOM' else 0)
        
        scene_sets = {'res_x': s.res_x, 'res_y': s.res_y, 'engine': 'CYCLES', 'samples': s.sample}
        img_sets = {'file_format': format_map[s.save_format], 'color_depth': s.color_depth, 'color_mode': s.color_mode, 'quality': s.quality, 'exr_codec': s.exr_code}
        cm_sets = {'view_transform': 'Standard', 'look': 'None'}
        
        with SceneSettingsContext('scene', scene_sets), SceneSettingsContext('image', img_sets), SceneSettingsContext('cm', cm_sets):
            for task in tasks:
                self.process_task(context, s, task, chans)
            # [改进] 只有在开启外部保存时才执行导出
            if s.export_model and s.save_out:
                self._export_results(s, tasks)

    def process_task(self, context, setting, task, channels):
        bpy.ops.object.select_all(action='DESELECT')
        for o in task.objects: o.select_set(True)
        if task.active_obj:
            context.view_layer.objects.active = task.active_obj
            
        handler = NodeGraphHandler(task.materials)
        task_images = {}
        try:
            for c in channels:
                img = self.process_channel(context, setting, task, c, handler, task_images)
                if img and c['id'] != 'CUSTOM':
                    task_images[c['channel_prop'].id] = img
        finally:
            handler.cleanup()

    def process_channel(self, context, setting, task, c, handler, task_images):
        name = f"{c['prefix']}{task.base_name}{c['suffix']}"
        img = self._get_or_create_image(name, setting, c)
        cid = c['id']
        
        # Dispatch logic
        if cid in ('ID_mat', 'ID_ele', 'ID_UVI', 'ID_seam', 'position', 'UV', 'wireframe'):
            mesh_type = None
            attr_name = None
            if cid.startswith('ID_') or cid == 'ID_seam':
                mesh_type = 'ID'
                id_key = cid.split('_')[1].upper() if '_' in cid else 'ELEMENT'
                attr_name = setup_mesh_attribute(task.active_obj, id_key, setting.id_start_color, setting.id_iterations, setting.id_manual_start_color)
                handler.temp_attributes.append((task.active_obj, attr_name))
            elif cid == 'position': mesh_type = 'POS'
            elif cid == 'UV': mesh_type = 'UV'
            elif cid == 'wireframe': mesh_type = 'WF'
            
            handler.setup_for_pass(bake_pass='EMIT', socket_name=None, image=img, mesh_type=mesh_type, attr_name=attr_name)
            bpy.ops.object.bake(type='EMIT', margin=setting.margin, use_clear=setting.clearimage)
            
        elif cid == 'CUSTOM':
            self._bake_custom(setting, task, c, handler, img, task_images)
        else:
            handler.setup_for_pass(bake_pass=c['bake_pass'], socket_name=c['node_socket'], image=img)
            self._call_bake_api(setting, c)
            
        if setting.save_out:
            save_image(image=img, path=setting.save_path, folder=setting.create_new_folder, folder_name=task.folder_name, file_format=setting.save_format, reload=setting.reload)
            
        self._write_result(context, img, c['name'], task.active_obj.name)
        return img

    def _bake_custom(self, s, task, c, handler, target, sources):
        prop = c['channel_prop']
        for mat in task.materials:
            if not mat or not mat.use_nodes: continue
            tree = mat.node_tree
            nodes = tree.nodes
            links = tree.links
            
            if mat not in handler.temp_nodes: handler.temp_nodes[mat] = []
            
            t_node = nodes.new('ShaderNodeTexImage')
            t_node.image = target
            nodes.active = t_node
            handler.temp_nodes[mat].append(t_node)
            
            emi = nodes.new('ShaderNodeEmission')
            handler.temp_nodes[mat].append(emi)
            
            if prop.bw:
                # Black & White Mode
                out = self._build_source(nodes, links, 0.0, prop.bw_settings, sources, handler.temp_nodes[mat])
                links.new(out, emi.inputs[0])
            else:
                # RGB Mode
                comb = nodes.new('ShaderNodeCombineColor' if bpy.app.version >= (3,3,0) else 'ShaderNodeCombineRGB')
                handler.temp_nodes[mat].append(comb)
                
                # R
                r_out = self._build_source(nodes, links, prop.r, prop.r_settings, sources, handler.temp_nodes[mat])
                links.new(r_out, comb.inputs[0])
                
                # G
                g_out = self._build_source(nodes, links, prop.g, prop.g_settings, sources, handler.temp_nodes[mat])
                links.new(g_out, comb.inputs[1])
                
                # B
                b_out = self._build_source(nodes, links, prop.b, prop.b_settings, sources, handler.temp_nodes[mat])
                links.new(b_out, comb.inputs[2])
                
                links.new(comb.outputs[0], emi.inputs[0])
            
            # Connect to Output
            out_node = handler._get_output_node(tree)
            if out_node:
                sock = out_node.inputs[0]
                if mat not in handler.history:
                    handler.history[mat] = {'sock': sock, 'src': sock.links[0].from_socket if sock.is_linked else None}
                links.new(emi.outputs[0], sock)
                
        bpy.ops.object.bake(type='EMIT', margin=s.margin, use_clear=s.clearimage)

    def _build_source(self, nodes, links, val, settings, sources, temps):
        """
        val: default float value (e.g. prop.r)
        settings: BakeChannelSource object (prop.r_settings)
        """
        if not settings.use_map:
            n = nodes.new('ShaderNodeValue')
            n.outputs[0].default_value = val
            temps.append(n)
            return n.outputs[0]
            
        src_id = settings.source
        src_img = sources.get(src_id)
        if not src_img:
            n = nodes.new('ShaderNodeValue')
            n.outputs[0].default_value = val # Fallback to val if map missing
            temps.append(n)
            return n.outputs[0]
            
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = src_img
        temps.append(tex)
        try: tex.image.colorspace_settings.name = 'Non-Color'
        except: pass
        
        out = tex.outputs[0]
        
        if settings.sep_col:
            sep = nodes.new('ShaderNodeSeparateColor' if bpy.app.version >= (3,3,0) else 'ShaderNodeSeparateRGB')
            temps.append(sep)
            links.new(out, sep.inputs[0])
            
            # Map channel selection
            # Logic: R=0, G=1, B=2, A=2 (Legacy behavior kept for A)
            idx = {'R':0, 'G':1, 'B':2, 'A':2}.get(settings.col_chan, 0)
            out = sep.outputs[idx]
            
        if settings.invert:
            inv = nodes.new('ShaderNodeInvert')
            temps.append(inv)
            links.new(out, inv.inputs[1])
            inv.inputs[0].default_value = 1.0
            out = inv.outputs[0]
            
        return out

    def _get_enabled_channels(self, s):
        res = []
        for c in s.channels:
            if not c.enabled: continue
            info = CHANNEL_BAKE_INFO.get(c.id, {})
            res.append({
                'id': c.id, 
                'name': c.name, 
                'channel_prop': c, 
                'bake_pass': info.get('bake_pass', 'EMIT'), 
                'node_socket': info.get('node_socket'), 
                'prefix': c.prefix, 
                'suffix': c.suffix, 
                'custom_cs': c.custom_cs
            })
        return res

    def _get_custom_channels(self, job):
        return [{
            'id': 'CUSTOM', 
            'name': c.name, 
            'channel_prop': c, 
            'bake_pass': 'EMIT', 
            'node_socket': None, 
            'prefix': c.prefix, 
            'suffix': c.suffix, 
            'custom_cs': c.color_space
        } for c in job.Custombakechannels]

    def _get_or_create_image(self, name, s, c):
        cs = c['custom_cs'] if s.colorspace_setting else ('Non-Color' if c['id'] == 'normal' else 'sRGB')
        if s.float32: cs = 'Linear'
        if bpy.app.version >= (4,0,0) and cs == 'Linear': cs = 'Linear Rec.709'
        return set_image(name, s.res_x, s.res_y, alpha=s.use_alpha, full=s.float32, space=cs, ncol=(cs == 'Non-Color'), fake_user=s.use_fake_user, clear=s.clearimage, basiccolor=s.colorbase)

    def _call_bake_api(self, s, c):
        params = {'type': c['bake_pass'], 'margin': s.margin, 'use_clear': s.clearimage, 'target': 'IMAGE_TEXTURES'}
        if c['bake_pass'] == 'NORMAL': 
            params['normal_space'] = 'OBJECT' if c['channel_prop'].normal_obj else 'TANGENT'
        if s.bake_mode == 'SELECT_ACTIVE': 
            params.update({
                'use_selected_to_active': True, 
                'use_cage': bool(s.cage_object), 
                'cage_object': s.cage_object.name if s.cage_object else "", 
                'cage_extrusion': s.extrusion, 
                'max_ray_distance': s.ray_distance
            })
        
        pf = set()
        cp = c['channel_prop']
        if c['id'] == 'diff':
            if cp.diff_dir: pf.add('DIRECT')
            if cp.diff_ind: pf.add('INDIRECT')
            if cp.diff_col: pf.add('COLOR')
        # Add checks for gloss/trans if needed, assuming similar logic existed or extends here
        
        if pf: params['pass_filter'] = pf
        bpy.ops.object.bake(**params)

    def _write_result(self, context, image, type_name, obj_name):
        results = context.scene.baked_image_results
        res = next((r for r in results if r.image == image), None)
        if not res: res = results.add()
        res.image = image
        res.channel_type = type_name
        res.object_name = obj_name

    def _export_results(self, s, tasks):
        for t in tasks:
            if not t.active_obj: continue
            path = Path(bpy.path.abspath(s.save_path))
            if s.create_new_folder: path = path / t.folder_name
            fpath = path / f"{t.base_name}.{s.export_format.lower()}"
            export_baked_model(t.active_obj, str(fpath), s.export_format)

class BAKETOOL_OT_GenericChannelOperator(bpy.types.Operator):
    bl_idname = "bake.generic_channel_op"
    bl_label = "Op"
    bl_options = {'REGISTER', 'UNDO'}
    
    action_type: props.EnumProperty(items=[('ADD','Add',''),('DELETE','Delete',''),('UP','Up',''),('DOWN','Down',''),('CLEAR','Clear','')], name="Action")
    target: props.StringProperty()
    
    def execute(self, context):
        bj = context.scene.BakeJobs
        job = bj.jobs[bj.job_index] if bj.jobs else None
        
        props_map = {
            "jobs_channel": (bj.jobs, "job_index"), 
            "job_custom_channel": (job.Custombakechannels if job else None, "Custombakechannels_index"), 
            "bake_objects": (job.setting.bake_objects if job else None, "active_object_index")
        }
        
        if self.target not in props_map: return {'CANCELLED'}
        coll, idx_name = props_map[self.target]
        if coll is None: return {'CANCELLED'}
        
        target_obj = bj if self.target=="jobs_channel" else job if self.target=="job_custom_channel" else job.setting
        idx = getattr(target_obj, idx_name)
        
        if self.action_type == 'ADD':
            item = coll.add()
            item.name = f"New {len(coll)}"
            setattr(target_obj, idx_name, len(coll)-1)
            if self.target == "jobs_channel": bpy.ops.bake.reset_channels()
            
        elif self.action_type == 'DELETE' and len(coll) > 0:
            coll.remove(idx)
            setattr(target_obj, idx_name, min(idx, len(coll)-1))
            
        elif self.action_type == 'CLEAR':
            coll.clear()
            setattr(target_obj, idx_name, -1)
            
        elif self.action_type in ('UP', 'DOWN') and len(coll) > 1:
            new_idx = idx - 1 if self.action_type == 'UP' else idx + 1
            if 0 <= new_idx < len(coll):
                coll.move(idx, new_idx)
                setattr(target_obj, idx_name, new_idx)
                
        return {'FINISHED'}

class BAKETOOL_OT_ResetChannels(bpy.types.Operator):
    bl_idname = "bake.reset_channels"
    bl_label = "Reset"
    
    def execute(self, context):
        if not context.scene.BakeJobs.jobs: return {'CANCELLED'}
        s = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting
        defs = []
        if s.bake_type == 'BSDF': 
            defs.extend(CHANNEL_DEFINITIONS['BSDF_4' if bpy.app.version >= (4,0,0) else 'BSDF_3'])
        elif s.bake_type in CHANNEL_DEFINITIONS: 
            defs.extend(CHANNEL_DEFINITIONS[s.bake_type])
        if s.use_special_map: 
            defs.extend(CHANNEL_DEFINITIONS['MESH'])
            
        d_ids = [d['id'] for d in defs]
        
        # Remove invalid channels
        for i in range(len(s.channels)-1, -1, -1):
            if s.channels[i].id not in d_ids: s.channels.remove(i)
            
        # Add new channels
        ex_ids = {c.id for c in s.channels}
        for d in defs:
            if d['id'] not in ex_ids:
                new = s.channels.add()
                new.id = d['id']
                new.name = d['name']
                if 'defaults' in d:
                    for k, v in d['defaults'].items():
                        try: setattr(new, k, v)
                        except: pass
                        
        # Reorder
        for t_idx, d_id in enumerate(d_ids):
            c_idx = next((i for i, c in enumerate(s.channels) if c.id == d_id), -1)
            if c_idx != -1 and c_idx != t_idx: 
                s.channels.move(c_idx, t_idx)
                
        return {'FINISHED'}

class BAKETOOL_OT_SetSaveLocal(bpy.types.Operator):
    bl_idname="bake.set_save_local"
    bl_label="Local"
    save_location: props.IntProperty(default=0)
    
    def execute(self,context):
        if not bpy.data.filepath: return {'CANCELLED'}
        path = str(Path(bpy.data.filepath).parent) + os.sep
        bj = context.scene.BakeJobs
        if self.save_location==0: bj.jobs[bj.job_index].setting.save_path=path
        elif self.save_location==2: bj.node_bake_save_path=path
        return{'FINISHED'}

class BAKETOOL_OT_RecordObjects(bpy.types.Operator):
    bl_idname="bake.record_objects"
    bl_label="Record"
    objecttype: props.IntProperty(default=0)
    allobjects: props.BoolProperty(default=False)
    
    def invoke(self,context,event): 
        self.allobjects=event.shift
        return self.execute(context)
        
    def execute(self,context):
        if not context.scene.BakeJobs.jobs: return {'CANCELLED'}
        s = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting
        
        if self.objecttype==0:
            s.bake_objects.clear()
            # Logic: Add selected meshes, exclude active if shift not held (logic from original code seems a bit odd but preserved)
            # Original: [o for o in context.selected_objects if o.type=='MESH' and (not self.allobjects or o!=context.active_object)]
            # Wait, original said: (not self.allobjects or o!=context.active_object)
            # If allobjects (Shift) is True: (False or o!=active) -> excludes active?
            # If allobjects (Shift) is False: (True or ...) -> includes all?
            # This seems inverted or I'm misinterpreting intent. 
            # "Shift to exclude active" maybe? 
            # Let's assume original logic was: "If Shift (allobjects=True), exclude active? No, usually Shift means Add."
            # Let's keep strict logic translation.
            
            targets = [o for o in context.selected_objects if o.type=='MESH']
            # if self.allobjects is True, we filter: (False or o!=active). So we KEEP objects that are NOT active. (Exclude active).
            # if self.allobjects is False, we filter: (True or ...). We KEEP all.
            
            if self.allobjects:
                targets = [o for o in targets if o != context.active_object]

            for o in targets:
                s.bake_objects.add().bakeobject = o
                
        elif self.objecttype==1: s.active_object=context.active_object
        elif self.objecttype==2: s.cage_object=context.active_object
        return{'FINISHED'}

class BAKETOOL_OT_BakeSelectedNode(bpy.types.Operator):
    bl_label = "Bake Node"
    bl_idname = "bake.selected_node_bake"
    
    @classmethod
    def poll(cls, context): 
        return context.active_object and context.active_node and context.active_object.active_material
        
    def execute(self, context):
        bj = context.scene.BakeJobs
        mat = context.active_object.active_material
        nt = mat.node_tree
        out = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output), next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'), None))
        
        if not out: return {'CANCELLED'}
        
        sets = {'res_x': bj.node_bake_res_x, 'res_y': bj.node_bake_res_y, 'engine': 'CYCLES', 'samples': bj.node_bake_sample}
        imgs = {'file_format': format_map[bj.node_bake_save_format], 'color_depth': bj.node_bake_color_depth, 'color_mode': bj.node_bake_color_mode, 'quality': bj.node_bake_quality}
        
        with SceneSettingsContext('scene', sets), SceneSettingsContext('image', imgs), SceneSettingsContext('cm', {'view_transform': 'Standard'}):
            for node in [n for n in nt.nodes if n.select]:
                sock = next((s for s in node.outputs if s.is_linked), node.outputs[0])
                img = bpy.data.images.new(f"{mat.name}_{node.name}", bj.node_bake_res_x, bj.node_bake_res_y, alpha=True)
                
                in_node = nt.nodes.new("ShaderNodeTexImage")
                in_node.image = img
                nt.nodes.active = in_node
                
                nt.links.new(sock, out.inputs[0])
                bpy.ops.object.bake(type='EMIT', margin=bj.node_bake_margin)
                
                if bj.node_bake_save_outside: 
                    save_image(img, bj.node_bake_save_path, file_format=bj.node_bake_save_format, reload=bj.node_bake_reload)
                else: 
                    img.pack()
                    
                if bj.node_bake_delete_node: 
                    nt.nodes.remove(in_node)
                    
        return {'FINISHED'}

class BAKETOOL_OT_DeleteResult(bpy.types.Operator):
    bl_idname = "baketool.delete_result"
    bl_label = "Delete"
    def execute(self, context):
        idx = context.scene.baked_image_results_index
        if idx >= 0:
            img = context.scene.baked_image_results[idx].image
            if img: bpy.data.images.remove(img)
            context.scene.baked_image_results.remove(idx)
            context.scene.baked_image_results_index = max(0, idx-1)
        return {'FINISHED'}

class BAKETOOL_OT_DeleteAllResults(bpy.types.Operator):
    bl_idname = "baketool.delete_all_results"
    bl_label = "Delete All"
    def execute(self, context):
        for r in context.scene.baked_image_results:
            if r.image: bpy.data.images.remove(r.image)
        context.scene.baked_image_results.clear()
        context.scene.baked_image_results_index = -1
        return {'FINISHED'}

class BAKETOOL_OT_ExportResult(bpy.types.Operator):
    bl_idname = "baketool.export_result"
    bl_label = "Export"
    filepath: props.StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event):
        self.filepath = context.scene.BakeJobs.bake_result_save_path or "//"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        r = context.scene.baked_image_results[context.scene.baked_image_results_index]
        bj = context.scene.BakeJobs
        if not r.image: return {'CANCELLED'}
        
        imgs = {'file_format': format_map[bj.bake_result_save_format], 'color_depth': bj.bake_result_color_depth, 'color_mode': bj.bake_result_color_mode}
        with SceneSettingsContext('image', imgs), SceneSettingsContext('cm', {'view_transform': 'Standard'}):
            save_image(image=r.image, path=os.path.dirname(self.filepath), file_format=bj.bake_result_save_format)
        return {'FINISHED'}

class BAKETOOL_OT_ExportAllResults(bpy.types.Operator):
    bl_idname = "baketool.export_all_results"
    bl_label = "Export All"
    directory: props.StringProperty(subtype="DIR_PATH")
    
    def invoke(self, context, event):
        self.directory = context.scene.BakeJobs.bake_result_save_path or "//"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        bj = context.scene.BakeJobs
        imgs = {'file_format': format_map[bj.bake_result_save_format], 'color_depth': bj.bake_result_color_depth, 'color_mode': bj.bake_result_color_mode}
        with SceneSettingsContext('image', imgs), SceneSettingsContext('cm', {'view_transform': 'Standard'}):
            for r in context.scene.baked_image_results:
                if r.image: save_image(image=r.image, path=self.directory, file_format=bj.bake_result_save_format)
        return {'FINISHED'}
