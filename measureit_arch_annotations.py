# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


# ----------------------------------------------------------
# File: measureit_arch_annotations.py
# Main panel for different MeasureitArch general actions
# Author:  Kevan Cress
#
# ----------------------------------------------------------
import bpy
import blf
import bgl
import gpu
from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D, Scene, UIList
from bpy.props import (
        CollectionProperty,
        FloatVectorProperty,
        IntProperty,
        BoolProperty,
        StringProperty,
        FloatProperty,
        EnumProperty,
        PointerProperty
        )
from .measureit_arch_baseclass import BaseProp, BaseWithText
from .measureit_arch_main import get_smart_selected, get_selected_vertex
import math

def annotation_update_flag(self,context):
    self.text_updated = True
    update_custom_props(self,context)

def update_custom_props(self,context):
    ignoredProps = ['AnnotationGenerator','DimensionGenerator','LineGenerator','_RNA_UI','cycles','cycles_visibility','obverts']
    idx = 0 
    for key in context.object.keys():
        if key not in ignoredProps:
            if key not in self.customProperties:
                self.customProperties.add().name = key
    for prop in self.customProperties:
        if prop.name not in context.object.keys():
            self.customProperties.remove(idx)
        idx += 1

class CustomProperties(PropertyGroup):
    name: StringProperty(name='Custom Properties')
bpy.utils.register_class(CustomProperties)

class AnnotationProperties(BaseWithText,PropertyGroup):
    customProperties: CollectionProperty(type=CustomProperties)
    annotationRotation:FloatVectorProperty(name='annotationOffset',
                            description='Rotation for Annotation',
                            default= (0.0,0.0,0.0),
                            subtype= 'EULER')

    annotationOffset: FloatVectorProperty(name='annotationOffset',
                            description='Offset for Annotation',
                            default= (1.0,1.0,1.0),
                            subtype= 'TRANSLATION')
    
    annotationTextSource: StringProperty(name='annotationTextSource',
                            description="Text Source",
                            update=annotation_update_flag)

    annotationAnchorObject: PointerProperty(type=Object)

    annotationAnchor: IntProperty(name="annotationAnchor",
                            description="Index of Vertex that the annotation is Anchored to")
    
    endcapSize: IntProperty(name="dimEndcapSize",
                description="End Cap size",
                default=15, min=1, max=500)

    endcapA: EnumProperty(
                    items=(('99', "--", "No Cap"),
                           ('D', "Dot", "Dot"),
                           ('T', "Triangle", "Triangle")),
                    name="A end",
                    description="Add arrows to point A") 

bpy.utils.register_class(AnnotationProperties)

class AnnotationContainer(PropertyGroup):
    num_annotations: IntProperty(name='Number of Annotations', min=0, max=1000, default=0,
                                description='Number total of Annotations')
    active_annotation_index: IntProperty(name='Active Annotation Index')
    show_anotation_settings: BoolProperty(name='Show Annotation Settings',default=False)
    # Array of segments
    annotations: CollectionProperty(type=AnnotationProperties)
bpy.utils.register_class(AnnotationContainer)
Object.AnnotationGenerator = CollectionProperty(type=AnnotationContainer)

class AddAnnotationButton(Operator):
    bl_idname = "measureit_arch.addannotationbutton"
    bl_label = "Add"
    bl_description = "Add a new Annotation (For Mesh Objects Select 1 Vertex in Edit Mode)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "EMPTY" or o.type == "CAMERA" or o.type == "LIGHT":
                return True
            elif o.type == "MESH" and  bpy.context.mode == 'EDIT_MESH':
                return True
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            scene = context.scene
            # Add properties
            mainobject = context.object
            if 'AnnotationGenerator' not in mainobject:
                mainobject.AnnotationGenerator.add()

            annotationGen = mainobject.AnnotationGenerator[0] 

            if mainobject.type=='MESH':
                mylist = get_selected_vertex(mainobject)
                if len(mylist) == 1:
                    annotationGen.num_annotations +=1
                    newAnnotation = annotationGen.annotations.add()
                    newAnnotation.annotationAnchor = mylist[0]
                    
                    context.area.tag_redraw()  
                    update_custom_props(newAnnotation,context)
                else:
                    self.report({'ERROR'},
                                "MeasureIt-ARCH: Select one vertex for creating measure label")
                    return {'FINISHED'}
            else:
                annotationGen.num_annotations +=1
                newAnnotation = annotationGen.annotations.add()
                newAnnotation.annotationAnchor = 9999999 
                context.area.tag_redraw()  
                update_custom_props(newAnnotation,context)
            
            newAnnotation.itemType = 'A'
            newAnnotation.annotationAnchorObject = mainobject
            newAnnotation.style = scene.measureit_arch_default_annotation_style
            
            if scene.measureit_arch_default_annotation_style is not '':
                newAnnotation.uses_style = True
            else:
                newAnnotation.uses_style = False

            newAnnotation.text = ("Annotation " + str(annotationGen.num_annotations))

            newAnnotation.lineWeight = 1
            newAnnotation.color = (0,0,0,1)
            newAnnotation.fontSize = 24
            return {'FINISHED'}
        else:
            self.report({'WARNING'},   
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}

