""" To be used with pytest
"""

from pathlib import Path

from extra_xwiz.geometry import check_geom_format

RSRC_PATH = '/gpfs/exfel/sw/software/xwiz_resources'

def test_correct_vds():
    geometry = Path(RSRC_PATH) / 'agipd_mar18_v11.geom'
    use_peaks = False
    assert check_geom_format(geometry, use_peaks) == True


def test_wrong_vds():
    geometry = Path(RSRC_PATH) / 'agipd_may20_v0.geom'
    use_peaks = False
    assert check_geom_format(geometry, use_peaks) == False


def test_correct_cxi():
    geometry = Path(RSRC_PATH) / 'agipd_may20_v0.geom'
    use_peaks = True
    assert check_geom_format(geometry, use_peaks) == True


def test_wrong_cxi():
    geometry = Path(RSRC_PATH) / 'agipd_mar18_v11.geom'
    use_peaks = True
    assert check_geom_format(geometry, use_peaks) == False


def test_wrong_mix():
    geometry = Path(RSRC_PATH) / 'agipd_2304_v1a.geom'
    use_peaks = True
    assert check_geom_format(geometry, use_peaks) == False
    use_peaks = False
    assert check_geom_format(geometry, use_peaks) == False



