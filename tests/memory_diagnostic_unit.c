#include "memory_diagnostic.h"
#include "cross_layer_fault.h"
#include "memory_diagnostic_backend.h"
#include "clo_dsf_revised.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static uint16_t read_word(void *p){return *(uint16_t *)p;}
static void write_word(void *p,uint16_t v){*(uint16_t *)p=v;}
int main(int argc,char **argv) {
 assert(argc==2);int mode=atoi(argv[1]);
 if(mode==0)for(unsigned v=0;v<=65535;v++) {
  uint16_t word=(uint16_t)v;memory_diagnostic_t d={0};
  memory_diagnostic_step(&d,0,read_word,write_word,&word);
  assert(word==v && d.valid && !d.failed && d.operations==7 && d.checks==1);
 }
 if(mode==1)for(unsigned bit=0;bit<16;bit++)for(unsigned polarity=0;polarity<2;polarity++) {
  ecu_state_t s={0};s.cross_layer_fault.enabled=true;s.cross_layer_fault.layer=FAULT_LAYER_MEMORY;
  s.cross_layer_fault.model=FAULT_MODEL_STUCK_BIT;s.cross_layer_fault.bit_index=bit;s.cross_layer_fault.stuck_polarity=polarity;s.cross_layer_runtime.active=true;
  uint16_t saved=polarity?(uint16_t)(92U|(1U<<bit)):(uint16_t)(92U&~(1U<<bit));
  s.control.target_register_c=s.control.target_shadow_c=saved;s.control.target_shadow_valid=true;
  memory_diagnostic_step(&s.control.memory_diagnostic,1000,cross_layer_memory_read,cross_layer_memory_write,&s);
  assert(s.control.memory_diagnostic.failed && s.control.target_register_c==saved && s.control.target_shadow_c==saved);
  s.cross_layer_runtime.active=false;
  memory_diagnostic_step(&s.control.memory_diagnostic,2000,cross_layer_memory_read,cross_layer_memory_write,&s);
  assert(!s.control.memory_diagnostic.failed && s.control.target_register_c==saved);
 }
 if(mode==2){uint16_t word=92;memory_diagnostic_t d={0};memory_diagnostic_step(&d,0,read_word,write_word,&word);
  memory_diagnostic_step(&d,999,read_word,write_word,&word);assert(d.checks==1);
  word=103;memory_diagnostic_step(&d,1000,read_word,write_word,&word);assert(d.checks==2&&!d.failed&&word==103);
  memory_diagnostic_step(&d,500,read_word,write_word,&word);assert(d.checks==2);
 }
 if(mode==3){ecu_state_t s={0};s.cross_layer_fault.enabled=true;s.cross_layer_fault.layer=FAULT_LAYER_MEMORY;s.cross_layer_fault.model=FAULT_MODEL_BIT_FLIP;s.cross_layer_runtime.active=true;s.control.target_register_c=93;s.control.target_shadow_c=92;
  memory_diagnostic_step(&s.control.memory_diagnostic,0,cross_layer_memory_read,cross_layer_memory_write,&s);
  assert(!s.control.memory_diagnostic.failed&&s.control.target_register_c==93&&s.control.target_shadow_c==92);
 }
 if(mode==4){clo_evidence_t e={0};runtime_observation_t o={0};o.memory_check_valid=true;o.memory_check_failed=true;o.memory_check_ms=1000;
  o.time_ms=1000;clo_revised_extract(&e,&o);assert(e.available[2]&&e.strength[2]==1);
  o.time_ms=1999;clo_revised_extract(&e,&o);assert(e.strength[2]==1);
  o.time_ms=2000;clo_revised_extract(&e,&o);assert(!e.available[2]&&e.strength[2]==0);
  o.time_ms=999;clo_revised_extract(&e,&o);assert(!e.available[2]&&e.strength[2]==0);
 }
 return 0;
}
