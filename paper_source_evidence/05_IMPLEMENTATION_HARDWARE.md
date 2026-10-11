# 05 — Software architecture, integrity RTL and native implementation

Evidence labels used throughout: **VERIFIED FROM SOURCE** (literal implemented behavior); **VERIFIED FROM EXPERIMENT ARTIFACT** (recorded outcomes/protocol); **DERIVED MATHEMATICALLY FROM VERIFIED SOURCE** (algebra or deterministic accounting, not a new experiment); **NOT RECOVERABLE / REQUIRES CONFIRMATION** (missing/limited evidence). Source paths are repository-relative unless explicitly absolute. Line numbers refer to the hashes in 07, not an assumed future HEAD.

## Functional data paths and trust boundaries

**VERIFIED FROM SOURCE.** Simulator physical state feeds A/B/C measurement producers; measurement outputs feed control and diagnosis. Register/shadow/probe results, scheduler-owned ledger, acquisition/delivery provenance and command/actual responses enter independent provider code. Sensor disagreement and protected-record mismatch enrich one sensor evidence channel; separate DS detection/origin heads plus precedence and G2 produce diagnostic outputs. A0, candidate branches, logging, ground-truth injector and healthy-reference scorer coexist in the campaign adapter but are not deployed method requirements. Their object size/runtime must not be presented as CLOVER cost.

Protected record ownership is a **logical modeled boundary**: producer publish and authorized transform may update the witness; downstream consumer supplies a candidate envelope/value/time. The C program itself does not demonstrate MPU permissions, privilege separation, independent clock/power, nonvolatile security, tamper resistance or freedom from common-cause software failures. Hardware producer port access control must be implemented externally.

## Digital integrity details

**VERIFIED FROM SOURCE.** Record fields are five uint32 words: channel ID, IEEE-style32-bit float value bit pattern (copied with memcpy, not numerically compared), sequence, timestamp_ms, CRC tag. Hardware protected storage is5×32+valid=**161 bits per channel**. This is not the C struct byte size, nor the three-channel system total or envelope/consumer storage.

CRC-32 traverses four canonical little-endian payload words channel,bits,sequence,ms; initialize all ones, reflected polynomial0xedb88320, complement final state. Excludes struct padding/pointers. Publish sequence is1 when previously invalid, otherwise prior+1 modulo32-bit. Legal transform retains identity/sequence/time, recomputes value bits and tag. CRC is an accidental-integrity check, not a MAC; a consistent replacement of data and witness can pass.

Mismatch causes are orthogonal bits:1=value/channel/envelope/tag comparison to protected record;2=sequence/time relation;4=invalid CRC on witness or envelope. Software invalid witness returns mask0 but availability separately distinguishes UNAVAILABLE. RTL reports result0 UNAVAILABLE,1 PASS,2 FAIL and the same three cause bits. Producer writes on rising edge; synchronous reset invalidates and clears; publish has priority over transform. Consumer ports never write protected storage. Transform arithmetic (e.g. authorized floating offset) is computed by the trusted producer; RTL receives transformed bits—it does not synthesize floating-point addition.

## RTL feasibility evidence, not full ECU hardware

**VERIFIED FROM EXPERIMENT ARTIFACT.** One62-line module;3,348 software-oracle comparisons with all8 outputs checked per cycle. Tests cover valid record, value/channel/sequence/time/tag corruption, reset/unavailable and value+tag modification with intact witness. Yosys0.58+76 maps to Nangate45 `nangate45nm_copy.lib` (library hash in record.json), Verilator4.038 simulates, OpenSTA2.7.0 analyzes. Mapped total4,556 cells =161 DFF +4,395 combinational; reported library area7,425.656, sequential area728.042. State explicitly as synthesis/library area, not measured die area.

STA setup:100-ns ideal clock;1-ns input delay on reset/publish/transform/producer/consumer/delivered inputs;1-ns output delay;output load.01 in library units. Worst reported path consumer_channel[3]→result[0] has4.4930-ns arrival including1-ns input delay, hence3.4930-ns incremental internal delay by subtraction. Slack94.5070 ns. This is pre-layout library-cell timing under those constraints, without extracted routing/parasitics. It is not a certified max frequency; do not invert this combinational IO path and claim a registered MCU clock limit. Consumer verification is combinational, zero added clock cycles once signals settle; publication takes one edge.

