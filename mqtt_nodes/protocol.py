import bpy

import json


def get_manifest():
    scn = bpy.context.scene
    inp_property_descs = []
    for prop in scn.mqtt_inputs:
        name = prop.property_name
        inp_property_descs.append({"name" : name})
    
    out_property_descs = []
    for prop in scn.mqtt_outputs:
        if prop.data_path and prop.topic:
            out_property_descs.append({
                "data_path": prop.data_path,
                "topic": prop.topic
            })
    
    manifest = {
        "input_properties" : inp_property_descs,
        "output_properties" : out_property_descs
    }
    return json.dumps(manifest)

