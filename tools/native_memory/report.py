"""Map-attributed payload accounting; keep host/harness overhead separate."""
import re,json,subprocess,gzip,hashlib
from pathlib import Path
B=Path('/tmp/clo-native-memory');O=Path('results/native_memory_footprint')
out={}
for m in ['clover','rf','rf_pipeline']:
 d=B/m;s=(d/'executable.map').read_text().split('Linker script and memory map',1)[1]
 matches=re.findall(r'^ (\.[\w.]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+) '+re.escape(str(d/'payload.o'))+r'$',s,re.M)
 groups={}
 for name,addr,size in matches:
  for kind in ['.text','.rodata','.data','.bss','.eh_frame']:
   if name==kind or name.startswith(kind+'.'):
    groups.setdefault(kind,[]).append({'section':name,'address':int(addr,16),'bytes':int(size,16)})
 payload={}
 for kind in ['.text','.rodata','.data','.bss','.eh_frame']:
  a=groups.get(kind,[]);logical=sum(x['bytes'] for x in a);span=max((x['address']+x['bytes'] for x in a),default=0)-min((x['address'] for x in a),default=0)
  payload[kind]={'content_bytes':logical,'span_bytes':span,'internal_alignment_bytes':span-logical}
 sections={}
 for line in (d/'replay.size').read_text().splitlines():
  a=line.split()
  if len(a)==3 and a[0].startswith('.') and a[1].isdigit():sections[a[0]]=int(a[1])
 segments=[]
 for line in (d/'replay.segments').read_text().splitlines():
  a=line.split()
  if a and a[0]=='LOAD':segments.append({'offset':int(a[1],16),'vaddr':int(a[2],16),'file_bytes':int(a[4],16),'memory_bytes':int(a[5],16),'alignment':int(a[-1],16)})
 model=2438432 if m.startswith('rf') else 0
 out[m]={'payload':payload,'payload_input_sections':groups,'model_bytes_included_in_rodata':model,'ROM_payload_text_rodata_data_span':sum(payload[k]['span_bytes'] for k in ['.text','.rodata','.data']),'RAM_static_payload_span':sum(payload[k]['span_bytes'] for k in ['.data','.bss']),'executable_sections_with_harness':sections,'ELF_file_bytes':(d/'replay').stat().st_size,'LOAD_segments_with_harness':segments,'load_file_bytes_sum':sum(x['file_bytes'] for x in segments),'load_memory_bytes_sum':sum(x['memory_bytes'] for x in segments),'libraries_not_included':subprocess.check_output(['ldd',str(d/'replay')],text=True),'sha256':hashlib.sha256((d/'replay').read_bytes()).hexdigest()}
(O/'footprint.json').write_text(json.dumps(out,indent=2))
for m,v in out.items():print(m,json.dumps({k:v[k] for k in ['payload','ROM_payload_text_rodata_data_span','RAM_static_payload_span','ELF_file_bytes']},indent=2))
