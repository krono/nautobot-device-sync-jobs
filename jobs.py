# Identify devices which are missing components from the device type definition
from nautobot.apps.jobs import Job, MultiObjectVar, register_jobs

from nautobot.dcim.models import Device, DeviceType, ConsolePort, ConsoleServerPort, PowerPort, PowerOutlet, Interface, RearPort, FrontPort, DeviceBay

name = 'Device Type Synchronization'



def _no_sync_tag(name, create=True):
  from nautobot.extras.utils import TaggableClassesQuery
  from nautobot.extras.models import Tag
  plural_name = name + 's'
  tag_name = f'↻̸{plural_name.title()}'
  if not create:
    return Tag.objects.get(name=tag_name)
  tag, created = Tag.objects.get_or_create(
    name=tag_name,
    description=f'Device tag to exempt devices and device types from automatic synchronization of {plural_name}',
    color='ffe4e1')
  if created:
    tag.content_types.add(*TaggableClassesQuery().as_queryset().filter(app_label='dcim'))
  return tag

COMPONENTS = {
    'console port': ConsolePort,
    'console server port': ConsoleServerPort,
    'power port': PowerPort,
    'power outlet': PowerOutlet,
    'interface': Interface,
    'rear port': RearPort,
    'front port': FrontPort,
    'device bay': DeviceBay,
}

# ensure tags
for tag in COMPONENTS.keys():
  _no_sync_tag(tag, create=True) # for side_effect

class MissingDeviceTypeComponents(Job):
  class Meta:
    name = 'Missing Device Type Components'
    description = 'Find devices which are missing components that are in the device type template'
    read_only = True
    has_sensitive_variables = False

  def run(self):
    devices = []
    for device in Device.objects.all():
      dt = device.device_type

      for name in COMPONENTS.keys():
        anti_tag = _no_sync_tag(name, create=False)
        item = name.replace(' ', '_')
        names = {i.name for i in getattr(device, item + 's').all()}
        templatenames = {i.name for i in getattr(dt, item + '_templates').all()}
        missing = templatenames - names
        if missing:
          if anti_tag in dt.tags.union(device.tags.all()):
            self.logger.info(f'Missing {item} {sorted(missing)!r} (exempted)', extra={"object": device})
          else:
            self.logger.warning(f'Missing {item} {sorted(missing)!r}', extra={"object": device})
            devices.append(device)
    return devices

class AddDeviceTypeComponents(Job):
  class Meta:
    name = 'Add Missing Device Type Components'
    description = 'Add components to devices which are missing compared to the device type template'
    has_sensitive_variables = False

  devices = MultiObjectVar(model=Device)#, required=False, default=[], null_option='None')
  # device_types = MultiObjectVar(model=DeviceType, required=False, default=[], null_option='None')
  # components = MultiObjectVar(model=Device, required=False, default=[], null_option='None')

  def run(self, devices):
    for device in devices:
      dt = device.device_type

      # Based on Device.save():
      # "If this is a new Device, instantiate all of the related components per the DeviceType definition""
      # Note that ordering is important: e.g. PowerPort before PowerOutlet, RearPort before FrontPort
      for name, klasse in COMPONENTS.items():
        anti_tag = _no_sync_tag(name)
        item = name.replace(' ', '_')
        if anti_tag in dt.tags.union(device.tags.all()):
          self.logger.info(f'{item} exempted', extra={"object": device})
          continue
        names = {i.name for i in getattr(device, item + 's').all()}
        templates = getattr(dt, item + '_template').all()
        items = [
          template.instantiate(device)
          for template in templates
          if template.name not in names
        ]
        if items:
          klass.objects.bulk_create(items)
          self.logger.success(f'Created {len(items)} {item}', extra={"object": device})

register_jobs(MissingDeviceTypeComponents, AddDeviceTypeComponents)
