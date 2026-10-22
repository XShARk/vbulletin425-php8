#!/usr/bin/env python3
"""Offline patcher for a licensed copy. No vendor files or credentials bundled."""
from __future__ import annotations
import argparse,base64,concurrent.futures,contextlib,datetime,hashlib,json,os,re,shutil,stat,subprocess,sys,tempfile,uuid
from pathlib import Path

HOME=Path(__file__).resolve().parent
VERSION='0.1.0-alpha.1'
RUNTIME={'includes/vb425_php8_runtime.php':'runtime.php','includes/vb425_php8_transformer.php':'transformer.php'}

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def normalise(data:bytes)->bytes:
    data=data.replace(b'\r\n',b'\n')
    # Vendor downloads personalise these metadata lines per license/account.
    data=re.sub(rb'^(\|\| # vBulletin 4\.2\.5 - Licence Number )[A-Za-z0-9]+[ \t]*(?:\|\|)?$',rb'\1<license>',data,flags=re.M)
    data=re.sub(rb'^(\|\| # Copyright [^\r\n0-9]*[0-9]{4}-)[0-9]{4}',rb'\1<year>',data,flags=re.M)
    return re.sub(rb'^(\|\| # Downloaded: )[0-9:, A-Za-z]+(: \$Revision: [0-9]+ \$)',rb'\1<date>\2',data,flags=re.M)
def normal_sha(data:bytes)->str:return sha(normalise(data))

def worker(sources:dict[str,bytes],php:str)->dict[str,bytes]:
    body=[{'path':name,'source':base64.b64encode(data).decode()} for name,data in sources.items()]
    proc=subprocess.run([php,str(HOME/'php/worker.php')],input=json.dumps(body).encode(),capture_output=True,timeout=120)
    if proc.returncode:raise RuntimeError('PHP tokenizer failed; no files changed. '+proc.stderr.decode(errors='replace')[:400])
    rows=json.loads(proc.stdout)
    errors=[row['path']+':'+str(row['parse_error']['line']) for row in rows if row['parse_error']]
    if errors:raise ValueError('Transformed PHP does not parse: '+', '.join(errors))
    return {row['path']:base64.b64decode(row['source']) for row in rows}

def replace_once(data:bytes,before:bytes,after:bytes,name:str)->bytes:
    if data.count(before)!=1:raise RuntimeError('Unexpected core anchor: '+name)
    return data.replace(before,after,1)

def core_rules(name:str,raw:bytes)->bytes:
    # Small context edits only; no complete vendor functions are redistributed.
    newline=b'\r\n' if b'\r\n' in raw else b'\n'
    source=raw
    if name=='includes/class_core.php':
        source=replace_once(source,b'<?php',b"<?php"+newline+b"require_once __DIR__.'/vb425_php8_runtime.php';",name+':bootstrap')
        source=source.replace(b'function execute_query($buffered = true, &$link)',b'function execute_query($buffered, &$link)')
        source=source.replace(b'strval($data) + 0',b'vb425_php8_number($data)')
        source=source.replace(b'preRegister($template_name, array $variables = NULL)',b'preRegister($template_name, ?array $variables = NULL)')
        source=source.replace(b'eval($template_code);',b'eval(vb425_php8_fragment($template_code));')
        old=b'''eval('$final_rendered = "' . $template_code . '";');'''
        new=b'''eval(vb425_php8_fragment('$final_rendered = "' . $template_code . '";'));'''
        source=replace_once(source,old,new,name+':legacy-template')
    if name=='includes/class_xml.php':
        for method in [b'handle_cdata',b'handle_element_start',b'handle_element_end']:
            source=source.replace(b'function '+method+b'(&$parser,',b'function '+method+b'($parser,')
        source,n=re.subn(rb'(class XMLparser extends vB_XML_Parser\s*\{\s*\})',lambda m:b"if (!class_exists('XMLParser', false)) {"+newline+m[1]+newline+b'}',source)
        if n!=1:raise RuntimeError('Unexpected XML alias anchor')
    if name=='includes/class_hook.php':
        source=replace_once(source,b'return self::$pluginlist["$hookname"];',b'return vb425_php8_fragment(self::$pluginlist["$hookname"]);',name+':hook-code')
    if name=='includes/adminfunctions_template.php':
        # Only the compiler return immediately following the template_compile hook.
        source,n=re.subn(rb"(fetch_hook\('template_compile'\)[^\n]*\n\s*)return \$template;",rb'\1return vb425_php8_fragment($template);',source)
        if n!=1:raise RuntimeError('Unexpected template compiler anchor')
    if name=='ajax.php':source=source.replace(b'if (!VB_API)',b"if (!defined('VB_API') || !VB_API)")
    if name in {'admincp/subscriptions.php','admincp/template.php'}:
        def legacy_ternary(match):
            expression=match[1]
            first=expression.index(b'?');second=expression.index(b'?',first+1)
            return b'log_admin_action(('+expression[:second].rstrip()+b') '+expression[second:]+b');'
        source,n=re.subn(rb'log_admin_action\(([^\r\n]+\?[^\r\n]+\?[^\r\n]+)\);',legacy_ternary,source)
        if n!=1:raise RuntimeError('Unexpected legacy admin ternary')
    if name=='packages/vbcms/search/result/content.php':
        source,n=re.subn(rb"(if\s*\(!\(\$search_result\['publishdate'\][^\n]+\)\)\s*\{\s*)continue;",rb'\1return false;',source,count=1)
        if n!=1:raise RuntimeError('Unexpected CMS non-loop continue')
    return source

