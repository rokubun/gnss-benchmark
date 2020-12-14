import datetime
import glob
import jinja2
import json
import os
import matplotlib.pyplot as plt
import numpy as np
import shutil
import subprocess
import tempfile
import pkg_resources
import re
from typing import Tuple

import pyproj
ecef = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
lla = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')    
transformer_lla_xyz = pyproj.Transformer.from_proj(lla, ecef)
transformer_xyz_lla = pyproj.Transformer.from_proj(ecef, lla)

from roktools import geodetic, logger
import roktools.time

from . import jason

TEMPLATES_PATH = pkg_resources.resource_filename('gnss_benchmark', 'templates')
DATASET_PATH = pkg_resources.resource_filename('gnss_benchmark', 'datasets')

FIGURE_FORMAT = 'png'

INVALID_RMS_VALUE = -9999

def make(processing_engine, description_files_root_path=DATASET_PATH, 
            output_folder='.', report_name='report.pdf', results=None, 
            runby='info@rokubun.cat', tests=[], pattern=None):
    """
    Make a report using the provided processing engine

    :params processing_engine: a method that accepts parameters and returns an
                                array of time tagged solutions. An example 
                                of such method can be seen in the example
                                provided for Rokubun Jason GNSS cloud service
    :params description_files_root_path: Folder where the test cases are located.
            By default, the test cases provided in the package will be used, 
            but the user can provide their own, following the same structure
            provided in the dataset folder. This is an optional field.
    :params output_folder: Folder where the report shall be placed.
    :params report_name: Name of the file where the report will be saved. 
            The extension will define the report format (e.g. 'md', 'pdf', 'odt',
            'docx', ...)
    :params results: Skip the processing by defining a set of results already
            provided by the processing engine. This is intended for debugging
            purposes.
    :params runby: Identifier (name, e-mail, ...) of the responsible that run
            the tool.
    """

    descriptions = _fetch_test_descriptions(description_files_root_path, pattern)

    if len(tests):
        descriptions = {k:v for k,v in descriptions.items() if k in tests}

    if not results:
        results = _run_processing_engine(descriptions, description_files_root_path, processing_engine)
    
    report_filename = _render_report(descriptions, results, output_folder, report_name, runby, processing_engine)
        
    return report_filename

def get_test_list(description_files_root_path=DATASET_PATH, pattern=None):
    """
    Get the list of available tests
    """

    logger.info(f'Description files from path: {description_files_root_path}')
    description_files = _get_description_files(description_files_root_path, pattern)

    return [f.split('/')[-2] for f in description_files]

# ------------------------------------------------------------------------------

def _get_description_files(description_files_root_path, pattern):

    description_files_path = os.path.join(description_files_root_path, '*/description.json')
    description_files = glob.glob(description_files_path)

    out = []
    for description_file in sorted(description_files):
        if pattern is None or pattern in description_file:
            out.append(description_file)

    return out

# ------------------------------------------------------------------------------

def _fetch_test_descriptions(description_files_root_path, pattern=None):

    description_files = _get_description_files(description_files_root_path, pattern)

    descriptions = {}

    for description_file in description_files:

        test_short_name = description_file.split('/')[-2]

        description = None
        with open(description_file, "r") as fh:
                description = json.load(fh)

        descriptions[test_short_name] = description
        
    return descriptions
    
# ------------------------------------------------------------------------------

