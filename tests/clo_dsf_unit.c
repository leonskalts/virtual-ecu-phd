#include "clo_dsf.h"
#include "ecu_types.h" /* Test harness only: prove hidden labels cannot affect detector. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define NEAR(a,b) assert(fabs((a)-(b))<1e-8)
static runtime_observation_t normal(unsigned int t)
{
    return (runtime_observation_t){.time_ms=t,.coolant_measured_c=92,.control_target_c=92,
        .sample_timestamp_ms=t,.sample_age_ms=0,.sample_freshness_ok=true,.sample_expected_period_ms=100,
        .timing={.period_ms=100,.relative_deadline_ms=100,.time_ms=t,.job_release_ms=(int)t,.actual_completion_ms=(int)t}};
}
static void step(clo_dsf_t *s, clo_config_t *c, unsigned int t, int channel)
{
    runtime_observation_t o=normal(t);
    if(channel==0) o.timing.deadline_exceeded=true;
    if(channel==1) {o.sample_age_ms=500;o.sample_freshness_ok=false;}
    if(channel==2) o.control_target_c=104;
    if(channel==3) o.coolant_measured_c=160;
    if(channel==4) o.pump_command=1;
    if(channel==5) o.coolant_measured_c=115;
    clo_dsf_step(s,c,CLO_FULL,&o);
    assert(ds_valid(&s->fused));
}
int main(int argc,char **argv)
{
    assert(argc==2);int test=atoi(argv[1]);
    ds_mass_t a,b,r;double k,p[DS_ATOMS];
    clo_config_t c;clo_config_default(&c);clo_dsf_t s;clo_dsf_init(&s);
    if(test==0) {ds_empty(&a);assert(!ds_valid(&a));assert(!ds_normalize(&a));assert(ds_assign(&a,2,.3));assert(ds_assign(&a,6,.2));assert(ds_normalize(&a));NEAR(a.mass[2],.6);assert(ds_valid(&a));}
    if(test==1) {ds_vacuous(&a);assert(ds_valid(&a));NEAR(ds_belief(&a,2),0);NEAR(ds_plausibility(&a,2),1);ds_pignistic(&a,p);NEAR(p[0],1.0/6);}
    if(test==2) {ds_vacuous(&a);a.mass[2]=.6;a.mass[63]=.4;ds_vacuous(&b);assert(ds_combine(&a,&b,DS_DEMPSTER,&r,&k));NEAR(r.mass[2],.6);NEAR(k,0);}
    if(test==3 || test==4) {ds_vacuous(&a);a.mass[2]=.6;a.mass[63]=.4;ds_vacuous(&b);b.mass[4]=.5;b.mass[63]=.5;
        assert(ds_combine(&a,&b,test==3?DS_DEMPSTER:DS_YAGER,&r,&k));NEAR(k,.3);
        NEAR(r.mass[2],test==3?3.0/7:.3);NEAR(r.mass[4],test==3?2.0/7:.2);NEAR(r.mass[63],test==3?2.0/7:.5);assert(ds_valid(&r));}
    if(test==5) {ds_empty(&a);a.mass[2]=1;ds_empty(&b);b.mass[4]=1;assert(!ds_combine(&a,&b,DS_DEMPSTER,&r,&k));NEAR(k,1);NEAR(r.mass[63],1);assert(ds_combine(&a,&b,DS_YAGER,&r,&k));NEAR(r.mass[63],1);}
    if(test==6) {ds_vacuous(&a);a.mass[6]=.8;a.mass[63]=.2;assert(ds_discount(&a,.5,&a));NEAR(a.mass[6],.4);NEAR(a.mass[63],.6);assert(!ds_discount(&a,NAN,&r));}
    if(test==7) {ds_empty(&a);a.mass[2]=.3;a.mass[6]=.4;a.mass[63]=.3;NEAR(ds_belief(&a,6),.7);NEAR(ds_plausibility(&a,4),.7);ds_pignistic(&a,p);NEAR(p[1],.55);NEAR(p[2],.25);}
    if(test==8) {ds_vacuous(&a);assert(!ds_assign(&a,0,.1));assert(!ds_assign(&a,64,.1));assert(!ds_assign(&a,1,NAN));a.mass[2]=INFINITY;assert(!ds_valid(&a));assert(!ds_normalize(&a));}
    if(test>=9 && test<=14) {int ch=test-9;step(&s,&c,0,-1);step(&s,&c,100,ch);assert(s.evidence.strength[ch]>.99);clo_evidence_mass(ch,1,true,&a);NEAR(a.mass[clo_supported_subsets[ch]],1);if(ch==5)assert(clo_supported_subsets[ch]==CLO_ABNORMAL);}
    if(test==15) {NEAR(clo_reliability(CLO_DIRECT,&c),.9);NEAR(clo_reliability(CLO_INDIRECT,&c),.6);NEAR(clo_reliability(CLO_UNAVAILABLE,&c),0);NEAR(clo_reliability(CLO_NOT_APPLICABLE,&c),0);clo_evidence_mass(0,1,false,&a);NEAR(a.mass[63],1);runtime_observation_t o=normal(0);o.control_target_c=NAN;clo_dsf_step(&s,&c,CLO_FULL,&o);assert(!s.evidence.available[2]);NEAR(s.evidence.reliability[2],0);}
    if(test>=16 && test<=19) {
        runtime_observation_t o=normal(0);o.timing.deadline_exceeded=true;
        if(test==18) {o.timing.deadline_exceeded=false;o.pump_command=1;}
        clo_dsf_step(&s,&c,CLO_FULL,&o);
        o=normal(100);o.timing.deadline_exceeded=true;if(test!=17)o.pump_command=1;
        if(test==19) s.evidence.onset_ms[0]=200;
        clo_dsf_step(&s,&c,CLO_FULL,&o);
        assert(s.output.propagation_support==(test==16));
        if(test==16) {assert(s.evidence.propagation_transitions&(1U<<4));NEAR(s.evidence.reliability[0],.99);}
    }
    if(test==20) {step(&s,&c,0,0);assert(s.output.state==CLO_STATE_SUSPECT);step(&s,&c,100,-1);assert(!s.output.alarm);for(int t=200;t<10000;t+=100)step(&s,&c,t,-1);assert(s.output.state==CLO_STATE_NORMAL);assert(s.output.fault_belief<1e-8);}
    if(test==21) {for(int t=0;t<1000;t+=100)step(&s,&c,t,2);assert(s.output.alarm);assert(s.output.estimated_origin==CLO_MEMORY);assert(s.output.alarm_timestamp_ms==100);}
    if(test==22) {for(int t=0;t<5000;t+=100)step(&s,&c,t,t%1000<400?4:-1);assert(s.output.alarm_timestamp_ms>=0);for(int t=5000;t<15000;t+=100)step(&s,&c,t,-1);assert(!s.output.alarm);assert(s.output.estimated_origin==0);}
    if(test==23) {for(int t=0;t<1000000;t+=100)step(&s,&c,t,-1);assert(s.output.alarm_timestamp_ms==-1);assert(s.output.state==CLO_STATE_NORMAL);}
    if(test==24) {for(int t=0;t<1000;t+=100)step(&s,&c,t,3);assert(s.output.estimated_origin==0);assert(s.output.origin_margin<.15);}
    if(test==25) {c.r_direct=.1;c.r_indirect=.1;c.alarm_threshold_suspect=.01;c.alarm_threshold_confirmed=.02;step(&s,&c,0,2);step(&s,&c,100,2);assert(s.output.alarm);assert(s.output.ignorance_mass>.5);assert(!s.output.localization_valid);}
    if(test==26) {step(&s,&c,0,0);clo_dsf_t saved=s;step(&s,&c,0,2);assert(!memcmp(&s,&saved,sizeof(s)));}
    if(test==27) {
        ecu_state_t left={0},right={0};left.cross_layer_fault.layer=FAULT_LAYER_MEMORY;right.cross_layer_fault.layer=FAULT_LAYER_ACTUATOR;
        left.cross_layer_fault.bit_index=1;right.cross_layer_fault.bit_index=5;right.cross_layer_runtime.active=true;
        right.plant.coolant_temp_true_c=999;right.faults.enabled=true;right.propagation.plant_ms=1;
        clo_dsf_t astate,bstate;clo_dsf_init(&astate);clo_dsf_init(&bstate);
        for(int t=0;t<1000;t+=100) {
            left.time.time_ms=right.time.time_ms=t;left.sensors.coolant_temp_meas_c=right.sensors.coolant_temp_meas_c=92;
            left.control.active_control_target_c=right.control.active_control_target_c=104;
            runtime_observation_t x,y;runtime_observation_capture(&left,&x);runtime_observation_capture(&right,&y);
            x.diagnostic_id=1;y.diagnostic_id=3003;x.detector_alarm=false;y.detector_alarm=true;
            clo_dsf_step(&astate,&c,CLO_FULL,&x);clo_dsf_step(&bstate,&c,CLO_FULL,&y);
            assert(!memcmp(&astate,&bstate,sizeof(astate)));
        }
    }
    if(test==28) {assert(clo_config_valid(&c));c.lambda_temporal=1;assert(!clo_config_valid(&c));clo_config_default(&c);c.r_direct=NAN;assert(!clo_config_valid(&c));}
    if(test==29) {runtime_observation_t o=normal(1000);o.sample_timestamp_ms=1100;clo_dsf_step(&s,&c,CLO_FULL,&o);assert(!s.evidence.available[1]);}
    if(test==30) {for(int t=0;t<1000;t+=100)step(&s,&c,t,2);for(int t=1000;t<11000;t+=100)step(&s,&c,t,-1);assert(s.output.fault_belief<1e-8);}
    if(test==31) {
        clo_config_t other=c;other.localization_threshold=1;other.localization_margin_threshold=1;
        clo_dsf_t twin;clo_dsf_init(&twin);
        for(int t=0;t<5000;t+=100) {
            step(&s,&c,t,t<2000?2:-1);step(&twin,&other,t,t<2000?2:-1);
            assert(s.output.alarm==twin.output.alarm);
            NEAR(s.output.fault_belief,twin.output.fault_belief);
        }
    }
    if(test==32) {
        srand(17);
        for(int trial=0;trial<200;trial++) {
            ds_empty(&a);ds_empty(&b);
            for(unsigned int i=1;i<DS_SIZE;i++) {a.mass[i]=(double)(rand()%100);b.mass[i]=(double)(rand()%100);}
            assert(ds_normalize(&a));assert(ds_normalize(&b));
            assert(ds_combine(&a,&b,DS_DEMPSTER,&r,&k));assert(ds_valid(&r));assert(k>=0 && k<=1);
            assert(ds_combine(&a,&b,DS_YAGER,&r,&k));assert(ds_valid(&r));
            assert(ds_discount(&r,.37,&r));assert(ds_valid(&r));
            ds_pignistic(&r,p);double sum=0;for(unsigned int i=0;i<DS_ATOMS;i++)sum+=p[i];NEAR(sum,1);
        }
    }
    if(test==33 || test==34) {
        c.r_direct=.99;c.propagation_bonus=1;
        runtime_observation_t o=normal(0);o.timing.deadline_exceeded=true;
        clo_dsf_step(&s,&c,CLO_FULL,&o);
        o=normal(test==33?100:5000);o.timing.deadline_exceeded=true;o.pump_command=1;
        clo_dsf_step(&s,&c,CLO_FULL,&o);
        assert(s.output.propagation_support==(test==33));
        NEAR(s.evidence.reliability[0],test==33?1:.99);
    }
    return 0;
}
