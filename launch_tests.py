#!/usr/bin/env python3
import glob
import json

from roktools import logger

if __name__ == "__main__":

    logger.set_level('DEBUG')

    for test_case_description in glob.glob("**/description.json", recursive=True):

        desc = None
        with open(test_case_description, 'r') as fh:
            desc = json.load(fh)

        if not desc:
            continue

        logger.info(f'Processing test case [ {test_case_description} ]')
        logger.debug(f'Test case description {desc}')
        

