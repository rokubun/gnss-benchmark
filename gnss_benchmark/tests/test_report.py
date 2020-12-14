import datetime
import os.path
import numpy as np

import roktools.time

import gnss_benchmark.report as report
import gnss_benchmark.jason as jason

def test_report__reference_trajectory_zero():

    path = os.path.dirname(os.path.realpath(__file__))
    csv_file = os.path.join(path, '../datasets/mosaicx5_multi_dynamic/reference_trajectory.csv')

    with open(csv_file, 'r') as fh_ref, open(csv_file, 'r') as fh_pos:

        reference = jason.convert_csv_output_to_processing_solutions(fh_ref)
        positions = jason.convert_csv_output_to_processing_solutions(fh_pos)

        enus = report.compute_enu_differences(positions, reference)
        assert len(enus) > 0

        enus = np.array(enus)
        assert np.mean(enus[:,0]) == 0
        assert np.mean(enus[:,1]) == 0
        assert np.mean(enus[:,2]) == 0


def test_report__compute_enu_differences_from_jason_zip():

    # 2106,238777.639000,41.4045930960,2.1550031360,135.81620,0.0717,0.0928,0.1857
    epoch = roktools.time.weektow_to_datetime(238777.639000, 2106)
    reference = jason.PositionFix(epoch,2.1550031360, 41.4045930960, 135.81620)

    path = os.path.dirname(os.path.realpath(__file__))
    zip_file = os.path.join(path, 'files/sample_jason_output.zip')

    positions = jason.extract_solution_from_zip(zip_file, 'PPK')
    assert len(positions) == 289

    enus = report.compute_enu_differences(positions, reference)
    assert len(enus) == 289

    rms_h, rms_u = report.compute_horiz_and_vertical_rms(enus)

    assert rms_h != report.INVALID_RMS_VALUE
    assert rms_u != report.INVALID_RMS_VALUE