## Native state, storage and host timing

**VERIFIED FROM EXPERIMENT ARTIFACT.** Original native-resource study verifies2,161,800 frames exactly before a pinned i7-14700 timing pass, GCC11.4 -O2 -fno-fast-math -ffp-contract=off. Median/P95/P99/max microseconds: CLOVER decision+G2 4.747/5.227/7.113/1468.846; replayable CLOVER core4.846/5.339/7.826/1468.943; RF features+inference4.743/5.647/10.974/5020.841. CLOCK_MONOTONIC_RAW is elapsed host time, not thread CPU time; includes clock and scheduling effects. Fixed order, no cold-cache/frequency/isolation guarantee. These are not embedded WCET or speed-superiority evidence.

The subsequent separately linked memory study (different build/layout) includes DS/temporal/localization/G2 and RF's full174 features/histories/200 trees/probability/localization. It also links RF B with the same reconstructible frozen provider prefix. Payload maps exclude replay main/buffers/CRT/loader; packet ABI adaptation remains included. `.data`=0 for all payloads. Exact table below is **bytes**, linked spans including within-region alignment:

| Component | CLOVER B | RF A decisions | RF B replayable pipeline |
|---|---:|---:|---:|
| .text |12605|1084|9305|
| .rodata |356|2438560|2438816|
| .bss |4432|4804|9360|
| Method unwind metadata |492|84|324|
| Code/constants+method unwind ROM |13453|2439728|2448445|
| Observed touched method stack |3544|2160|4184|
| Static RAM+observed stack |7976|6964|13544|

RF B/CLOVER B ratios:181.999926× ROM including unwind;2.111913× static RAM;1.698094× static+observed-stack. Both B boundaries omit producer transaction engines equally; A RF must not be compared directly against B CLOVER as equal-pipeline RAM. Pure CLOVER A is not separately allocated in the frozen fused layout. No full producer-side ECU size is measured.

RF model2,438,432 B is already included in .rodata, not an addition;4,804-B histories already lie in BSS. CLOVER4,304-B state plus12-B G2 are subsets of its BSS, not additions. Stack contains local feature/DS temporaries; do not count them twice. Node export uses72-byte nodes,33,856 nodes and200 roots;135,424 B is intra-node alignment, and internal-node class probabilities remain stored. This is the actual verified export, not an irreducible RF representation. RF B also retains unused fields of the original provider context.

Full ELF files30,024 /2,453,536 /2,462,688 B include headers, symbols and harness. They are not deployed ROM/RAM. Maps/readelf/size/nm account for merged constants, internal padding, startup, dynamic linkage and LOAD-page gaps separately. Shared libc/libm code is not included in payload ROM; measured stacks include reached callees. Dedicated-stack A5 watermark measures touched bytes, not all untouched reservations or a proven worst-case stack bound. No MCU deployment, power/energy claim, full ECU synthesis or physical security validation follows.

## Original implementation and constraint excerpts


### Exact source: digital_sensor_integrity.h

**VERIFIED FROM SOURCE.** `include/digital_sensor_integrity.h` — `file`, lines 1–11

```text
   1: #ifndef DIGITAL_SENSOR_INTEGRITY_H
   2: #define DIGITAL_SENSOR_INTEGRITY_H
   3: #include <stdint.h>
   4: #include <stdbool.h>
   5: typedef struct { uint32_t channel,bits,sequence,ms,tag; } di_record_t;
   6: typedef struct { di_record_t protected_record; bool valid; } di_witness_t;
   7: uint32_t di_tag(const di_record_t *r);
   8: void di_publish(di_witness_t *w,di_record_t *r,unsigned channel,float value,unsigned ms);
   9: void di_transform(di_witness_t *w,di_record_t *r,float offset);
  10: unsigned di_verify(const di_witness_t *w,const di_record_t *r,float value,unsigned ms);
  11: #endif
```


### Exact source: digital_sensor_integrity.c

**VERIFIED FROM SOURCE.** `src/v7_3/digital_sensor_integrity.c` — `file`, lines 1–34

