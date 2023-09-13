# Identify devices which are missing components from the device type definition
from nautobot.extras.jobs import Job

from nautobot.dcim.models import Device
from nautobot.extras.models import Tag
from nautobot.extras.utils import TaggableClassesQuery

name = "Device Type Synchronization"



def _no_sync_tag(name, create=False):
  from django.utils.text import slugify
  args = {
    'name': f"↻̸{name.title()}",
    'slug': f"no-device-type-sync-{slugify(name)}",
    'description': f"Device tag to exempt devices and device types from automatic synchronization of {name}",
    'color': "ffe4e1",
    'content_types': TaggableClassesQuery().as_queryset().filter(app_label='dcim')
  }
  if create:
    return Tag.objects.get_or_create(**args)
  else
    return Tag.objects.get(**args)

# ensure tags
for tag in ('console ports', 'console server ports', 'power ports', 'power outlets', 'interfaces', 'rear ports', 'front ports', 'device bays'):
  _no_sync_tag(name, create=True) # for side_effect

class MissingDeviceTypeComponents(Job):
  class Meta:
    name = "Missing Device Type Components"
    description = "Find devices which are missing components that are in the device type template"
    read_only = True

  def test_find_missing(self):
    for device in Device.objects.all():
      dt = device.device_type

      for item, templateitem, anti_tag in [
        ('consoleports', 'consoleporttemplates', _no_sync_tag('console ports')),
        ('consoleserverports', 'consoleserverporttemplates', _no_sync_tag('console server ports')),
        ('powerports', 'powerporttemplates', _no_sync_tag('power ports')),
        ('poweroutlets', 'poweroutlettemplates', _no_sync_tag('power outlets')),
        ('interfaces', 'interfacetemplates', _no_sync_tag('interfaces')),
        ('rearports', 'rearporttemplates', _no_sync_tag('rear ports')),
        ('frontports', 'frontporttemplates', _no_sync_tag('front ports')),
        ('devicebays', 'devicebaytemplates', _no_sync_tag('device bays')),
      ]:
        names = {i.name for i in getattr(device, item).all()}
        templatenames = {i.name for i in getattr(dt, templateitem).all()}
        missing = templatenames - names
        if missing:
          if anti_tag in [dt.tags + device.tags]:
            self.log_info(device, f"Missing {item} {sorte(missing)!r} (exempted)")
          else:
            self.log_warning(device, f"Missing {item} {sorte(missing)!r}")
