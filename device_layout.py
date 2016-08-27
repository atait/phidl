# -*- coding: utf-8 -*-
"""
Created on Wed Jul 20 17:47:14 2016

@author: anm16
"""


from __future__ import division # Otherwise integer division e.g.  20 / 7 = 2
from __future__ import print_function # Use print('hello') instead of print 'hello'
from __future__ import absolute_import

import numpy as np
import gdspy
import yaml
from copy import deepcopy

from matplotlib import pyplot as plt
from matplotlib.patches import Polygon as PolygonPatch
from matplotlib.collections import PatchCollection



def rotate_points(points, angle = 45, center = [0,0]):
    """ Rotates points around a centerpoint defined by ``center``.  ``points`` may be
    input as either single points [1,2] or array-like[N][2], and will return in kind
    """
    angle = angle*np.pi/180
    ca = np.cos(angle)
    sa = np.sin(angle)
    sa = np.array((-sa, sa))
    c0 = np.array(center)
    if np.array(points).ndim == 2: 
        return (points - c0) * ca + (points - c0)[:,::-1] * sa + c0
    if np.array(points).ndim == 1: 
        return (points - c0) * ca + (points - c0)[::-1] * sa + c0
    


def reflect_points(points, p1 = [0,0], p2 = [1,0]):
    """ Reflects points across the line formed by p1 and p2.  ``points`` may be
    input as either single points [1,2] or array-like[N][2], and will return in kind
    """
    # From http://math.stackexchange.com/questions/11515/point-reflection-across-a-line
    points = np.array(points); p1 = np.array(p1); p2 = np.array(p2);
    if np.array(points).ndim == 1: 
        p = points
        return 2*(p1 + (p2-p1)*np.dot((p2-p1),(p-p1))/np.linalg.norm(p2-p1)**2) - p
    if np.array(points).ndim == 2: 
        return np.array([2*(p1 + (p2-p1)*np.dot((p2-p1),(p-p1))/np.linalg.norm(p2-p1)**2) - p for p in points])


def translate_points(points, d = [1,2]):
    """ Reflects points across the line formed by p1 and p2.  ``points`` may be
    input as either single points [1,2] or array-like[N][2], and will return in kind
    """
    points = np.array(points) + d
    return points
    

class Port(object):
    # TODO: Make so normal and bounds are properties which can be set and
    # which will set their midpoint and orientation and width accordingly
    def __init__(self, name = None, midpoint = [0,0], width = 1, orientation = 90, parent = None):
        self.name = name
        self.midpoint = midpoint
        self.width = width
        self.orientation = mod(orientation,360)
        self.parent = parent
        
    def __repr__(self):
        return ('Port (name %s, midpoint %s, width %s, orientation %s)' % \
                (self.name, self.midpoint, self.width, self.orientation))
        
    def bounds(self):
        dx = self.width/2*np.cos((self.orientation - 90)*np.pi/180)
        dy = self.width/2*np.sin((self.orientation - 90)*np.pi/180)
        left_point = self.midpoint - np.array([dx,dy])
        right_point = self.midpoint + np.array([dx,dy])
        return np.array([left_point, right_point])
        
    def normal(self):
        dx = np.cos((self.orientation)*np.pi/180)
        dy = np.sin((self.orientation)*np.pi/180)
        return np.array([self.midpoint, self.midpoint + np.array([dx,dy])])
        
        
