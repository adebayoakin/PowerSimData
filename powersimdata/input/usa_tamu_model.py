import os
import pandas as pd

from powersimdata.input.abstract_grid import AbstractGrid
from powersimdata.input.csv_reader import CSVReader
from powersimdata.input.helpers import (csv_to_data_frame,
                                        add_column_to_data_frame)


class TAMU(AbstractGrid):
    """TAMU network.

    """
    def __init__(self, interconnect):
        """Constructor.

        :param list interconnect: interconnect name(s).
        """
        super().__init__()
        self._set_data_loc()

        if check_interconnect(interconnect):
            self.interconnect = interconnect
            self._build_network()

    def _set_data_loc(self):
        """Sets data location.

        :raises IOError: if directory does not exist.
        """
        top_dirname = os.path.dirname(__file__)
        data_loc = os.path.join(top_dirname, 'data', 'usa_tamu')
        if os.path.isdir(data_loc) is False:
            raise IOError('%s directory not found' % data_loc)
        else:
            self.data_loc = data_loc

    def _set_storage(self):
        """Sets storage properties.

        """
        self.storage['duration'] = 4
        self.storage['min_stor'] = 0.05
        self.storage['max_stor'] = 0.95
        self.storage['InEff'] = 0.9
        self.storage['OutEff'] = 0.9
        self.storage['energy_price'] = 20

    def _build_network(self):
        """Build network.

        """
        reader = CSVReader(self.data_loc)
        self.bus = reader.bus
        self.plant = reader.plant
        self.branch = reader.branch
        self.dcline = reader.dcline
        self.gencost['after'] = self.gencost['before'] = reader.gencost

        self._set_storage()

        add_information_to_model(self)

        if 'USA' not in self.interconnect:
            self._drop_interconnect()

    def _drop_interconnect(self):
        """Trim data frames to only keep information pertaining to the user
            defined interconnect(s)

        """
        for key, value in self.__dict__.items():
            if key in ['sub', 'bus2sub', 'bus', 'plant', 'branch']:
                value.query('interconnect == @self.interconnect',
                            inplace=True)
            elif key == 'gencost':
                value['before'].query('interconnect == @self.interconnect',
                                      inplace=True)
            elif key == 'dcline':
                value.query('from_interconnect == @self.interconnect &'
                            'to_interconnect == @self.interconnect',
                            inplace=True)
        self.id2zone = {k: self.id2zone[k] for k in self.bus.zone_id.unique()}
        self.zone2id = {value: key for key, value in self.id2zone.items()}


def check_interconnect(interconnect):
    """Checks interconnect.

    :param list interconnect: interconnect name(s).
    :raises TypeError: if parameter has wrong type.
    :raises Exception: if interconnect not found or combination of
        interconnect is not appropriate.
    :return: (*bool*) -- if valid
    """
    possible = ['Eastern', 'Texas', 'Western', 'USA']
    if not isinstance(interconnect, list):
        raise TypeError("List of string(s) is expected for interconnect")

    for i in interconnect:
        if i not in possible:
            raise ValueError("Wrong interconnect. Choose from %s" %
                             " | ".join(possible))
    n = len(interconnect)
    if n > len(set(interconnect)):
        raise ValueError("List of interconnects contains duplicate values")
    if 'USA' in interconnect and n > 1:
        raise ValueError("USA interconnect cannot be paired")

    return True


def add_information_to_model(model):
    """Adds information to TAMU model. This is done inplace.

    :param powersimdata.input.TAMU model: TAMU instance.
    """
    model.sub = csv_to_data_frame(model.data_loc, 'sub.csv')
    model.bus2sub = csv_to_data_frame(model.data_loc, 'bus2sub.csv')
    model.id2zone = csv_to_data_frame(
        model.data_loc, 'zone.csv').zone_name.to_dict()
    model.zone2id = {v: k for k, v in model.id2zone.items()}

    bus2zone = model.bus.zone_id.to_dict()
    bus2coord = pd.merge(
        model.bus2sub[['sub_id']],
        model.sub[['lat', 'lon']],
        on='sub_id').set_index(
        model.bus2sub.index).drop(columns='sub_id').to_dict()

    def get_lat(idx):
        return [bus2coord['lat'][i] for i in idx]

    def get_lon(idx):
        return [bus2coord['lon'][i] for i in idx]

    def get_zone_id(idx):
        return [bus2zone[i] for i in idx]

    def get_zone_name(idx):
        return [model.id2zone[bus2zone[i]] for i in idx]

    extra_col_bus = {
        'lat': get_lat(model.bus.index),
        'lon': get_lon(model.bus.index)}
    add_column_to_data_frame(model.bus, extra_col_bus)

    extra_col_plant = {
        'lat': get_lat(model.plant.bus_id),
        'lon': get_lon(model.plant.bus_id),
        'zone_id': get_zone_id(model.plant.bus_id),
        'zone_name': get_zone_name(model.plant.bus_id)}
    add_column_to_data_frame(model.plant, extra_col_plant)

    extra_col_branch = {
        'from_zone_id': get_zone_id(model.branch.from_bus_id),
        'to_zone_id': get_zone_id(model.branch.to_bus_id),
        'from_zone_name': get_zone_name(model.branch.from_bus_id),
        'to_zone_name': get_zone_name(model.branch.to_bus_id),
        'from_lat': get_lat(model.branch.from_bus_id),
        'from_lon': get_lon(model.branch.from_bus_id),
        'to_lat': get_lat(model.branch.to_bus_id),
        'to_lon': get_lon(model.branch.to_bus_id)}
    add_column_to_data_frame(model.branch, extra_col_branch)
