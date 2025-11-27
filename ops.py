import bpy
from bpy import props
import mathutils
import bmesh
from .utils import *
from .constants import *

class set_save_local(bpy.types.Operator):
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
        
class record_objects(bpy.types.Operator):
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
        
   
class GenericChannelOperator(bpy.types.Operator):
    """通用通道操作类，用于管理不同类型的集合"""
    bl_idname = "bake.generic_channel_op"
    bl_label = "Channel Operation"
    bl_description = "Perform operations on specified channel collections"

    # 操作类型枚举
    operation: bpy.props.EnumProperty(
        items=[
            ('ADD', "Add", "Add a new item to the collection", 'ADD', 0),
            ('DELETE', "Delete", "Delete the selected item", 'REMOVE', 1),
            ('UP', "Up", "Move the selected item up", 'TRIA_DOWN', 2),
            ('DOWN', "Down", "Move the selected item down", 'TRIA_UP', 3),
            ('CLEAR', "Clear", "Clear all items in the collection", 'BRUSH_DATA', 4),
        ],
        name="Operation",
        description="The operation to perform on the collection"
    )

    # 目标集合名称（字符串）
    target: bpy.props.StringProperty(
        name="Target",
        description="The name of the target collection to operate on",
        default=""
    )

    # 目标属性映射字典
    TARGET_PROPERTIES = {
        "jobs_channel": {
            "collection": lambda context: context.scene.BakeJobs.jobs,
            "index": lambda context: context.scene.BakeJobs.job_index,
            "index_setter": lambda context, value: setattr(context.scene.BakeJobs, "job_index", value)
        },
        "job_custom_channel": {
            "collection": lambda context: context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].Custombakechannels,
            "index": lambda context: context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].Custombakechannels_index,
            "index_setter": lambda context, value: setattr(context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index], "Custombakechannels_index", value)
        },
        "custom_channel": {
            "collection": lambda context: context.scene.BakeJobs.custom_bake_channels,
            "index": lambda context: context.scene.BakeJobs.custom_bake_channels_index,
            "index_setter": lambda context, value: setattr(context.scene.BakeJobs, "custom_bake_channels_index", value)
        }

    }

    @classmethod
    def poll(cls, context):
        """检查操作是否可执行的基本条件"""
        # 只检查场景和 BakeJobs 是否存在，具体目标检查推迟到 execute
        return context.scene is not None and context.scene.BakeJobs is not None

    def execute(self, context):
        """执行通用集合操作"""
        # 检查目标是否有效
        if self.target not in self.TARGET_PROPERTIES:
            return report_error(self, f"Unknown target: {self.target}", status='CANCELLED')

        # 获取目标属性
        props = self.TARGET_PROPERTIES[self.target]
        try:
            collection = props["collection"](context)
            index = props["index"](context)
        except (IndexError, AttributeError):
            return report_error(self, f"Invalid collection or index for target: {self.target}", status='CANCELLED')

        set_index = props["index_setter"]

        # 根据操作类型执行具体逻辑
        if self.operation == 'ADD':
            collection.add()
            collection[len(collection)-1].name=self.target+str(len(collection))
            self.report({'INFO'}, f"Added new item to {self.target}")
        
        elif self.operation == 'DELETE':
            if len(collection) > 0 and 0 <= index < len(collection):
                collection.remove(index)
                set_index(context, min(index, len(collection) - 1))
                self.report({'INFO'}, f"Deleted item at index {index} from {self.target}")
            else:
                return report_error(self, f"Cannot delete: invalid index or empty collection for {self.target}", status='CANCELLED')
        
        elif self.operation == 'UP':
            if len(collection) > 0 and index > 0 and index < len(collection):
                collection.move(index, index - 1)
                set_index(context, index - 1)
                self.report({'INFO'}, f"Moved item up in {self.target}")
            else:
                return report_error(self, f"Cannot move up: invalid index or already at top in {self.target}", status='CANCELLED')
        
        elif self.operation == 'DOWN':
            if len(collection) > 0 and index >= 0 and index < len(collection) - 1:
                collection.move(index, index + 1)
                set_index(context, index + 1)
                self.report({'INFO'}, f"Moved item down in {self.target}")
            else:
                return report_error(self, f"Cannot move down: invalid index or already at bottom in {self.target}", status='CANCELLED')
        
        elif self.operation == 'CLEAR':
            if len(collection) > 0:
                collection.clear()
                set_index(context, -1)
                self.report({'INFO'}, f"Cleared all items in {self.target}")
            else:
                return report_error(self, f"Cannot clear: collection is already empty for {self.target}", status='CANCELLED')
        
        return {'FINISHED'}


