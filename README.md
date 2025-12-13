# Blender MQTT Nodes

A Blender addon that enables bidirectional communication between Blender and MQTT brokers. Drive geometry nodes, object properties, and animations with MQTT data, and stream Blender properties to MQTT topics in real-time.

## Features

- **MQTT Input Properties**: Receive MQTT messages and drive Blender properties/animations
- **MQTT Output Properties**: Stream any Blender property to MQTT topics
- **Real-time Updates**: Timer-based or frame-based publishing options
- **Driver Integration**: Works seamlessly with Blender's driver system
- **Decay Animation**: Optional decay effects for input values

## Installation

1. Download or clone this repository
2. In Blender, go to **Edit → Preferences → Add-ons**
3. Click **Install...** and select the `mqtt_nodes` folder
4. Enable the "MQTT Nodes" addon

## Requirements

- Blender 3.4 or later
- Python package: `paho-mqtt` (install via pip: `pip install paho-mqtt`)
- An MQTT broker (e.g., Mosquitto, HiveMQ, etc.)

## Configuration

### MQTT Connection Settings

1. Go to **Properties → Scene → MQTT** panel
2. Set **Broker Host**: IP address or hostname of your MQTT broker (e.g., `localhost` or `192.168.1.100`)
3. Set **Topic Prefix**: Prefix for all topics (e.g., `/blender/` or `/bl_prop_input/`)
4. Click **Reconnect** to establish the connection

## MQTT Input Properties (Receiving Data)

Receive MQTT messages and use them to drive Blender properties.

### Setup

1. In the **MQTT** panel, under **Input Properties**, click **ADD**
2. Set **Custom Property Name**: The name of the scene property to create (e.g., `posz`, `rotation_x`)
3. The property will be created on the scene and updated when MQTT messages arrive

### MQTT Topic Format

Messages should be published to: `{topic_prefix}{property_name}`

For example:
- Topic Prefix: `/blender/`
- Property Name: `posz`
- Full Topic: `/blender/posz`
- Message: `10.5` (a float value)

### Using Input Properties in Drivers

1. Add a driver to any property (right-click → **Add Driver**)
2. Set driver type to **Scripted Expression**
3. Use the expression:
   ```
   bpy.data.scenes["Scene"]["your_property_name"]
   ```
   Replace `"Scene"` with your actual scene name and `"your_property_name"` with your property name.

### Decay Animation

Enable decay for float values:
- **Do Decay**: Enable decay animation
- **Hold N Frames**: Number of frames to hold the peak value before decaying
- **Decay Rate**: Amount to decay per frame

## MQTT Output Properties (Publishing Data)

Stream any Blender property to MQTT topics in real-time.

### Setup

1. In the **MQTT** panel, under **Output Properties**, click **ADD OUTPUT**
2. Set **Data Path**: Python data path to the property you want to stream
   - Examples:
     - `bpy.data.objects["Cube"].location[2]` - Z position of Cube
     - `bpy.data.objects["Cube"].location` - Full location vector
     - `bpy.data.objects["Cube"].rotation_euler[1]` - Y rotation
     - `bpy.data.scenes["Scene"].frame_current` - Current frame number
     - `bpy.data.objects["Cube"]["custom_prop"]` - Custom property
3. Set **Topic**: The topic postfix to publish to (e.g., `posz`, `location`, `frame`)
4. Choose publishing mode:
   - **Publish on Frame**: Publishes when the frame changes (for animation)
   - **Timer Interval**: Publishes at regular intervals (for real-time updates)

### Publishing Modes

#### Frame-based Publishing
- Publishes when the animation frame changes
- Best for animation playback
- Enable **Publish on Frame**

#### Timer-based Publishing
- Publishes at regular intervals (e.g., 0.1s = 10Hz, 0.01s = 100Hz)
- Best for real-time/interactive updates
- Disable **Publish on Frame** and set **Timer Interval**

### Data Format

- **Single values** (int, float): Published as string
- **Vectors** (location, rotation, etc.): Published as JSON array
- **Strings**: Published as-is

## Examples

### Example 1: Drive Object Position with MQTT

**Input Setup:**
- Property Name: `cube_z`
- Topic: (empty, uses property name)
- Full Topic: `/blender/cube_z`

**Driver Setup:**
1. Select your object
2. Add driver to Location Z
3. Expression: `bpy.data.scenes["Scene"]["cube_z"]`

**Publish to MQTT:**
```bash
mosquitto_pub -h localhost -t /blender/cube_z -m "5.0"
```

### Example 2: Stream Object Position to MQTT

**Output Setup:**
- Data Path: `bpy.data.objects["Cube"].location[2]`
- Topic: `cube_z`
- Publish on Frame: Disabled
- Timer Interval: `0.1` (10Hz)

**Result:** The Z position of "Cube" is published to `/blender/cube_z` 10 times per second.

### Example 3: Stream Full Location Vector

**Output Setup:**
- Data Path: `bpy.data.objects["Cube"].location`
- Topic: `cube_location`
- Publish on Frame: Enabled

**Result:** The full location vector `[x, y, z]` is published as JSON array to `/blender/cube_location` on each frame.

### Example 4: Stream Current Frame

**Output Setup:**
- Data Path: `bpy.data.scenes["Scene"].frame_current`
- Topic: `frame`
- Publish on Frame: Enabled

**Result:** The current frame number is published to `/blender/frame` on each frame change.

## Troubleshooting

### Connection Issues
- Verify the broker host is correct and accessible
- Check that the MQTT broker is running
- Ensure port 1883 is not blocked by firewall
- Click **Reconnect** if connection fails

### Properties Not Updating
- Verify the topic name matches exactly (case-sensitive)
- Check that messages are being published to the correct topic
- Ensure the property name is set (not "NOT_SET")
- Check the Blender console for error messages

### Driver Not Working
- Verify the scene name in the expression matches your actual scene name
- Check that the property exists: `bpy.data.scenes["Scene"]["property_name"]` in Python console
- Ensure at least one MQTT message has been received (properties are created on first message)

### Empty `{}` Messages
- This happens when a data path evaluates to an empty dict or invalid type
- Check your data path syntax
- Ensure the property exists and is accessible
- The addon now skips publishing invalid values automatically

## Technical Details

### Thread Safety
- MQTT communication runs in a separate thread
- Property updates are queued and processed in the main thread
- Driver updates are triggered automatically after property changes

### Performance
- Timer-based publishing uses the minimum interval from all active output properties
- Frame-based publishing only occurs on frame changes
- Invalid data paths are silently skipped to avoid errors

## License

See LICENSE file for details.

## Credits

**Original Author:** Aurel Wildfellner

This addon was originally created by Aurel Wildfellner to drive geometry nodes with MQTT data. Additional features for output property streaming have been added.

## Support

This addon is in TESTING status. Report issues or contribute improvements via the repository.
