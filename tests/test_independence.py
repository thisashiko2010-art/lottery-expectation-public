import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.analyze_independence import encode_channels, max_lag_correlation, permutation_test

def test_lottery_set_encoding_preserves_k_per_draw():
    rows=np.array([[1,4,7],[2,5,8],[3,6,9]])
    x=encode_channels(rows,'miniloto')
    assert x.shape==(3,31)
    assert np.all(x.sum(axis=1)==3)

def test_digit_encoding_preserves_each_draw_vector():
    rows=np.array([[0,1,2],[9,8,7],[0,0,0]])
    x=encode_channels(rows,'numbers3')
    assert x.shape==(3,30)
    assert np.all(x.sum(axis=1)==3)

def test_bingo_encoding_has_eight_active_channels():
    rows=np.array([[1,2,3,4,5,1,2,3],[5,4,3,2,1,5,4,3]])
    x=encode_channels(rows,'bingo5')
    assert x.shape==(2,40)
    assert np.all(x.sum(axis=1)==8)

def test_constant_channels_do_not_crash():
    x=np.ones((20,3),dtype=int)
    assert max_lag_correlation(x,5)==0.0

def test_permutation_result_is_reproducible():
    rows=np.array([[1,2,3],[2,3,4],[3,4,5],[4,5,6],[5,6,7],[6,7,8]])
    a=permutation_test(rows,'miniloto',49,123,3)
    b=permutation_test(rows,'miniloto',49,123,3)
    assert a==b