def _run_processing_engine(descriptions, description_files_root_path, processing_engine):

    results = {}

    for test_short_name, description in descriptions.items():

        test_data_path = os.path.join(description_files_root_path, test_short_name)
        test_files = glob.glob(os.path.join(test_data_path, '*'))

        src_dir = os.getcwd()
        with tempfile.TemporaryDirectory() as tempfolder:

            for test_file in test_files:
                shutil.copy(test_file, tempfolder) 

            os.chdir(tempfolder)

            results[test_short_name] = []

            for configuration in description['configurations']:

                strategy = configuration['strategy']

                cfg = {**description['inputs'], **configuration}
                cfg['label'] = "gnss_benchmark__{}_{}".format(test_short_name, strategy)
                logger.debug('Running processing engine for {} / {}'.format(test_short_name, strategy))
                positions = processing_engine.run(**cfg)

                logger.debug('Computing ENU differences relative to reference')

                reference = None
                if 'validation' in description:
                    validation = description['validation']
                    reference = None
                    if 'reference_position' in validation:
                        logger.debug(f'Found Reference position for strategy {strategy}')
                        try:
                            ecef_m = validation['reference_position'][strategy]
                            logger.debug(f'Found Reference position for strategy {strategy}: {str(ecef_m)}')
                            llh = transformer_xyz_lla.transform(*ecef_m)
                            reference = jason.PositionFix(datetime.datetime.now(), *llh)
                        except KeyError:
                            pass

                    elif 'reference_trajectory' in validation:
                        try:
                            logger.debug(f'Found reference trajectory for strategy {strategy}')
                            trajectory_file =  validation['reference_trajectory'][strategy]
                            reference = jason.convert_csv_output_to_processing_solutions(trajectory_file)
                        except KeyError:
                            pass

                enus = compute_enu_differences(positions, reference)
                results[test_short_name].append(enus)

            os.chdir(src_dir)

    return results
 
# ------------------------------------------------------------------------------

def compute_enu_differences(positions, reference):

    if positions is None or reference is None:
        return None

    enus = []
    for position in positions:
        position_ref = reference.interpolate(position.epoch)
        lon_ref = position_ref.longitude_deg
        lat_ref = position_ref.latitude_deg
        hgt_ref = position_ref.altitude_m
        xyz_ref = transformer_lla_xyz.transform(lon_ref, lat_ref, hgt_ref )

        lon = position.longitude_deg
        lat = position.latitude_deg
        hgt = position.altitude_m
        xyz = transformer_lla_xyz.transform(lon, lat, hgt)

        d_xyz = np.subtract(xyz, xyz_ref)

        enu = geodetic.ecef_to_enu(lon_ref, lat_ref, *d_xyz)

        enus.append(enu)

    return enus

# ------------------------------------------------------------------------------

def _render_report(descriptions, results, output_folder, report_name, runby, processing_engine):
    

    statistics = _compute_statistics(descriptions, results)

    logger.debug(f'Computed statistics')
    
    statistic_tables = _build_markdown_tables(descriptions, statistics)

    logger.debug(f'Computed statistics table')

    output_abspath = os.path.abspath(output_folder)
    logger.debug(f'Output absolute path [ {output_abspath} ]')

    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tempfolder:
        os.chdir(tempfolder)

        figure_path = os.path.join(tempfolder, 'figures')
        os.mkdir(figure_path)

        figures = {}
        for test_name, description in descriptions.items():
            result = results[test_name]
            figures[test_name] = _make_plots(test_name, description, result, figure_path)

        doc = None
        with open(os.path.join(TEMPLATES_PATH, 'report.md.jinja'), 'r') as fh:
            template = jinja2.Template(fh.read())
            render_values = {
                'tests': descriptions,
                'figures': figures,
                'date': datetime.datetime.utcnow(),
                'runby': runby,
                'statistic_tables': statistic_tables,
                'engine_version': processing_engine.version()
            }
            doc = template.render(render_values)

        markdown_filename = os.path.join(tempfolder, 'report.md') 
        with open(markdown_filename, "w") as outfh:
            outfh.write(doc)


        logger.debug(f'Markdown report rendered {markdown_filename}')

        # hack: if read is not performed, the pandoc command does not work
        with open(markdown_filename, "r") as fh:
            _ = fh.read()
    
        output_filename = os.path.join(output_abspath, report_name)
        if output_filename.endswith('.md'):
            figure_dst_path = os.path.join(output_abspath, 'figures')
            shutil.rmtree(figure_dst_path, ignore_errors=True)
            shutil.copytree(figure_path, figure_dst_path)
            shutil.copy(markdown_filename, output_filename)

        else:
            cmd = ["pandoc", "-o", output_filename, markdown_filename]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()

            logger.debug(f'pandoc stdout: {stdout}')
            logger.debug(f'pandoc stderr: {stderr}')

        os.chdir(cwd)

        logger.debug(f'Written report: {output_filename}')

    return output_filename

# ------------------------------------------------------------------------------

