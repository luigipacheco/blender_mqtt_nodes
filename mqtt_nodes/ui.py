import bpy

from bpy.types import Panel

class MQTTNodePanel(Panel):

    bl_label = 'MQTT'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'MQTT'
    bl_idname = 'NODE_PT_mqtt'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        row = layout.row()
        row.label(text="This is a test")


class MQTTPanel(Panel):
    bl_label = 'MQTT'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'
    bl_idname = 'SCENE_PT_mqtt'

    def draw(self, context):
        scn = bpy.context.scene
        mqtt_settings = scn.mqtt_settings
        layout = self.layout
        box = layout.box()
        col = box.column()
        col.prop(mqtt_settings, "broker_host")
        col.prop(mqtt_settings, "topic_prefix")
        col.operator("mqtt.reconnect_client", text="Reconnect")
        # props
        box = layout.box()
        col = box.column()
        for idx, input_prop in enumerate(scn.mqtt_inputs):
            row = col.row()
            if input_prop.property_name == 'NOT_SET':
                row.alert = True
            row.prop(input_prop, "property_name", text="")
            row.operator("mqtt.remove_input_property", text="", icon="CANCEL").property_index = idx
            row = col.row()
            row.prop(input_prop, "do_decay_float", text="Decay")
            if input_prop.do_decay_float:
                row.prop(input_prop, "decay_hold_peak_frames", text="hold frames")
                row.prop(input_prop, "decay_rate", text="rate")
        col = box.column()
        col.operator("mqtt.add_input_property", text="ADD")
        
        # Output properties
        box = layout.box()
        box.label(text="Output Properties")
        col = box.column()
        for idx, output_prop in enumerate(scn.mqtt_outputs):
            row = col.row()
            if not output_prop.data_path or not output_prop.topic:
                row.alert = True
            row.prop(output_prop, "data_path", text="Data Path")
            row = col.row()
            row.prop(output_prop, "topic", text="Topic")
            row = col.row()
            row.prop(output_prop, "publish_on_frame", text="Publish on Frame")
            if not output_prop.publish_on_frame:
                row = col.row()
                row.prop(output_prop, "timer_interval", text="Timer Interval (s)")
            row = col.row()
            row.operator("mqtt.remove_output_property", text="", icon="CANCEL").property_index = idx
        col = box.column()
        col.operator("mqtt.add_output_property", text="ADD OUTPUT")
        

