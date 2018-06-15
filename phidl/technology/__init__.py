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


#: All of the technology properties, not to be directly accessed, rather through below functions
PROPERTIES = None
def reload_properties():
    tech_dict = dict(WAVEGUIDES=properties.load_waveguides(),
                     TRANSISTIONS=properties.load_transitions(),
                     CONDUCTORS=properties.load_conductors(),
                     VIAS=properties.load_vias(),
                     WIRES=properties.load_wires())
    global PROPERTIES
    PROPERTIES = PropertyStruct(**tech_dict)


#: The technology layer definitions as a ``LayerSet``, to be accessed through ``layers`` function
LAYERS = None
def reload_layers():
    global LAYERS
    LAYERS = loader.get_layerset()


#### Accessors ####

def better_getitem(category_dict, element_name):
    ''' Similar to ``category_dict.__getitem__(element_name)``, except
        returns the possible keys when element_name is None, and
        includes the possible keys when raising KeyError
    '''
    if element_name is None:
        return list(category_dict.keys())
    else:
        try:
            return category_dict[element_name]
        except KeyError:
            raise KeyError(f'{element_name} not found in available elements: ' +
                           str(list(category_dict.keys())))


def wgXSections(wg_name=None):
    return better_getitem(PROPERTIES.WAVEGUIDES, wg_name)


def transitions(tr_name=None):
    return better_getitem(PROPERTIES.TRANSISTIONS, tr_name)


def wires(wire_name=None):
    return better_getitem(PROPERTIES.WIRES, wire_name)


def conductors(cond_name=None):
    return better_getitem(PROPERTIES.CONDUCTORS, cond_name)


def vias(via_name=None):
    return better_getitem(PROPERTIES.VIAS, via_name)


def layers(layer_name=None):
    return better_getitem(LAYERS, layer_name)


# Import all submodule functions and classes so they are visible outside
from . import select, loader, properties
from phidl.technology.select import *
from phidl.technology.loader import *
from phidl.technology.properties import *


# Initialize
set_technology_name(klayout_last_open_technology())



