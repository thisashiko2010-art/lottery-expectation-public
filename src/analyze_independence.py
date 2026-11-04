#!/usr/bin/env python3
"""Structure-preserving temporal-independence diagnostics for six JP lotteries."""
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

GAMES = {
    "miniloto": {"mode":"set", "N":31, "k":5},
    "loto6": {"mode":"set", "N":43, "k":6},
    "loto7": {"mode":"set", "N":37, "k":7},
    "numbers3": {"mode":"digits", "width":3},
    "numbers4": {"mode":"digits", "width":4},
    "bingo5": {"mode":"bingo", "width":8},
}

def load_draws(db: str, game: str):
    with sqlite3.connect(db) as con:
        df = pd.read_sql_query("SELECT draw_no,draw_date,numbers_json,winning_number FROM draws WHERE game=? ORDER BY draw_no", con, params=(game,))
    if df.empty: raise ValueError(f"No data for {game}")
    ids = df.draw_no.to_numpy(dtype=int)
    if len(np.unique(ids)) != len(ids) or np.any(np.diff(ids) <= 0):
        raise ValueError(f"Duplicate or unordered draw IDs for {game}")
    if not np.array_equal(ids, np.arange(ids[0], ids[-1] + 1)):
        raise ValueError(f"Missing draw IDs for {game}")
    cfg=GAMES[game]
    if cfg['mode']=='digits':
        vals=[]
        for value in df.winning_number.astype(str):
            value=value.zfill(cfg['width'])
            if len(value)!=cfg['width'] or not value.isdigit(): raise ValueError(f"Invalid winning number: {value}")
            vals.append([int(c) for c in value])
        rows=np.asarray(vals,dtype=np.int8)
    else:
        rows=np.asarray([json.loads(s) for s in df.numbers_json],dtype=int)
        if cfg['mode']=='set':
            if rows.shape[1]!=cfg['k'] or np.any((rows<1)|(rows>cfg['N'])): raise ValueError(f"Invalid number range/count for {game}")
            if any(len(set(r))!=cfg['k'] for r in rows): raise ValueError(f"Duplicate number within draw for {game}")
        else:
            if rows.shape[1]!=8: raise ValueError('Bingo5 must contain 8 cells')
            rows=rows.copy()
            for j in range(8): rows[:,j] -= 5*j
            if np.any((rows<1)|(rows>5)): raise ValueError('Bingo5 cell outside 1..5')
        rows=rows.astype(np.int8)
    return df, rows

def encode_channels(rows: np.ndarray, game: str) -> np.ndarray:
    """One-hot channels; row order is the draw order, columns retain within-draw structure."""
    cfg=GAMES[game]
    if cfg['mode']=='set':
        out=np.zeros((len(rows),cfg['N']),dtype=np.int8)
        rr=np.repeat(np.arange(len(rows)),rows.shape[1])
        cc=rows.reshape(-1)-1
        out[rr,cc]=1
        return out
    categories=5 if cfg['mode']=='bingo' else 10
    first=1 if cfg['mode']=='bingo' else 0
    return np.concatenate([(rows[:,j,None] == np.arange(first,first+categories)[None,:]).astype(np.int8) for j in range(rows.shape[1])],axis=1)

def max_lag_correlation(x: np.ndarray, max_lag: int) -> float:
    x=np.asarray(x,dtype=np.float64)
    best=0.0
    for lag in range(1,min(max_lag,len(x)-2)+1):
        a=x[:-lag]; b=x[lag:]
        ac=a-a.mean(axis=0); bc=b-b.mean(axis=0)
        den=np.sqrt(np.sum(ac*ac,axis=0)*np.sum(bc*bc,axis=0))
        num=np.sum(ac*bc,axis=0)
        corr=np.divide(num,den,out=np.zeros_like(num),where=den>0)
        if corr.size: best=max(best,float(np.max(np.abs(corr))))
    return best

def permutation_test(rows: np.ndarray, game: str, reps: int, seed: int, max_lag: int):
    """Permute whole draw rows, never individual channels; preserves each draw's structure."""
    x=encode_channels(rows,game)
    observed=max_lag_correlation(x,max_lag)
    rng=np.random.default_rng(seed)
    exceed=0
    for _ in range(reps):
        permuted=x[rng.permutation(len(x))]
        if max_lag_correlation(permuted,max_lag) >= observed-1e-15: exceed += 1
    return {"statistic":"maximum absolute one-hot channel correlation over lags",
            "observed_max_abs_correlation":observed,"max_lag":min(max_lag,len(x)-2),
            "permutations":reps,"seed":seed,"p_value":(exceed+1)/(reps+1),
            "null":"uniform permutation of complete draw rows; within-draw combinations/digit vectors/cell vectors preserved"}

def adjacent_overlap(rows: np.ndarray):
    overlaps=np.asarray([len(set(a.tolist()) & set(b.tolist())) for a,b in zip(rows[:-1],rows[1:])],dtype=int)
    vals,counts=np.unique(overlaps,return_counts=True)
    return {"adjacent_pairs":int(len(overlaps)),"mean_shared_numbers":float(overlaps.mean()),
            "overlap_count_distribution":{str(int(v)):int(c) for v,c in zip(vals,counts)},
            "note":"Descriptive only in this version; no separate p-value is attached."}

def analyze(db: str, out: str, reps: int=999, seed: int=20261101, max_lag: int=10):
    report={"version":"0.4","purpose":"Exploratory temporal dependence diagnostics; not a prediction model.",
            "method_note":"Permutation unit is the complete draw row. This corrects v0.2's channel-wise shuffle, which could break within-draw structure.",
            "seed":seed,"permutations_per_game":reps,"games":{}}
    for idx,game in enumerate(GAMES):
        df,rows=load_draws(db,game)
        temporal=permutation_test(rows,game,reps,seed+idx,max_lag)
        item={"draw_count":int(len(rows)),"draw_range":[int(df.draw_no.min()),int(df.draw_no.max())],
              "date_range":[str(df.draw_date.min()),str(df.draw_date.max())],
              "temporal_dependence":temporal,
              "adjacent_identical_draws":int(np.sum(np.all(rows[1:]==rows[:-1],axis=1)))}
        if GAMES[game]['mode']=='set': item['adjacent_overlap']=adjacent_overlap(rows)
        report['games'][game]=item
    report['interpretation']="A small raw p-value is only a screening signal. It is not evidence of a physical cause or a reliable next-draw advantage. Confirm data quality, adjust for multiple testing, and reproduce on a pre-specified holdout period before any conclusion."
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--db',default='database/lottery_history.sqlite3')
    p.add_argument('--out',default='reports/independence_analysis_v0_4.json')
    p.add_argument('--permutations',type=int,default=999)
    p.add_argument('--seed',type=int,default=20261101)
    p.add_argument('--max-lag',type=int,default=10)
    a=p.parse_args()
    r=analyze(a.db,a.out,a.permutations,a.seed,a.max_lag)
    for g,v in r['games'].items(): print(f"{g}: n={v['draw_count']}, max-r={v['temporal_dependence']['observed_max_abs_correlation']:.5f}, p={v['temporal_dependence']['p_value']:.4f}")
