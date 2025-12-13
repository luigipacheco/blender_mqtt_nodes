# Author: Aurel Wildfellner

bl_info = {
    "name": "MQTT Nodes",
    "author": "Aurel Wildfellner",
    "blender": (3, 4, 0),
    "location": "Node > Toolbox",
    "description": "Drive geometry nodes with MQTT data",
    "warning": "",
    "wiki_url": "",
    "support": 'TESTING',
    "category": "Node"}


import bpy

from bpy.app.handlers import persistent

from bpy.props import (
        StringProperty,
        BoolProperty,
        IntProperty,
        FloatProperty,
        EnumProperty,
        PointerProperty,
        CollectionProperty
        )
from bpy.types import (
        PropertyGroup
        )

from . import ui, operators
from . import mqtt_connection
from . import driver_utils

# Import pending_updates from mqtt_connection
from .mqtt_connection import pending_updates

class MQTTSettingsProp(PropertyGroup):
    broker_host : StringProperty(
            name="Broker Host",
            description="IP or hostname of the broker",
            default=""
            )
    topic_prefix : StringProperty(
            name="Topic Prefix",
            description="Prefix for the topic before all the input topics",
            default="/bl_prop_input/"
            )

def update_input_property(prop, context):
    mqtt_connection.mqtt_connection.pub_manifest()

class MQTTInputProp(PropertyGroup):
    topic : StringProperty(
            name="Topic",
            description="The topic postfix to get input data from",
            default=""
            )
    property_name : StringProperty(
            name="Custom Property Name",
            description="The name of the custom to write to in the scene",
            default="NOT_SET",
            update=update_input_property
            )
    min_value : FloatProperty(
            name="Min Value",
            description="If a float value, limit to this minimum",
            default=0.0
            )
    max_value : FloatProperty(
            name="Max Value",
            description="If a float value, limit to this maximum",
            default=1.0
            )
    do_decay_float : BoolProperty(
            name="Do Decay",
            description="Decay the input value with animation. Must be convertable to float.",
            default=False
            )
    decay_current_value : FloatProperty(
            name="Current Value",
            default=0.0
            )
    decay_hold_peak_frames : IntProperty(
            name="Hold N Frames",
            description="Hold the input value for n frames before decaying",
            default=4
            )
    decay_curr_hold_peak_frames : IntProperty(
            name="Counter for holding n remaining frames",
            default=0
            )
    decay_rate : FloatProperty(
           name="Decay Rate",
           description="Decay per frame",
           default=0.05
           )


def process_mqtt_updates():
    """Process pending MQTT updates in the main thread (similar to Foscap's process_shape_key_updates)"""
    scn = bpy.context.scene
    do_update_drivers = False
    
    while pending_updates:
        var_name, value = pending_updates.pop(0)
        for prop in scn.mqtt_inputs:
            if prop.property_name == var_name:
                print("[MQTT] update var:", var_name, " = ", value)
                scn[var_name] = value
                if prop.do_decay_float:
                    prop.decay_current_value = value
                    prop.decay_curr_hold_peak_frames = prop.decay_hold_peak_frames
                do_update_drivers = True
    
    if do_update_drivers:
        driver_utils.update_all_drivers()
        scn.update_tag()
    
    # Return interval for next timer call (similar to Foscap pattern)
    return 0.01


def updateSceneVarsByFilters(scn):
    do_update_drivers = False
    for input_prop in scn.mqtt_inputs:
        if input_prop.do_decay_float:
            ## decay
            if input_prop.decay_curr_hold_peak_frames > 0:
                input_prop.decay_curr_hold_peak_frames -= 1
            else:
                if scn[input_prop.property_name] == 0.0:
                    break
                next_c_value = input_prop.decay_current_value - \
                        input_prop.decay_rate
                input_prop.decay_current_value = next_c_value
                do_update_drivers = True
                if next_c_value < 0.0:
                    scn[input_prop.property_name] = 0.0
                elif next_c_value < scn[input_prop.property_name]:
                    scn[input_prop.property_name] = next_c_value
    if do_update_drivers:
        driver_utils.update_all_drivers()
        scn.update_tag()


@persistent
def pre_frame_change_handler(scn):
    updateSceneVarsByFilters(scn) 

@persistent
def post_file_load_handler(none_par):
    print("post_file_load_handler !!!!!!!!!")
    scn = bpy.context.scene
    host = scn.mqtt_settings.broker_host
    topic = scn.mqtt_settings.topic_prefix
    # sanity check hostname
    if len(host) > 3:
        mqtt_connection.mqtt_connection.run(host, topic)
        # Register the timer for processing updates if not already registered
        if not bpy.app.timers.is_registered(process_mqtt_updates):
            bpy.app.timers.register(process_mqtt_updates)

classes = [
    MQTTSettingsProp,
    MQTTInputProp,
    ui.MQTTNodePanel,
    ui.MQTTPanel,
    operators.MQTTAddInputProperty,
    operators.MQTTRemoveInputProperty,
    operators.MQTTReconnectClient,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mqtt_settings = PointerProperty(type=MQTTSettingsProp)
    bpy.types.Scene.mqtt_inputs = CollectionProperty(type=MQTTInputProp)
    bpy.app.handlers.load_post.append(post_file_load_handler)
    bpy.app.handlers.frame_change_pre.append(pre_frame_change_handler)
    # Register timer for processing MQTT updates (similar to Foscap pattern)
    if not bpy.app.timers.is_registered(process_mqtt_updates):
        bpy.app.timers.register(process_mqtt_updates)


def unregister():
    mqtt_connection.mqtt_connection.stop()
    # Unregister timer for processing MQTT updates
    if bpy.app.timers.is_registered(process_mqtt_updates):
        bpy.app.timers.unregister(process_mqtt_updates)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mqtt_inputs
    del bpy.types.Scene.mqtt_settings