# TODO: Add "select" function which can return subdevices, polygons, etc on specific layers or other criteria
class Device(gdspy.Cell):
    id = 0
    
    def __init__(self, name = 'Unnamed', exclude_from_global=True):
        self.ports = {}
        self.parameters = {}
        self.subdevices = []
        Device.id += 1
        name = '%s%06d' % (name, Device.id) # Write name e.g. 'Unnamed000005'
        super(Device, self).__init__(name, exclude_from_global)


    @property
    def layers(self):
        return self.get_layers()
        
    def add_device(self, device):
        subdevice = SubDevice(device)   # Create a SubDevice (CellReference)
        self.add(subdevice)             # Add SubDevice (CellReference) to Device (Cell)
        self.subdevices.append(subdevice) # Add to the list of subdevices (for convenience)
        return subdevice                # Return the SubDevice (CellReference)

    def add_polygon(self, polygon, layer = 0, datatype = 0):
        if type(polygon) is gdspy.Polygon:
            pass
        elif type(polygon) is gdspy.PolygonSet:
            pass
        elif len(polygon[0]) == 2: # Then it must be of the form [[1,2],[3,4],[5,6]]
            polygon = gdspy.Polygon(polygon, layer, datatype)
        elif len(polygon[0]) > 2: # Then it must be of the form [[1,3,5],[2,4,6]]
            polygon = gdspy.Polygon(xy2p(polygon), layer, datatype)
        self.add(polygon)
        return polygon
        
    def add_port(self, name = None, midpoint = [0,0], width = 1, orientation = 45, port = None):
        """ Can be called to copy an existing port like add_port(port = existing_port) or
        to create a new port add_port(myname, mymidpoint, mywidth, myorientation).
        Can also be called to copy an existing port with a new name like add_port(port = existing_port, name = new_name)"""
        if type(port) == Port: p = port
        else:                  p = Port(name, midpoint, width, orientation, parent = self)
        if name is not None: p.name = name
        if self.ports.has_key(p.name):
            raise ValueError('[DEVICE] add_port() error: Port name already exists in this device') 
        self.ports[p.name] = p
        return p
        
    def remove_port(self, name):
        self.ports.pop(name, None)
        
    def bbox(self, boundary = None):
        box = self.get_bounding_box() # Returns like [(-1,-2), (4,5)]
        if type(boundary) is str:
            boundary = boundary.upper() # Make uppercase
            if boundary == 'NE':    return np.array(box[1])
            if boundary == 'SE':    return np.array([box[1][0], box[0][1]])
            if boundary == 'SW':    return np.array(box[0])
            if boundary == 'NW':    return np.array([box[0][0], box[1][1]])
            if boundary == 'N':     return box[1][1]
            if boundary == 'S':     return box[0][1]
            if boundary == 'E':     return box[1][0]
            if boundary == 'W':     return box[0][0]
        else: return box
    
    def write_gds(self, filename, unit = 1e-6, precision = 1e-9):
        gdspy.gds_print(filename, cells=[self], name='library', unit=unit, precision=precision)

    # TODO: Write align function that takes a polygon/subdevice and moves it to the destination
    def align(self, element, destination):
        pass
    
    def connect(self, port, destination):
        sd = port.parent
        sd.connect(port, destination)
        return sd
        
            
    def route(self, port1, port2, path_type = 'sine', width_type = 'straight', width1 = None, width2 = None, layer = 0, datatype = 0):
        # Assuming they're both Ports for now
        point_a = np.array(port1.midpoint)
        if width1 is None:  width1 = port1.width
        point_b = np.array(port2.midpoint)
        if width2 is None:  width2 = port2.width
        if round(abs(mod(port1.orientation - port2.orientation,360)),3) != 180:
            raise ValueError('[DEVICE] route() error: Ports do not face each other (orientations must be 180 apart)') 
        orientation = port1.orientation
        
        separation = point_b - point_a  # Vector drawn from A to B
        distance = np.linalg.norm(separation) # Magnitude of vector from A to B
        rotation = np.arctan2(separation[1],separation[0])*180/np.pi # Rotation of vector from A to B
        angle = rotation - orientation   # If looking out along the normal of ``a``, the angle you would have to look to see ``b``
        forward_distance = distance*np.cos(angle*np.pi/180)
        lateral_distance = distance*np.sin(angle*np.pi/180)
        
        # Create a path assuming starting at the origin and setting orientation = 0
        # use the "connect" function later to move the path to the correct location
        xf = forward_distance
        yf = lateral_distance
        if path_type == 'straight':
            curve_fun = lambda t: [xf*t, yf*t]
            curve_deriv_fun = lambda t: [xf + t*0, yf + t*0]
        if path_type == 'sine':
            curve_fun = lambda t: [xf*t, yf*(1-np.cos(t*np.pi))/2]
            curve_deriv_fun = lambda t: [xf  + t*0, yf*(np.sin(t*np.pi)*np.pi)/2]
        #if path_type == 'semicircle':
        #    def semicircle(t):
        #        t = np.array(t)
        #        x,y = np.zeros(t.shape), np.zeros(t.shape)
        #        ii = (0 <= t) & (t <= 0.5)
        #        jj = (0.5 < t) & (t <= 1)
        #        x[ii] = (np.cos(-np.pi/2 + t[ii]*np.pi/2))*xf
        #        y[ii] = (np.sin(-np.pi/2 + t[ii]*np.pi/2)+1)*yf*2
        #        x[jj] = (np.cos(np.pi*3/2 - t[jj]*np.pi)+2)*xf/2
        #        y[jj] = (np.sin(np.pi*3/2 - t[jj]*np.pi)+1)*yf/2
        #        return x,y
        #    curve_fun = semicircle
        #    curve_deriv_fun = None
        if width_type == 'straight':
            width_fun = lambda t: (width2 - width1)*t + width1
        if width_type == 'sine':
            width_fun = lambda t: (width2 - width1)*(1-np.cos(t*np.pi))/2 + width1
        
        route_path = gdspy.Path(width = width1, initial_point = [0,0])
        route_path.parametric(curve_fun, curve_deriv_fun, number_of_evaluations=99,\
                max_points=199, final_width=width_fun, final_distance=None, layer=layer, datatype=datatype)
        
        # Make the route path into a Device with ports, and use "connect" to move it
        # into the proper location
        d = Device()
        d.add(route_path)
        d.add_port(name = 1, midpoint = [0,0], width = width1, orientation = 180)
        d.add_port(name = 2, midpoint = [forward_distance,lateral_distance], width = width2, orientation = 0)
        r = self.add_device(d)
        r.connect(1, port1)
        return r

    def rotate(self, angle = 45, center = [0,0]):
        for e in self.elements:
            if type(e) is gdspy.Polygon or type(e) is gdspy.PolygonSet:
                e.rotate(angle = angle*np.pi/180, center = center)
            if type(e) is SubDevice: 
                e.rotate(angle, center)
        for p in self.ports.values():
            p.midpoint = rotate_points(p.midpoint, angle, center)
            p.orientation = mod(p.orientation + angle, 360)
            
    # FIXME Add logic to make this accept things like origin = myport
    def move(self, origin = [0,0], destination = [0,0]):
        for e in self.elements:
            if type(e) is gdspy.Polygon or type(e) is gdspy.PolygonSet: 
                dx,dy = np.array(destination) - origin
                e.translate(dx,dy)
            if type(e) is SubDevice: 
                e.move(origin, destination)
        for p in self.ports.values():
            p.midpoint = np.array(p.midpoint) + np.array(destination) - np.array(origin)
            
    # FIXME Make this work for all types of elements    
