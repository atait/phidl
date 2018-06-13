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


#### Functions that are similar to what SiEPIC does ####

from .utilities import read_lyp
def get_technology():
    ''' This is similar to what SiEPIC tools does, except 
        1. using phidl.Layer instead of pya.LayerInfo, and
        2. using ``active_technology``
    '''
    with open(tech_files('*.lyt', exactly_one=True)[0]) as fx:
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


def get_technology_by_name(tech_name):
    ''' This is similar to what SiEPIC tools does, except 
        1. using phidl.Layer instead of pya.LayerInfo
    '''
    set_technology_name(techname)
    return get_technology()


#### Finally something interesting: getting layers ####

def get_LayerSet():
    with open(tech_files('*.lyt', exactly_one=True)[0]) as fx:
        klayout_techdef = xml_to_dict(fx.read())  # KLayout toplevel technology definition. Mostly useless options for reading LEF and DXF
    lyp_file_relative = klayout_techdef['technology']['layer-properties_file']
    lyp_file = os.path.join(available_tech_paths[active_technology], lyp_file_relative)
    return read_lyp(lyp_file)


#### Technology properties ####


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


#### Packaging in a more useful way: stripped top and object-like accessors ####

class TechnologyTree(object):
    def __init__(self, name):
        self.name = name


def dict_to_object(tech_dict):
    # Find entries that are named, remove that item and key a new dictionary with its value
    treename = list(tech_dict.keys())[0]
    te = TechnologyTree(treename)
    for k, v in tech_dict[treename].items():
        try:
            elName = v['name']
        except KeyError:
            pass
        else:
            setattr(te, k, v)


#### Helpers ####

class obj(object):
    casts = None

    def __init__(self, **attributes):
        self._namedattributes = list(attributes.keys())
        for k, v in attributes.items():
            if k in self.casts:
                attributes[k] = self.casts[k](v)
        self.__dict__.update(attributes)

    def __repr__(self):
        attrstrs = (f'{k}={getattr(self, k)}' for k in self._namedattributes)
        fullstr = ', '.join(attrstrs)
        return f'{type(self).__name__}({fullstr})'


def handle_names(dicts_with_name):
    ''' Takes a list of dicts with "name" key
        Returns a list of names and MODIFIES THE DICTS

        Handles those without names by creating unique names
    '''
    name_keys = []
    iunnamed = 0
    for named_dict in dicts_with_name:
        name = named_dict.pop('name', None)
        if name is None:
            name = f'Unnamed {iunnamed}'
            iunnamed += 1
        name_keys.append(name)
    return name_keys


#### Specific tech categories ####
from phidl.device_layout import Device
import phidl.geometry as pg
from phidl.routing import _arc
lys = get_LayerSet()
import numpy as np
from phidl.quickplotter import quickplot2 as qp
class Waveguide(obj):
    components = None
    casts = dict(radius=float, loss=float)

    def cell_straight(self, length, no_taper=False):
        WG = Device()
        maxwidth = 0
        for comp in self.components:
            el = WG.add_ref(pg.rectangle(size=[length, comp.width], layer=lys[comp.layer]))
            el.y -= comp.width / 2
            maxwidth = max(maxwidth, comp.width)
        WG.add_port(name = 'wgport1', midpoint = [0,0], width = maxwidth, orientation = 180)
        WG.add_port(name = 'wgport2', midpoint = [length, 0], width = maxwidth, orientation = 0)
        return WG

    def cell_bend(self, radius=None, theta=90):
        BEND = Device()
        if radius is None:
            radius = self.radius
        maxwidth = 0
        for comp in self.components:
            if theta < 0:
                start_angle = 90
            else:
                start_angle = -90
            el = BEND.add_ref(_arc(radius=radius, width=comp.width, 
                                     theta=theta, start_angle=start_angle, 
                                     angle_resolution=2.5, layer=lys[comp.layer]))
            el.move(origin=el.ports[1].midpoint, destination = (0,0))
            maxwidth = max(maxwidth, comp.width)
        BEND.add_port(name = 'wgport1', midpoint = el.ports[1].midpoint, width = maxwidth, orientation = el.ports[1].orientation)
        BEND.add_port(name = 'wgport2', midpoint = el.ports[2].midpoint, width = maxwidth, orientation = el.ports[2].orientation)
        return BEND

    def cell_points(self, ptlist):
        import pdb; pdb.set_trace()
        WG = Device()
        points = np.asarray(ptlist)
        dxdy = points[1:] - points[:-1]
        angles = (np.arctan2(dxdy[:,1], dxdy[:,0])).tolist()
        angles = np.array(angles + [angles[-1]]) * 180 / np.pi
        da = angles[1:] - angles[:-1]
        lengths = np.sqrt(np.sum(dxdy ** 2, axis=1))
        next_point = points[0]
        for iSegment in range(len(lengths)):
            adj_len = lengths[iSegment] 
            if iSegment > 0:
                adj_len -= self.radius * abs(np.tan(da[iSegment-1] * np.pi / 180))
            if iSegment < len(lengths) - 1:
                adj_len -= self.radius * abs(np.tan(da[iSegment] * np.pi / 180))
            straight = self.cell_straight(adj_len)
            if iSegment < len(lengths)-1:
                bent = self.cell_bend(theta=da[iSegment])
                bent.move([adj_len, 0])
                be = straight.add_ref(bent)
            straight.rotate(angles[iSegment]).move(next_point)
            st = WG.add_ref(straight)
            next_point = be.ports['wgport2'].midpoint
            # be = WG.add_ref(bent)
            # be.move(be.ports['wgport1'].midpoint, st.ports['wgport2'])
        return WG



