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

import pyproj
ecef = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
lla = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')    
transformer = pyproj.Transformer.from_proj(lla, ecef)

from roktools import geodetic

TEMPLATES_PATH = pkg_resources.resource_filename('gnss_benchmark', 'templates')
DATASET_PATH = pkg_resources.resource_filename('gnss_benchmark', 'datasets')

FIGURE_FORMAT = 'png'

def make(processing_engine, description_files_root_path=DATASET_PATH, 
            output_folder='.', report_name='report.pdf', results=None, 
            runby='info@rokubun.cat'):
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

    descriptions = _fetch_test_descriptions(description_files_root_path)

    if not results:
        results = _run_processing_engine(descriptions, description_files_root_path, processing_engine)
    
    report_filename = _render_report(descriptions, results, output_folder, report_name, runby)
        
    return report_filename


# ------------------------------------------------------------------------------

def _fetch_test_descriptions(description_files_root_path):

    description_files_path = os.path.join(description_files_root_path, '*/description.json')
    description_files = glob.glob(description_files_path)

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

                cfg = {**description['inputs'], **configuration}

                positions = processing_engine(**cfg)
                reference_position = description['validation']['reference_position']
                enus = compute_enu_differences(positions, reference_position)

                results[test_short_name].append(enus)

            os.chdir(src_dir)

    return results
 
# ------------------------------------------------------------------------------

def compute_enu_differences(positions, reference_position):
    
    ref_llh = geodetic.xyz_to_lla(*reference_position)

    lons = positions['longitudedeg']
    lats = positions['latitudedeg']
    hgts = positions['heightm']

    x, y, z = list(zip(transformer.transform(lons, lats, hgts )))

    x = x[0].flatten()
    y = y[0].flatten()
    z = z[0].flatten()
    ecef_positions = np.stack([x, y, z], axis=-1)
    d_xyzs = np.subtract(ecef_positions, reference_position)

    enus = None
        
    for d_xyz in d_xyzs:
    
        incoming = [geodetic.ecef_to_enu(*ref_llh[0:2], *d_xyz)]
        if enus is None:
            enus = np.array(incoming)
        else:
            enus = np.concatenate((enus, incoming))
            
    return enus

# ------------------------------------------------------------------------------

def _render_report(descriptions, results, output_folder, report_name, runby):
    

    statistics = _compute_statistics(descriptions, results)
    
    statistic_tables = _build_markdown_tables(descriptions, statistics)

    output_abspath = os.path.abspath(output_folder)

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
                'statistic_tables': statistic_tables
            }
            doc = template.render(render_values)

        markdown_filename = os.path.join(tempfolder, 'report.md') 
        with open(markdown_filename, "w") as outfh:
            outfh.write(doc)

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
            _, _ = p.communicate()

        os.chdir(cwd)

    return output_filename

# ------------------------------------------------------------------------------

def _compute_statistics(descriptions, results):
    
    statistics = {}
    for test_short_name,result in results.items():

        conf_list = enumerate(descriptions[test_short_name]['configurations'])
        
        statistics[test_short_name] = []
        for i_conf, _ in conf_list:
            
            enus = result[i_conf]
                        
            N = len(enus[:,0])
            rms_east = np.linalg.norm(enus[:,0]) / np.sqrt(N)
            rms_north = np.linalg.norm(enus[:,1]) / np.sqrt(N)
            rms_h = np.linalg.norm([rms_east, rms_north]) 
            rms_up = np.linalg.norm(enus[:,2])  / np.sqrt(N)

            statistics[test_short_name].append((rms_h, rms_up))

            
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

        enu_dynamic = enus[strategy]['dynamic']
        enu_static = enus[strategy]['static']
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
