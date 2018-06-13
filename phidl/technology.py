''' This module interfaces with KLayout
'''

# Is KLayout installed?
import os
klayout_dir = os.path.expanduser('~/.klayout/salt')
if not os.path.isdir(klayout_dir):
    raise ImportError('KLayout does not seem to be installed.\nDid not find "~/.klayout"')

available_tech_paths = dict()
for root, dirnames, filenames in os.walk(klayout_dir, followlinks=True):
    if os.path.split(root)[1] == 'tech':
        for technology_name in dirnames:
            available_tech_paths[technology_name] = os.path.join(root, technology_name)


from .utilities import read_lyp
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
    lys_object = read_lyp(lyp_file)
    # this makes it so you can call technology['si'] and get the same thing as lys['si']
    for lay in lys_object._layers:
        technology[lay.name] = lay
    return technology


# Todo
# Find the right path (github?, .pathto file?)
# ~Read xml files~
# Parse them into prettier dictionaries depending




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
