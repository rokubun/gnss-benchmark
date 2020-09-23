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
    gnss_benchmark make_report [-r <name>] [-o path] [-f filename] [-d <level>]

Options:
    -h --help           shows the help
    -v --version        shows the version
    -r --runby <name>   Name or e-mail of the one who ran the tool [default: info@rokubun.cat]
    -o --output-folder <folder>  Output folder at which to store the report [default: .]
    -f --filename <filename>     Name of the report file. The extension of the file will 
                        define its format (other supported formats are 'odt' 
                        (OpenOffice) or 'md' (Markdown)) [default: report.pdf]
    -d --debug (DEBUG | INFO | WARNING | CRITICAL)
                        Output debug information or more verbose output [default: CRITICAL]

Commands:
    make_report     Make the performance report using the test cases defined in the
                    GNSS benchmark repository
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

    logger.set_level(args['--debug'])

    logger.debug("Start main, parsed arg\n {}".format(args))

    if args['make_report']:

        report.make(jason.processing_engine, 
                    description_files_root_path=report.DATASET_PATH, 
                    output_folder=args['--output-folder'],
                    report_name=args['--filename'], 
                    runby=args['--runby'])

    return 0

if __name__ == "__main__":

    return_code = main()
    sys.exit(return_code)
