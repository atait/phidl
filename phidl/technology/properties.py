''' Specific categories of properties for integrated photonics.
    Developed for silicon
'''
from . import PropertyStruct, layers, wgXSection
from .loader import get_properties_from_file


def pull_names(dicts_with_name):
    ''' Takes a list of dicts with "name" key
        Returns a list of names and MODIFIES THE DICTS by removing these items

        Handles those without names by creating unique names and not modifying the dicts
    '''
    name_vals = []
    iunnamed = 0
    for named_dict in dicts_with_name:
        name = named_dict.pop('name', None)
        if name is None:
            name = f'Unnamed {iunnamed}'
            iunnamed += 1
        name_vals.append(name)
    return name_vals


#### Specific tech categories ####

from phidl.device_layout import Device
import phidl.geometry as pg
from phidl.routing import _arc
import numpy as np
class WGXSection(PropertyStruct):
    components = None
    casts = dict(radius=float, loss=float)

    def cell_straight(self, length):
        WG = Device()
        maxwidth = 0
        for comp in self.components:
            el = WG.add_ref(pg.rectangle(size=[length, comp.width], layer=layers(comp.layer)))
            el.y -= comp.width / 2
            maxwidth = max(maxwidth, comp.width)
        WG.add_port(name = 'wgport1', midpoint = [0,0], width = maxwidth, orientation = 180)
        WG.add_port(name = 'wgport2', midpoint = [length, 0], width = maxwidth, orientation = 0)
        return WG

    def cell_bend(self, theta=90, radius=None):
        ''' By default radius is the waveguide minimum radius '''
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
                                     angle_resolution=2.5, layer=layers(comp.layer)))
            el.move(origin=el.ports[1].midpoint, destination = (0,0))
            maxwidth = max(maxwidth, comp.width)
        BEND.add_port(name = 'wgport1', midpoint = el.ports[1].midpoint, width = maxwidth, orientation = el.ports[1].orientation)
        BEND.add_port(name = 'wgport2', midpoint = el.ports[2].midpoint, width = maxwidth, orientation = el.ports[2].orientation)
        return BEND

    def cell_points(self, ptlist):
        WG = Device()
        # Compute angles and lengths (not accounting for arcs) of segments
        points = np.asarray(ptlist)
        dxdy = points[1:] - points[:-1]
        angles = (np.arctan2(dxdy[:,1], dxdy[:,0])).tolist()
        angles = np.array(angles + [angles[-1]]) * 180 / np.pi
        turns = angles[1:] - angles[:-1]
        if any(abs(turns) > 165):
            raise ValueError('Too sharp of turns.')
        lengths = np.sqrt(np.sum(dxdy ** 2, axis=1))

        next_point = points[0]
        for iSegment in range(len(lengths)):
            if lengths[iSegment] == 0:
                continue
            adj_len = lengths[iSegment] 
            if iSegment > 0:
                adj_len -= self.radius * abs(np.tan(turns[iSegment-1] / 2 * np.pi / 180))
            if iSegment < len(lengths) - 1:
                adj_len -= self.radius * abs(np.tan(turns[iSegment] / 2 * np.pi / 180))
            if adj_len < 0:
                raise ValueError('Length was negative. Points are too close together or turns are too sharp')
            straight = self.cell_straight(adj_len)
            if iSegment < len(lengths)-1:
                bent = self.cell_bend(theta=turns[iSegment])
                bent.move([adj_len, 0])
                be = straight.add_ref(bent)
            straight.rotate(angles[iSegment]).move(next_point)
            st = WG.add_ref(straight)
            if len(lengths) > 2:
                next_point = be.ports['wgport2'].midpoint
        return WG


class WGXSectionComponent(PropertyStruct):
    casts = dict(width=float, offset=float)
    layer = None


def load_waveguides():
    top_list = get_properties_from_file('WAVEGUIDES')['waveguides']['waveguide']
    if not isinstance(top_list, list): top_list = [top_list]
    wg_keys = pull_names(top_list)
    wg_dict = dict()
    for wg_key, wg in zip(wg_keys, top_list):
        loaded_components = wg.pop('component', list())
        if not isinstance(loaded_components, list): loaded_components = [loaded_components]
        wg_components = []
        for comp in loaded_components:
            wg_components.append(WGXSectionComponent(**comp))
        wg_dict[wg_key] = WGXSection(components=wg_components, **wg)
    return wg_dict


class Transition(PropertyStruct):
    casts = dict(length=float, loss=float, bezier=float)

    def cell(self, inverted=False):
        if not inverted:
            source = self.source
            dest = self.dest
        else:
            source = self.dest
            dest = self.source
        wg_source = wgXSection(source)
        wg_dest = wgXSection(dest)
        # Find all of the relevant layers
        layer_names = set()
        for c in wg_source.components:
            layer_names.add(c.layer)
        for c in wg_dest.components:
            layer_names.add(c.layer)
        # Each layer has a pair of widths
        layer_widths = dict((k, np.zeros(2)) for k in layer_names)
        for c in wg_source.components:
            layer_widths[c.layer][0] = c.width
        for c in wg_dest.components:
            layer_widths[c.layer][1] = c.width

        D = Device()
        maxwidths = [0, 0]
        for lName, widths in layer_widths.items():
            maxwidths[0] = max(maxwidths[0], widths[0])
            maxwidths[1] = max(maxwidths[1], widths[1])
            lt = pg.taper(length=self.length, width1=widths[0], width2=widths[1], layer=layers(lName))
            lt.ports = dict()
            D.add_ref(lt)
        D.add_port(name = 'wgport1', midpoint = [0,0], width = maxwidths[0], orientation = 180)
        D.add_port(name = 'wgport2', midpoint = [self.length, 0], width = maxwidths[1], orientation = 0)
        return D


def load_transitions():
    top_list = get_properties_from_file('WAVEGUIDES')['waveguides']['transition']
    if not isinstance(top_list, list): top_list = [top_list]
    tr_keys = pull_names(top_list)
    tr_dict = dict()
    for tr_key, tr in zip(tr_keys, top_list):
        tr['source'] = tr_key.split(' to ')[0]
        tr['dest'] = tr_key.split(' to ')[1]
        tr_dict[tr_key] = Transition(**tr)
    return tr_dict


class Conductor(PropertyStruct):
    casts = dict(thickness=float, sheet=float)
    # type = None
    # layer = None
    # material = None

class Dopant(PropertyStruct):
    pass

class Semiconductor(PropertyStruct):
    ''' A doped semiconductor is a conductor '''
    def doped_with(self, dopant):
        if isinstance(dopant, str):
            dopant = self.dopants[dopant]
        new_attrs = dict((k, getattr(self, k)) for k in self._namedattributes)
        new_attrs.pop('dopants')
        new_attrs['layer'] = [self.layer, dopant.layer]
        new_attrs['sheet'] = dopant.sheet
        return Conductor(**new_attrs)


def load_conductors():
    top_list = get_properties_from_file('CONDUCTORS')['conductors']['conductor']
    if not isinstance(top_list, list): top_list = [top_list]
    cond_keys = pull_names(top_list)
    cond_dict = dict()
    for cond_key, cond in zip(cond_keys, top_list):
        dp_list = cond.pop('doped', None)
        if dp_list is not None:
            if not isinstance(dp_list, list): dp_list = [dp_list]
            cond['dopants'] = dict()
            dp_keys = pull_names(dp_list)
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


def load_vias():
    pass


def load_wires():
    pass
