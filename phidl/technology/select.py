''' This module interfaces with KLayout
'''
import os
from phidl.utilities import xml_to_dict
from . import reload_layers, reload_properties


#### What technologies are in KLayout? ####

#: key = technology name; value = path to where its files are located
available_tech_paths = dict()
klayout_application_path = os.path.expanduser('~/.klayout')  # This might not work on Windows
if not os.path.isdir(klayout_application_path):
    raise ImportError('KLayout does not seem to be installed.\nDid not find "~/.klayout"')
for root, dirnames, filenames in os.walk(os.path.join(klayout_application_path, 'salt'), followlinks=True):
    if os.path.split(root)[1] == 'tech':
        for technology_name in dirnames:
            available_tech_paths[technology_name] = os.path.join(root, technology_name)



#### technology selection handling ####

def klayout_last_open_technology():
    rc_file = os.path.join(klayout_application_path, 'klayoutrc')
    with open(rc_file, 'r') as file:
        rc_dict = xml_to_dict(file.read())
    return rc_dict['config']['initial-technology']


_active_technology = None
def get_technology_name():
    return _active_technology


def get_technology_path():
    return available_tech_paths[_active_technology]


def set_technology_name(technology_name):
    if technology_name not in available_tech_paths.keys():
        raise ValueError((f'{technology_name} was not found in available technologies:' +
                         ', '.join(available_tech_paths.keys())))
    global _active_technology
    _active_technology = technology_name
    reload_layers()
    reload_properties()




