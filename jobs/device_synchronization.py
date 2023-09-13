# Identify devices which are missing components from the device type definition
from nautobot.extras.jobs import Job

from nautobot.dcim.models import Device

name = "Device Type Synchronization"



def _no_sync_tag(name, create=True):
  from nautobot.extras.utils import TaggableClassesQuery
  from nautobot.extras.models import Tag
  from django.utils.text import slugify
  slug = f"no-device-type-sync-{slugify(name)}"
  if not create:
    return Tag.objects.get(slug=slug)
  tag, created = Tag.objects.get_or_create(
    name=f"↻̸{name.title()}",
    slug=slug,
    description=f"Device tag to exempt devices and device types from automatic synchronization of {name}",
    color="ffe4e1")
  if created:
    tag.content_types.add(*TaggableClassesQuery().as_queryset().filter(app_label='dcim'))
  return tag

# ensure tags
for tag in ('console ports', 'console server ports', 'power ports', 'power outlets', 'interfaces', 'rear ports', 'front ports', 'device bays'):
  _no_sync_tag(tag, create=True) # for side_effect

class MissingDeviceTypeComponents(Job):
  class Meta:
    name = "Missing Device Type Components"
    description = "Find devices which are missing components that are in the device type template"
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
            self.log_info(device, f"Missing {item} {sorted(missing)!r} (exempted)")
          else:
            self.log_warning(device, f"Missing {item} {sorted(missing)!r}")
