''' Holds the technology layers and properties. Also functions for selecting technology.

    These are subpackage-wide globals, meaning it only reads from the files when
        1. the subpackage is imported
        2. the selected technology changes or
        3. when ``reload_properties`` is called.

    Rationale is that property structures are objects. If they are loaded only once,
    then references made in different places will actually point to the same object.
'''


class PropertyStruct(object):
    casts = []

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


#: All of the technology properties
PROPERTIES = None
def reload_properties():
    tech_dict = dict(WAVEGUIDES=properties.load_waveguides(),
                     TRANSISTIONS=properties.load_transitions(),
                     CONDUCTORS=properties.load_conductors(),
                     VIAS=properties.load_vias(),
                     WIRES=properties.load_wires())
    global PROPERTIES
    PROPERTIES = PropertyStruct(**tech_dict)


def wgXSection(wg_name=None):
    if wg_name is None:
        return list(PROPERTIES.WAVEGUIDES.keys())
    else:
        try:
            return PROPERTIES.WAVEGUIDES[wg_name]
        except KeyError:
            raise KeyError(f'Waveguide {wg_name} not found in available waveguides: ' +
                           str(wgXSection(None)))


def transitions(tr_name=None):
    if tr_name is None:
        return list(PROPERTIES.TRANSISTIONS.keys())
    else:
        try:
            return PROPERTIES.TRANSISTIONS[tr_name]
        except KeyError:
            raise KeyError(f'Transition {tr_name} not found in available: ' +
                           str(transitions(None)))


#: The technology layer definitions as a ``LayerSet``
LAYERS = None
def reload_layers():
    global LAYERS
    LAYERS = loader.get_layerset()


def layers(layer_name=None):
    if layer_name is None:
        return list(LAYERS.keys())
    else:
        try:
            return LAYERS[layer_name]
        except KeyError:
            raise KeyError(f'Layer {layer_name} not found in available layers: ' +
                           str(layers(None)))


# Import all submodule functions and classes so they are visible outside
from . import select, loader, properties
from phidl.technology.select import *
from phidl.technology.loader import *
from phidl.technology.properties import *


# Initialize
set_technology_name(klayout_last_open_technology())