#    def reflect(self, p1, p2):
#        for e in self.elements:
#            e.reflect(angle, center)

    
    
    
class SubDevice(gdspy.CellReference):
    def __init__(self, device, origin=(0, 0), rotation=0, magnification=None, x_reflection=False):
        super(SubDevice, self).__init__(device, origin, rotation, magnification, x_reflection)
        self.parent_ports = device.ports
        self._local_ports = deepcopy(device.ports)
    
    @property
    def ports(self):
        """ This property allows you to access mysubdevice.ports, and receive a copy
        of the ports dict which is correctly rotated and translated"""
        for key in self.parent_ports.keys():
            port = self.parent_ports[key] 
            new_midpoint, new_orientation = self._transform_port(port.midpoint, \
                port.orientation, self.origin, self.rotation, self.x_reflection)
            self._local_ports[key].midpoint = new_midpoint
            self._local_ports[key].orientation = mod(new_orientation,360)
            self._local_ports[key].parent = self
        return self._local_ports


    def _transform_port(self, point, orientation, origin=[0, 0], rotation=None, x_reflection=False):
        # Apply GDS-type transformations (x_ref)
        new_point = np.array(point)
        new_orientation = orientation
        
        if x_reflection:
            new_point[1] = -new_point[1]
            new_orientation = -orientation
        if rotation is not None:
            new_point = rotate_points(new_point, angle = rotation, center = [0, 0])
            new_orientation += rotation
        if origin is not None:
            new_point = new_point + np.array(origin)
        new_orientation = mod(new_orientation, 360)
            
        return new_point, new_orientation
        
        
        
    def bbox(self, boundary = None):
        """ Returns the bounding box in the format of the southwest and northeast
        corners [(-1,-2), (4,5)].  ``boundary`` can be specified to be edges
        or vertices of the bounding box.  For instance specifying east 'E'
        returns the maximum +x coordinate, while 'NE' returns the max [+x,+y] """
        box = self.get_bounding_box() # Returns like [(-1,-2), (4,5)]
        if type(boundary) is str:
            boundary = boundary.upper() # Make uppercase
            if boundary == 'NE':    return np.array(box[1])
            if boundary == 'SE':    return np.array([box[1][0], box[0][1]])
            if boundary == 'SW':    return np.array(box[0])
            if boundary == 'NW':    return np.array([box[0][0], box[1][1]])
            if boundary == 'N':     return box[1][1]
            if boundary == 'S':     return box[0][1]
            if boundary == 'E':     return box[1][0]
            if boundary == 'W':     return box[0][0]
        else: return box
                
                

    def translate(self, d = [1,2]):
        self.origin = np.array(self.origin) + np.array(d)
        return self
        
        
    def move(self, origin = [0,0], destination = [0,0]):
        """ Moves the SubDevice from the origin point to the destination.  Both
         origin and destination can be 1x2 array-like, Port, or a key
         corresponding to one of the Ports in this subdevice """
        if type(origin) is Port:            o = origin.midpoint
        elif np.array(origin).size == 2:    o = origin
        elif self.ports.has_key(origin):    o = self.ports[origin].midpoint
        else: raise ValueError('[SubDevice.move()] ``origin`` not array-like, a port, or port name')
            
        if type(destination) is Port:           d = destination.midpoint
        elif np.array(origin).size == 2:        d = destination
        elif self.ports.has_key(destination):   d = self.ports[destination].midpoint
        else: raise ValueError('[SubDevice.move()] ``destination`` not array-like, a port, or port name')
            
        self.origin = np.array(self.origin) + np.array(d) - np.array(o)
        return self
        
        
    def rotate(self, angle = 45, center = [0,0]):
        if type(center) is Port:  center = center.midpoint
        self.rotation += angle
        self.origin = rotate_points(self.origin, angle, center)
        return self
        
        
    def reflect(self, p1 = [0,1], p2 = [0,0]):
        if type(p1) is Port:  p1 = p1.midpoint
        if type(p2) is Port:  p2 = p2.midpoint
        p1 = np.array(p1);  p2 = np.array(p2)
        # Translate so reflection axis passes through origin
        self.origin = self.origin - p1
        
        # Rotate so reflection axis aligns with x-axis
        angle = np.arctan((p2[1]-p1[1])/(p2[0]-p1[0]))*180/np.pi
        self.origin = rotate_points(self.origin, angle = -angle, center = [0,0])
        self.rotation -= angle
        
        # Reflect across x-axis
        self.x_reflection = not self.x_reflection
        self.origin[1] = -self.origin[1]
        self.rotation = -self.rotation
        
        # Un-rotate and un-translate
        self.origin = rotate_points(self.origin, angle = angle, center = [0,0])
        self.rotation += angle
        self.origin = self.origin + p1
        return self
        
        
    def connect(self, port, destination):
        # ``port`` can either be a string with the name or an actual Port
        if self.ports.has_key(port):
            p = self.ports[port]
        elif type(port) is Port:
            p = port
        
        self.rotate(angle =  180 + destination.orientation - p.orientation, center = p.midpoint)
        self.move(origin = p, destination = destination)
        return self



