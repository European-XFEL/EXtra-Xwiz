""" To be used with pytest
"""

from extra_xwiz.utilities import determine_detector

agipd_run_path = '/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030'
jngfr_run_path = '/gpfs/exfel/exp/SPB/202031/p900145/proc/r0752'

def test_agipd_det():

    det_type = determine_detector(agipd_run_path)
    assert(det_type == 'AGIPD')

def test_jungfrau_det():

    det_type = determine_detector(jngfr_run_path)
    assert(det_type == 'JNGFR')

