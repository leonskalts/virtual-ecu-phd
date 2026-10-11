#!/usr/bin/env python3
"""Isolated RTL feasibility build; never invokes a fault campaign."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl_integrity_poc'
LIB=Path('/usr/local/share/qflow/tech/nangate45nm/nangate45nm_copy.lib')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 protected=[ROOT/'src/v7_3/digital_sensor_integrity.c',ROOT/'include/digital_sensor_integrity.h',ROOT/'presets/gui_session_state.json']
 protected += [p for d in ['integrity_final_unseen','benign_alarm_development','digital_integrity_development'] for p in (ROOT/'results'/d).iterdir() if p.is_file()]
 before={str(p):sha(p) for p in protected}
 def run(cmd,name):
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
  (OUT/(name+'.log')).write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(name+': '+(p.stdout+p.stderr)[-3000:])
  return p.stdout
 with tempfile.TemporaryDirectory(prefix='rtl-integrity-') as tmp:
  w=Path(tmp);obj=w/'obj';bridge=w/'bridge.cpp'
  # Verilator requires C++ bindings; the actual testbench and software oracle are C.
  inputs=['reset','publish','transform','producer_channel','producer_bits','producer_ms','consumer_channel','consumer_bits','consumer_sequence','consumer_ms','consumer_tag','delivered_bits','delivered_ms']
  outputs=['witness_valid','sealed_channel','sealed_bits','sealed_sequence','sealed_ms','sealed_tag','causes','result']
  bridge.write_text('#include "Vdigital_integrity_monitor.h"\n#include <stdint.h>\nextern "C" void rtl_tick(const uint32_t *i,uint32_t *o){\nstatic Vdigital_integrity_monitor d;\n'+''.join(f'd.{n}=i[{k}];\n' for k,n in enumerate(inputs))+'d.clk=0;d.eval();d.clk=1;d.eval();\n'+''.join(f'o[{k}]=d.{n};\n' for k,n in enumerate(outputs))+'}\n')
  for source,name in [('src/v7_3/digital_sensor_integrity.c','oracle'),('sim/integrity/digital_integrity_tb.c','tb')]:
   run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Iinclude','-c',source,'-o',str(w/(name+'.o'))],name+'_compile')
  run(['verilator','--cc','--exe','--top-module','digital_integrity_monitor','--Mdir',str(obj),'rtl/integrity/digital_integrity_monitor.v',str(bridge),str(w/'oracle.o'),str(w/'tb.o')],'verilator')
  run(['make','-C',str(obj),'-f','Vdigital_integrity_monitor.mk','-j2'],'simulation_build')
  print(run([str(obj/'Vdigital_integrity_monitor')],'simulation'),flush=True)
  ys=w/'synth.ys';ys.write_text(f'read_verilog rtl/integrity/digital_integrity_monitor.v\nhierarchy -check -top digital_integrity_monitor\nsynth -top digital_integrity_monitor\ndfflibmap -liberty {LIB}\nabc -liberty {LIB}\nclean\ncheck\ntee -o {OUT}/statistics.json stat -json -liberty {LIB}\nwrite_verilog -noattr -noexpr {OUT}/mapped.v\n')
  run(['yosys','-s',str(ys)],'synthesis');print('SYNTHESIS COMPLETE',flush=True)
  sta=w/'timing.tcl';sta.write_text(f'read_liberty {LIB}\nread_verilog {OUT}/mapped.v\nlink_design digital_integrity_monitor\ncreate_clock -name clk -period 100 [get_ports clk]\nset_input_delay 1 -clock clk [get_ports {{reset publish transform producer_* consumer_* delivered_*}}]\nset_output_delay 1 -clock clk [all_outputs]\nset_load 0.01 [all_outputs]\nreport_checks -path_delay max -group_count 5 -digits 4\nreport_worst_slack -max\nexit\n')
  run(['sta','-exit',str(sta)],'timing')
  (OUT/'synthesis.ys').write_text(ys.read_text());(OUT/'timing.tcl').write_text(sta.read_text())
 for p,v in before.items():assert sha(Path(p))==v,p
 files=['rtl/integrity/digital_integrity_monitor.v','sim/integrity/digital_integrity_tb.c','scripts/run_rtl_integrity_poc.py']
 report=dict(source_hashes={p:sha(ROOT/p) for p in files},library=str(LIB),library_sha256=sha(LIB),protected_files_unchanged=len(before),gui_sha256=before[str(ROOT/'presets/gui_session_state.json')],rtl_lines=len((ROOT/files[0]).read_text().splitlines()),rtl_modules=1,protected_storage_bits=161,verification_latency='combinational; zero additional clock cycles after inputs/witness settle',producer_latency='one rising edge; synchronous reset; publish takes precedence over transform',tools={n:run(cmd,n+'_version').strip() for n,cmd in [('yosys',['yosys','-V']),('verilator',['verilator','--version']),('sta',['sta','-version'])]})
 (OUT/'record.json').write_text(json.dumps(report,indent=2)+'\n');print('PROTECTED FILES UNCHANGED',len(before),flush=True)
if __name__=='__main__':main()