def p2xy(points):
    """ Takes in a list of [x,y] pairs and converts them to lists of x points 
    and y points.  So p2xy([[1,5],[2,6],[3,7]]) returns [[1,2,3],[5,6,7]]
    """
    p = np.array(points)
    x = p[:,0]
    y = p[:,1]
    return np.array([x,y])
    
def xy2p(*args):
    """ Takes in lists of x points and y points, e.g. [1,2,3],[5,6,7] and
    converts it to the point format e.g. [[1,5],[2,6],[3,7]].  Can either be
    called as xy2p(xpts, ypts) or as xy2p(xy) where xy = [xpts, ypts]
    """
    if len(args) == 1:      x,y = args[0][0], args[0][1] 
    elif len(args) == 2:    x,y = args[0],    args[1]
    points = np.array(zip(*[x,y]))
    return points
    
    
def quickplot(items, overlay_ports = True, overlay_subports = True, label_ports = True, new_window = True):
    """ Takes a list of devices/subdevices/polygons or single one of those, and
    plots them.  Also has the option to overlay their ports """
    if new_window: fig, ax = plt.subplots(1)
    else:
        ax = plt.gca()  # Get current figure
        ax.cla()        # Clears the axes of all previous polygons
    
    # Iterate through each each Device/Subdevice/Polygon
    patches = []
    if type(items) is not list:  items = [items]
    for item in items:
        if type(item) is Device or type(item) is SubDevice:
            polygons = item.get_polygons(by_spec=False, depth=None)
            for p in polygons:
                patches.append(PolygonPatch(p, closed=True, alpha = 0.4))
            for name, port in item.ports.items():
                _draw_port(port, arrow_scale = 2, shape = 'full', color = 'k')
                plt.text(port.midpoint[0], port.midpoint[1], name)
        if type(item) is Device and overlay_subports is True:
            for sd in item.subdevices:
                for name, port in sd.ports.items():
                    _draw_port(port, arrow_scale = 1, shape = 'right', color = 'r')
                    plt.text(port.midpoint[0], port.midpoint[1], name)
        if type(item) is gdspy.Polygon:
            p = item.points
            patches.append(PolygonPatch(p, closed=True, alpha = 0.4))
    pc = PatchCollection(patches, alpha=0.4)
    # TODO: Change this to per-layer coloring    
    np.random.seed(0)
    colors = 100*np.random.rand(len(patches))
    pc.set_array(np.array(colors))
    ax.add_collection(pc)
    plt.axis('equal')
    ax.grid(True, which='both', alpha = 0.4)
    ax.axhline(y=0, color='k', alpha = 0.2, linewidth = 1)
    ax.axvline(x=0, color='k', alpha = 0.2, linewidth = 1)
    plt.draw()


