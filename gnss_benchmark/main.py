#!/usr/bin/env python
"""
Make report of GNSS benchmarking

This client uses Rokubun's Jason service (GNSS computing in the cloud) as the
processing engine. Therefore, the following environment variables for the service
authentication should be defined: 
- JASON_API_KEY
- JASON_SECRET_TOKEN

Usage:
    gnss_benchmark -h | --help
    gnss_benchmark --version
    gnss_benchmark make_report [-d <path>] [-t <testname> ...] [-o path] [-f filename] [-r <name>] [-l <loglevel>]
    gnss_benchmark list_tests [-d <path>] [-l <loglevel>]

Options:
    -h --help           shows the help
    -v --version        shows the version
    -r --runby <name>   Name or e-mail of the one who ran the tool [default: info@rokubun.cat]
    -o --output-folder <folder>  Output folder at which to store the report [default: .]
    -f --filename <filename>     Name of the report file. The extension of the file will 
                        define its format (other supported formats are 'odt' 
                        (OpenOffice) or 'md' (Markdown)) [default: report.pdf]
    -l --log (DEBUG | INFO | WARNING | CRITICAL)
                        Output debug information or more verbose output [default: CRITICAL]
    -t --test <testname> Select tests to run (can be repeated). If not set,
                        all tests will be run. The name of the test must be equal
                        to the folder name of the dataset folder
    -d --dataset <path> path where the datasets will be located. If not defined, 
                        tests defined in the gnss benchmark package will be used

Commands:
    make_report     Make the performance report using the test cases defined in the
                    GNSS benchmark repository
    list_tests      Outputs the list of datasets available for testing
"""
import os.path
import pkg_resources
import sys

import docopt
from roktools import logger

from . import jason
from . import report

def main():

    version = pkg_resources.require("gnss-benchmark")[0].version

    args = docopt.docopt(__doc__, version=version, options_first=False)

    logger.set_level(args['--log'])

    logger.debug("Start main, parsed arg\n {}".format(args))

    dataset_path = args['--dataset'] if args['--dataset'] else report.DATASET_PATH

    if args['make_report']:
        jason_engine = jason.ProcessingEngine()
        report.make(jason_engine, 
                    description_files_root_path=dataset_path, 
                    output_folder=args['--output-folder'],
                    report_name=args['--filename'], 
                    runby=args['--runby'], tests=args['--test'])

    if args['list_tests']:
        test_list = report.get_test_list(description_files_root_path=dataset_path)

        sys.stdout.write('\n'.join(test_list) + '\n')


    return 0

if __name__ == "__main__":

    return_code = main()
    sys.exit(return_code)
