import os
import zipfile
import numpy as np

import jason_gnss.commands

def processing_engine(rover_file, strategy, rover_dynamics, base_file=None, base_lonlathgt=None):
    """
    Definition of the processing engine to be used to compute the solution.
    
    You can use your own processing engine as long as it conforms to the signature
    :params rover_file: The data file to process (e.g. RINEX file)
    :params strategy: Which processing strategy to use (SPP, PPP, PPK)
    :params base_file: (optional, only for PPK processing) name of the filename with the base GNSS data
    :params base_lonlathgt: (optional, only for PPK processing)
    
    The method should return a named numpy array with at least the following fields:
    - 'GPSW': GPS week
    - 'GPSSoW': GPS seconds of the week
    - 'latitudedeg': Latitude in degrees
    - 'longitudedeg': Longitude in degrees
    - 'heightm': Height in meters
    """
    
    result_zip_file = jason_gnss.commands.process(rover_file=rover_file, strategy=strategy,
                                                  rover_dynamics=rover_dynamics,
                                                  base_file=base_file, base_lonlathgt=base_lonlathgt)

    pos_estimates = None
    
    with zipfile.ZipFile(result_zip_file, 'r') as jason_zip:

        namelist = jason_zip.namelist()

        pattern = '{}.csv'.format(strategy)
        candidate_list = list(filter(lambda x: x.endswith(pattern), namelist))  

        if candidate_list:
            with jason_zip.open(candidate_list[0]) as csv_fh:

                    pos_estimates = np.genfromtxt(csv_fh, names=True, delimiter=",")
                    pos_estimates = np.atleast_1d(pos_estimates) # for one-row only cases
                    
    os.remove(result_zip_file)

    return pos_estimates
