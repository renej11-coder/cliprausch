"""Detect existing burned-in captions before adding any text to the video."""
import csv
import hashlib
import io
from pathlib import Path
import re
import tempfile
import unicodedata
from .media import command

POLICY_VERSION=3

def tokens(text):
    text=unicodedata.normalize('NFKD',text.lower().replace('ß','ss'))
    return re.findall(r'[a-z0-9]+',text)

def existing_caption_line(line,speech):
    words=tokens(line['text']);spoken=set(tokens(speech))
    if line['confidence']<45 or not .12<=line['cx']<=.86:return False
    matching=set(words)&spoken
    speech_match=len(matching)>=2 and sum(map(len,matching))>=6 and line['cy']>=.2
    # Ambiguous subtitle-shaped text near bottom centre is preserved conservatively.
    caption_shape=.24<=line['cx']<=.76 and line['cy']>=.78 and len(words)>=2 and sum(map(len,words))>=7
    return speech_match or caption_shape

def decide(detected,complete):
    if not complete:raise ValueError('subtitle_scan_incomplete')
    return 'source_preserved' if detected else 'word_highlight'

def ocr_lines(path,width,height):
    result=command(['tesseract',str(path),'stdout','-l','deu+eng','--psm','11','tsv'])
    groups={}
    for row in csv.DictReader(io.StringIO(result.stdout),delimiter='\t'):
        if row.get('level')!='5' or not row.get('text','').strip():continue
        confidence=float(row['conf'])
        if confidence<0:continue
        key=tuple(row[k] for k in ('block_num','par_num','line_num'))
        groups.setdefault(key,[]).append((row,confidence))
    lines=[]
    for parts in groups.values():
        left=min(int(r['left']) for r,_ in parts);top=min(int(r['top']) for r,_ in parts)
        right=max(int(r['left'])+int(r['width']) for r,_ in parts)
        bottom=max(int(r['top'])+int(r['height']) for r,_ in parts)
        lines.append({'text':' '.join(r['text'] for r,_ in parts),'confidence':sum(c for _,c in parts)/len(parts),
            'cx':(left+right)/2/width,'cy':(top+bottom)/2/height})
    return lines

def scan(source,metadata,words):
    source=Path(source);fingerprint=hashlib.sha256(source.read_bytes()).hexdigest()
    report={'policy_version':POLICY_VERSION,'method':'tesseract_deu_eng_v1','source_sha256':fingerprint,
        'complete':False,'detected':False,'sample_rate':2,'frames_scanned':0,'planned_frames':0}
    with tempfile.TemporaryDirectory(prefix='cliprausch-subtitles-') as root:
        directory=Path(root)
        command(['ffmpeg','-y','-v','error','-i',str(source),'-vf','fps=2,scale=1600:-2',str(directory/'%04d.png')])
        frames=sorted(directory.glob('*.png'));report['planned_frames']=len(frames)
        if len(frames)<max(1,int(metadata['duration']*2)-2):raise ValueError('subtitle_scan_incomplete')
        height=round(metadata['height']*1600/metadata['width']/2)*2
        for index,path in enumerate(frames):
            moment=index/2+.25
            speech=' '.join(w['text'] for w in words if w['end']>=moment-1 and w['start']<=moment+1)
            try:lines=ocr_lines(path,1600,height)
            except Exception:raise ValueError('subtitle_scan_failed') from None
            report['frames_scanned']+=1
            found=next((line for line in lines if existing_caption_line(line,speech)),None)
            if found:
                report.update(detected=True,complete=True,at=moment,matched_text=found['text'][:160]);break
        else:report['complete']=True
    report['decision']=decide(report['detected'],report['complete'])
    report['added_caption_tracks']=0 if report['detected'] else 1
    return report