```text
   1: #include "digital_sensor_integrity.h"
   2: #include <string.h>
   3: /* CRC-32 covers canonical little-endian words; no struct padding or pointers.
   4:  * The protected record models an isolated driver mailbox. CRC is not a MAC.
   5:  * Independent protected storage, NOT secrecy of the polynomial, is the trust
   6:  * assumption. Producer and legitimate transform API alone may update it. */
   7: uint32_t di_tag(const di_record_t *r){
   8:  uint32_t crc=~0U,v[4]={r->channel,r->bits,r->sequence,r->ms};
   9:  for(unsigned i=0;i<4;i++)for(unsigned b=0;b<4;b++){
  10:   crc^=(v[i]>>(8*b))&255U;
  11:   for(unsigned k=0;k<8;k++)crc=(crc>>1)^((0U-(crc&1U))&0xedb88320U);
  12:  }
  13:  return ~crc;
  14: }
  15: void di_publish(di_witness_t *w,di_record_t *r,unsigned channel,float value,unsigned ms){
  16:  di_record_t p={.channel=channel,.sequence=w->valid?w->protected_record.sequence+1:1,.ms=ms};
  17:  memcpy(&p.bits,&value,sizeof p.bits);p.tag=di_tag(&p);w->protected_record=p;w->valid=true;*r=p;
  18: }
  19: void di_transform(di_witness_t *w,di_record_t *r,float offset){
  20:  if(!w->valid)return;
  21:  float v;memcpy(&v,&w->protected_record.bits,sizeof v);v+=offset;
  22:  memcpy(&w->protected_record.bits,&v,sizeof v);w->protected_record.tag=di_tag(&w->protected_record);
  23:  /* Update only envelope integrity, never overwrite the delivered value. */
  24:  *r=w->protected_record;
  25: }
  26: unsigned di_verify(const di_witness_t *w,const di_record_t *r,float value,unsigned ms){
  27:  if(!w->valid)return 0;
  28:  uint32_t bits;memcpy(&bits,&value,sizeof bits);
  29:  const di_record_t *p=&w->protected_record;unsigned status=0;
  30:  if(p->tag!=di_tag(p)||r->tag!=di_tag(r))status|=4;
  31:  if(bits!=p->bits||r->bits!=p->bits||r->tag!=p->tag||r->channel!=p->channel)status|=1;
  32:  if(ms!=p->ms||r->sequence!=p->sequence||r->ms!=p->ms)status|=2;
  33:  return status;
  34: }
```


### Exact source: digital_integrity_monitor.v

**VERIFIED FROM SOURCE.** `rtl/integrity/digital_integrity_monitor.v` — `file`, lines 1–62