class M_ARCH_UL_annotations_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):    
        scene = bpy.context.scene
        hasGen = False
        if 'StyleGenerator' in scene:
            StyleGen = scene.StyleGenerator[0]
            hasGen = True
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            annotation = item
            layout.use_property_decorate = False
            row = layout.row(align=True)
            subrow = row.row()
            subrow.prop(annotation, "text", text="",emboss=False,icon='FONT_DATA')
            
            if annotation.visible: visIcon = 'HIDE_OFF'
            else: visIcon = 'HIDE_ON'

            if annotation.uses_style: styleIcon = 'LINKED'
            else: styleIcon = 'UNLINKED'
            
            subrow = row.row(align=True)
            if not annotation.uses_style:
                subrow = row.row()
                subrow.scale_x = 0.6
                subrow.prop(annotation, 'color', text="" )
            else:
                row.prop_search(annotation,'style', StyleGen,'annotations',text="", icon='COLOR')
                row.separator()

            if hasGen:
                row = row.row(align=True)
                row.prop(annotation, 'uses_style', text="",toggle=True, icon=styleIcon,emboss=False)
            
            row.prop(annotation, "visible", text="", icon = visIcon)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')

class OBJECT_PT_UIAnnotations(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "MeasureIt-ARCH Anotations"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        obj = context.object
        if context.object is not None:
            if 'AnnotationGenerator' in context.object:     
                scene = context.scene
                annoGen = context.object.AnnotationGenerator[0]

                row = layout.row()
                
                # Draw The UI List
                row.template_list("M_ARCH_UL_annotations_list", "", annoGen, "annotations", annoGen, "active_annotation_index",rows=2, type='DEFAULT')
                
                # Operators Next to List
                col = row.column(align=True)
                op = col.operator("measureit_arch.deletepropbutton", text="", icon="X")
                op.tag = annoGen.active_annotation_index  # saves internal data
                op.item_type = 'A'
                op.is_style = False
                col.separator()

                col.menu("OBJECT_MT_annotation_menu", icon='DOWNARROW_HLT', text="")


                
                # Settings Below List

                if len(annoGen.annotations) > 0 and  annoGen.active_annotation_index < len(annoGen.annotations):
                    annotation = annoGen.annotations[annoGen.active_annotation_index]

                    if annoGen.show_anotation_settings: settingsIcon = 'DISCLOSURE_TRI_DOWN'
                    else: settingsIcon = 'DISCLOSURE_TRI_RIGHT'
                    
                    box = layout.box()
                    col = box.column()
                    row = col.row()
                    row.prop(annoGen, 'show_anotation_settings', text="", icon=settingsIcon,emboss=False)
                    row.label(text= annotation.text + ' Settings:')

                    if annoGen.show_anotation_settings:
                        if not annotation.uses_style:
                            split = box.split(factor=0.485)
                            col = split.column()
                            col.alignment ='RIGHT'
                            col.label(text='Font')
                            col = split.column(align=True)
                            col.template_ID(annotation, "font", open="font.open", unlink="font.unlink")

                            col = box.column(align=True)
                            col.prop_search(annotation,'annotationTextSource', annotation ,'customProperties',text="Text Source")
                            col.prop(annotation, 'textResolution', text="Resolution")
                            col.prop(annotation, 'fontSize', text="Size") 
                            col.prop(annotation, 'textAlignment', text='Alignment')
                            col.prop(annotation, 'textPosition', text='Position')

                            col = box.column(align=True)
                            col.prop(annotation, 'endcapA', text='End Cap')
                            col.prop(annotation, 'endcapSize', text='Size')

                            col = box.column(align=True)
                            col.prop(annotation, 'lineWeight', text="Line Weight" )
                        
                        col = box.column()
                        col.prop(annotation, 'annotationOffset', text='Offset')
                        col.prop(annotation, 'annotationRotation', text='Rotation')
                        col.prop(annotation,'textFlippedX',text='Flip Text X')
                        col.prop(annotation,'textFlippedY',text='Flip Text Y')

                # Delete Operator (Move to drop down menu next to list)
                col = layout.column()

 
class OBJECT_MT_annotation_menu(bpy.types.Menu):
    bl_label = "Custom Menu"

    def draw(self,context):
        layout = self.layout

        delOp = layout.operator("measureit_arch.deleteallitemsbutton", text="Delete All Annotations", icon="X")
        delOp.is_style = False
        delOp.item_type = 'A'
