"""Run without service credentials."""
import json
import sys
import traceback
from pathlib import Path
from .media import render

if __name__=='__main__':
    words=json.loads(open(sys.argv[3],encoding='utf-8').read()) if len(sys.argv)>3 else None
    try:
        render(sys.argv[1],sys.argv[2],words)
    except Exception as error:
        import re
        reason=str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z_]{3,90}',str(error)) else 'external_dependency_error'
        last=traceback.extract_tb(error.__traceback__)[-1]
        out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
        (out/'render-error.json').write_text(json.dumps({'reason':reason,'type':type(error).__name__,
            'location':Path(last.filename).name+':'+str(last.lineno)},indent=2),encoding='utf-8')
        raise SystemExit(2 if reason!='external_dependency_error' else 3)