```text
   1: // Logical producer-owned boundary; one instance per sensor channel.
   2: // CRC-32 is not authentication. Producer ports must be access-controlled externally.
   3: module digital_integrity_monitor (
   4:     input wire clk, reset,
   5:     input wire publish, transform,
   6:     input wire [31:0] producer_channel, producer_bits, producer_ms,
   7:     input wire [31:0] consumer_channel, consumer_bits, consumer_sequence,
   8:     input wire [31:0] consumer_ms, consumer_tag, delivered_bits, delivered_ms,
   9:     output reg witness_valid,
  10:     output reg [31:0] sealed_channel, sealed_bits, sealed_sequence,
  11:     output reg [31:0] sealed_ms, sealed_tag,
  12:     output wire [2:0] causes,
  13:     output wire [1:0] result // 0 UNAVAILABLE, 1 PASS, 2 FAIL
  14: );
  15:     function [31:0] record_crc;
  16:         input [31:0] channel, bits, sequence_number, timestamp;
  17:         reg [127:0] payload;
  18:         reg [31:0] crc;
  19:         integer i;
  20:         begin
  21:             // Low bit first equals software's little-endian byte traversal.
  22:             payload = {timestamp, sequence_number, bits, channel};
  23:             crc = 32'hffffffff;
  24:             for (i = 0; i < 128; i = i + 1)
  25:                 crc = (crc >> 1) ^ ((crc[0] ^ payload[i]) ? 32'hedb88320 : 32'b0);
  26:             record_crc = ~crc;
  27:         end
  28:     endfunction
  29: 
  30:     wire [31:0] next_sequence = witness_valid ? sealed_sequence + 32'd1 : 32'd1;
  31:     wire [31:0] new_tag = record_crc(publish ? producer_channel : sealed_channel,
  32:         producer_bits, publish ? next_sequence : sealed_sequence,
  33:         publish ? producer_ms : sealed_ms);
  34:     always @(posedge clk) begin
  35:         if (reset) begin
  36:             witness_valid <= 1'b0;
  37:             sealed_channel <= 0; sealed_bits <= 0; sealed_sequence <= 0;
  38:             sealed_ms <= 0; sealed_tag <= 0;
  39:         end else if (publish) begin
  40:             witness_valid <= 1'b1;
  41:             sealed_channel <= producer_channel;
  42:             sealed_bits <= producer_bits;
  43:             sealed_sequence <= next_sequence;
  44:             sealed_ms <= producer_ms;
  45:             sealed_tag <= new_tag;
  46:         end else if (transform && witness_valid) begin
  47:             // Trusted producer supplies result of its legitimate transformation.
  48:             // Like di_transform: retain channel/sequence/time, update bits and tag.
  49:             sealed_bits <= producer_bits;
  50:             sealed_tag <= new_tag;
  51:         end
  52:     end
  53:     assign causes[0] = witness_valid &&
  54:         (delivered_bits != sealed_bits || consumer_bits != sealed_bits ||
  55:          consumer_tag != sealed_tag || consumer_channel != sealed_channel);
  56:     assign causes[1] = witness_valid &&
  57:         (delivered_ms != sealed_ms || consumer_sequence != sealed_sequence || consumer_ms != sealed_ms);
  58:     assign causes[2] = witness_valid &&
  59:         (sealed_tag != record_crc(sealed_channel, sealed_bits, sealed_sequence, sealed_ms) ||
  60:          consumer_tag != record_crc(consumer_channel, consumer_bits, consumer_sequence, consumer_ms));
  61:     assign result = !witness_valid ? 2'd0 : (|causes ? 2'd2 : 2'd1);
  62: endmodule
```


### Exact source: timing.tcl

**VERIFIED FROM SOURCE.** `results/rtl_integrity_poc/timing.tcl` — `file`, lines 1–10

```text
   1: read_liberty /usr/local/share/qflow/tech/nangate45nm/nangate45nm_copy.lib
   2: read_verilog /home/leonskal/code/virtual-ecu-phd/results/rtl_integrity_poc/mapped.v
   3: link_design digital_integrity_monitor
   4: create_clock -name clk -period 100 [get_ports clk]
   5: set_input_delay 1 -clock clk [get_ports {reset publish transform producer_* consumer_* delivered_*}]
   6: set_output_delay 1 -clock clk [all_outputs]
   7: set_load 0.01 [all_outputs]
   8: report_checks -path_delay max -group_count 5 -digits 4
   9: report_worst_slack -max
  10: exit
```


### Exact source: clo_dsf_revised.h

**VERIFIED FROM SOURCE.** `include/clo_dsf_revised.h` — `file`, lines 1–42

```text
   1: #ifndef CLO_DSF_REVISED_H
   2: #define CLO_DSF_REVISED_H
   3: #include "clo_dsf_final.h"
   4: /* Runtime provenance for the current anomaly episode, separate from DS masses.
   5:  * No fault labels or propagation scores participate. */
   6: typedef struct {
   7:     clo_final_t fusion;
   8:     unsigned int direct_onset_ms, direct_origins, actuator_unresolved;
   9:     bool sensor_established_first, ambiguous_onset;
  10:     bool qualified_anomaly_episode;
  11:     /* Absolute-slew provider needs five consecutive in-envelope acquisitions. */
  12:     unsigned int slew_qualification_count, slew_qualification_ms;
  13:     double previous_local_excess;
  14:     unsigned int previous_local_ms;
  15:     int previous_local_direction;
  16:     bool previous_local_valid;
  17:     /* Finite sensor-response forecast; no simulator or injector state. */
  18:     float response_history[5];
  19:     unsigned int response_count, response_last_ms, response_anchor_ms;
  20:     float response_load, response_speed, response_ambient, response_target, response_fan;
  21:     double response_anchor, response_slope, response_residual, response_strength;
  22:     unsigned int response_streak;
  23:     int response_sign;
  24:     bool response_active;
  25:     /* 32 s signed disagreement window, one correlated sensor feature. */
  26:     double reference_window[320], reference_sum, reference_mean, reference_strength;
  27:     unsigned int reference_count, reference_index, reference_last_ms;
  28:     /* Fast differential contract, independent of which sensor is faulty. */
  29:     double fast_previous, fast_anchor, fast_strength;
  30:     double fast_integral, fast_bound_integral;
  31:     unsigned int fast_integral_count;
  32:     int fast_integral_sign;
  33:     unsigned int fast_last_ms, fast_anchor_ms, fast_count, fast_index, fast_edges;
  34:     unsigned char fast_edge_history[10];
  35:     int fast_sign;
  36:     bool fast_valid, fast_active;
  37: } clo_revised_t;
  38: void clo_revised_init(clo_revised_t *s);
  39: void clo_revised_extract(clo_evidence_t *e, const runtime_observation_t *o);
  40: void clo_revised_step(clo_revised_t *s, const clo_final_config_t *c,
  41:                       const runtime_observation_t *o);
  42: #endif
```