class Baketool_bake_operator(bpy.types.Operator):
    bl_label = "bake"
    bl_idname = "bake.bake_operator"
    bl_description="Start baking operator"
    
    """
    Operator for baking textures in Blender with support for multiple types and modes.
    Attributes:
        bl_label (str): Display name of the operator.
        bl_idname (str): Internal identifier of the operator.
        bl_description (str): Short description of the operator.
        objects (list): List of objects to bake.
    Blender烘焙纹理的操作符，支持多种类型和模式。
    属性：
        bl_label (str): 操作符的显示名称。
        bl_idname (str): 操作符的内部标识符。
        bl_description (str): 操作符的简短描述。
        objects (list): 要烘焙的对象列表。
    """
    objects = []
    act = None
    cage = None
    job = None
    setting = None
    UV = ''
    name = ''
    foldername = ''
    nor_obj = 'TANGENT'
    normalx = 'POS_X'
    normaly = 'POS_Y'
    normalz = 'POS_Z'
    start = 0
    end = 0
    framerange = 1
    
    MESH_MAP_CONFIGS = {
        'SHADOW': {'type': 'SHADOW', 'node_setup': None},
        'ENVIRONMENT': {'type': 'ENVIRONMENT', 'node_setup': None},
        'VERTEX': {'type': 'EMIT', 'node_setup': 'vertex'},
        'BEVEL': {'type': 'EMIT', 'node_setup': 'bevel'},
        'AO': {'type': 'EMIT', 'node_setup': 'ao'},
        'UV': {'type': 'EMIT', 'node_setup': 'uv'},
        'WIREFRAME': {'type': 'EMIT', 'node_setup': 'wireframe'},
        'BEVNOR': {'type': 'NORMAL', 'node_setup': 'bevnor'},
        'POSITION': {'type': 'EMIT', 'node_setup': 'position'},
        'SLOPE': {'type': 'EMIT', 'node_setup': 'slope'},
        'THICKNESS': {'type': 'EMIT', 'node_setup': 'thickness'},
        'IDMAT': {'type': 'EMIT', 'node_setup': 'idmat'},
        'SELECT': {'type': 'EMIT', 'node_setup': 'select'},
        'IDELE': {'type': 'EMIT', 'node_setup': 'idele'},
        'IDUVI': {'type': 'EMIT', 'node_setup': 'iduvi'},
        'IDSEAM': {'type': 'EMIT', 'node_setup': 'idseam'}
    }
    
    @classmethod
    def poll(self,context):
        for job in context.scene.BakeJobs.jobs:
            if len(job.setting.bake_objects)>0:
                return True
        if len(context.selected_objects)>0 and context.active_object!=None:
            if context.active_object.type!='MESH':
                return False
            return True
        return False
        
        
    def execute(self,context):
        """
        Execute the baking process for selected objects.
        Args:
            context: Blender context.
        Returns:
            set: Operator status ('FINISHED' or 'CANCELLED').
        执行所选对象的烘焙过程。
        参数:
            context: Blender 上下文。
        返回:
            set: 操作符状态 ('FINISHED' 或 'CANCELLED')。
        """
        logger.info("Starting bake execution")
        
        # Record original settings / 记录原始设置
        original_settings = {
            'scene': manage_scene_settings('scene', getorset=False),
            'image': manage_scene_settings('image', getorset=False),
            'bake': manage_scene_settings('bake', getorset=False)
            }
        logger.debug("Original settings captured")
        for job in context.scene.BakeJobs.jobs:
            self.job=job
            self.setting=job.setting
            setting=self.setting
            logger.info(f"Starting a job: {self.job.name}")
            # Set scene parameters / 设置场景参数
            scene_settings = {
                'res_x': self.setting.res_x,
                'res_y': self.setting.res_y,
                'engine': 'CYCLES',  
                'samples': self.setting.samples if hasattr(self.setting, 'samples') else None
            }
            manage_scene_settings('scene', scene_settings, getorset=True)

            # 设置图像参数
            image_settings = {
                'file_format': format_map[self.setting.save_format],
                'color_depth': self.setting.color_depth,
                'color_mode': 'RGBA' if self.setting.use_alpha else 'RGB',
                'quality': self.setting.quality
            }
            manage_scene_settings('image', image_settings, getorset=True)

            # 设置烘焙参数
            bake_settings = {
                'margin': self.setting.margin,
                'normal_space': 'TANGENT' if not self.setting.normal_obj else 'OBJECT'
            }
            manage_scene_settings('bake', bake_settings, getorset=True)
            
            logger.debug("Job settings applied")
            
            if len(self.setting.bake_objects) > 0:
                # 清空对象列表并将设置中的对象添加到对象列表中
                self.objects.clear()
                for obj in self.setting.bake_objects:
                    self.objects.append(obj.bakeobject)
            else:
                # 如果没有设置中的对象，则使用上下文中的选定对象
                self.objects = context.selected_objects

            # 设置活动对象，如果有设置则使用设置中的对象，否则使用上下文中的活动对象
            self.act = setting.active_object if setting.active_object else context.active_object

            # 设置笼体对象，如果没有设置则为None
            self.cage = setting.cage_object if setting.cage_object else None

            # 根据设置中的normal_type配置法线方向
            if self.setting.normal_type == 'OPENGL' or setting.normal_type == 'DIRECTX':
                self.normalx = 'POS_X'
                self.normaly = 'POS_Y' if setting.normal_type == 'OPENGL' else 'NEG_Y'
                self.normalz = 'POS_Z'
            else:
                self.normalx = setting.normal_X
                self.normaly = setting.normal_Y
                self.normalz = setting.normal_Z

            # 配置帧范围
            if not self.setting.bake_motion_use_custom:
                self.framerange = (context.scene.frame_end - context.scene.frame_start) + 1
                self.start = context.scene.frame_start
                self.end = context.scene.frame_end
            else:
                self.framerange = setting.bake_motion_last
                self.start = setting.bake_motion_start
                self.end = setting.bake_motion_start + setting.bake_motion_last

            # 根据设置中的normal_obj确定法线对象类型
            self.nor_obj = 'TANGENT' if not setting.normal_obj else 'OBJECT'
        
            # 在 execute 方法中动态生成通道配置
            imagemap_BSDF = get_imagemaps(self.setting, 'BSDF')
            imagemap_basic = get_imagemaps(self.setting, 'BASIC')
            imagemap_mutires = get_imagemaps(self.setting, 'MULTIRES')
            imagemap_mesh = get_imagemaps(self.setting, 'MESH')
            #用于检测用户的一些不当操作//Used to detect some improper user operations
            
            if self.setting.special_bake_method!="AUTOATLAS":
                if self.setting.special_bake_method!='VERTEXCOLOR':
                    if self.setting.bake_type=='BSDF' and self.setting.bake_mode=='SELECT_ACTIVE':
                        return report_error(self, "Please select baking mode")
                else:
                    if self.setting.bake_type=='BASIC' and (self.setting.bake_mode=='COMBINE_OBJECT' or self.setting.bake_mode=='SPILT_MATERIAL'):
                        return report_error(self, "Please select baking mode")
                    if self.setting.bake_type=='MULTIRES':
                        return report_error(self, "Please check option")
            else:
                if self.setting.bake_type=='MULTIRES':
                    return report_error(self, "Please check option")
            if self.setting.bake_texture_apply==True:
                t=False
                for map in imagemap_BSDF:
                    if map['enabled']==True:
                        t=True
                if t==False and self.setting.bake_type=='BSDF':
                    return report_error(self, "No apply material")
            
            has_BSDF=False
            #检查材质中是否有输出和 BSDF 节点//Check if the material has an output and BSDF node
            if self.setting.bake_type=='BSDF' or (self.setting.bake_type=='BASIC' and self.setting.bake_mode!='SELECT_ACTIVE'):
                for obj in self.objects:
                    for matslot in obj.material_slots:
                        has_output=False
                        for node in matslot.material.node_tree.nodes:
                            if node.bl_idname=='ShaderNodeOutputMaterial' and node.is_active_output==True:
                                has_output=True
                                break
                        if has_output==False:
                            return report_error(self, "No output found in material")
            
            elif self.setting.bake_type=='BASIC' and self.setting.bake_mode=='SELECT_ACTIVE':
                for matslot in self.act.material_slots:
                    has_output=False
                    for node in matslot.material.node_tree.nodes:
                        if node.bl_idname=='ShaderNodeOutputMaterial' and node.is_active_output==True:
                            has_output=True
                            break
                    if has_output==False:
                        return report_error(self, "No output found in material")
            #检查 BSDF 节点//Check BSDF node
            for matslot in self.act.material_slots:
                for node in matslot.material.node_tree.nodes:
                    if node.bl_idname=='ShaderNodeOutputMaterial' and node.is_active_output==True:
                        if len(node.inputs[0].links)>0:
                            if node.inputs[0].links[0].from_node.bl_idname=='ShaderNodeBsdfPrincipled':
                                has_BSDF=True
                                break
            #检查 BSDF 节点//Check BSDF node
            if has_BSDF==False and self.setting.bake_type=='BSDF' and self.setting.use_special_map==False:
                return report_error(self, "No valid BSDF node")
            #检查 UV 情况//Check UV status
            if self.setting.special_bake_method!='VERTEXCOLOR' and self.setting.special_bake_method!='AUTOATLAS':
                if self.setting.bake_mode!='SELECT_ACTIVE':
                    for obj in self.objects:
                        if len(obj.data.uv_layers)==0:
                            return report_error(self, "No UV, add UV to bake")
                else:
                    if len(self.act.data.uv_layers)==0:
                        return report_error(self, "No UV, add UV to bake")
            #有非网格物体时报告错误，物体缺少材质时报告错误//Report an error if there is a non-mesh object, or if an object lacks materials
            for obj in self.objects:
                obj.hide_render=False
                if obj.type!='MESH' and self.setting.bake_type!='SELECT_ACTIVE':
                    return report_error(self, "There is an object type that is not a mesh")
                if len(obj.data.materials)==0 and (self.setting.bake_mode!='SELECT_ACTIVE'):
                    return report_error(self, "No available materials")
                    
            if self.setting.bake_type=='BASIC' and self.setting.bake_mode=='SELECT_ACTIVE' and len(self.act.data.materials)==0:
                return report_error(self, "No available materials")
                
            if (self.setting.save_out==True and len(self.setting.save_path)<1) or (self.setting.use_custom_map==True and len(self.setting.custom_file_path)<1):
                return report_error(self, "Please set a save location")
                
            if (self.setting.bake_type=='BASIC' and self.setting.combine) and not ((self.setting.com_dir or self.setting.com_ind) and (self.setting.com_diff or self.setting.com_tran or self.setting.com_gloss) or self.setting.com_emi):
                return report_error(self, 'When doing combine baking, it is necessary to select emission, or at least select one of indirect, direct, and one of diffuse gloss or projection')
                
            if (self.setting.bake_type=='BASIC' and self.setting.diff) and not (self.setting.diff_dir or self.setting.diff_ind or self.setting.diff_col):
                return report_error(self, 'When doing diffuse baking, it is necessary to select one of direct, indirect, or color')
                
            if (self.setting.bake_type=='BASIC' and self.setting.gloss) and not (self.setting.gloss_dir or self.setting.gloss_ind or self.setting.gloss_col):
                return report_error(self, 'When doing diffuse baking, it is necessary to select one of direct, indirect, or color')
                
            #其他//Others
            if len(bpy.data.filepath)==0 and self.setting.save_and_quit:
                return report_error(self, "File not save")
                
            #检查完毕//Inspection completed
            
            #替换原有分支调用//Replace the original branch calls
            if setting.special_bake_method == 'AUTOATLAS':
                self.bake_objects(context, imagemap_BSDF if setting.bake_type == 'BSDF' else imagemap_basic, imagemap_mesh)
            elif setting.special_bake_method == 'VERTEXCOLOR':
                self.bake_objects(context, imagemap_BSDF if setting.bake_type == 'BSDF' else imagemap_basic, imagemap_mesh)
            else:
                if setting.bake_type == 'BSDF':
                    self.bake_objects(context, imagemap_BSDF, imagemap_mesh)
                elif setting.bake_type == 'BASIC':
                    self.bake_objects(context, imagemap_basic, imagemap_mesh)
                elif setting.bake_type == 'MULTIRES':
                    self.bake_objects(context, imagemap_mutires, imagemap_mesh)
            logger.info(f"Ending a job: {self.job.name}")
        if self.setting.save_and_quit:
            bpy.ops.wm.save_mainfile(exit=True)
        #恢复原始设置//Restore original settings
        for category, settings in original_settings.items():
            manage_scene_settings(category, settings, getorset=True)
            
        logger.info("Baking task completed successfully")
        self.report({'INFO'}, "Baking task completed")
        return {'FINISHED'}
        
    def bake_objects(self, context, imagemap, imagemap_mesh):
        """通用烘焙方法，根据模式处理对象并执行烘焙。
        
        Args:
            context: Blender 上下文。
            imagemap: 主贴图配置列表。
            imagemap_mesh: 网格贴图配置列表。
        """
        setting = self.setting
        objects = self.objects
        act = self.act

        #处理特殊方法：Auto Atlas 的 UV 设置//Handle special method: UV settings for Auto Atlas
        if setting.special_bake_method == 'AUTOATLAS':
            self.setup_auto_atlas(objects, act)

        #根据烘焙模式确定目标对象和名称//Determine target objects and names based on bake mode
        if setting.bake_mode == 'SINGLE_OBJECT' or setting.special_bake_method == 'VERTEXCOLOR':
            for obj in objects:
                set_active_and_selected(obj, objects)
                name = self.set_name(obj, setting.name_setting)
                self.process_bake([obj], name, imagemap, imagemap_mesh, spematerial=None)
        elif setting.bake_mode == 'COMBINE_OBJECT':
            name = self.set_name(act, setting.name_setting)
            self.process_bake(objects, name, imagemap, imagemap_mesh)
        elif setting.bake_mode == 'SELECT_ACTIVE':
            name = self.set_name(act, setting.name_setting)
            target_objs = [act] if setting.bake_type == 'BASIC' else objects
            activebake_obj = act if setting.bake_type == 'BSDF' else None
            self.process_bake(target_objs, name, imagemap, imagemap_mesh, activebake_object=activebake_obj)
        elif setting.bake_mode == 'SPILT_MATERIAL':
            for obj in objects:
                for matslot in obj.material_slots:
                    set_active_and_selected(obj, objects)
                    name = self.set_name(obj, setting.name_setting, material=matslot.material)
                    self.process_bake([obj], name, imagemap, imagemap_mesh, spematerial=matslot.material)
        elif setting.bake_type == 'MULTIRES':
            self.adjust_multires(context)
            if setting.bake_mode == 'SINGLE_OBJECT':
                for obj in objects:
                    set_active_and_selected(obj, objects)
                    name = self.set_name(obj, setting.name_setting)
                    self.process_bake([obj], name, imagemap, imagemap_mesh)
            elif setting.bake_mode == 'COMBINE_OBJECT':
                name = self.set_name(act, setting.name_setting)
                self.process_bake(objects, name, imagemap, imagemap_mesh)

    def setup_auto_atlas(self, objects, act):
        """设置 Auto Atlas 的 UV 层。"""
        bpy.ops.object.mode_set(mode='OBJECT')
        ori_UV = [obj.data.uv_layers.active for obj in objects]
        for obj in objects:
            for ver in obj.data.vertices:
                ver.select = True
            UVblock = obj.data.uv_layers.get('altas_bake_UV') or obj.data.uv_layers.new(name='altas_bake_UV')
            obj.data.uv_layers.active = UVblock
            if bpy.app.version >= (3, 5, 0):
                for uvloop in UVblock.vertex_selection:
                    uvloop.value = True
            else:
                for uvloop in UVblock.data:
                    uvloop.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        if self.setting.altas_pack_method == 'REPACK':
            bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=self.setting.altas_margin)
        else:
            bpy.context.area.type = 'IMAGE_EDITOR'
            bpy.context.area.ui_type = 'UV'
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin=self.setting.altas_margin)
            bpy.context.area.type = 'VIEW_3D'
        self.UV = 'altas_bake_UV'
        bpy.ops.object.mode_set(mode=act.mode)
        for i, obj in enumerate(objects):
            obj.data.uv_layers.active = ori_UV[i]

    def adjust_multires(self, context):
        """调整 MULTIRES 级别。"""
        for obj in context.selected_objects:
            for mod in obj.modifiers:
                if mod.type == 'MULTIRES':
                    mod.levels = self.setting.mutlires_divide
                    break

    def process_bake(self, target_objs, name, imagemap, imagemap_mesh, spematerial=None, activebake_object=None):
        """执行烘焙并处理额外功能。"""
        setting = self.setting
        imagemap = self.add_basic_image_and_bake_base(
            objects=target_objs, imagemap=imagemap, name=name, 
            spematerial=spematerial, activebake_object=activebake_object
        )
        if setting.bake_type != 'MULTIRES':
            if setting.use_special_map:
                imagemap_mesh = self.bake_mesh_map(target_objs, name, imagemap_mesh, spematerial)
            if setting.use_custom_map and setting.special_bake_method != 'VERTEXCOLOR' and not setting.bake_motion:
                self.bake_custom_channel(imagemap=imagemap, name=name, meshimagemap=imagemap_mesh, obj=target_objs[0])
            if setting.bake_texture_apply and setting.bake_type == 'BSDF' and not setting.bake_motion and setting.special_bake_method != 'VERTEXCOLOR' and not setting.bake_mode=='SPILT_MATERIAL':
                for obj in target_objs:
                    self.apply_bake(imagemap=imagemap, obj=obj)
        for map in imagemap:
            map['image'] = None  # 重置图像引用，避免内存占用
            
    #添加通道和图片，准备开始烘焙//Add channels and images, prepare to start baking
    def add_basic_image_and_bake_base(self,objects,imagemap,name='',spematerial=None,activebake_object=None,multires=False):
        
        mat_collection = []
        for obj in objects:
            obj.hide_render = False
            folder_name = self.set_name(obj, self.setting.name_setting, spematerial) if self.setting.create_new_folder else ''
            for matslot in obj.material_slots:
                mat_collection.append(create_matinfo(matslot.material, spematerial))
                matslot.material.node_tree.nodes.active = None

        for map in imagemap:
            
            if map['enabled']:
                mapname = map['prefix'] + name + map['suffix']
                logger.debug(f"Processing map: {map['type']},map name: {mapname}")
                if self.setting.special_bake_method == 'VERTEXCOLOR':
                    for obj in objects:
                        vc = obj.data.attributes.new(mapname, 'FLOAT_COLOR' if self.setting.float32 else 'BYTE_COLOR', 'POINT')
                        obj.data.attributes.active_color = vc
                        logger.debug(f"Created vertex color'{map['image'].name}' for {map['type']}")
                else:
                    colorspace = map['custom_cs'] if self.setting.colorspace_setting else map['default_cs']
                    if self.setting.float32:
                        colorspace = 'Linear'  # Assuming 'linear' is defined elsewhere as 'Linear'
                    ncol = (colorspace == 'Non-Color')
                    save_out = self.setting.save_out or self.setting.bake_motion
                    motion = self.setting.bake_motion
                    mode = 'RGBA' if self.setting.use_alpha else map['color_mode']
                    map['image'] = set_image(
                        mapname, self.setting.res_x, self.setting.res_y, alpha=self.setting.use_alpha,
                        full=self.setting.float32, space=colorspace, ncol=ncol, fake_user=self.setting.use_fake_user,
                        clear=self.setting.clearimage, basiccolor=self.setting.colorbase
                    )
                    logger.debug(f"Created image '{map['image'].name}' for {map['type']}")
                if self.setting.bake_type == 'BSDF':
                    for matinfo in mat_collection:
                        if matinfo['bsdf_node'] and not matinfo['is_not_special']:
                            if self.setting.special_bake_method != 'VERTEXCOLOR':
                                matinfo['bake_image_node'] = matinfo['material'].node_tree.nodes.new("ShaderNodeTexImage")
                                matinfo['bake_image_node'].image = map['image']
                                matinfo['material'].node_tree.nodes.active = matinfo['bake_image_node']

                            if map['type'] != 'NORMAL' and matinfo['bsdf_node'].inputs.get(map['node_name']) and matinfo['bsdf_node'].inputs.get(map['node_name']).links:
                                from_socket = matinfo['bsdf_node'].inputs.get(map['node_name']).links[0].from_socket
                                if map['type'] in ('SUBFACECOL', 'EMI', 'COLOR'):
                                    matinfo['material'].node_tree.links.new(from_socket, matinfo['output_node'].inputs[0])
                                else:
                                    bw = matinfo['material'].node_tree.nodes.new('ShaderNodeRGBToBW')
                                    matinfo['extra_nodes'].append(bw)
                                    matinfo['material'].node_tree.links.new(from_socket, bw.inputs[0])
                                    if map['type'] == 'ROUGH' and self.setting.rough_inv:
                                        inv = matinfo['material'].node_tree.nodes.new('ShaderNodeInvert')
                                        matinfo['extra_nodes'].append(inv)
                                        matinfo['material'].node_tree.links.new(bw.outputs[0], inv.inputs[1])
                                        matinfo['material'].node_tree.links.new(inv.outputs[0], matinfo['output_node'].inputs[0])
                                    else:
                                        matinfo['material'].node_tree.links.new(bw.outputs[0], matinfo['output_node'].inputs[0])
                            elif map['type'] != 'NORMAL' and not matinfo['bsdf_node'].inputs.get(map['node_name']).links:
                                matinfo['temp_image'] = bpy.data.images.new('for place', 32, 32)
                                matinfo['temp_image_node'] = matinfo['material'].node_tree.nodes.new("ShaderNodeTexImage")
                                matinfo['temp_image_node'].image = matinfo['temp_image']
                                if matinfo['bsdf_node'].inputs.get(map['node_name']).type == 'RGBA':
                                    matinfo['temp_image'].generated_color = matinfo['bsdf_node'].inputs.get(map['node_name']).default_value
                                else:
                                    v = matinfo['bsdf_node'].inputs.get(map['node_name']).default_value
                                    matinfo['temp_image'].generated_color = (v, v, v, 1)
                                matinfo['material'].node_tree.links.new(matinfo['temp_image_node'].outputs[0], matinfo['output_node'].inputs[0])
                        elif self.setting.special_bake_method != 'VERTEXCOLOR':
                            matinfo['temp_image'] = bpy.data.images.new('for place', 32, 32)
                            matinfo['temp_image_node'] = matinfo['material'].node_tree.nodes.new("ShaderNodeTexImage")
                            matinfo['temp_image_node'].image = matinfo['temp_image']
                            matinfo['material'].node_tree.nodes.active = matinfo['temp_image_node']

                    if self.setting.special_bake_method == 'VERTEXCOLOR':
                        self.bake(map=map, vertex=True)
                    else:
                        if motion:
                            bpy.context.scene.frame_current = self.start
                            for i in range(self.framerange):
                                index = i + self.setting.bake_motion_startindex
                                self.bake(map=map, clear=self.setting.clearimage)
                                save_image(
                                    image=map['image'],
                                    path=self.setting.save_path,
                                    folder=self.setting.create_new_folder,
                                    folder_name=folder_name,
                                    file_format=self.setting.save_format,
                                    color_depth=self.setting.color_depth,
                                    color_mode=mode,
                                    quality=self.setting.quality,
                                    motion=motion,
                                    frame=index,
                                    exr_codec=self.setting.exr_code,
                                    color_space=colorspace,
                                    reload=self.setting.reload,
                                    fillnum=self.setting.bake_motion_digit,
                                    denoise=self.setting.use_denoise,
                                    denoise_method=self.setting.denoise_method,
                                    save=save_out
                                )
                                bpy.context.scene.frame_current += 1
                            bpy.data.images.remove(map['image'])
                        else:
                            self.bake(map=map, clear=self.setting.clearimage)
                            save_image(
                                image=map['image'],
                                path=self.setting.save_path,
                                folder=self.setting.create_new_folder,
                                folder_name=folder_name,
                                file_format=self.setting.save_format,
                                color_depth=self.setting.color_depth,
                                color_mode=mode,
                                quality=self.setting.quality,
                                exr_codec=self.setting.exr_code,
                                color_space=colorspace,
                                reload=self.setting.reload,
                                denoise=self.setting.use_denoise,
                                denoise_method=self.setting.denoise_method,
                                save=save_out
                            )
                            # 添加烘焙结果到集合属性
                            self.write_result(map)
                        logger.debug(f"Saved image '{map['image'].name}' to {os.path.join(self.setting.save_path, folder_name)}")
                    if map['type'] != 'NORMAL':
                        for matinfo in mat_collection:
                            if matinfo['bsdf_node']:
                                matinfo['material'].node_tree.links.new(matinfo['bsdf_node'].outputs[0], matinfo['output_node'].inputs[0])

                    for matinfo in mat_collection:
                        if matinfo['bake_image_node']:
                            matinfo['material'].node_tree.nodes.remove(matinfo['bake_image_node'])
                            matinfo['bake_image_node'] = None
                        if matinfo['temp_image']:
                            bpy.data.images.remove(matinfo['temp_image'])
                            matinfo['temp_image'] = None
                        if matinfo['temp_image_node']:
                            matinfo['material'].node_tree.nodes.remove(matinfo['temp_image_node'])
                            matinfo['temp_image_node'] = None
                        for node in matinfo['extra_nodes']:
                            matinfo['material'].node_tree.nodes.remove(node)
                        matinfo['extra_nodes'].clear()
                    
        return imagemap
        
    def bake(self, map, clear=True, vertex=False, motion=False):
        """准备并执行贴图或顶点色的烘焙。
            map (list/tuple): 贴图信息，map['type'] 为类型，map['node_name'] 为具体烘焙类型。
            clear (bool): 是否清除目标，默认 True。
            vertex (bool): 是否烘焙顶点色，默认 False。
            motion (bool): 未使用参数，保留兼容性。
        """
        #Cage 设置//Cage settings
        cage = self.setting.cage_object is not None
        cagename = self.setting.cage_object.name if cage else ''

        #贴图类型与过滤器映射//Map type and filter mapping
        filter_map = {
            'DIFF': {'DIRECT': self.setting.diff_dir, 'INDIRECT': self.setting.diff_ind, 'COLOR': self.setting.diff_col},
            'GLOSSY': {'DIRECT': self.setting.gloss_dir, 'INDIRECT': self.setting.gloss_ind, 'COLOR': self.setting.gloss_col},
            'TRANB': {'DIRECT': self.setting.tranb_dir, 'INDIRECT': self.setting.tranb_ind, 'COLOR': self.setting.tranb_col},
            'COM': {
                'DIFFUSE': self.setting.com_diff, 'EMIT': self.setting.com_emi, 'GLOSSY': self.setting.com_gloss,
                'TRANSMISSION': self.setting.com_tran, 'DIRECT': self.setting.com_dir, 'INDIRECT': self.setting.com_ind
            }
        }

        #计算 Pass Filter//Calculate Pass Filter
        pf = {key for key, value in filter_map.get(map['type'], {'COLOR': True}).items() if value} if map['type'] in filter_map else {'COLOR'}

        #MULTIRES 特殊处理//Special handling for MULTIRES
        if not vertex and self.setting.bake_type == 'MULTIRES':
            scene = bpy.context.scene.render
            original_type, original_multires = scene.bake_type, scene.use_bake_multires
            scene.bake_type, scene.use_bake_multires = map['node_name'], True
            bpy.ops.object.bake_image()
            scene.bake_type, scene.use_bake_multires = original_type, original_multires
            return

        #通用烘焙参数//General bake parameters
        params = {
        'type': 'NORMAL' if map['type'] == 'NORMAL' else ('EMIT' if self.setting.bake_type == 'BSDF' else map['node_name']),
        'pass_filter': pf,
        'margin': self.setting.margin,
        'normal_r': self.normalx,
        'normal_g': self.normaly,
        'normal_b': self.normalz,
        'normal_space': self.nor_obj,
        'use_clear': clear,
        'target': 'VERTEX_COLORS' if vertex else 'IMAGE_TEXTURES'
        }

        #BSDF 或 SELECT_ACTIVE 特定参数//Specific parameters for BSDF or SELECT_ACTIVE
        if self.setting.bake_type == 'BSDF' and map['type'] != "NORMAL":
            params['save_mode'] = 'INTERNAL'
        elif not vertex and self.setting.bake_mode == 'SELECT_ACTIVE':
            params.update({
                'use_selected_to_active': True,
                'use_cage': cage,
                'cage_object': cagename,
                'cage_extrusion': self.setting.extrusion,
                'max_ray_distance': self.setting.ray_distance,
                'save_mode': 'INTERNAL'
            })

        #UV 参数仅用于贴图//UV parameters are only used for textures
        if not vertex:
            params['uv_layer'] = self.UV

        bpy.ops.object.bake(**params)
        
        
    def set_name(self,obj,method,material=None):
        if material==None:
            if self.setting.name_setting=='OBJECT':
                name=obj.name
            elif self.setting.name_setting=='MAT':
                name=obj.active_material.name
            elif self.setting.name_setting=='OBJ_MAT':
                name=obj.name+'_'+obj.active_material.name
            else:
                name=self.setting.custom_name
        else:
            if self.setting.name_setting=='OBJECT':
                name=obj.name
            elif self.setting.name_setting=='MAT':
                name=material.name
            elif self.setting.name_setting=='OBJ_MAT':
                name=obj.name+'_'+material.name
            else:
                name=self.setting.custom_name
        return name
    
    #烘焙自定义通道的方法（贴图集，名字，特殊贴图集（可选））//Method to bake custom channels (texture set, name, special texture set (optional))
    
    def bake_custom_channel(self, imagemap, name, meshimagemap=None, obj=None):
        """烘焙自定义通道到图像文件。
        
        Args:
            imagemap (list): 贴图映射列表。
            meshimagemap (list, optional): 网格贴图映射列表。
            name (str): 基础文件名。
            obj (Object, optional): 用于文件夹命名的对象。
        """
        #合并通道映射//Merge channel mappings
        channel_map = {map['type']: map['image'] for map in imagemap}
        if meshimagemap:
            channel_map.update({map['type']: map['image'] for map in meshimagemap})

        #相机设置//Camera settings
        scene = bpy.context.scene
        has_cam = scene.camera is not None
        if not has_cam:
            camera = bpy.data.cameras.new('tem cam')
            cam_obj = bpy.data.objects.new('tem cam', camera)
            scene.collection.objects.link(cam_obj)
            scene.camera = cam_obj

        #节点设置//Node settings
        scene.use_nodes = True
        nodes = scene.node_tree.nodes
        res = next((n for n in nodes if n.bl_idname == 'CompositorNodeComposite'), None) or nodes.new("CompositorNodeComposite")
        nodes.active = res
        source = res.inputs[0].links[0].from_socket if res.inputs[0].links else None

        #通道和版本映射//Channel and version mapping
        version_map = {
            'BSDF': ('r_map_BSDF3', 'g_map_BSDF3', 'b_map_BSDF3', 'a_map_BSDF3', 'bw_map_BSDF3') if bpy.app.version < (4, 0, 0) else
                    ('r_map_BSDF4', 'g_map_BSDF4', 'b_map_BSDF4', 'a_map_BSDF4', 'bw_map_BSDF4'),
            'BASIC': ('r_map_basic', 'g_map_basic', 'b_map_basic', 'a_map_basic', 'bw_map_basic')
        }
        bake_type = self.setting.bake_type
        r_map, g_map, b_map, a_map, bw_map = version_map.get(bake_type, version_map['BSDF'])

        #保存场景设置并应用分辨率//Save scene settings and apply resolution
        scene_setting = manage_scene_settings(category='scene')
        
        scene.render.resolution_x, scene.render.resolution_y = self.job.setting.res_x, self.job.setting.res_y

        for map in self.job.Custombakechannels:
            #文件路径配置//File path configuration
            file_extension = '.' + map.save_format.lower()
            custom_name = name
            if self.setting.custom_new_folder and obj:
                folder_settings = {
                    'OBJECT': obj.name,
                    'MAT': obj.active_material.name,
                    'OBJ_MAT': f"{obj.name}_{obj.active_material.name}",
                    'CUSTOM': self.setting.custom_folder_name
                }
                custom_folder_name = folder_settings.get(self.setting.custom_folder_name_setting, '')
                filepath = f"{self.setting.custom_file_path}{custom_folder_name}\\{map.prefix}{custom_name}{map.suffix}{file_extension}"
            else:
                filepath = f"{self.setting.custom_file_path}{map.prefix}{custom_name}{map.suffix}{file_extension}"
            scene.render.filepath = filepath

            # 图像设置
            image_settings = {
                'file_format': format_map[map.save_format],
                'color_depth': map.color_depth,
                'color_mode': map.color_mode,
                'quality': map.quality,
                'compression': (100-map.quality),
                'exr_codec': map.exr_code,
            }
            manage_scene_settings('image', image_settings, getorset=True)

            #通道配置 [使用通道, 贴图, 分离颜色, 颜色通道, 反转, 默认值]//Channel configuration [use channel, texture, separate color, color channel, invert, default value]
            channels = [
                [map.r_usemap, channel_map[map.__getattribute__(r_map)], map.r_sepcol, map.r_colchan, map.r_invert, map.r],
                [map.g_usemap, channel_map[map.__getattribute__(g_map)], map.g_sepcol, map.g_colchan, map.g_invert, map.g],
                [map.b_usemap, channel_map[map.__getattribute__(b_map)], map.b_sepcol, map.b_colchan, map.b_invert, map.b],
                [map.a_usemap, channel_map[map.__getattribute__(a_map)], map.a_sepcol, map.a_colchan, map.a_invert, map.a],
                [None, channel_map[map.__getattribute__(bw_map)], map.bw_sepcol, map.bw_colchan, map.bw_invert, map.bw]
            ]

            #节点处理//Node processing
            nodeset = []
            links = scene.node_tree.links
            if not map.bw:  # RGBA 模式
                com = nodes.new("CompositorNodeCombineColor")
                nodeset.append(com)
                for i, (use, img, sep, col, inv, default) in enumerate(channels[:4]):
                    if use and img:
                        out = self._process_channel(nodes, links, nodeset, img, sep, col, inv)
                        links.new(out, com.inputs[i])
                    else:
                        com.inputs[i].default_value = default
                output = com.outputs[0]
            else:  # BW 模式
                use, img, sep, col, inv, default = channels[4]
                imagenode = nodes.new("CompositorNodeImage")
                imagenode.image = img
                nodeset.append(imagenode)
                output = self._process_channel(nodes, links, nodeset, img, sep, col, inv)

            #颜色空间转换//Color space conversion
            is_linear = map.color_space != 'SRGB' and map.save_format not in ('EXR', 'HDR')
            if is_linear:
                convert = nodes.new("CompositorNodeConvertColorSpace")
                convert.from_color_space, convert.to_color_space = 'sRGB', 'Linear'
                nodeset.append(convert)
                links.new(output, convert.inputs[0])
                links.new(convert.outputs[0], res.inputs[0])
            else:
                links.new(output, res.inputs[0])

            #渲染并加载图像//Render and load image
            bpy.ops.render.render(write_still=True)
            load_image = bpy.data.images.load(filepath=filepath, check_existing=False)
            load_image.colorspace_settings.name = color_space_map[map.color_space]

            #清理节点//Clean up nodes
            for node in nodeset:
                nodes.remove(node)

        #恢复原始状态//Restore original state
        if source:
            links.new(source, res.inputs[0])
        if not has_cam:
            bpy.data.objects.remove(cam_obj)
            bpy.data.cameras.remove(camera)
        manage_scene_settings('scene', scene_setting, getorset=True)
        manage_scene_settings('image', scene_setting, getorset=True)
        

    def _process_channel(self, nodes, links, nodeset, img, sep, col, inv):
        """处理单个通道的节点逻辑。
        
        Args:
            nodes: 节点树。
            links: 链接管理器。
            nodeset (list): 待清理的节点列表。
            img: 通道图像。
            sep (bool): 是否分离颜色。
            col (str): 颜色通道（R/G/B/A）。
            inv (bool): 是否反转。
        Returns:
            Socket: 输出插口。
        """
        imagenode = nodes.new("CompositorNodeImage")
        imagenode.image = img
        nodeset.append(imagenode)
        out = imagenode.outputs[0]

        if sep:
            sepnode = nodes.new("CompositorNodeSeparateColor")
            nodeset.append(sepnode)
            links.new(out, sepnode.inputs[0])
            out = sepnode.outputs[['R', 'G', 'B', 'A'].index(col)]

        if inv:
            invert = nodes.new("CompositorNodeInvert")
            nodeset.append(invert)
            links.new(out, invert.inputs[1])
            out = invert.outputs[0]

        return out
        
    def apply_bake(self, imagemap, obj):  # 对于单个物体的应用烘焙的方法
        """
        Apply baked texture maps to a duplicated object by creating a new material.
        This method duplicates the input object, creates a new material with a Principled BSDF shader, and connects
        baked texture maps from the imagemap list to the appropriate BSDF inputs. It handles special cases like
        normal maps and roughness inversion, and organizes the resulting object in a 'bake' collection.
        Principle (原理):
            - Creates a copy of the object and its mesh to avoid modifying the original.
            - Constructs a new material with a node tree, linking baked images to BSDF inputs based on their type.
            - For normal maps, adds a Normal Map node with optional swizzling based on self.normalx/y/z settings.
            - Adjusts node positions for visual clarity in the node editor.
        Args:
            self: The instance of the operator class (e.g., Baketool_bake_operator), providing settings like normalx/y/z.
            imagemap (list): A list of dictionaries containing baked texture map info (type, image, node_name, etc.).
            obj (bpy.types.Object): The Blender object to apply the bake to.
        Returns:
            None
        将烘焙的纹理贴图应用于复制的对象，通过创建新材质实现。
        此方法复制输入对象，创建一个带有 Principled BSDF 着色器的新材质，并将 imagemap 列表中的烘焙纹理贴图连接到相应的 BSDF 输入。它处理特殊情况，如法线贴图和粗糙度反转，并将结果对象组织到 'bake' 集合中。
        原理:
            - 复制对象及其网格以避免修改原始对象。
            - 构建一个带有节点树的新材质，根据贴图类型将烘焙图像链接到 BSDF 输入。
            - 对于法线贴图，添加 Normal Map 节点，并根据 self.normalx/y/z 设置可选通道调整。
            - 调整节点位置以在节点编辑器中实现视觉清晰。
        参数:
            self: 操作符类实例（例如 Baketool_bake_operator），提供 normalx/y/z 等设置。
            imagemap (list): 包含烘焙纹理贴图信息的字典列表（type, image, node_name 等）。
            obj (bpy.types.Object): 要应用烘焙的 Blender 对象。
        返回:
            None
        """
        new_obj = obj.copy()  # 复制原始对象
        new_obj.name = obj.name + "_bake"  # 为新对象命名，添加 "_bake" 后缀
        if bpy.data.collections.get('bake') == None:
            coll = bpy.data.collections.new('bake')  # 如果 'bake' 集合不存在，则创建
        else:
            coll = bpy.data.collections.get('bake')  # 否则获取现有 'bake' 集合
        coll.objects.link(new_obj)  # 将新对象链接到 'bake' 集合
        mesh = obj.data.copy()  # 复制原始对象的网格数据
        mesh.name = new_obj.name  # 为新网格命名，与新对象一致
        
        new_obj.data = mesh  # 将新网格绑定到新对象
        new_mat = bpy.data.materials.new(obj.name + "_bake")  # 创建新材质，命名与对象一致
        new_mat.use_nodes = True  # 启用节点树
        new_mat.blend_method = 'HASHED'  # 设置混合模式为 'HASHED'
        
        BSDF = new_mat.node_tree.nodes.get("Principled BSDF")  # 获取 Principled BSDF 节点
        
        index = 0  # 用于跟踪非法线贴图的索引，调整节点位置
        for map in imagemap:
            if map['image'] is not None and map['type'] != 'NORMAL':
                index += 1  # 递增索引以垂直排列节点
                outsocket = BSDF.inputs.get(map['node_name'])  # 获取 BSDF 的目标输入插口
                imagenode = new_mat.node_tree.nodes.new("ShaderNodeTexImage")  # 创建图像纹理节点
                imagenode.image = map['image']  # 将烘焙图像绑定到节点
                imagenode.location[0] -= 400  # 设置节点水平位置，向左偏移
                imagenode.location[1] += 1250 - (index * 300)  # 设置节点垂直位置，从上向下排列
                
                insocket = imagenode.outputs[0]  # 获取图像节点的输出插口
                if map['type'] == 'ROUGH' and self.setting.rough_inv == True:
                    inv1 = new_mat.node_tree.nodes.new("ShaderNodeInvert")  # 创建反转节点用于粗糙度
                    inv1.location = imagenode.location  # 初始位置与图像节点相同
                    imagenode.location[0] -= 300  # 将图像节点向左再偏移以容纳反转节点
                    new_mat.node_tree.links.new(insocket, inv1.inputs[1])  # 连接图像输出到反转输入
                    new_mat.node_tree.links.new(inv1.outputs[0], outsocket)  # 连接反转输出到 BSDF 输入
                else:
                    new_mat.node_tree.links.new(insocket, outsocket)  # 直接连接图像输出到 BSDF 输入
                    
            if map['image'] != None and map['type'] == 'NORMAL':
                outsocket = BSDF.inputs.get(map['node_name'])  # 获取 BSDF 的法线输入插口
                
                norimagenode = new_mat.node_tree.nodes.new("ShaderNodeTexImage")  # 创建法线图像节点
                norimagenode.image = map['image']  # 绑定法线贴图
                normalnode = new_mat.node_tree.nodes.new("ShaderNodeNormalMap")  # 创建法线贴图节点
                norimagenode.location[0] -= 450  # 设置法线图像节点水平位置
                normalnode.location[0] -= 200  # 设置法线贴图节点水平位置
                
                if self.normalx != 'POS_X' or self.normaly != 'POS_Y' or self.normalz != 'POS_Z':
                    itemlist = ['POS_X', 'POS_Y', 'POS_Z', 'NEG_X', 'NEG_Y', 'NEG_Z']  # 定义可能的法线方向
                    spe = new_mat.node_tree.nodes.new("ShaderNodeSeparateColor")  # 创建分离颜色节点
                    com = new_mat.node_tree.nodes.new("ShaderNodeCombineColor")  # 创建组合颜色节点
                    new_mat.node_tree.links.new(norimagenode.outputs[0], spe.inputs[0])  # 连接图像到分离节点
                    new_mat.node_tree.links.new(com.outputs[0], normalnode.inputs[1])  # 连接组合输出到法线输入
                    indexlist = [itemlist.index(self.normalx), itemlist.index(self.normaly), itemlist.index(self.normalz)]  # 获取法线方向索引
                    invnodes = [None, None, None]  # 初始化反转节点列表
                    for i in range(len(indexlist)):
                        if indexlist[i] > 2:  # 如果方向为负值（NEG_X/Y/Z）
                            invnodes[i] = new_mat.node_tree.nodes.new("ShaderNodeInvert")  # 创建反转节点
                            new_mat.node_tree.links.new(spe.outputs[indexlist[i] % 3], invnodes[i].inputs[1])  # 连接分离输出到反转输入
                            new_mat.node_tree.links.new(invnodes[i].outputs[0], com.inputs[i])  # 连接反转输出到组合输入
                        else:
                            new_mat.node_tree.links.new(spe.outputs[indexlist[i] % 3], com.inputs[i])  # 直接连接分离输出到组合输入
                else:
                    new_mat.node_tree.links.new(norimagenode.outputs[0], normalnode.inputs[1])  # 直接连接图像到法线节点
                        
                if self.setting.normal_obj == True:
                    normalnode.space = 'OBJECT'  # 设置法线空间为对象空间（否则默认为切线空间）
                    
                new_mat.node_tree.links.new(normalnode.outputs[0], outsocket)  # 连接法线输出到 BSDF 输入
                
        if any(item['type'] == 'NORMAL' and item['image'] is not None for item in imagemap):
            norimagenode.location[1] += 1250 - ((index + 1) * 300)  # 调整法线图像节点垂直位置
            normalnode.location[1] += 1250 - ((index + 1) * 300)  # 调整法线贴图节点垂直位置
            if self.normalx != 'POS_X' or self.normaly != 'POS_Y' or self.normalz != 'POS_Z':
                norimagenode.location[0] -= 700  # 调整法线图像节点水平位置以容纳额外节点
                spe.location[0] -= 800  # 设置分离节点水平位置
                com.location[0] -= 400  # 设置组合节点水平位置
                spe.location[1] += 1250 - ((index + 1) * 300)  # 设置分离节点垂直位置
                com.location[1] += 1250 - ((index + 1) * 300)  # 设置组合节点垂直位置
                for i in range(len(invnodes)):
                    if invnodes[i] != None:
                        invnodes[i].location[0] -= 600  # 设置反转节点水平位置
                        invnodes[i].location[1] += 1250 - ((index + 1) * 300) - (i * 100)  # 设置反转节点垂直位置，逐层偏移
                    
        mesh.materials.clear()  # 清除新网格的现有材质
        mesh.materials.append(new_mat)  # 添加新材质到网格
        if bpy.context.scene.collection.children.get('bake') == None:
            bpy.context.scene.collection.children.link(coll)  # 如果 'bake' 集合未链接到场景，则链接
        obj.hide_set(True)  # 隐藏原始对象
        new_obj.hide_set(False)  # 显示新对象
        coll.hide_viewport = False  # 确保 'bake' 集合在视口中可见
        coll.hide_select = False  # 确保 'bake' 集合可选择
        new_obj.select_set(False)  # 取消新对象的选中状态
        
        if self.setting.special_bake_method == 'AUTOATLAS':
            newUV = mesh.uv_layers.get('altas_bake_UV')  # 获取 'altas_bake_UV' UV 层
            newUV.active = True  # 设置为活动 UV 层
            newUV.active_render = True  # 设置为渲染时的活动 UV 层
        
        else:
            mesh.uv_layers.active.active_render = True  # 设置当前活动 UV 层为渲染时的活动层
            
        # 添加导出逻辑
        if self.setting.export_model and self.setting.save_out:
            export_path = os.path.join(
                self.setting.save_path,
                self.get_folder_name(obj, None) if self.setting.create_new_folder else '',
                f"{new_obj.name}.{self.setting.export_format.lower()}"
            )
            export_baked_model(new_obj, export_path, self.setting.export_format, logger)
            
    def bake_mesh_map(self, objects, name, imagemap_mesh, spematerial=None):
        """
        Bake mesh maps (e.g., AO, IDMAT) and save results.
        This method processes a list of objects, baking specified mesh maps (e.g., AO, UV, IDMAT) into images or vertex colors.
        It uses a centralized node setup function to configure materials and handles saving and cleanup.
        Principle (原理):
            - Creates temporary objects and materials as needed for special maps (e.g., SELECT, IDELE).
            - Configures material nodes based on map type using a unified setup method.
            - Bakes the results and saves them to disk, restoring original state afterward.
        Args:
            objects (list): List of bpy.types.Object instances to bake.
            name (str): Base name for map files.
            imagemap_mesh (list): List of mesh map configurations (dictionaries with 'type', 'enabled', etc.).
            spematerial (bpy.types.Material, optional): Specific material to filter by. Defaults to None.
        Returns:
            list: Updated mesh map configuration list with baked images.
        烘焙网格贴图（如 AO、IDMAT）并保存结果。
        此方法处理对象列表，将指定的网格贴图（例如 AO、UV、IDMAT）烘焙到图像或顶点色中。
        它使用集中的节点设置函数配置材质，并处理保存和清理。
        原理:
            - 为特殊贴图（例如 SELECT、IDELE）按需创建临时对象和材质。
            - 使用统一的设置方法根据贴图类型配置材质节点。
            - 烘焙结果并保存到磁盘，之后恢复原始状态。
        参数:
            objects (list): 要烘焙的 bpy.types.Object 实例列表。
            name (str): 贴图文件的基础名称。
            imagemap_mesh (list): 网格贴图配置列表（包含 'type', 'enabled' 等键的字典）。
            spematerial (bpy.types.Material, 可选): 用于筛选的特定材质，默认为 None。
        返回:list: 更新后的网格贴图配置列表，包含烘焙后的图像。
        """
        logger.info(f"Baking mesh maps for {len(objects)} objects with base name: {name}")
        folder_name = self.get_folder_name(objects[0], spematerial) if self.setting.create_new_folder else ''
        target = 'IMAGE_TEXTURES' if self.setting.special_bake_method != 'VERTEXCOLOR' else 'VERTEX_COLORS'

        for map in imagemap_mesh:
            if not map['enabled']:
                continue
            logger.info(f"Processing mesh map: {map['type']}")

            # 获取贴图配置
            config = self.MESH_MAP_CONFIGS.get(map['type'], {'type': map['type'], 'node_setup': None})
            cs = map['custom_cs'] if self.setting.colorspace_setting else map['default_cs']
            if self.setting.float32:
                cs = 'Linear' if map['type'] != 'BEVNOR' else 'Non-Color'
            ncol = cs == 'Non-Color'

            # 创建目标（图像或顶点色）
            if target == 'IMAGE_TEXTURES':
                if ((self.setting.bake_mode == 'SELECT_ACTIVE' and self.setting.bake_type == 'BASIC') or \
                        self.setting.bake_mode == 'SPILT_MATERIAL' or \
                        self.setting.bake_motion) and map['type'] not in ('SHADOW', 'ENVIRONMENT'):
                    print(f"Skipping {map['type']} for mode {self.setting.bake_mode}")
                    logger.info(f"Skipping {map['type']} for mode {self.setting.bake_mode}")
                    continue
                map['image'] = set_image(
                    map['prefix'] + name + map['suffix'], self.setting.res_x, self.setting.res_y,
                    alpha=False, full=self.setting.float32, space=cs, ncol=ncol,
                    fake_user=self.setting.use_fake_user, clear=self.setting.clearimage, basiccolor=self.setting.colorbase
                )
                print(f"Created image: {map['image'].name}")
                logger.debug(f"Created image '{map['image'].name}' for {map['type']}")
            else:
                if map['type'] not in ('SHADOW', 'ENVIRONMENT'):
                    print(f"Skipping {map['type']} for vertex color mode")
                    logger.info(f"Skipping {map['type']} for vertex color mode")
                    continue
                for obj in objects:
                    vername = map['prefix'] + name + map['suffix']
                    vc_type = 'FLOAT_COLOR' if self.setting.float32 else 'BYTE_COLOR'
                    vc = obj.data.attributes.new(vername, vc_type, 'POINT')
                    obj.data.attributes.active_color = vc
                    print(f"Created vertex color layer: {vername} on {obj.name}")
                    logger.debug(f"Created vertex color layer: {vername} on {obj.name}")
            # 初始化材质集合和临时对象
            mat_collection = []
            temp_objects = []

            if map['type'] in ('SELECT', 'IDELE', 'IDUVI', 'IDSEAM'):
                mat_collection, temp_objects = self._prepare_special_map(objects, map, spematerial)
            else:
                for obj in objects:
                    for matslot in obj.material_slots:
                        matinfo = create_matinfo(matslot.material, spematerial)
                        if not matinfo['output_node']:
                            return report_error(self, f"No output found in material '{matslot.material.name}'")
                        matinfo['owner'] = obj
                        mat_collection.append(matinfo)

            # 配置节点并执行烘焙
            for matinfo in mat_collection:
                if target == 'IMAGE_TEXTURES' and (spematerial is None or matinfo['material'] == spematerial):
                    imagenode = matinfo['material'].node_tree.nodes.new('ShaderNodeTexImage')
                    imagenode.image = map['image']
                    matinfo['material'].node_tree.nodes.active = imagenode
                    matinfo['extra_nodes'].append(imagenode)
                    print(f"Set active image node for material '{matinfo['material'].name}' on {matinfo['owner'].name}")

                output_socket = self.setup_mesh_map_nodes(matinfo, config['node_setup'])
                if output_socket and matinfo['output_node']:
                    matinfo['material'].node_tree.links.new(output_socket, matinfo['output_node'].inputs[0])
                    print(f"Linked output socket for {map['type']} in material '{matinfo['material'].name}'")

            try:
                bpy.ops.object.bake(type=config['type'], margin=self.setting.margin, target=target, save_mode='INTERNAL')
                logger.info(f"Baked {map['type']} successfully")
            except Exception as e:
                logger.error(f"Bake failed for {map['type']}: {e}")
                return imagemap_mesh

            # 清理
            self._cleanup_mat_collection(mat_collection)
            if temp_objects:
                for obj in temp_objects:
                    for mat in obj.data.materials:
                        if mat:
                            bpy.data.materials.remove(mat)
                    bpy.data.objects.remove(obj)
                for obj in objects:
                    obj.select_set(True)
                print(f"Cleaned up {len(temp_objects)} temporary objects")

            # 保存图像
            if target == 'IMAGE_TEXTURES':
                save_image(
                    image=map['image'], path=self.setting.save_path, folder=self.setting.create_new_folder,
                    folder_name=folder_name, file_format=self.setting.save_format, color_depth=self.setting.color_depth,
                    color_mode=map['color_mode'], quality=self.setting.quality, exr_codec=self.setting.exr_code,
                    color_space=cs, reload=self.setting.reload, denoise=self.setting.use_denoise,
                    denoise_method=self.setting.denoise_method, save=self.setting.save_out
                )
                self.write_result(map)

        logger.info("Mesh baking completed")
        return imagemap_mesh

    def setup_mesh_map_nodes(self, matinfo, setup_type):
        """
        Configure material nodes for a specific mesh map type.
        This method centralizes node setup logic for all mesh map types, reducing code duplication.
        It returns the output socket to connect to the material output node.
        Args:
            matinfo (dict): Material information dictionary from create_matinfo.
            setup_type (str): Type of node setup ('vertex', 'bevel', 'ao', etc.) or None.
        Returns:
            bpy.types.NodeSocket or None: The output socket to connect to the material output, or None if no setup is needed.
        为特定网格贴图类型配置材质节点。
        此方法集中处理所有网格贴图类型的节点设置逻辑，减少代码重复。
        它返回要连接到材质输出节点的输出插口。
        参数:
            matinfo (dict): 来自 create_matinfo 的材质信息字典。
            setup_type (str): 节点设置类型（'vertex', 'bevel', 'ao' 等）或 None。
        返回:
            bpy.types.NodeSocket 或 None: 要连接到材质输出的输出插口，若无需设置则返回 None。
        """
        if not setup_type:
            return None

        nodes = matinfo['material'].node_tree.nodes
        links = matinfo['material'].node_tree.links

        if setup_type == 'vertex':
            if matinfo['owner'].data.vertex_colors:
                vernode = nodes.new('ShaderNodeVertexColor')
                vernode.layer_name = matinfo['owner'].data.vertex_colors.active.name
                matinfo['extra_nodes'].append(vernode)
                return vernode.outputs[0]

        elif setup_type == 'bevel':
            bevel = nodes.new('ShaderNodeBevel')
            bevel.samples = self.setting.bevel_sample
            bevel.inputs[0].default_value = self.setting.bevel_rad
            vmc = nodes.new('ShaderNodeVectorMath')
            vmc.operation = 'CROSS_PRODUCT'
            vma = nodes.new('ShaderNodeVectorMath')
            vma.operation = 'ABSOLUTE'
            vml = nodes.new('ShaderNodeVectorMath')
            vml.operation = 'LENGTH'
            geo = nodes.new('ShaderNodeNewGeometry')
            matinfo['extra_nodes'].extend([bevel, vmc, vma, vml, geo])
            links.new(bevel.outputs[0], vmc.inputs[0])
            links.new(geo.outputs[1], vmc.inputs[1])
            links.new(vmc.outputs[0], vma.inputs[0])
            links.new(vma.outputs[0], vml.inputs[0])
            return vml.outputs[1]

        elif setup_type == 'ao':
            ao = nodes.new('ShaderNodeAmbientOcclusion')
            ao.samples = self.setting.ao_sample
            ao.inside = self.setting.ao_inside
            ao.only_local = self.setting.ao_local
            ao.inputs[1].default_value = self.setting.ao_dis
            matinfo['extra_nodes'].append(ao)
            return ao.outputs[0]

        elif setup_type == 'uv':
            tex = nodes.new('ShaderNodeTexCoord')
            sep = nodes.new('ShaderNodeSeparateColor')
            com = nodes.new('ShaderNodeCombineColor')
            com.inputs[2].default_value = 1
            matinfo['extra_nodes'].extend([tex, sep, com])
            links.new(tex.outputs[2], sep.inputs[0])
            links.new(sep.outputs[1], com.inputs[1])
            return com.outputs[0]

        elif setup_type == 'wireframe':
            wf = nodes.new('ShaderNodeWireframe')
            wf.inputs[0].default_value = self.setting.wireframe_dis
            wf.use_pixel_size = self.setting.wireframe_use_pix
            matinfo['extra_nodes'].append(wf)
            return wf.outputs[0]

        elif setup_type == 'bevnor':
            bevel = nodes.new('ShaderNodeBevel')
            bevel.samples = self.setting.bevnor_sample
            bevel.inputs[0].default_value = self.setting.bevnor_rad
            bsdf = nodes.new('ShaderNodeBsdfPrincipled')
            matinfo['extra_nodes'].extend([bevel, bsdf])
            links.new(bevel.outputs[0], bsdf.inputs['Normal'])
            return bsdf.outputs[0]

        elif setup_type == 'position':
            tex = nodes.new('ShaderNodeTexCoord')
            sep = nodes.new('ShaderNodeSeparateColor')
            com = nodes.new('ShaderNodeCombineColor')
            gma = nodes.new('ShaderNodeGamma')
            inv = nodes.new('ShaderNodeInvert') if self.setting.position_invg else None
            matinfo['extra_nodes'].extend([tex, sep, com, gma] + ([inv] if inv else []))
            links.new(tex.outputs[0], sep.inputs[0])
            links.new(sep.outputs[0], com.inputs[0])
            if self.setting.position_invg:
                links.new(sep.outputs[1], inv.inputs[1])
                links.new(inv.outputs[0], com.inputs[1])
            else:
                links.new(sep.outputs[1], com.inputs[1])
            links.new(sep.outputs[2], com.inputs[2])
            links.new(com.outputs[0], gma.inputs[0])
            gma.inputs[1].default_value = 2.2
            return gma.outputs[0]

        elif setup_type == 'slope':
            tex = nodes.new('ShaderNodeTexCoord')
            sep = nodes.new('ShaderNodeSeparateColor')
            math1 = nodes.new('ShaderNodeMath')
            math2 = nodes.new('ShaderNodeMath') if not self.setting.slope_invert else None
            matinfo['extra_nodes'].extend([tex, sep, math1] + ([math2] if math2 else []))
            math1.operation = 'ABSOLUTE'
            if math2:
                math2.operation = 'SUBTRACT'
                math2.inputs[0].default_value = 1.0
            channel = {'X': 0, 'Y': 1, 'Z': 2}.get(self.setting.slope_directions, 2)
            links.new(tex.outputs[1], sep.inputs[0])
            links.new(sep.outputs[channel], math1.inputs[0])
            if math2:
                links.new(math1.outputs[0], math2.inputs[1])
                return math2.outputs[0]
            return math1.outputs[0]

        elif setup_type == 'thickness':
            ao = nodes.new('ShaderNodeAmbientOcclusion')
            ao.samples = 32
            ao.only_local = True
            ao.inside = True
            ao.inputs[1].default_value = self.setting.thickness_distance
            inv = nodes.new('ShaderNodeInvert')
            con = nodes.new('ShaderNodeBrightContrast')
            con.inputs[2].default_value = self.setting.thickness_contrast
            matinfo['extra_nodes'].extend([ao, inv, con])
            links.new(ao.outputs[0], inv.inputs[1])
            links.new(inv.outputs[0], con.inputs[0])
            return con.outputs[0]

        elif setup_type == 'idmat':
            total_mats = len([m for obj in self.objects for m in obj.material_slots])
            mat_index = sum(len(obj.material_slots) for obj in self.objects[:self.objects.index(matinfo['owner'])]) + \
                        [m.material for m in matinfo['owner'].material_slots].index(matinfo['material'])
            hue = mat_index / max(1, total_mats)
            col = mathutils.Color((1.0, 0.0, 0.0))
            col.h = hue
            colnode = nodes.new('ShaderNodeRGB')
            colnode.outputs[0].default_value = (col.r, col.g, col.b, 1.0)
            matinfo['extra_nodes'].append(colnode)
            return colnode.outputs[0]

        elif setup_type == 'select':
            color = matinfo.get('select_color', (1.0, 1.0, 1.0, 1.0))
            colnode = nodes.new('ShaderNodeRGB')
            colnode.outputs[0].default_value = color
            matinfo['extra_nodes'].append(colnode)
            return colnode.outputs[0]

        elif setup_type in ('idele', 'iduvi', 'idseam'):
            index_key = f"{setup_type}_index"
            element_index = matinfo.get(index_key, 0)
            hue = element_index / max(1, self.setting.ID_num)
            col = mathutils.Color((1.0, 0.0, 0.0))
            col.h = hue
            colnode = nodes.new('ShaderNodeRGB')
            colnode.outputs[0].default_value = (col.r, col.g, col.b, 1.0)
            matinfo['extra_nodes'].append(colnode)
            return colnode.outputs[0]

        return None

    def _prepare_special_map(self, objects, map, spematerial):
        """
        Prepare temporary objects and materials for special mesh maps (SELECT, IDELE, IDUVI, IDSEAM).
        Args:
            objects (list): List of bpy.types.Object instances.
            map (dict): Mesh map configuration dictionary.
            spematerial (bpy.types.Material, optional): Specific material to filter by.
        Returns:
            tuple: (mat_collection, temp_objects) where:
                - mat_collection (list): List of material info dictionaries.
                - temp_objects (list): List of temporary objects created.
        为特殊网格贴图（SELECT、IDELE、IDUVI、IDSEAM）准备临时对象和材质。
        参数:
            objects (list): bpy.types.Object 实例列表。
            map (dict): 网格贴图配置字典。
            spematerial (bpy.types.Material, 可选): 用于筛选的特定材质。
        返回:
            tuple: (mat_collection, temp_objects)，其中：
                - mat_collection (list): 材质信息字典列表。
                - temp_objects (list): 创建的临时对象列表。
        """
        mat_collection = []
        temp_objects = []

        if map['type'] == 'SELECT':
            sel_mat = bpy.data.materials.new('select_mat')
            sel_mat.use_nodes = True
            sel_col = sel_mat.node_tree.nodes.new('ShaderNodeRGB')
            sel_col.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
            sel_out = get_output(sel_mat.node_tree.nodes)
            sel_imagenode = sel_mat.node_tree.nodes.new('ShaderNodeTexImage')
            sel_imagenode.image = map['image']
            sel_mat.node_tree.nodes.active = sel_imagenode
            sel_mat.node_tree.links.new(sel_col.outputs[0], sel_out.inputs[0])

            unsel_mat = bpy.data.materials.new('unselect_mat')
            unsel_mat.use_nodes = True
            unsel_col = unsel_mat.node_tree.nodes.new('ShaderNodeRGB')
            unsel_col.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
            unsel_out = get_output(unsel_mat.node_tree.nodes)
            unsel_imagenode = unsel_mat.node_tree.nodes.new('ShaderNodeTexImage')
            unsel_imagenode.image = map['image']
            unsel_mat.node_tree.nodes.active = unsel_imagenode
            unsel_mat.node_tree.links.new(unsel_col.outputs[0], unsel_out.inputs[0])

            for obj in objects:
                faces = {f.index for f in obj.data.polygons if f.select}
                no = copy_object(obj, clear_material=True)
                temp_objects.append(no)
                obj.select_set(False)
                no.select_set(True)
                no.data.materials.append(sel_mat)
                no.data.materials.append(unsel_mat)
                for poly in no.data.polygons:
                    poly.material_index = 0 if poly.index in faces else 1
                sel_matinfo = create_matinfo(sel_mat, spematerial)
                sel_matinfo['owner'] = no
                sel_matinfo['select_color'] = (1.0, 1.0, 1.0, 1.0)
                mat_collection.append(sel_matinfo)
                unsel_matinfo = create_matinfo(unsel_mat, spematerial)
                unsel_matinfo['owner'] = no
                unsel_matinfo['select_color'] = (0.0, 0.0, 0.0, 1.0)
                mat_collection.append(unsel_matinfo)

        elif map['type'] in ('IDELE', 'IDUVI', 'IDSEAM'):
            bpy.ops.object.mode_set(mode='OBJECT')
            for obj in objects:
                no = copy_object(obj, clear_material=True)
                temp_objects.append(no)
                obj.select_set(False)
                no.select_set(True)
                bm = bmesh.new()
                bm.from_mesh(no.data)
                bm.faces.ensure_lookup_table()
                delimit = {'UV'} if map['type'] == 'IDUVI' else {'SEAM'} if map['type'] == 'IDSEAM' else set()
                faces_list = []
                used_faces = set()
                for i in range(len(bm.faces)):
                    if i in used_faces:
                        continue
                    bpy.ops.object.mode_set(mode='EDIT')
                    bm.faces[i].select = True
                    bpy.ops.mesh.select_linked(delimit=delimit)
                    bmesh.update_edit_mesh(no.data)
                    group = [i2 for i2 in range(len(bm.faces)) if bm.faces[i2].select]
                    used_faces.update(group)
                    faces_list.append(group)
                    for i2 in group:
                        bm.faces[i2].select = False

                for idx, faces in enumerate(faces_list):
                    mat = bpy.data.materials.new(f"{no.name}_group_{idx}")
                    mat.use_nodes = True
                    colnode = mat.node_tree.nodes.new('ShaderNodeRGB')
                    hue = idx / max(1, self.setting.ID_num)
                    col = mathutils.Color((1.0, 0.0, 0.0))
                    col.h = hue
                    colnode.outputs[0].default_value = (col.r, col.g, col.b, 1.0)
                    imagenode = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    imagenode.image = map['image']
                    mat.node_tree.nodes.active = imagenode
                    mat.node_tree.links.new(colnode.outputs[0], get_output(mat.node_tree.nodes).inputs[0])
                    no.data.materials.append(mat)
                    for fi in faces:
                        no.data.polygons[fi].material_index = idx
                    matinfo = create_matinfo(mat, spematerial)
                    matinfo['owner'] = no
                    matinfo[f"{map['type'].lower()}_index"] = idx
                    mat_collection.append(matinfo)
                bpy.ops.object.mode_set(mode='OBJECT')
                bm.to_mesh(no.data)
                bm.free()

        return mat_collection, temp_objects

    def _cleanup_mat_collection(self, mat_collection):
        """
        Clean up material collection after baking.
        Args:
            mat_collection (list): List of material info dictionaries to clean up.
        Returns:
            None
        清理烘焙后的材质集合。
        参数:
            mat_collection (list): 要清理的材质信息字典列表。
        返回:
            None
        """
        for matinfo in mat_collection:
            if matinfo['bsdf_node']:
                matinfo['material'].node_tree.links.new(matinfo['bsdf_node'].outputs[0], matinfo['output_node'].inputs[0])
            for node in matinfo['extra_nodes']:
                matinfo['material'].node_tree.nodes.remove(node)
            matinfo['extra_nodes'].clear()
            if matinfo['temp_image']:
                bpy.data.images.remove(matinfo['temp_image'])
                matinfo['temp_image'] = None
                matinfo['temp_image_node'] = None
    
    def get_folder_name(self, obj, spematerial):
        """获取文件夹名称。"""
        setting = self.setting
        if setting.new_folder_name_setting == 'OBJECT':
            return obj.name
        elif setting.new_folder_name_setting == 'MAT':
            return spematerial.name if spematerial else obj.active_material.name
        elif setting.new_folder_name_setting == 'OBJ_MAT':
            mat_name = spematerial.name if spematerial else obj.active_material.name
            return f"{obj.name}_{mat_name}"
        return setting.folder_name
        
    def write_result(self,map):
        result = bpy.context.scene.baked_image_results.add()
        result.image = map['image']
        result.color_depth = self.setting.color_depth
        result.color_space = map['custom_cs'] if self.setting.colorspace_setting else map['default_cs']
        result.filepath = bpy.path.abspath(os.path.join(self.setting.save_path, self.foldername, f"{map['image'].name}.{self.setting.save_format.lower()}")) if self.setting.save_out else ""
        result.channel_type = map['type']
        