class WaveguideComponent(obj):
    casts = dict(width=float, offset=float)
    layer = None


def WAVEGUIDES():
    top_list = tech_properties_dict('WAVEGUIDES')['waveguides']['waveguide']
    if not isinstance(top_list, list): top_list = [top_list]
    wg_keys = handle_names(top_list)
    wg_dict = dict()
    for wg_key, wg in zip(wg_keys, top_list):
        loaded_components = wg.pop('component', list())
        if not isinstance(loaded_components, list): loaded_components = [loaded_components]
        wg_components = []
        for comp in loaded_components:
            wg_components.append(WaveguideComponent(**comp))
        wg_dict[wg_key] = Waveguide(components=wg_components, **wg)
    return wg_dict


class Transition(obj):
    casts = dict(length=float, loss=float, bezier=float)


def TRANSISTIONS():
    top_list = tech_properties_dict('WAVEGUIDES')['waveguides']['transition']
    if not isinstance(top_list, list): top_list = [top_list]
    tr_keys = handle_names(top_list)
    tr_dict = dict()
    for tr_key, tr in zip(tr_keys, top_list):
        tr_dict['from'] = tr_key.split(' to ')[0]
        tr_dict['to'] = tr_key.split(' to ')[1]
        tr_dict[tr_key] = Transition(**tr)
    return tr_dict


class Conductor(obj):
    pass
    # type = None
    # layer = None
    # material = None
    # thickness = None
    # sheet = None

class Dopant(obj):
    pass

class Semiconductor(obj):
    ''' A doped semiconductor is a conductor '''
    def doped_with(self, dopant):
        if isinstance(dopant, str):
            dopant = self.dopants[dopant]
        new_attrs = dict((k, getattr(self, k)) for k in self._namedattributes)
        new_attrs.pop('dopants')
        new_attrs['layer'] = [self.layer, dopant.layer]
        new_attrs['sheet'] = dopant.sheet
        return Conductor(**new_attrs)


def CONDUCTORS():
    top_list = tech_properties_dict('CONDUCTORS')['conductors']['conductor']
    if not isinstance(top_list, list): top_list = [top_list]
    cond_keys = handle_names(top_list)
    cond_dict = dict()
    for cond_key, cond in zip(cond_keys, top_list):
        dp_list = cond.pop('doped', None)
        if dp_list is not None:
            if not isinstance(dp_list, list): dp_list = [dp_list]
            cond['dopants'] = dict()
            dp_keys = handle_names(dp_list)
            for dp_key, dp in zip(dp_keys, dp_list):
                theDopant = Dopant(**dp)
                cond['dopants'][dp_key] = theDopant
            theSemiconductor = Semiconductor(**cond)
            cond_dict[cond_key] = theSemiconductor
            for dp_key in dp_keys:
                cond_dict[cond_key + ' - ' + dp_key] = theSemiconductor.doped_with(dp_key)
        else:
            cond_dict[cond_key] = Conductor(**cond)
        # loaded_components = cond.pop('component', list())
        # if not isinstance(loaded_components, list): loaded_components = [loaded_components]
        # cond_components = []
        # for comp in loaded_components:
        #     cond_components.append(WaveguideComponent(**comp))
    return cond_dict