### Exact source: clo_dsf_final.h

**VERIFIED FROM SOURCE.** `include/clo_dsf_final.h` — `file`, lines 1–22

```text
   1: #ifndef CLO_DSF_FINAL_H
   2: #define CLO_DSF_FINAL_H
   3: #include "clo_dsf_candidate2.h" /* Frozen feature/DS types and logical origin mapping. */
   4: /* No origin discount or propagation modulation parameter exists here. */
   5: typedef struct {
   6:     double r_detection, lambda_temporal, suspect_threshold, confirmed_threshold;
   7:     double localization_threshold, localization_margin_threshold, ignorance_limit;
   8:     unsigned int confirmation_persistence;
   9: } clo_final_config_t;
  10: typedef struct {
  11:     ds_mass_t detection_mass, origin_mass;
  12:     clo_evidence_t evidence;
  13:     c2_output_t output;
  14:     unsigned int confirmation_count, previous_time_ms;
  15:     bool has_previous_time;
  16: } clo_final_t;
  17: void clo_final_init(clo_final_t *s);
  18: bool clo_final_config_valid(const clo_final_config_t *c);
  19: void clo_final_step(clo_final_t *s,const clo_final_config_t *c,const runtime_observation_t *o);
  20: /* Diagnostic update only. It cannot read/write masses, output or decisions. */
  21: void clo_final_diagnostic(clo_evidence_t *e,unsigned int now,unsigned int window_ms);
  22: #endif
```


### Exact source: origin_rf.py

**VERIFIED FROM SOURCE.** `python/virtual_ecu/origin_rf.py` — `file`, lines 1–60