class selected_node_bake(bpy.types.Operator):
    bl_label = "Selected Node Bake"
    bl_idname = "bake.selected_node_bake"
    bl_description = "Bake selected material nodes to image"
    #将选中的材质节点烘焙到图像//Bake selected material nodes to an image

    @classmethod
    def poll(cls, context):
        """Check if baking operation can proceed        检查烘焙操作是否可以继续"""
        if not context.active_object or not context.selected_objects:
            return False  # 没有活动对象或选中对象
        
        if not context.selected_nodes or not context.active_node:
            return False  # 没有选中的节点或活动节点
            
        bake_jobs = context.scene.BakeJobs
        active_node = context.active_object.active_material.node_tree.nodes.active
        if not bake_jobs.node_bake_auto_find_socket:
            if bake_jobs.node_bake_socket_index >= len(active_node.outputs):
                return False  # socket索引超出范围
                
        # 检查是否存在活动的材质输出节点
        # Check if there's an active material output node
        return any(node.bl_idname == 'ShaderNodeOutputMaterial' and node.is_active_output 
                  for node in context.active_object.active_material.node_tree.nodes)

    def execute(self, context):
        """Execute the baking operation        执行烘焙操作"""
        logger.info("Starting selected node bake operation")
        bake_jobs = context.scene.BakeJobs
        
        # 如果保存到外部但路径为空，则报错
        # Report error if saving externally but path is empty
        if bake_jobs.node_bake_save_outside and not bake_jobs.node_bake_save_path:
            logger.error("Save path is empty for external save")
            return report_error(self, "Please set a valid save path")

        material = context.active_object.active_material
        node_tree = material.node_tree
        logger.info(f"Job started | Object: {context.active_object.name} | Material: {material.name} | "
                    f"Resolution: {bake_jobs.node_bake_res_x}x{bake_jobs.node_bake_res_y}")
        # 寻找输出节点
        # Find output node
        output_node = next((node for node in node_tree.nodes 
                          if node.bl_idname == 'ShaderNodeOutputMaterial' and node.is_active_output), None)
        if not output_node:
            logger.error("No active material output node found")
            return report_error(self, "No active material output node found")

        output_socket = output_node.inputs[0]
        original_link = output_socket.links[0].from_socket if output_socket.links else None
        
        # 存储场景设置
        # Store scene settings
        original_settings = {
            'scene': manage_scene_settings('scene', getorset=False),
            'image': manage_scene_settings('image', getorset=False),
            'bake': manage_scene_settings('bake', getorset=False)
            }
        
        # 设置场景参数
        scene_settings = {
            'res_x': bake_jobs.node_bake_res_x,
            'res_y': bake_jobs.node_bake_res_y,
            'engine': 'CYCLES',  # 示例值，可根据需要调整
            'samples': bake_jobs.node_bake_sample
        }
        manage_scene_settings('scene', scene_settings, getorset=True)

        
        image_settings = {
            'file_format': format_map[bake_jobs.node_bake_save_format],
            'color_depth': bake_jobs.node_bake_color_depth,
            'color_mode': bake_jobs.node_bake_color_mode,
            'quality': bake_jobs.node_bake_quality,
            'compression': (100-bake_jobs.node_bake_quality),
            'exr_codec': bake_jobs.node_bake_exr_code,
        }
        manage_scene_settings('image', image_settings, getorset=True)

        # 设置烘焙参数
        bake_settings = {
            'margin': bake_jobs.node_bake_margin
        }
        manage_scene_settings('bake', bake_settings, getorset=True)
        logger.info("Node bake settings applied")
        #监测是否有空材质槽，有则加一个空材质节点
        # Add an empty material node if empty material slots monitored
        mat_info_collection=[]
        for mat_slot in bpy.context.active_object.material_slots:
            if mat_slot.material!=bpy.context.active_object.active_material:
                mat_info_collection.append(make_temnode(mat_slot.material))

        # 处理每个选中的节点
        # Process each selected node
        
        for node in [n for n in node_tree.nodes if n.select]:
            logger.debug(f"Processing node: {node.name} ({node.bl_idname})")
            socket = self.get_output_socket(node, bake_jobs)
            if not socket:
                logger.error(f"No valid output socket found for node {node.name}")
                return report_error(self, "No valid output socket found for node")

            # 创建烘焙用的图像
            # Create image for baking
            image_name = f"{material.name} {node.label or node.name}"
            image = self.create_bake_image(image_name, bake_jobs)
            logger.debug(f"Created bake image: {image.name} ({bake_jobs.node_bake_res_x}x{bake_jobs.node_bake_res_y})")
            # 设置烘焙节点
            # Setup baking nodes
            image_node = self.setup_bake_nodes(node_tree, node, image, bake_jobs)
            node_tree.links.new(socket, output_socket)

            # 执行烘焙
            # Perform bake
            bpy.ops.object.bake(type='EMIT', 
                              margin=bake_jobs.node_bake_margin,
                              margin_type='EXTEND',
                              target='IMAGE_TEXTURES')
            logger.info(f"Baked node {node.name} successfully")
            # 保存并清理
            # Save and cleanup
            self.save_and_cleanup(node_tree, image, image_node, bake_jobs)

        # 恢复原始连接和设置
        # Restore original connections and settings
        if original_link:
            node_tree.links.new(original_link, output_socket)
        if len(mat_info_collection)>0:
            for mat_info in mat_info_collection:
                clear_temnode(mat_info)
            
        for category, settings in original_settings.items():
            manage_scene_settings(category, settings, getorset=True)
            
        logger.info("Restored original settings and completed node bake")
        self.report({'INFO'}, "Selected node bake operation finished")
        return {'FINISHED'}

    def get_output_socket(self, node, bake_jobs):
        """Get the appropriate output socket from the node        获取节点合适的输出插口"""
        if not bake_jobs.node_bake_auto_find_socket:
            return node.outputs[bake_jobs.node_bake_socket_index]
        
        # 先找已连接的插口，再找启用的插口
        # First find linked socket, then enabled socket
        return next((s for s in node.outputs if s.is_linked), 
                   next((s for s in node.outputs if s.enabled), None))

    def create_bake_image(self, name, bake_jobs):
        """Create a new image for baking        为烘焙创建新图像"""
        color_space = ('sRGB' if bake_jobs.node_bake_color_space == 'SRGB' else 'Linear' if bake_jobs.node_bake_color_space == 'LINEAR' else 'Non-Color')
                      
        return bpy.data.images.new(
            name=name,
            width=bake_jobs.node_bake_res_x,
            height=bake_jobs.node_bake_res_y,
            alpha=True,
            float_buffer=bake_jobs.node_bake_float32,
            is_data=(color_space == 'Non-Color')
        )

    def setup_bake_nodes(self, node_tree, source_node, image, bake_jobs):
        """Setup temporary nodes for baking        设置用于烘焙的临时节点"""
        image_node = node_tree.nodes.new("ShaderNodeTexImage")
        image_node.location = source_node.location + mathutils.Vector((250, 0))
        image_node.image = image
        node_tree.nodes.active = image_node
        return image_node

    def save_and_cleanup(self, node_tree, image, image_node, bake_jobs):
        """Save the baked image and clean up        保存烘焙图像并清理"""
        if bake_jobs.node_bake_save_outside:
            image.filepath_raw = bake_jobs.node_bake_save_path
            image.file_format = bake_jobs.node_bake_format
            image.save()
            logger.debug(f"Saved image {image.name} to {bake_jobs.node_bake_save_path}")
        else:
            image.pack()
            logger.debug(f"Packed image {image.name} into .blend file")
        if bake_jobs.node_bake_delect_node:
            node_tree.nodes.remove(image_node)
            logger.debug(f"Removed image node {image_node.name}")
