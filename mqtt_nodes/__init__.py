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
import json

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
    mqtt_enabled : BoolProperty(
            name="MQTT Enabled",
            description="Enable/disable all MQTT input and output updates",
            default=True
            )

def update_input_property(prop, context):
    mqtt_connection.mqtt_connection.pub_manifest()

def update_output_property(prop, context):
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


class MQTTOutputProp(PropertyGroup):
    data_path : StringProperty(
            name="Data Path",
            description="Python data path to the property (e.g., 'bpy.data.objects[\"Cube\"].location[2]')",
            default="",
            update=update_output_property
            )
    topic : StringProperty(
            name="Topic",
            description="The topic postfix to publish the property to",
            default="",
            update=update_output_property
            )
    publish_on_frame : BoolProperty(
            name="Publish on Frame",
            description="Publish the property value on each frame change",
            default=True
            )
    timer_interval : FloatProperty(
            name="Timer Interval",
            description="Interval in seconds to publish when not publishing on frame (0.01 = 100Hz)",
            default=0.1,
            min=0.01,
            max=10.0
            )


def get_attribute_names(self, context):
    """Get list of attribute names for the selected object"""
    items = [("NONE", "None", "")]
    if self.object and hasattr(self.object, 'data') and hasattr(self.object.data, 'attributes'):
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = depsgraph.objects.get(self.object.name)
        if obj_eval and obj_eval.data and hasattr(obj_eval.data, 'attributes'):
            for attr in obj_eval.data.attributes:
                items.append((attr.name, attr.name, ""))
    return items


class MQTTAttributeOutputProp(PropertyGroup):
    object : PointerProperty(
            name="Object",
            description="The object with the geometry node attribute",
            type=bpy.types.Object,
            update=update_output_property
            )
    attribute_name : StringProperty(
            name="Attribute Name",
            description="Name of the attribute to stream",
            default="",
            update=update_output_property
            )
    attribute_index : IntProperty(
            name="Index",
            description="Index of the attribute element to stream (-1 for all instances)",
            default=0,
            min=-1,
            update=update_output_property
            )
    stream_all_instances : BoolProperty(
            name="Stream All Instances",
            description="Stream all instances of the attribute as an array",
            default=False,
            update=update_output_property
            )
    topic : StringProperty(
            name="Topic",
            description="The topic postfix to publish the attribute to",
            default="",
            update=update_output_property
            )
    publish_on_frame : BoolProperty(
            name="Publish on Frame",
            description="Publish the attribute value on each frame change",
            default=True
            )
    timer_interval : FloatProperty(
            name="Timer Interval",
            description="Interval in seconds to publish when not publishing on frame (0.01 = 100Hz)",
            default=0.1,
            min=0.01,
            max=10.0
            )


def process_mqtt_updates():
    """Process pending MQTT updates in the main thread (similar to Foscap's process_shape_key_updates)"""
    scn = bpy.context.scene
    # Skip processing if MQTT is paused
    if not scn.mqtt_settings.mqtt_enabled:
        return 0.01
    
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
    # Skip decay updates if MQTT is paused
    if not scn.mqtt_settings.mqtt_enabled:
        return
    
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


def publish_attribute_output_value(attr_prop, client, context):
    """Publish a geometry node attribute value to MQTT"""
    if not attr_prop.object or not attr_prop.attribute_name or not attr_prop.topic:
        return False
    
    try:
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = depsgraph.objects.get(attr_prop.object.name)
        if not obj_eval or not obj_eval.data or not hasattr(obj_eval.data, 'attributes'):
            return False
        
        attr = obj_eval.data.attributes.get(attr_prop.attribute_name)
        if not attr:
            return False
        
        # Determine if attribute has .value or .vector
        has_value = hasattr(attr.data[0], 'value') if len(attr.data) > 0 else False
        has_vector = hasattr(attr.data[0], 'vector') if len(attr.data) > 0 else False
        
        if attr_prop.stream_all_instances or attr_prop.attribute_index < 0:
            # Stream all instances
            values = []
            for i in range(len(attr.data)):
                if has_vector:
                    vec = attr.data[i].vector
                    values.append([float(vec[0]), float(vec[1]), float(vec[2])])
                elif has_value:
                    values.append(float(attr.data[i].value))
                else:
                    return False
            
            payload = json.dumps(values)
        else:
            # Stream single index
            idx = attr_prop.attribute_index
            if idx >= len(attr.data):
                return False
            
            if has_vector:
                vec = attr.data[idx].vector
                payload = json.dumps([float(vec[0]), float(vec[1]), float(vec[2])])
            elif has_value:
                payload = str(float(attr.data[idx].value))
            else:
                return False
        
        # Publish to topic
        full_topic = mqtt_connection.mqtt_connection._topic_prefix + attr_prop.topic
        client.publish(full_topic, payload, qos=0, retain=False)
        return True
        
    except (AttributeError, KeyError, TypeError, ValueError, IndexError) as e:
        return False