def compute_horiz_and_vertical_rms(enus: list = []) -> Tuple[float, float]:

    rms_h = INVALID_RMS_VALUE
    rms_up = INVALID_RMS_VALUE

    if enus is not None:

        enus = np.array(enus)
        enus = np.atleast_1d(enus)

        N = len(enus[:,0])
        rms_east = np.linalg.norm(enus[:,0]) / np.sqrt(N)
        rms_north = np.linalg.norm(enus[:,1]) / np.sqrt(N)
        rms_h = np.linalg.norm([rms_east, rms_north]) 
        rms_up = np.linalg.norm(enus[:,2])  / np.sqrt(N)

    return rms_h, rms_up

# ------------------------------------------------------------------------------

def _compute_statistics(descriptions, results):
    
    statistics = {}
    for test_short_name,result in results.items():

        conf_list = enumerate(descriptions[test_short_name]['configurations'])
        
        statistics[test_short_name] = []
        for i_conf, _ in conf_list:

            rms = compute_horiz_and_vertical_rms(result[i_conf])

            statistics[test_short_name].append(rms)
            
    return statistics    

# ------------------------------------------------------------------------------

def _make_plots(test_name, description, result, dst_folder):
    
    enus = {}
    for i_config, config in enumerate(description['configurations']):
        
        strategy = config['strategy']
        dynamics = config['rover_dynamics']
        
        if strategy not in enus:
            enus[strategy] = {}
        
        enus[strategy][dynamics] = result[i_config]

        
    filenames = []
    
    for strategy in enus:
        
        fig = plt.figure(figsize=(10,10))
        ax = fig.gca()

        name = description['info']['name']
        ax.set_title(f'{name} - {strategy}\nDifference ($\Delta$) against reference')

        if enus[strategy]['dynamic'] is not None and enus[strategy]['static'] is not None:

            enu_dynamic = np.array(enus[strategy]['dynamic'])
            enu_static = np.array(enus[strategy]['static'])
            ax.plot(enu_dynamic[:,0], enu_dynamic[:,1], '.b', color='#0072bd', markersize=2, label='dynamic')
            ax.plot(enu_static[:,0], enu_static[:,1], '.r', color='#a2142f', markersize=14, label='static')
            ax.legend()
            ax.set_aspect('equal')

            max_delta = max( [max(np.abs(enu_dynamic[:,0]-enu_static[:,0])), max(np.abs(enu_dynamic[:,1]-enu_static[:,1]))] )

            ax.set_xlim(enu_static[:,0]-max_delta, enu_static[:,0]+max_delta)
            ax.set_ylim(enu_static[:,1]-max_delta, enu_static[:,1]+max_delta)

            max_delta = max( [max(np.abs(enu_dynamic[:,0])), max(np.abs(enu_dynamic[:,1]))] )

            ax.set_xlim(-max_delta, +max_delta)
            ax.set_ylim(-max_delta, +max_delta)

            ax.set_xlabel('$\Delta$ Easting [m]')
            ax.set_ylabel('$\Delta$ Northing [m]')
            ax.grid(color='0.95')

        plt.plot()
        output_file = os.path.join(dst_folder, f'{test_name}_{strategy.lower()}.{FIGURE_FORMAT}')
        plt.savefig(output_file)
        filenames.append(os.path.basename(output_file))

    return filenames

# ------------------------------------------------------------------------------

def _build_markdown_tables(descriptions, statistics):
    
    statistics_md = {}

    for test_short_name, stats in statistics.items():

        markdown_table = '| strategy | dynamics | Horizontal error [m] | Vertical error [m] |\n'
        markdown_table += '|:---:|:---:|:---:|:---:|\n'
        
        description = descriptions[test_short_name]

        configurations = enumerate(description['configurations'])
        for i_conf, configuration in configurations:
            strategy = configuration['strategy']
            dynamics = configuration['rover_dynamics']
            rms_h, rms_v = stats[i_conf]
        
            markdown_table += '|{}|{}|{:.3f}|{:.3f}|\n'.format(strategy, dynamics, rms_h, rms_v)

        statistics_md[test_short_name] = markdown_table

    return statistics_md

# ------------------------------------------------------------------------------
