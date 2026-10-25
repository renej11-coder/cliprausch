"""Run without service credentials."""
import json
import sys
from .media import render

if __name__=='__main__':
    words=json.loads(open(sys.argv[3],encoding='utf-8').read()) if len(sys.argv)>3 else None
    render(sys.argv[1],sys.argv[2],words)