def publish_output_property_value(output_prop, client):
    """Publish a single output property value to MQTT"""
    if not output_prop.data_path or not output_prop.topic:
        return False
    
    data_path = output_prop.data_path
    
    # Try to evaluate the data path and get the property value
    try:
        # Evaluate the data path safely (only allow access to bpy and standard types)
        # This allows paths like: bpy.data.objects["Cube"].location[2]
        value = eval(data_path, {"__builtins__": {}, "bpy": bpy})
        
        # Skip None values
        if value is None:
            return False
        
        # Skip empty dicts and empty objects
        if isinstance(value, dict) and len(value) == 0:
            return False
        
        # Convert to appropriate format
        if isinstance(value, (list, tuple)):
            # For vector properties, publish as JSON array
            try:
                payload = json.dumps([float(v) for v in value])
            except (TypeError, ValueError):
                # If conversion fails, skip this publish
                return False
        elif isinstance(value, (int, float)):
            # For numeric values, publish as string
            payload = str(value)
        elif isinstance(value, bool):
            # For boolean values, publish as string
            payload = str(value)
        elif isinstance(value, str):
            # For string values, publish as-is
            payload = value
        else:
            # For other types (dict, complex objects), skip publishing
            # to avoid publishing empty dicts or unexpected data
            return False
        
        # Publish to topic
        full_topic = mqtt_connection.mqtt_connection._topic_prefix + output_prop.topic
        client.publish(full_topic, payload, qos=0, retain=False)
        return True
        
    except (AttributeError, KeyError, TypeError, ValueError, NameError, SyntaxError) as e:
        # Property doesn't exist, can't be accessed, or invalid syntax
        # Silently skip - this is expected for invalid data paths
        return False


def publish_output_properties(scn, context=None):
    """Publish all output properties that have publish_on_frame enabled"""
    # Skip publishing if MQTT is paused
    if not scn.mqtt_settings.mqtt_enabled:
        return
    
    client = mqtt_connection.mqtt_connection._client
    if not client:
        return
    # Check if client is connected
    try:
        if not client.is_connected():
            return
    except:
        return
    
    if context is None:
        context = bpy.context
    
    for output_prop in scn.mqtt_outputs:
        if not output_prop.publish_on_frame:
            continue
        publish_output_property_value(output_prop, client)
    
    # Publish attribute outputs
    for attr_prop in scn.mqtt_attribute_outputs:
        if not attr_prop.publish_on_frame:
            continue
        publish_attribute_output_value(attr_prop, client, context)


def publish_timer_output_properties():
    """Timer function to publish output properties that use timer-based publishing"""
    scn = bpy.context.scene
    context = bpy.context
    # Skip publishing if MQTT is paused
    if not scn.mqtt_settings.mqtt_enabled:
        return 0.1
    
    client = mqtt_connection.mqtt_connection._client
    if not client:
        return 0.1  # Default interval if not connected
    # Check if client is connected
    try:
        if not client.is_connected():
            return 0.1
    except:
        return 0.1
    
    # Find the minimum timer interval from all timer-based output properties
    min_interval = 10.0  # Default to 10 seconds if no timer properties
    
    for output_prop in scn.mqtt_outputs:
        if not output_prop.data_path or not output_prop.topic:
            continue
        if output_prop.publish_on_frame:
            continue  # Skip frame-based publishing
        
        # Publish this property
        publish_output_property_value(output_prop, client)
        
        # Track minimum interval
        if output_prop.timer_interval < min_interval:
            min_interval = output_prop.timer_interval
    
    # Publish timer-based attribute outputs
    for attr_prop in scn.mqtt_attribute_outputs:
        if not attr_prop.object or not attr_prop.attribute_name or not attr_prop.topic:
            continue
        if attr_prop.publish_on_frame:
            continue  # Skip frame-based publishing
        
        # Publish this attribute
        publish_attribute_output_value(attr_prop, client, context)
        
        # Track minimum interval
        if attr_prop.timer_interval < min_interval:
            min_interval = attr_prop.timer_interval
    
    # Return the minimum interval for next timer call
    return min_interval if min_interval < 10.0 else 0.1


@persistent
def pre_frame_change_handler(scn):
    updateSceneVarsByFilters(scn)
    # Publish output properties on frame change
    publish_output_properties(scn, bpy.context) 

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
        # Register the timer for publishing output properties if not already registered
        if not bpy.app.timers.is_registered(publish_timer_output_properties):
            bpy.app.timers.register(publish_timer_output_properties)

classes = [
    MQTTSettingsProp,
    MQTTInputProp,
    MQTTOutputProp,
    MQTTAttributeOutputProp,
    ui.MQTTNodePanel,
    ui.MQTTPanel,
    operators.MQTTAddInputProperty,
    operators.MQTTRemoveInputProperty,
    operators.MQTTAddOutputProperty,
    operators.MQTTRemoveOutputProperty,
    operators.MQTTAddAttributeOutputProperty,
    operators.MQTTRemoveAttributeOutputProperty,
    operators.MQTTReconnectClient,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mqtt_settings = PointerProperty(type=MQTTSettingsProp)
    bpy.types.Scene.mqtt_inputs = CollectionProperty(type=MQTTInputProp)
    bpy.types.Scene.mqtt_outputs = CollectionProperty(type=MQTTOutputProp)
    bpy.types.Scene.mqtt_attribute_outputs = CollectionProperty(type=MQTTAttributeOutputProp)
    bpy.app.handlers.load_post.append(post_file_load_handler)
    bpy.app.handlers.frame_change_pre.append(pre_frame_change_handler)
    # Register timer for processing MQTT updates (similar to Foscap pattern)
    if not bpy.app.timers.is_registered(process_mqtt_updates):
        bpy.app.timers.register(process_mqtt_updates)
    # Register timer for publishing output properties
    if not bpy.app.timers.is_registered(publish_timer_output_properties):
        bpy.app.timers.register(publish_timer_output_properties)


def unregister():
    mqtt_connection.mqtt_connection.stop()
    # Unregister timer for processing MQTT updates
    if bpy.app.timers.is_registered(process_mqtt_updates):
        bpy.app.timers.unregister(process_mqtt_updates)
    # Unregister timer for publishing output properties
    if bpy.app.timers.is_registered(publish_timer_output_properties):
        bpy.app.timers.unregister(publish_timer_output_properties)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mqtt_inputs
    del bpy.types.Scene.mqtt_outputs
    del bpy.types.Scene.mqtt_attribute_outputs
    del bpy.types.Scene.mqtt_settings

