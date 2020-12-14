import datetime
import os
import zipfile
import numpy as np

import roktools.logger
import roktools.time

import jason_gnss.commands

ENGINE_NAME_STR = 'engine name'


# ------------------------------------------------------------------------------

class PositionFix(object):

    def __init__(self, epoch, longitude_deg, latitude_deg, altitude_m):

        self.epoch = epoch
        self.longitude_deg = longitude_deg
        self.latitude_deg = latitude_deg
        self.altitude_m = altitude_m

    def interpolate(self, epoch):
        return self

    def __repr__(self):
        out = '{},{},{},{}'.format(self.epoch, self.longitude_deg, self.latitude_deg, self.altitude_m)
        return out


# ------------------------------------------------------------------------------

class ProcessingSolutions(object):

    LAT_STR = 'longitudedeg'
    LON_STR = 'latitudedeg'
    HGT_STR = 'eightm'
    SIGMA3D_STR = 'sigma3D'
    EPOCH_STR = 'epoch'

    # --------------------------------------------------------------------------

    def __init__(self):
        self.processing_solutions = []
        self.up_to_date = False

    # --------------------------------------------------------------------------

    def __len__(self):
        return self.processing_solutions.__len__()

    def __repr__(self):
        return '\n'.join([str(p) for p in self.processing_solutions])

    # --------------------------------------------------------------------------

    def append(self, processing_solution):

        if isinstance(processing_solution, PositionFix):
            self.processing_solutions.append(processing_solution)
            self.up_to_date = False
        else:
            raise TypeError('Unable to add solution into a PositionFix instance')

    # --------------------------------------------------------------------------

    def __iter__(self):
        return self.processing_solutions.__iter__()

    # --------------------------------------------------------------------------

    def interpolate(self, epoch):

        self._update()

        elapsed_time = self._compute_elapsed_time(epoch)

        lon = np.interp(elapsed_time, self.elapsed_times, self.longitudes)
        lat = np.interp(elapsed_time, self.elapsed_times, self.latitudes)
        hgt = np.interp(elapsed_time, self.elapsed_times, self.altitudes)

        coordinates = (lon, lat, hgt, 0.0)

        epoch = self.t_0 + datetime.timedelta(seconds=elapsed_time)

        return PositionFix(epoch, lon, lat, hgt)

    # --------------------------------------------------------------------------

    def _update(self):

        if not self.up_to_date:
            self.latitudes = [p.latitude_deg for p in self.processing_solutions]
            self.longitudes = [p.longitude_deg for p in self.processing_solutions]
            self.altitudes = [p.altitude_m for p in self.processing_solutions]

            self.t_0 = self.processing_solutions[0].epoch
            self.elapsed_times = [(p.epoch - self.t_0).total_seconds() for p in self.processing_solutions]

            self.up_to_date = True

    # --------------------------------------------------------------------------

    def _compute_elapsed_time(self, epoch):

        self._update()

        return (epoch - self.t_0).total_seconds()
 
# ------------------------------------------------------------------------------

class ProcessingEngine(object):

    def __init__(self):
        pass

    def version(self):

        out = jason_gnss.commands.api_status()
        out.update({ENGINE_NAME_STR: 'jason'})
        return out

    def run(self, rover_file: str, strategy: str, rover_dynamics: str, base_file: str = None,
            base_lonlathgt: list = None, label: str = 'gnss-benchmark', 
            broadcast_file: str = None, sp3_file: str = None) -> ProcessingSolutions:
        """
        Definition of the processing engine to be used to compute the solution.
    
        You can use your own processing engine as long as it conforms to the signature
        :params rover_file: The data file to process (e.g. RINEX file)
        :params strategy: Which processing strategy to use (SPP, PPP, PPK)
        :params base_file: (optional, only for PPK processing) name of the filename with the base GNSS data
        :params base_lonlathgt: (optional, only for PPK processing)
    
        :returns: a ProcessingSolutions instance
        """
    
        result_zip_file = jason_gnss.commands.process(rover_file=rover_file, strategy=strategy,
                                                      rover_dynamics=rover_dynamics,
                                                      base_file=base_file, base_lonlathgt=base_lonlathgt,
                                                      label=label)

        out = None
        if not result_zip_file:
            roktools.logger.warning(f'Could not run process for {rover_file} / {strategy} / {rover_dynamics}')
        
        else:
            out = extract_solution_from_zip(result_zip_file, strategy)
            os.remove(result_zip_file)

        return out

# ------------------------------------------------------------------------------

def extract_solution_from_zip(zip_filename: str, strategy: str) -> ProcessingSolutions:

    out = None
    
    with zipfile.ZipFile(zip_filename, 'r') as jason_zip:

        namelist = jason_zip.namelist()

        pattern = '{}.csv'.format(strategy)
        candidate_list = list(filter(lambda x: x.endswith(pattern), namelist))  

        roktools.logger.debug('Files within the zip file: {}'.format(namelist))
        roktools.logger.debug('Result files from GNSS job: {}'.format(candidate_list))

        if candidate_list:
            with jason_zip.open(candidate_list[0]) as csv_fh:
                out = convert_csv_output_to_processing_solutions(csv_fh)
                    
    return out

# ------------------------------------------------------------------------------

def convert_csv_output_to_processing_solutions(csv_fh) -> ProcessingSolutions:

    data = np.genfromtxt(csv_fh, names=True, delimiter=",")
    data = np.atleast_1d(data) # for one-row only cases

    out = ProcessingSolutions()
    for datum in data:
        week = datum['GPSW']
        tow = datum['GPSSoW']
        epoch = roktools.time.weektow_to_datetime(tow, week)
        lon = datum['longitudedeg']
        lat = datum['latitudedeg']
        hgt = datum['heightm']
        solution = PositionFix(epoch, lon, lat, hgt)

        out.append(solution)

    return out