def _draw_port(port, arrow_scale = 1, **kwargs):
    x = port.midpoint[0]
    y = port.midpoint[1]
    nv = port.normal()
    n = (nv[1]-nv[0])*arrow_scale
    dx, dy = n[0], n[1]
    xbound, ybound = p2xy(port.bounds())
    #plt.plot(x, y, 'rp', markersize = 12) # Draw port midpoint
    plt.plot(xbound, ybound, 'r', linewidth = 3) # Draw port edge
    plt.arrow(x, y, dx, dy,length_includes_head=True, width = 0.1*arrow_scale, head_width=0.3*arrow_scale, **kwargs)


#def applyconfig(fun, filename = 'myconfig.yaml', **kwargs):
#    with open(filename) as f:  config_dict = yaml.load(f) # Load arguments from config file
#    config_dict.update(**kwargs)                          # Replace any additional arguments  
#    return fun(**config_dict)
#
#    
#def useconfig(filename = 'myconfig.yaml', **kwargs):
#    with open(filename) as f:  config_dict = yaml.load(f) # Load arguments from config file
#    config_dict.update(**kwargs)                          # Replace any additional arguments  
#    return config_dict
#
#    
#filename = 'C:/Users/anm16/Downloads/temp.yaml'
#d = _load_config_file(filename)
#
#
#y = applyconfig(beamsplitter, filename, arm_length = 50)
#quickplot(y)
#
#y = beamsplitter(**useconfig(filename, arm_length = 50))
#quickplot(y)