# 删除选中的烘焙结果
class BAKETOOL_OT_DeleteResult(bpy.types.Operator):
    bl_idname = "baketool.delete_result"
    bl_label = "Delete Selected Result"
    bl_description = "Delete the selected baked image result"

    @classmethod
    def poll(cls, context):
        return context.scene.baked_image_results_index >= 0

    def execute(self, context):
        index = context.scene.baked_image_results_index
        results = context.scene.baked_image_results
        if results[index].image:
            bpy.data.images.remove(results[index].image)  # 删除图像数据块
        results.remove(index)
        context.scene.baked_image_results_index = min(max(0, index - 1), len(results) - 1)
        return {'FINISHED'}

# 删除所有烘焙结果
class BAKETOOL_OT_DeleteAllResults(bpy.types.Operator):
    bl_idname = "baketool.delete_all_results"
    bl_label = "Delete All Results"
    bl_description = "Delete all baked image results"

    def execute(self, context):
        results = context.scene.baked_image_results
        for result in results:
            if result.image:
                bpy.data.images.remove(result.image)  # 删除所有图像数据块
        results.clear()
        context.scene.baked_image_results_index = -1
        return {'FINISHED'}

# 导出选中的烘焙结果
class BAKETOOL_OT_ExportResult(bpy.types.Operator):
    bl_idname = "baketool.export_result"
    bl_label = "Export Selected Result"
    bl_description = "Export the selected baked image with customizable settings"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def poll(cls, context):
        return (context.scene.baked_image_results_index >= 0 and 
                context.scene.baked_image_results[context.scene.baked_image_results_index].image is not None)

    def invoke(self, context, event):
        # 初始化文件选择器，默认路径为 BakeJobs 中的 bake_result_save_path
        bake_jobs = context.scene.BakeJobs
        self.filepath = bpy.path.abspath(bake_jobs.bake_result_save_path) if bake_jobs.bake_result_save_path else bpy.path.abspath("//")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        index = context.scene.baked_image_results_index
        result = context.scene.baked_image_results[index]
        bake_jobs = context.scene.BakeJobs

        if not result.image:
            self.report({'ERROR'}, "No image to export")
            return {'CANCELLED'}

        # 从 BakeJobs 获取导出设置
        save_image(
            image=result.image,
            path=os.path.dirname(self.filepath),  # 使用选择的文件路径的目录部分
            folder=False,  # 不创建子文件夹
            folder_name="",
            file_format=bake_jobs.bake_result_save_format,
            color_depth=bake_jobs.bake_result_color_depth,
            color_mode=bake_jobs.bake_result_color_mode,
            quality=bake_jobs.bake_result_quality,
            exr_codec=bake_jobs.bake_result_exr_code,
            color_space='sRGB' if bake_jobs.bake_result_color_space == 'DEFAULT' else bake_jobs.bake_result_color_space,
            reload=False,  # 导出时不重新加载
            denoise=bake_jobs.bake_result_use_denoise,
            denoise_method=bake_jobs.bake_result_denoise_method,
            save=True
        )

        self.report({'INFO'}, f"Exported {result.image.name} to {self.filepath}")
        return {'FINISHED'}

