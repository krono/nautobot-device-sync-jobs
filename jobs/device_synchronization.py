# Identify devices which are missing components from the device type definition
from nautobot.extras.jobs import Job, MultiObjectVar

from nautobot.dcim.models import Device, DeviceType, ConsolePort, ConsoleServerPort, PowerPort, PowerOutlet, Interface, RearPort, FrontPort, DeviceBay

name = 'Device Type Synchronization'



def _no_sync_tag(name, create=True):
  from nautobot.extras.utils import TaggableClassesQuery
  from nautobot.extras.models import Tag
  from django.utils.text import slugify
  slug = f'no-device-type-sync-{slugify(name)}'
  if not create:
    return Tag.objects.get(slug=slug)
  tag, created = Tag.objects.get_or_create(
    name=f'↻̸{name.title()}',
    slug=slug,
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

  def test_find_missing(self):
    for device in Device.objects.all():
      dt = device.device_type

      for item, templateitem, anti_tag in [
        ('consoleports', 'consoleporttemplates', _no_sync_tag('console ports', create=False)),
        ('consoleserverports', 'consoleserverporttemplates', _no_sync_tag('console server ports', create=False)),
        ('powerports', 'powerporttemplates', _no_sync_tag('power ports', create=False)),
        ('poweroutlets', 'poweroutlettemplates', _no_sync_tag('power outlets', create=False)),
        ('interfaces', 'interfacetemplates', _no_sync_tag('interfaces', create=False)),
        ('rearports', 'rearporttemplates', _no_sync_tag('rear ports', create=False)),
        ('frontports', 'frontporttemplates', _no_sync_tag('front ports', create=False)),
        ('devicebays', 'devicebaytemplates', _no_sync_tag('device bays', create=False)),
      ]:
        names = {i.name for i in getattr(device, item).all()}
        templatenames = {i.name for i in getattr(dt, templateitem).all()}
        missing = templatenames - names
        if missing:
          if anti_tag in dt.tags.union(device.tags.all()):
            self.log_info(device, f'Missing {item} {sorted(missing)!r} (exempted)')
          else:
            self.log_warning(device, f'Missing {item} {sorted(missing)!r}')

class AddDeviceTypeComponents(Job):
  class Meta:
    name = 'Add Missing Device Type Components'
    description = 'Add components to devices which are missing compared to the device type template'
    has_sensitive_variables = False

  devices = MultiObjectVar(model=Device)#, required=False, default=[], null_option='None')
  # device_types = MultiObjectVar(model=DeviceType, required=False, default=[], null_option='None')
  # components = MultiObjectVar(model=Device, required=False, default=[], null_option='None')

  def run(self, data, commit):
    for device in data['devices']:
      dt = device.device_type

      # Based on Device.save():
      # "If this is a new Device, instantiate all of the related components per the DeviceType definition""
      # Note that ordering is important: e.g. PowerPort before PowerOutlet, RearPort before FrontPort
      for klass, item, templateitem, anti_tag in [
        (ConsolePort, 'consoleports', 'consoleporttemplates', _no_sync_tag('console ports')),
        (ConsoleServerPort, 'consoleserverports', 'consoleserverporttemplates', _no_sync_tag('console server ports')),
        (PowerPort, 'powerports', 'powerporttemplates', _no_sync_tag('power ports')),
        (PowerOutlet, 'poweroutlets', 'poweroutlettemplates', _no_sync_tag('power outlets')),
        (Interface, 'interfaces', 'interfacetemplates', _no_sync_tag('interfaces')),
        (RearPort, 'rearports', 'rearporttemplates', _no_sync_tag('rear ports')),
        (FrontPort, 'frontports', 'frontporttemplates', _no_sync_tag('front ports')),
        (DeviceBay,'devicebays', 'devicebaytemplates', _no_sync_tag('device bays')),
      ]:
        if anti_tag in dt.tags.union(device.tags.all()):
          self.log_info(device, f'{item} exempted')
          continue
        names = {i.name for i in getattr(device, item).all()}
        templates = getattr(dt, templateitem).all()
        items = [
          template.instantiate(device)
          for template in templates
          if template.name not in names
        ]
        if items:
          klass.objects.bulk_create(items)
          self.log_success('%s (%d): created %d %s' % (device.name, device.id, len(items), item))