def ensure_root(root:Path)->Path:
    if root.is_symlink():raise ValueError('A symlink cannot be the forum root')
    root=root.resolve(strict=True)
    core=root/'includes/class_core.php'
    if not core.is_file() or not re.search(rb"define\(['\"]FILE_VERSION['\"],\s*['\"]4\.2\.5['\"]",core.read_bytes()):
        raise ValueError('This profile requires vBulletin 4.2.5 (not an upgrade from another version)')
    return root

def safe_path(root:Path,name:str)->Path:
    rel=Path(name)
    if rel.is_absolute() or '..' in rel.parts or ':' in name or '\\' in name:raise ValueError('Unsafe relative path')
    path=root/rel
    current=path
    while current!=root:
        if current.is_symlink():raise ValueError('Symlink in target: '+name)
        current=current.parent
    if not path.resolve().is_relative_to(root):raise ValueError('Path escapes root')
    return path

def plan(root:Path,php:str)->tuple[dict,dict[str,bytes]]:
    profile=json.loads((HOME/'profiles/4.2.5.json').read_text())
    originals={};conflicts=[];missing=[];already=0;compatible=0
    for name,row in profile['files'].items():
        p=safe_path(root,name)
        if not p.exists():
            if name in profile['required']:missing.append(name)
            continue
        raw=p.read_bytes();digest=normal_sha(raw)
        if digest==row['patched_sha256']:
            if row['stock_sha256']==row['patched_sha256']:compatible+=1
            else:already+=1
            continue
        if digest!=row['stock_sha256']:conflicts.append(name);continue
        originals[name]=raw
    transformed=worker({name:core_rules(name,raw) for name,raw in originals.items()},php)
    for name,raw in transformed.items():
        if normal_sha(raw)!=profile['files'][name]['patched_sha256']:raise ValueError('Rules/profile mismatch; no files changed: '+name)
    changes={name:raw for name,raw in transformed.items() if raw!=originals[name]}
    for name,source in RUNTIME.items():
        new=(HOME/'php'/source).read_bytes();p=safe_path(root,name)
        if p.exists() and p.read_bytes()!=new:conflicts.append(name)
        elif not p.exists():changes[name]=new
    known=set(profile['files'])|set(RUNTIME)
    unknown=sorted(p.relative_to(root).as_posix() for p in root.rglob('*.php') if p.is_file() and p.relative_to(root).as_posix() not in known and p.relative_to(root).as_posix()!='includes/config.php')
    report={'tool_version':VERSION,'target':'PHP 8.4','files_to_change':sorted(changes),'already_patched_files':already,
        'unchanged_compatible_files':compatible,
        'modified_core_conflicts':conflicts,'missing_required_files':missing,'third_party_php_not_modified':unknown,
        'planned_input_sha256':{name:sha(originals[name]) if name in originals else None for name in changes},
        'database_modified':False,'safe_to_apply':not(conflicts or missing)}
    return report,changes

def lint(changes:dict[str,bytes],php:str)->list[str]:
    with tempfile.TemporaryDirectory(prefix='vb425-lint-') as td:
        paths=[]
        for i,(name,data) in enumerate(changes.items()):
            p=Path(td)/(str(i)+'.php');p.write_bytes(data);paths.append((name,p))
        def one(item):
            name,path=item;p=subprocess.run([php,'-l',str(path)],capture_output=True,timeout=30)
            return name if p.returncode else None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:return [x for x in executor.map(one,paths) if x]

