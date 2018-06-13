''' This module interfaces with KLayout
'''

# Is SiEPIC Tools installed?
import os
klayout_dir = os.path.expanduser('~/.klayout/salt')
if not os.path.isdir(klayout_dir):
    raise ImportError('KLayout does not seem to be installed.\nDid not find "~/.klayout"')

available_technologies = []
for root, dirnames, filenames in os.walk(klayout_dir, followlinks=True):
    if os.path.split(root)[1] == 'tech':
        available_technologies.extend(dirnames)

from .device_layout import Layer
def get_technology_by_name(tech_name):
    klayout_techdef = tech_top()
    technology = {}
    technology['technology_name'] = klayout_techdef['technology']['name']
    technology['dbu'] = klayout_techdef['technology']['dbu']
    # technology['base_path'] = os.path.expanduser(klayout_techdef['technology']['original_base_path'])
    technology['base_path'] = TECHNOLOGY_PATH
    lyp_file = os.path.join(TECHNOLOGY_PATH, klayout_techdef['technology']['layer-properties_file'])
    with open(lyp_file, 'r') as fx:
        layer_dict = xml_to_dict(fx.read())['layer-properties']['properties']
    # technology['layers'] = layer_dict
    for k in layer_dict:
        layerInfo = k['source'].split('@')[0]
        # if 'group-members' in k:
        #     # encoutered a layer group, look inside:
        #     j = k['group-members']
        #     if 'name' in j:
        #         layerInfo_j = j['source'].split('@')[0]
        #         technology[j['name']] = pya.LayerInfo(
        #             int(layerInfo_j.split('/')[0]), int(layerInfo_j.split('/')[1]))
        #     else:
        #         for j in k['group-members']:
        #             layerInfo_j = j['source'].split('@')[0]
        #             technology[j['name']] = pya.LayerInfo(
        #                 int(layerInfo_j.split('/')[0]), int(layerInfo_j.split('/')[1]))
        #     if k['source'] != '*/*@*':
        #         technology[k['name']] = pya.LayerInfo(
        #             int(layerInfo.split('/')[0]), int(layerInfo.split('/')[1]))
        # else:
        technology[k['name']] = Layer(gds_layer=int(layerInfo.split('/')[0]), 
                                      gds_datatype=int(layerInfo.split('/')[1]))
    return technology

    # # Layers:
    # file = open(lyp_file, 'r')
    # layer_dict = xml_to_dict(file.read())['layer-properties']['properties']
    # file.close()


    # return technology

# available_packages = os.listdir(os.path.join(klayout_dir, 'salt'))
# # required_packages = ['siepic_tools', 'xsection']
# siepic_python_dir = os.path.join(klayout_dir, 'salt/siepic_tools/python')
# if not os.path.isdir(siepic_python_dir):
#     raise ImportError('SiEPIC Tools does not seem to be installed.\nIts name must be exactly "~/.klayout/salt/siepic_tools"')

# import sys
# sys.path.append(siepic_python_dir)

# from . import pyamock as pya
# import SiEPIC


# Todo
# Find the right path (github?, .pathto file?)
# ~Read xml files~
# Parse them into prettier dictionaries depending


# XML to Dict parser, from:
# https://stackoverflow.com/questions/2148119/how-to-convert-an-xml-string-to-a-dictionary-in-python/10077069
import fnmatch


import os
with open('../.pathtotech', 'r') as file:
    TECHNOLOGY_PATH = os.path.expanduser(file.read()).strip()


#### Helpers



#### Low level


def tech_files(search_pattern, exactly_one=False):
    ''' Searches the technology base path for a file search pattern.

        Args:
            search_pattern (str): file pattern. Default is all XML property files
            exactly_one (bool): Do we expect to find exactly one matching file? If we don't, error
    '''
    dir_path = TECHNOLOGY_PATH
    matches = []
    for root, dirnames, filenames in os.walk(dir_path, followlinks=True):
        for filename in fnmatch.filter(filenames, search_pattern):
            matches.append(os.path.join(root, filename))
    if exactly_one:
        if len(matches) == 0:
            raise FileNotFoundError(f'Did not find a file matching {search_pattern} in {dir_path}')
        elif len(matches) > 1:
            raise FileNotFoundError(f'Pattern {search_pattern} not unique. Found the following:\n'
                                    '\n'.join(matches))
    return matches


def tech_top():
    with open(tech_files('*.lyt', exactly_one=True)[0]) as fx:
        return xml_to_dict(fx.read())

def tech_properties_dict(search_pattern='*.xml'):
    ''' Puts everything that matches the search_pattern in one dictionary,
        but errors if duplicate keys are found on the top level.

        Returns:
            (dict or None): None if no files matched. This is mainly for backwards compatibility
    '''
    if not search_pattern.endswith('.xml'):
        if '.' in search_pattern:
            raise ValueError('Technology properties are in .xml files only')
        search_pattern += '.xml'
    matching_files = tech_files(search_pattern)
    if len(matching_files) == 0:
        return None

    full_dict = dict()
    for match in matching_files:
        try:
            with open(match, 'r') as file:
                this_dict = xml_to_dict(file.read())
        except IOError as e:  # Happens when XML is corrupted
            e.args = (e.args[0] + f' File {match}', )
            raise
        for prop, val in this_dict.items():
            if prop in full_dict.keys():
                raise ValueError(f'Duplicate top-level property category: {prop} in {match}')
        full_dict.update(this_dict)
    return full_dict


class TechnologyTree(object):
    def __init__(self, name):
        self.name = name




def xml_to_object(t):
    raw = xml_to_dict_raw(t)
    # Find entries that are named, remove that item and key a new dictionary with its value
    treename = list(raw.keys())[0]
    te = TechnologyTree(treename)
    for k, v in raw[treename].items():
        try:
            elName = v['name']
        except KeyError:
            pass
        else:
            setattr(te, k, v)


def WAVEGUIDES():
    pass
