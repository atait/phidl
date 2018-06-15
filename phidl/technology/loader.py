''' This is about how to load the files
'''
from phidl.utilities import xml_to_dict, read_lyp
from .select import get_technology_path
import fnmatch
import os


def tech_files_matching(search_pattern, exactly_one=False):
    ''' Searches the technology base path for a file search pattern.

        Args:
            search_pattern (str): file pattern. Default is all XML property files
            exactly_one (bool): Do we expect to find exactly one matching file? If we don't, error
    '''
    dir_path = get_technology_path()
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


def get_layerset():
    with open(tech_files_matching('*.lyt', exactly_one=True)[0]) as fx:
        klayout_techdef = xml_to_dict(fx.read())  # KLayout toplevel technology definition. Mostly useless options for reading LEF and DXF
    lyp_file_relative = klayout_techdef['technology']['layer-properties_file']
    lyp_file = os.path.join(get_technology_path(), lyp_file_relative)
    return read_lyp(lyp_file)


def get_properties_from_file(search_pattern='*.xml'):
    ''' Puts everything that matches the search_pattern in one dictionary,
        but errors if duplicate keys are found on the top level.

        Returns:
            (dict or None): None if no files matched. This is mainly for backwards compatibility
    '''
    if not search_pattern.endswith('.xml'):
        if '.' in search_pattern:
            raise ValueError('Technology properties are in .xml files only')
        search_pattern += '.xml'
    matching_files = tech_files_matching(search_pattern)
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



#### Functions that are similar to what SiEPIC does ####

def siepic_get_technology():
    ''' This is similar to what SiEPIC tools does, except 
        1. using phidl.Layer instead of pya.LayerInfo, and
        2. using ``active_technology``
    '''
    with open(tech_files_matching('*.lyt', exactly_one=True)[0]) as fx:
        klayout_techdef = xml_to_dict(fx.read())  # KLayout toplevel technology definition. Mostly useless options for reading LEF and DXF
    technology = {}
    technology['technology_name'] = klayout_techdef['technology']['name']
    technology['dbu'] = klayout_techdef['technology']['dbu']
    # technology['base_path'] = os.path.expanduser(klayout_techdef['technology']['original_base_path'])
    technology['base_path'] = available_tech_paths[active_technology]
    lyp_file = os.path.join(technology['base_path'], klayout_techdef['technology']['layer-properties_file'])
    lys_object = read_lyp(lyp_file)
    # this makes it so you can call technology['si'] and get the same thing as lys['si']
    for lay_name in lys_object._layers:
        technology[lay_name] = lys_object[lay_name]
    return technology


def siepic_get_technology_by_name(tech_name):
    ''' This is similar to what SiEPIC tools does, except 
        1. using phidl.Layer instead of pya.LayerInfo
    '''
    set_technology_name(techname)
    return siepic_get_technology()