```text
   1: """Causal common-input RF features. No predictions or case metadata accepted."""
   2: import numpy as np
   3: # Same trusted observation fields consumed by the frozen providers/core. Diagnostic
   4: # alarm/id/safety outputs are excluded: they are unused by the frozen core.
   5: OBS = ['time_ms','coolant_measured_c','sample_timestamp_ms','sample_age_ms',
   6:  'control_target_c','pump_command','fan_command','pump_actual','fan_actual',
   7:  'control_execution_ms','engine_load','ambient_c','vehicle_speed_kph',
   8:  'sample_freshness_ok','sample_expected_period_ms','target_register_c',
   9:  'target_shadow_c','target_shadow_valid','memory_check_ms','memory_check_valid',
  10:  'memory_check_failed','source_c','source_previous_c','source_ms','source_previous_ms',
  11:  'source_valid','source_previous_valid','reference_c','reference_ms','reference_enabled',
  12:  'reference_valid','reference_failed']
  13: TIMING=['task_id','time_ms','period_ms','relative_deadline_ms','release_sequence',
  14:  'execution_sequence','current_release_ms','job_release_ms','actual_start_ms',
  15:  'actual_completion_ms','last_successful_execution_ms','execution_age_ms',
  16:  'job_outstanding','missed_expected_execution','deadline_exceeded','cancelled_release_count']
  17: C=['value_c','previous_c','sample_ms','previous_ms','valid','previous_valid','failed']
  18: EXTRA=['triplex_strength','triplex_ambiguous','triplex_qualified','triplex_aligned_c',
  19:  'qualified_sensor_strength','local_sensor_strength',
  20:  'integrity_available','integrity_bad','integrity_status_A','integrity_status_B',
  21:  'integrity_status_C','integrity_held_fail']
  22: FIELDS=OBS+['timing.'+x for x in TIMING]+['C.'+x for x in C]+EXTRA
  23: CLASSES=['NORMAL','MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR']
  24: TIME_FIELDS={'sample_timestamp_ms','control_execution_ms','memory_check_ms','source_ms',
  25:  'source_previous_ms','reference_ms','timing.time_ms','timing.current_release_ms',
  26:  'timing.job_release_ms','timing.actual_start_ms','timing.actual_completion_ms',
  27:  'timing.last_successful_execution_ms','C.sample_ms','C.previous_ms'}
  28: 
  29: def schema():
  30:  return dict(raw_fields=FIELDS,excluded=['diagnostic_id','safety_state','detector_alarm',
  31:  'CLOVER alarm/origin/beliefs/direct_origins','injected origin/start/duration','offline plant propagation'],
  32:  feature_encoding='All packet fields except absolute time; timestamp fields become signed age (negative sentinel retained); explicit finite masks. Include six strength/availability/origin-support vectors. Add 10-frame and 50-frame causal means/maxima of six masked provider strengths. No absolute case clock, future samples or outcome fields.',
  33:  origin_support='Provider support sets, not CLOVER estimated origin. Captured before DS fusion.',
  34:  classes=CLASSES)
  35: 
  36: def features(packet,e):
  37:  a=np.asarray(packet,float);assert a.shape[1]==len(FIELDS)
  38:  assert np.array_equal(a[:,0],e.time_ms)
  39:  v=a[:,1:].copy();names=FIELDS[1:]
  40:  for j,name in enumerate(names):
  41:   if name in TIME_FIELDS:v[:,j]=np.where(v[:,j]>=0,a[:,0]-v[:,j],v[:,j])
  42:  valid=np.isfinite(v);v=np.where(valid,v,0.)
  43:  pieces=[v,valid.astype(float),e.values,e.available.astype(float),e.origin_subset.astype(float)]
  44:  for width in [10,50]:
  45:   padded=np.pad(e.values,((width-1,0),(0,0)))
  46:   avail=np.pad(e.available.astype(float),((width-1,0),(0,0)))
  47:   windows=np.lib.stride_tricks.sliding_window_view(padded,width,axis=0)
  48:   counts=np.lib.stride_tricks.sliding_window_view(avail,width,axis=0).sum(axis=-1)
  49:   mean=np.divide(windows.sum(axis=-1),counts,out=np.zeros_like(e.values),where=counts>0)
  50:   pieces.extend([mean,windows.max(axis=-1)])
  51:  return np.column_stack(pieces)
  52: 
  53: def decisions(prob,alarm_threshold,confidence,margin):
  54:  p=np.asarray(prob,float);assert p.ndim==2 and p.shape[1]==6
  55:  fault=1-p[:,0];alarm=fault>alarm_threshold
  56:  conditional=np.divide(p[:,1:],fault[:,None],out=np.zeros_like(p[:,1:]),where=fault[:,None]>0)
  57:  ordered=np.sort(conditional,axis=1);top=np.argmax(conditional,axis=1)
  58:  qualified=(ordered[:,-1]>=confidence)&((ordered[:,-1]-ordered[:,-2])>=margin)
  59:  origin=np.where(alarm&qualified,1<<top,0)
  60:  return alarm,origin
```

Evidence/implementation: `results/rtl_integrity_poc/record.json` — `file`, lines 1–21.

Evidence/implementation: `results/rtl_integrity_poc/statistics.json` — `file`, lines 1–93.

Evidence/implementation: `results/rtl_integrity_poc/timing.log` — `file`, lines 1–386.

Evidence/implementation: `results/rtl_integrity_poc/simulation.log` — `file`, lines 1–1.

Evidence/implementation: `results/native_resource_benchmark/findings.md` — `file`, lines 1–36.

Evidence/implementation: `results/native_memory_footprint/findings.md` — `file`, lines 1–59.

Evidence/implementation: `tools/native_memory/build.py` — `file`, lines 1–57.

Evidence/implementation: `tools/native_memory/build_pipeline.py` — `file`, lines 1–47.

Evidence/implementation: `tools/native_memory/stack_call.S` — `file`, lines 1–19.

Evidence/implementation: `tools/native_memory/stack_driver.c` — `file`, lines 1–14.