# 导出所有烘焙结果
class BAKETOOL_OT_ExportAllResults(bpy.types.Operator):
    bl_idname = "baketool.export_all_results"
    bl_label = "Export All Results"
    bl_description = "Export all baked image results to a directory with customizable settings"

    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    
    @classmethod
    def poll(cls, context):
        return (context.scene.baked_image_results_index >= 0)

    def invoke(self, context, event):
        # 初始化目录选择器，默认路径为 BakeJobs 中的 bake_result_save_path
        bake_jobs = context.scene.BakeJobs
        self.directory = bpy.path.abspath(bake_jobs.bake_result_save_path) if bake_jobs.bake_result_save_path else bpy.path.abspath("//")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        results = context.scene.baked_image_results
        bake_jobs = context.scene.BakeJobs

        if not results:
            self.report({'ERROR'}, "No baked results to export")
            return {'CANCELLED'}

        exported_count = 0
        for result in results:
            if result.image:
                # 使用图像名称作为文件名，加上 BakeJobs 中的格式扩展名
                file_name = f"{result.image.name}.{bake_jobs.bake_result_save_format.lower()}"
                filepath = os.path.join(self.directory, file_name)

                save_image(
                    image=result.image,
                    path=self.directory,
                    folder=False,
                    folder_name="",
                    file_format=bake_jobs.bake_result_save_format,
                    color_depth=bake_jobs.bake_result_color_depth,
                    color_mode=bake_jobs.bake_result_color_mode,
                    quality=bake_jobs.bake_result_quality,
                    exr_codec=bake_jobs.bake_result_exr_code,
                    color_space='sRGB' if bake_jobs.bake_result_color_space == 'DEFAULT' else bake_jobs.bake_result_color_space,
                    reload=False,
                    denoise=bake_jobs.bake_result_use_denoise,
                    denoise_method=bake_jobs.bake_result_denoise_method,
                    save=True
                )
                exported_count += 1
                self.report({'INFO'}, f"Exported {result.image.name} to {filepath}")

        self.report({'INFO'}, f"Exported {exported_count} images to {self.directory}")
        return {'FINISHED'}