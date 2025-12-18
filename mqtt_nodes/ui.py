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
        row = col.row()
        row.prop(mqtt_settings, "mqtt_enabled", text="MQTT Enabled")
        if mqtt_settings.mqtt_enabled:
            row.label(text="", icon="PLAY")
        else:
            row.label(text="", icon="PAUSE")
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
        
        # Attribute Output properties
        box = layout.box()
        box.label(text="Attribute Output Properties")
        col = box.column()
        for idx, attr_prop in enumerate(scn.mqtt_attribute_outputs):
            row = col.row()
            if not attr_prop.object or not attr_prop.attribute_name or not attr_prop.topic:
                row.alert = True
            row.prop(attr_prop, "object", text="Object")
            row = col.row()
            row.prop(attr_prop, "attribute_name", text="Attribute")
            row = col.row()
            row.prop(attr_prop, "stream_all_instances", text="Stream All Instances")
            if not attr_prop.stream_all_instances:
                row.prop(attr_prop, "attribute_index", text="Index")
            row = col.row()
            row.prop(attr_prop, "topic", text="Topic")
            row = col.row()
            row.prop(attr_prop, "publish_on_frame", text="Publish on Frame")
            if not attr_prop.publish_on_frame:
                row = col.row()
                row.prop(attr_prop, "timer_interval", text="Timer Interval (s)")
            row = col.row()
            row.operator("mqtt.remove_attribute_output_property", text="", icon="CANCEL").property_index = idx
        col = box.column()
        col.operator("mqtt.add_attribute_output_property", text="ADD ATTRIBUTE OUTPUT")
        

