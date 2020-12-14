import datetime
import os.path

import roktools.time
import gnss_benchmark.jason as jason

# ------------------------------------------------------------------------------

def test_jason__processing_solutions_from_csv():

    path = os.path.dirname(os.path.realpath(__file__))
    csv_file = os.path.join(path, '../datasets/mosaicx5_multi_dynamic/reference_trajectory.csv')

    proc_solutions = jason.convert_csv_output_to_processing_solutions(csv_file)

    assert len(proc_solutions) == 1158

    # 2134,46615.000000,41.6423503240,2.3593755210,258.85330,0.0541,0.0445,0.1128
    epoch = roktools.time.weektow_to_datetime(46615, 2134)
    solution = proc_solutions.interpolate(epoch)
    assert round(solution.latitude_deg - 41.6423503240, 7) == 0
    assert round(solution.longitude_deg - 2.3593755210, 7) == 0
    assert round(solution.altitude_m - 258.85330, 6) == 0

    #2134,46551.000000,41.6397991150,2.3593832160,254.26630,0.0524,0.0445,0.1101
    #2134,46552.000000,41.6398669480,2.3593832030,254.30160,0.0525,0.0445,0.110
    epoch = roktools.time.weektow_to_datetime(46551.5, 2134)
    solution = proc_solutions.interpolate(epoch)
    assert round(solution.latitude_deg - (41.6397991150 + 41.6398669480) / 2, 7) == 0
    assert round(solution.longitude_deg - (2.3593832160 + 2.3593832030) / 2, 7) == 0
    assert round(solution.altitude_m - (254.26630 + 254.30160)/ 2, 6) == 0 

# ------------------------------------------------------------------------------

def test_jason__processing_solutions_single_append():

    proc_solutions = jason.ProcessingSolutions()
    assert len(proc_solutions) == 0

    proc_solution = jason.PositionFix(datetime.datetime.now(), 2.1, 41.2, 56.3)

    proc_solutions.append(proc_solution)
    assert len(proc_solutions) == 1

# ------------------------------------------------------------------------------

def test_jason__extract_solution_from_zip():

    path = os.path.dirname(os.path.realpath(__file__))
    zip_file = os.path.join(path, 'files/sample_jason_output.zip')

    out = jason.extract_solution_from_zip(zip_file, 'PPK')
    assert isinstance(out, jason.ProcessingSolutions)
    assert len(out) == 289
