# Identify devices which are missing components from the device type definition
from nautobot.apps.jobs import Job, MultiObjectVar, register_jobs

from nautobot.dcim.models import Device, DeviceType, ConsolePort, ConsoleServerPort, PowerPort, PowerOutlet, Interface, RearPort, FrontPort, DeviceBay

name = 'Device Type Synchronization'



def _no_sync_tag(name, create=True):
  from nautobot.extras.utils import TaggableClassesQuery
  from nautobot.extras.models import Tag
  tag_name = f'↻̸{name.title()}'
  if not create:
    return Tag.objects.get_by_natural_key(tag_name)
  tag, created = Tag.objects.get_or_create(
    name=tag_name,
    description=f'Device tag to exempt devices and device types from automatic synchronization of {name}',
    color='ffe4e1')
  if created:
    tag.content_types.add(*TaggableClassesQuery().as_queryset().filter(app_label='dcim'))
  return tag

# ensure tags
for tag in ('console ports', 'console server ports', 'power ports', 'power outlets', 'interfaces', 'rear ports', 'front ports', 'device bays'):
  _no_sync_tag(tag, create=True) # for side_effect

class MissingDeviceTypeComponents(Job):
  class Meta:
    name = 'Missing Device Type Components'
    description = 'Find devices which are missing components that are in the device type template'
    read_only = True
    has_sensitive_variables = False

  def run(self):
    for device in Device.objects.all():
      dt = device.device_type

      for name in (
        'console ports',
        'console server ports',
        'power ports',
        'power outlets',
        'interfaces',
        'rear ports',
        'front ports',
        'device bays',
    ):
        anti_tag = _no_sync_tag(name, create=False)
        item = name.replace(' ', '_')
        names = {i.name for i in getattr(device, item).all()}
        templatenames = {i.name for i in getattr(dt, item + '_templates').all()}
        missing = templatenames - names
        if missing:
          if anti_tag in dt.tags.union(device.tags.all()):
            self.logger.info(device, f'Missing {item} {sorted(missing)!r} (exempted)')
          else:
            self.logger.warning(device, f'Missing {item} {sorted(missing)!r}')

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
      for klass, item, templateitem, anti_tag in [
        (ConsolePort, 'console ports')
        (ConsoleServerPort 'console server ports')
        (PowerPort, 'power ports')
        (PowerOutlet, 'power outlets')
        (Interface, 'interfaces')
        (RearPort, 'rear ports')
        (FrontPort, 'front ports')
        (DeviceBay, 'device bays')
      ]:
        anti_tag = _no_sync_tag(name)
        item = name.replace(' ', '_')
        if anti_tag in dt.tags.union(device.tags.all()):
          self.logger.info(device, f'{item} exempted')
          continue
        names = {i.name for i in getattr(device, item).all()}
        templates = getattr(dt, item + '_template').all()
        items = [
          template.instantiate(device)
          for template in templates
          if template.name not in names
        ]
        if items:
          klass.objects.bulk_create(items)
          self.logger.success(device, f'Created {len(items)} {item}')

register_jobs(MissingDeviceTypeComponents, AddDeviceTypeComponents)
