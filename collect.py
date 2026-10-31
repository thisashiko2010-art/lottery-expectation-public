#!/usr/bin/env python3
"""Six-game public lottery archive collector. Keeps raw JSON and normalized CSV."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
import requests
import pandas as pd

ROOT=Path(__file__).resolve().parent
SOURCES=json.loads((ROOT/'config/sources.json').read_text(encoding='utf-8'))
SCHEMA={'loto6':(6,43,1),'loto7':(7,37,2),'miniloto':(5,31,1),'bingo5':(8,40,0),'numbers3':(3,9,0),'numbers4':(4,9,0)}

def first(d,*keys):
    if isinstance(d,dict):
        for k in keys:
            if k in d and d[k] is not None: return d[k]
    return None

def rows_from(payload):
    if isinstance(payload,list): return payload
    if isinstance(payload,dict):
        for k in ('data','draws','results','history','items'):
            if isinstance(payload.get(k),list): return payload[k]
    raise ValueError('JSON内に履歴配列がありません')

def as_ints(v):
    if v is None: raise ValueError('数字データがありません')
    if isinstance(v,str):
        # comma / Japanese comma / whitespace separated; preserve digit string for Numbers elsewhere
        v=[x for x in re.split(r'[,、\s]+',v.strip()) if x]
    if not isinstance(v,(list,tuple)): v=[v]
    return [int(x) for x in v]

def normalize(game, rows):
    count,maxnum,bonus_count=SCHEMA[game]; result=[]; issues=[]
    for i,r in enumerate(rows,1):
        try:
            if not isinstance(r,dict): raise ValueError('行がオブジェクト形式ではありません')
            draw=first(r,'round','draw_no','draw','no','回号','開催回','drawNumber')
            date=first(r,'date','draw_date','抽せん日','抽選日','開催日')
            if draw is None: raise ValueError('回号がありません')
            if date is None: raise ValueError('抽せん日がありません')
            # Accept both the documented feed shape (round/date/numbers/bonus)
            # and common camelCase shape (drawNumber/date/main/bonus).
            nums=first(r,'numbers','winning_numbers','main_numbers','本数字','main')
            if nums is None:
                cols=[f'n{x}' for x in range(1,count+1)]
                if all(k in r for k in cols): nums=[r[k] for k in cols]
            if game.startswith('numbers'):
                width=count
                if nums is None: nums=first(r,'number','winning_number','当せん番号','当選番号','result')
                if isinstance(nums,(str,int)):
                    s=str(nums).strip()
                    # Number feeds may use e.g. "=\"007\"" or plain 7.
                    m=re.search(r'="?(\d+)"?',s)
                    if m: s=m.group(1)
                    if not s.isdigit(): raise ValueError('ナンバーズ数字を解釈できません')
                    s=s.zfill(width)
                    if len(s)!=width: raise ValueError('ナンバーズの桁数が不正です')
                    number=s
                else:
                    ds=as_ints(nums)
                    if len(ds)!=width or any(x<0 or x>9 for x in ds): raise ValueError('ナンバーズの桁数または範囲が不正です')
                    number=''.join(map(str,ds))
                result.append({'draw_no':int(draw),'draw_date':str(date),'winning_number':number})
                continue
            vals=as_ints(nums)
            if len(vals)!=count: raise ValueError(f'本数字は{count}個必要です')
            if len(set(vals))!=count: raise ValueError('本数字に重複があります')
            if any(x<1 or x>maxnum for x in vals): raise ValueError('本数字の範囲外です')
            if game=='bingo5':
                for col,val in enumerate(vals):
                    lo,hi=col*5+1,col*5+5
                    if not lo<=val<=hi: raise ValueError(f'ビンゴ5第{col+1}列の範囲外です')
            else: vals=sorted(vals)
            bonus=first(r,'bonus','bonus_number','bonus_numbers','ボーナス数字','Ｂ数字')
            bvals=[] if bonus is None or bonus==[] else as_ints(bonus)
            if len(bvals) not in (0,bonus_count): raise ValueError(f'ボーナス数字は{bonus_count}個必要です')
            if any(x<1 or x>maxnum for x in bvals): raise ValueError('ボーナス数字の範囲外です')
            if set(vals)&set(bvals): raise ValueError('本数字とボーナス数字が重複しています')
            row={'draw_no':int(draw),'draw_date':str(date)}
            row.update({f'n{x+1}':v for x,v in enumerate(vals)})
            row.update({f'bonus{x+1}':bvals[x] if x<len(bvals) else None for x in range(bonus_count)})
            result.append(row)
        except Exception as e: issues.append(f'行{i}: {e}')
    return result,issues

def collect(games,timeout=40):
    for d in ('data/raw','data/normalized','reports'): (ROOT/d).mkdir(parents=True,exist_ok=True)
    report={'collected_at_utc':datetime.now(timezone.utc).isoformat(),'games':{}}
    session=requests.Session(); session.headers['User-Agent']='LotteryResearchCollector/0.3 (personal research)'
    for game in games:
        url=SOURCES[game]; info={'source_url':url,'status':'failed'}
        try:
            res=session.get(url,timeout=timeout); res.raise_for_status(); raw=res.content
            if not raw: raise ValueError('空ファイルです')
            (ROOT/f'data/raw/{game}.json').write_bytes(raw)
            payload=res.json(); source_rows=rows_from(payload); normalized,issues=normalize(game,source_rows)
            if not normalized: raise ValueError('有効な抽せんデータが0件です。JSON構造を確認してください')
            df=pd.DataFrame(normalized)
            df=df.sort_values('draw_no').reset_index(drop=True)
            dup=int(df['draw_no'].duplicated().sum())
            nums=df['draw_no'].astype(int).tolist(); gaps=[]
            unique=sorted(set(nums))
            for a,b in zip(unique,unique[1:]):
                if b-a>1: gaps.append([a+1,b-1])
            if game.startswith('numbers'):
                widths=df['winning_number'].astype(str).str.len().unique().tolist()
                if widths!=[SCHEMA[game][0]]: issues.append(f'桁数の不一致: {widths}')
            csvpath=ROOT/f'data/normalized/{game}.csv'; df.to_csv(csvpath,index=False,encoding='utf-8-sig')
            info.update({'status':'downloaded','sha256':hashlib.sha256(raw).hexdigest(),'raw_bytes':len(raw),
                         'source_rows':len(source_rows),'valid_rows':len(df),'duplicate_draw_numbers':dup,
                         'first_draw':int(df.draw_no.min()),'last_draw':int(df.draw_no.max()),
                         'missing_draw_ranges':gaps[:300],'validation_issue_count':len(issues),
                         'validation_issues_sample':issues[:50],'normalized_csv':str(csvpath.relative_to(ROOT))})
        except Exception as e: info['error']=f'{type(e).__name__}: {e}'
        report['games'][game]=info
        print(f"{game}: {info['status']} ({info.get('valid_rows',0)} valid rows)")
    (ROOT/'reports/collection_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--games',nargs='*',choices=list(SOURCES),default=list(SOURCES)); p.add_argument('--timeout',type=int,default=40)
    a=p.parse_args(); result=collect(a.games,a.timeout)
    if any(v['status']!='downloaded' for v in result['games'].values()): raise SystemExit(1)
