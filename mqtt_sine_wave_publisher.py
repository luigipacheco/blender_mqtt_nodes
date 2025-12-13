#!/usr/bin/env python3
"""
MQTT Sine Wave Publisher for Blender MQTT Nodes Addon

This script publishes a sine wave movement value for z-axis movement.
The addon should be configured with a property name (e.g., "z_position") 
that matches the topic name used here.

Usage:
    python mqtt_sine_wave_publisher.py

Edit the configuration values in the main() function to customize:
    - BROKER_HOST: MQTT broker IP address
    - TOPIC_PREFIX: Topic prefix (default: /bl_prop_input/)
    - PROPERTY_NAME: Property name for z-axis movement
    - FREQUENCY: Sine wave frequency in Hz
    - AMPLITUDE: Sine wave amplitude
    - OFFSET: Sine wave offset
"""

import paho.mqtt.client as mqtt
import time
import math
import sys


class SineWavePublisher:
    def __init__(self, broker_host, topic_prefix, property_name, frequency=0.5, amplitude=1.0, offset=0.0):
        self.broker_host = broker_host
        self.topic_prefix = topic_prefix
        self.property_name = property_name
        self.frequency = frequency  # Hz
        self.amplitude = amplitude
        self.offset = offset
        self.running = False
        
        # Ensure topic prefix ends with /
        if not self.topic_prefix.endswith('/'):
            self.topic_prefix += '/'
        
        # Full topic path
        self.topic = f"{self.topic_prefix}{self.property_name}"
        
        # Create MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] Connected to broker at {self.broker_host}")
            print(f"[MQTT] Publishing to topic: {self.topic}")
        else:
            print(f"[MQTT] Failed to connect, return code {rc}")
            sys.exit(1)
    
    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"[MQTT] Unexpected disconnection (rc={rc})")
        else:
            print("[MQTT] Disconnected")
    
    def connect(self):
        """Connect to the MQTT broker"""
        try:
            self.client.connect(self.broker_host, 1883, 60)
            self.client.loop_start()
            # Wait a moment for connection to establish
            time.sleep(0.5)
        except Exception as e:
            print(f"[ERROR] Failed to connect to MQTT broker: {e}")
            sys.exit(1)
    
    def publish_sine_wave(self, duration=None, update_rate=30):
        """
        Publish sine wave values continuously
        
        Args:
            duration: How long to publish (in seconds). None = infinite
            update_rate: Updates per second (default: 30 Hz for smooth animation)
        """
        self.running = True
        start_time = time.time()
        period = 1.0 / self.frequency  # Period in seconds
        
        print(f"[INFO] Starting sine wave publisher")
        print(f"       Frequency: {self.frequency} Hz")
        print(f"       Amplitude: {self.amplitude}")
        print(f"       Offset: {self.offset}")
        print(f"       Update rate: {update_rate} Hz")
        print(f"       Press Ctrl+C to stop")
        
        try:
            while self.running:
                elapsed = time.time() - start_time
                
                # Calculate sine wave value
                # sin(2π * frequency * time)
                sine_value = math.sin(2 * math.pi * self.frequency * elapsed)
                
                # Scale by amplitude and add offset
                value = self.amplitude * sine_value + self.offset
                
                # Publish the value
                self.client.publish(self.topic, str(value), qos=0)
                
                # Print value occasionally (every second)
                if int(elapsed) != int(elapsed - 1.0/update_rate):
                    print(f"[{elapsed:.1f}s] Value: {value:.4f}")
                
                # Check if duration limit reached
                if duration is not None and elapsed >= duration:
                    break
                
                # Sleep to maintain update rate
                time.sleep(1.0 / update_rate)
                
        except KeyboardInterrupt:
            print("\n[INFO] Stopping publisher...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop publishing and disconnect"""
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        print("[INFO] Publisher stopped")


def main():
    # Configuration - edit these values as needed
    BROKER_HOST = '192.168.1.20'
    TOPIC_PREFIX = 'blender/'
    PROPERTY_NAME = 'z_position'
    FREQUENCY = 0.5  # Hz (one cycle per 2 seconds)
    AMPLITUDE = 1.0
    OFFSET = 0.0
    UPDATE_RATE = 60.0  # Hz
    DURATION = None  # None = infinite, or set to number of seconds
    
    # Create publisher
    publisher = SineWavePublisher(
        broker_host=BROKER_HOST,
        topic_prefix=TOPIC_PREFIX,
        property_name=PROPERTY_NAME,
        frequency=FREQUENCY,
        amplitude=AMPLITUDE,
        offset=OFFSET
    )
    
    # Connect and publish
    publisher.connect()
    publisher.publish_sine_wave(duration=DURATION, update_rate=UPDATE_RATE)


if __name__ == '__main__':
    main()

