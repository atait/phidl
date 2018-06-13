''' This module interfaces with KLayout
'''
import fnmatch
from .utilities import xml_to_dict

#### What technologies are in KLayout? ####
import os
klayout_application_path = os.path.expanduser('~/.klayout')  # This might not work on Windows
if not os.path.isdir(klayout_application_path):
    raise ImportError('KLayout does not seem to be installed.\nDid not find "~/.klayout"')

available_tech_paths = dict()
for root, dirnames, filenames in os.walk(os.path.join(klayout_application_path, 'salt'), followlinks=True):
    if os.path.split(root)[1] == 'tech':
        for technology_name in dirnames:
            available_tech_paths[technology_name] = os.path.join(root, technology_name)


#### technology name handling ####

def klayout_last_open_technology():
    rc_file = os.path.join(klayout_application_path, 'klayoutrc')
    with open(rc_file, 'r') as file:
        rc_dict = xml_to_dict(file.read())
    return rc_dict['config']['initial-technology']


active_technology = klayout_last_open_technology()


def set_technology_name(technology_name):
    if technology_name not in available_tech_paths.keys():
        raise ValueError(f'{technology_name} was not found in available technologies:'
                         ', '.join(available_tech_paths.keys()))
    global active_technology
    active_technology = technology_name


def get_technology_name():
    return active_technology


#### scanning the technology for included files ####

def tech_files(search_pattern, exactly_one=False):
    ''' Searches the technology base path for a file search pattern.

        Args:
            search_pattern (str): file pattern. Default is all XML property files
            exactly_one (bool): Do we expect to find exactly one matching file? If we don't, error
    '''
    dir_path = available_tech_paths[active_technology]
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
