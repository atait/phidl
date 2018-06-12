# Todo
# Find the right path (github?, .pathto file?)
# ~Read xml files~
# Parse them into prettier dictionaries depending


# XML to Dict parser, from:
# https://stackoverflow.com/questions/2148119/how-to-convert-an-xml-string-to-a-dictionary-in-python/10077069
from collections import defaultdict
from xml.etree import cElementTree
import fnmatch


import os
with open('../.pathtotech', 'r') as file:
    tech_path = file.read()
TECHNOLOGY_PATH = tech_path


#### Helpers


def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def xml_to_dict(t):
    try:
        e = cElementTree.XML(t)
    except:
        raise IOError("Error in the XML string.")
    return etree_to_dict(e)


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
