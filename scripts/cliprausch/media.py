"""Secret-free rendering with genuine word timing and no added headline."""
import hashlib
import json
import math
from pathlib import Path
import subprocess

def command(args,**kwargs):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=600,**kwargs)

def validate_words(words,duration):
    if not isinstance(words,list) or not words:raise ValueError('speech_required')
    previous=0
    for word in words:
        a,b=word['start'],word['end'];text=word['text'].strip()
        if (type(a) not in (int,float) or type(b) not in (int,float) or
            not math.isfinite(a+b) or not 0<=a<b<=duration or a<previous or
            not text or len(text)>24 or word.get('probability',1)<.6):
            raise ValueError('word_timing_or_confidence_requires_correction')
        previous=b
    return words

def clock(seconds):
    ticks=round(seconds*100)
    return f'{ticks//360000}:{ticks//6000%60:02}:{ticks//100%60:02}.{ticks%100:02}'

def draft_word_timings(words,duration):
    """Preserve ASR uncertainty for review; repair only <=80ms timing overlaps."""
    result=[];uncertain=[];previous=0
    for index,word in enumerate(words):
        row=dict(word);a,b=row['start'],row['end']
        if a<previous-.08 or a<-.08 or b>duration+.12:raise ValueError('word_timing_requires_correction')
        row['start']=max(0,a,previous);row['end']=min(duration,b)
        if row.get('probability',1)<.6:uncertain.append(index)
        result.append(row);previous=row['end']
    validate_words([{k:v for k,v in w.items() if k!='probability'} for w in result],duration)
    return result,uncertain

def ass_subtitles(words,duration):
    validate_words(words,duration)
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,DejaVu Sans,58,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,90,190,390,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    groups=[];group=[]
    for word in words:
        if group and (len(group)==4 or sum(len(w['text'])+1 for w in group)+len(word['text'])>23 or
                      word['start']-group[-1]['end']>.45):
            groups.append(group);group=[]
        group.append(word)
    if group:groups.append(group)
    lines=[]
    for group in groups:
        for index,word in enumerate(group):
            end=group[index+1]['start'] if index+1<len(group) else word['end']
            def clean(s):return s.replace('\\','').replace('{','(').replace('}',')').replace('\n',' ').replace('\r',' ')
            phrase=' '.join((r'{\1c&HFFFF00&}' if i==index else r'{\1c&HFFFFFF&}')+
                            clean(w['text']) for i,w in enumerate(group))
            # Conservative all-wide-glyph bound keeps even W-heavy phrases in 800px.
            visible=' '.join(w['text'] for w in group)
            units=sum(1 if ch in 'MW@#' else .3 if ch in " il.,!|'" else .78 if ch.isupper() else .65 for ch in visible)
            font_size=min(58,max(30,int(780/max(1,units))))
            lines.append(f'Dialogue: 0,{clock(word["start"])},{clock(end)},Main,,0,0,0,,{{\\fs{font_size}\\fad(35,35)}}{phrase}')
    return header+'\n'.join(lines)+'\n'

def probe(path):
    data=json.loads(command(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]).stdout)
    video=next(s for s in data['streams'] if s['codec_type']=='video')
    audio=next(s for s in data['streams'] if s['codec_type']=='audio')
    return {'width':video['width'],'height':video['height'],'duration':float(data['format']['duration']),
        'video_codec':video['codec_name'],'audio_codec':audio['codec_name']}

def render(source,out,words=None):
    source=Path(source).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    metadata=probe(source);duration=metadata['duration']
    if not 15<=duration<=60:raise ValueError('duration_outside_15_60')
    generated=words is None;uncertain=[];uncertain_segments=[]
    if generated:
        from faster_whisper import WhisperModel
        model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4)
        segments,info=model.transcribe(str(source),language='de',word_timestamps=True,
            vad_filter=True,condition_on_previous_text=False,beam_size=5)
        words=[]
        for segment in segments:
            if segment.no_speech_prob>.5 or segment.avg_logprob<-.7:
                uncertain_segments.append({'start':segment.start,'end':segment.end,
                    'no_speech_probability':segment.no_speech_prob,'average_log_probability':segment.avg_logprob})
            words.extend(dict(start=w.start,end=w.end,text=w.word.strip(),probability=w.probability)
                for w in segment.words or [] if w.word.strip())
    if generated:words,uncertain=draft_word_timings(words,duration)
    else:validate_words(words,duration)
    (out/'transcript.json').write_text(json.dumps(words,ensure_ascii=False,indent=2),encoding='utf-8')
    display_words=[{k:v for k,v in w.items() if k!='probability'} for w in words]
    (out/'subs.ass').write_text(ass_subtitles(display_words,duration),encoding='utf-8')
    filters=('[0:v]split=2[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,'
        'crop=1080:1920,boxblur=25:10[bg];[b]scale=1080:1500:force_original_aspect_ratio=decrease,'
        'setsar=1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=subs.ass,format=yuv420p[v]')
    movie=out/'final.mp4'
    command(['ffmpeg','-y','-v','error','-i',str(source),'-filter_complex',filters,
        '-map','[v]','-map','0:a:0','-c:v','libx264','-preset','veryfast','-crf','20','-r','30',
        '-c:a','aac','-b:a','160k','-af','loudnorm=I=-16:TP=-1.5:LRA=11',
        '-movflags','+faststart',str(movie)],cwd=out)
    final=probe(movie)
    if (final['width'],final['height'],final['video_codec'],final['audio_codec'])!=(1080,1920,'h264','aac') or not 15<=final['duration']<=60.1:
        raise ValueError('render_qa_failed')
    command(['ffmpeg','-v','error','-xerror','-i',str(movie),'-f','null','-'])
    command(['ffmpeg','-y','-v','error','-i',str(movie),'-vf','fps=1/4,scale=270:-2,tile=3x5',
        '-frames:v','1',str(out/'contact-sheet.jpg')])
    evidence={**final,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'sha256':hashlib.sha256(movie.read_bytes()).hexdigest(),'subtitle_mode':'word_highlight',
        'headline':False,'full_decode':True,'human_review':'required',
        'uncertain_word_indexes':uncertain,'uncertain_segments':uncertain_segments,
        'transcript_accuracy':'draft_not_verified'}
    (out/'qa.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    return evidence
