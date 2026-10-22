#!/usr/bin/env python3
"""Package only audited utility files. Does not publish or contact GitHub."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import argparse,hashlib,json
from check_release import ALLOW,ROOT,check
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    errors=check()
    if errors:raise SystemExit('Release check failed: '+', '.join(errors))
    output=args.output.resolve()
    if output.exists():raise SystemExit('Output already exists; choose a new release filename')
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT/'dist'):raise SystemExit('Place releases outside the source tree or in ignored dist/')
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'x',compression=ZIP_DEFLATED) as z:
        for name in sorted(ALLOW):z.write(ROOT/name,'vbulletin425-php8/'+name)
    with ZipFile(output) as z:
        assert z.testzip() is None
        assert {n.removeprefix('vbulletin425-php8/') for n in z.namelist()}==ALLOW
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n')
    print(json.dumps({'archive':str(output),'sha256':digest,'files':len(ALLOW),'bytes':output.stat().st_size,'published':False},indent=2))
if __name__=='__main__':main()
