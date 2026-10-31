"""Run one browser QA script and verify requested art against a supplied pinned index.

This checks observed network paths only, not a complete index restore.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
import subprocess
from urllib.parse import unquote, urlparse
from playwright.sync_api import Browser, BrowserContext

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--index',required=True,type=Path)
parser.add_argument('--report',required=True,type=Path)
parser.add_argument('script',type=Path)
args,forwarded=parser.parse_known_args()
root=Path(__file__).resolve().parents[1]
requested=set()

def observe(original):
    def create(*a,**kw):
        page=original(*a,**kw)
        def request(event):
            path=unquote(urlparse(event.url).path)
            if '/assets/' in path:requested.add('Web/wwwroot/assets/'+path.split('/assets/',1)[1])
        page.on('request',request)
        return page
    return create

Browser.new_page=observe(Browser.new_page)
BrowserContext.new_page=observe(BrowserContext.new_page)
sys.argv=[str(args.script),*forwarded]
sys.path.insert(0,str(args.script.resolve().parent))
runpy.run_path(str(args.script),run_name='__main__')
index={row['path']:row for row in json.loads(args.index.read_text())['files']}
failures=[]
source_owned=[]
for relative in sorted(requested):
    path=root/relative
    row=index.get(relative)
    if not row:
        tracked=subprocess.run(['git','ls-files','--error-unmatch',relative],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
        if tracked and path.is_file():source_owned.append(relative)
        else:failures.append({'path':relative,'reason':'neither pinned art nor tracked source'})
    elif not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
        failures.append({'path':relative,'reason':'missing or digest differs'})
report={'scope':'only browser-observed art requests; not full index hydration','requestedPaths':sorted(requested),'verified':len(requested)-len(failures),'sourceOwnedPaths':source_owned,'failures':failures}
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,indent=2))
print(json.dumps({'requestedArt':len(requested),'failures':failures}))
assert not failures,failures
