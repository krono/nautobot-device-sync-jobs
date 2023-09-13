# Nautobot Device Sync Jobs

Sync Jobs for Nautobot

# Missing Device Type Components

#### Purpose

Find devices which are missing components that are in the device type template

#### Job Logic

1. Enumerate all devices
2. Get components of each device's device type
3. Compare to already existing device components
4. Report missing components

#### Notes

Uses a few tags to _exempt_ certain devices/device types/... from the sync logic

----

_to be implemented_

# Add Device Type Components 

#### Purpose 

Ensure that components that are added to _device types_ are mirrored on already existing _device_ instances.

#### Job Logic

* *tbd* *

#### Notes