def atomic(path:Path,data:bytes,mode:int|None=None):
    fd,name=tempfile.mkstemp(prefix='.vb425-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:handle.write(data);handle.flush();os.fsync(handle.fileno())
        os.chmod(name,mode if mode is not None else 0o644)
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

@contextlib.contextmanager
def site_lock(root:Path):
    lock=root/'.vb425-php8-lock'
    try:lock.mkdir(mode=0o700)
    except FileExistsError:raise ValueError('An apply/restore lock exists; check for a running or interrupted operation')
    try:yield
    finally:lock.rmdir()

def apply(root:Path,php:str,backup_root:Path,report:dict,changes:dict[str,bytes])->dict:
    backup_root=backup_root.resolve()
    if backup_root.is_relative_to(root) or backup_root.is_relative_to(HOME):raise ValueError('Backup directory must be outside both the forum and this public project')
    if not report['safe_to_apply']:raise ValueError('Modified or missing core files: review the report; no changes applied')
    failed=lint(changes,php)
    if failed:raise ValueError('PHP lint failed; no changes applied: '+', '.join(failed))
    if not changes:return {**report,'applied':0}
    backup_root.mkdir(parents=True,exist_ok=True,mode=0o700)
    run=backup_root/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]);run.mkdir(mode=0o700)
    rows=[]
    for name,data in changes.items():
        path=safe_path(root,name);exists=path.exists();old=path.read_bytes() if exists else None
        if (sha(old) if exists else None)!=report['planned_input_sha256'][name]:raise RuntimeError('File changed after check: '+name)
        row={'path':name,'before_sha256':sha(old) if exists else None,'after_sha256':sha(data),'mode':stat.S_IMODE(path.stat().st_mode) if exists else 0o644}
        if exists:
            target=run/'files'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(old)
        rows.append(row)
    manifest={'tool_version':VERSION,'root':str(root),'files':rows,'status':'prepared'}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2))
    written=[]
    try:
        for row in rows:
            path=safe_path(root,row['path']);current=sha(path.read_bytes()) if path.exists() else None
            if current!=row['before_sha256']:raise RuntimeError('Concurrent edit detected: '+row['path'])
            atomic(path,changes[row['path']],row['mode']);written.append(row)
    except BaseException:
        for row in reversed(written):
            path=safe_path(root,row['path'])
            if row['before_sha256'] is None:path.unlink()
            else:atomic(path,(run/'files'/row['path']).read_bytes(),row['mode'])
        raise
    manifest['status']='applied';(run/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return {**report,'applied':len(rows),'backup_run':str(run)}

def restore(root:Path,run:Path)->dict:
    run=run.resolve(strict=True);m=json.loads((run/'manifest.json').read_text())
    if Path(m['root']).resolve()!=root or m['status'] not in {'applied','prepared'}:raise ValueError('Backup root/status does not match')
    paths=[]
    for row in m['files']:
        path=safe_path(root,row['path'])
        backup=safe_path(run/'files',row['path'])
        if row['before_sha256'] is not None and (not backup.is_file() or sha(backup.read_bytes())!=row['before_sha256']):raise ValueError('Backup integrity failure')
        current=sha(path.read_bytes()) if path.is_file() else None
        if current==row['before_sha256']:continue
        if current!=row['after_sha256']:raise ValueError('Restore would overwrite a later edit: '+row['path'])
        paths.append((row,path,backup))
    completed=[]
    try:
        for row,path,backup in reversed(paths):
            patched=path.read_bytes()
            if sha(patched)!=row['after_sha256']:raise ValueError('Concurrent edit during restore: '+row['path'])
            if row['before_sha256'] is None:path.unlink()
            else:atomic(path,backup.read_bytes(),row['mode'])
            completed.append((row,path,patched))
    except BaseException:
        for row,path,patched in reversed(completed):atomic(path,patched,row['mode'])
        raise
    m['status']='restored';(run/'manifest.json').write_text(json.dumps(m,indent=2))
    return {'restored':len(paths),'database_modified':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',action='version',version=VERSION)
    parser.add_argument('command',choices=['check','apply','restore'])
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--php',default='php')
    parser.add_argument('--backup-dir',type=Path)
    parser.add_argument('--backup-run',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args(argv)
    try:
        root=ensure_root(args.root)
        if root==HOME or HOME.is_relative_to(root):raise ValueError('Keep this utility outside the forum document root')
        if args.report and (args.report.resolve().is_relative_to(root) or args.report.resolve().is_relative_to(HOME)):raise ValueError('Reports must be outside the forum and public project')
        if args.command=='restore':
            if not args.backup_run:raise ValueError('--backup-run is required')
            with site_lock(root):report=restore(root,args.backup_run)
        else:
            check=subprocess.run([args.php,'-r','exit(PHP_VERSION_ID>=80100?0:1);'],capture_output=True)
            if check.returncode:raise ValueError('The patcher requires PHP CLI >= 8.1; use the intended PHP 8.4 binary')
            if args.command=='apply':
                if not args.backup_dir:raise ValueError('--backup-dir is required')
                with site_lock(root):
                    report,changes=plan(root,args.php)
                    report=apply(root,args.php,args.backup_dir,report,changes)
            else:report,changes=plan(root,args.php)
        print(json.dumps(report,indent=2))
        if args.report:
            dest=args.report.resolve()
            if dest.is_relative_to(root):raise ValueError('Reports must be outside the forum')
            dest.write_text(json.dumps(report,indent=2),encoding='utf-8')
        return 0 if report.get('safe_to_apply',True) else 2
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as error:
        print('Error: '+str(error),file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
