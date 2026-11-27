"""Rebuild the unsigned portable v1.2.0 archive using original bundled dependencies.
Usage: python rebuild_portable.py ORIGINAL_EXE SOURCE_DIR OUTPUT_EXE
Python 3.12 is required to compile compatible bytecode. No application code is executed.
"""
import sys,struct,zlib,marshal,hashlib
from pathlib import Path

original,source,output=map(Path,sys.argv[1:])
expected='eb570a43b65c1b65b5f9a304c2b7528f3d2bdef89668443de45937554a2aa609'
b=original.read_bytes()
assert hashlib.sha256(b).hexdigest()==expected,'Original release checksum mismatch'
assert sys.version_info[:2]==(3,12),'Use Python 3.12'
magic=b'MEI\014\013\012\013\016';pos=b.rfind(magic)
_,length,to,tl,version,lib=struct.unpack('!8sIIII64s',b[pos:pos+88]);start=pos+88-length
entries=[];offset=start+to
while offset<start+to+tl:
 n,p,sz,usz,compressed,kind=struct.unpack('!IIIIBc',b[offset:offset+18])
 name=b[offset+18:offset+n].rstrip(b'\0').decode();entries.append((name,kind,p,sz,usz,compressed));offset+=n

def replace_pyz(data):
 toc=dict(marshal.loads(data[struct.unpack('!I',data[8:12])[0]:]))
 body=bytearray(data[:12]);new=[]
 for name,(typ,p,sz) in toc.items():
  raw=data[p:p+sz]
  path=source/Path(*name.split('.'))
  path=path/'__init__.py' if typ==1 else path.with_suffix('.py')
  if (name=='restore_apps' or name.startswith('restore_gui')) and path.is_file():
   code=compile(path.read_bytes(),name.replace('.','/')+('/__init__.py' if typ==1 else '.py'),'exec')
   raw=zlib.compress(marshal.dumps(code),6)
  new.append((name,(typ,len(body),len(raw))));body.extend(raw)
 toc_offset=len(body);body.extend(marshal.dumps(new));body[8:12]=struct.pack('!I',toc_offset)
 return bytes(body)

extras = {name: source / "build/res" / name for name in
          ("ipatool-cpp.exe", "IPATOOL_CPP_LICENSE.txt", "IPA_DOWNLOADER_LICENSE.txt")}
for name, path in extras.items():
 assert path.is_file(), str(path)
 entries.append((name,b'b',0,0,0,1))
payload=bytearray();new_toc=bytearray();changed=[]
for name,kind,p,sz,usz,compressed in entries:
 if name.replace("\\", "/").lower() in {"ipatool.exe", "libunicorn.dll", "unicorn_copying.txt"}:
  continue
 raw=b[start+p:start+p+sz];replacement=extras[name].read_bytes() if name in extras else None
 if kind==b'z':replacement=replace_pyz(zlib.decompress(raw) if compressed else raw)
 elif name.replace('\\','/').startswith('restore_gui/qml/'):
  path=source/Path(name.replace('\\','/'))
  if path.is_file():replacement=path.read_bytes()
 if replacement is not None:
  raw=zlib.compress(replacement,6) if compressed else replacement;usz=len(replacement);changed.append(name)
 p=len(payload);payload.extend(raw);encoded=name.encode()+b'\0';n=(18+len(encoded)+15)//16*16
 new_toc.extend(struct.pack('!IIIIBc',n,p,len(raw),usz,compressed,kind)+encoded+b'\0'*(n-18-len(encoded)))
to=len(payload);payload.extend(new_toc);length=len(payload)+88
payload.extend(struct.pack('!8sIIII64s',magic,length,to,len(new_toc),version,lib))
output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(b[:start]+payload)
print('Written:',output,'bytes:',output.stat().st_size,'modified entries:',len(changed))
print('SHA256:',hashlib.sha256(output.read_bytes()).hexdigest())
