/* Self-checking C testbench: frozen software implementation is the oracle.
 * rtl_tick is a generated Verilator binding, not virtual-ECU runtime code. */
#include "digital_sensor_integrity.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern void rtl_tick(const uint32_t in[13], uint32_t out[8]);
static di_witness_t witness;
static di_record_t envelope;
static unsigned checks;
static uint32_t random_state=0x59a24c71;
static uint32_t rnd(void) {random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;return random_state;}
static float as_float(uint32_t bits) {float v;memcpy(&v,&bits,4);return v;}
static void check(unsigned op, uint32_t channel, uint32_t bits, uint32_t ms,
                  unsigned mutation, const char *label)
{
    if(op==0){memset(&witness,0,sizeof witness);memset(&envelope,0,sizeof envelope);}
    if(op==1)di_publish(&witness,&envelope,channel,as_float(bits),ms);
    if(op==2){di_transform(&witness,&envelope,0.5f);bits=witness.protected_record.bits;}
    di_record_t r=envelope;
    uint32_t value=r.bits, timestamp=r.ms;
    switch(mutation) {
    case 1:value^=1;break;
    case 2:r.channel^=1;break;
    case 3:r.sequence^=1;break;
    case 4:r.ms^=1;break;
    case 5:r.tag^=1;break;
    case 6:r.bits^=1;value=r.bits;r.tag=di_tag(&r);break;
    case 7:timestamp^=1;break;
    case 8:r.bits^=1;break;
    case 9:r.sequence--;r.tag=di_tag(&r);break;
    case 10:r.channel^=1;r.tag=di_tag(&r);break;
    case 11:r.channel^=1;r.sequence^=1;r.tag^=1;value^=1;break;
    }
    unsigned status=di_verify(&witness,&r,as_float(value),timestamp);
    uint32_t in[13]={op==0,op==1,op==2,channel,bits,ms,r.channel,r.bits,r.sequence,r.ms,r.tag,value,timestamp},out[8];
    rtl_tick(in,out);
    uint32_t expected[8]={witness.valid,witness.protected_record.channel,witness.protected_record.bits,
        witness.protected_record.sequence,witness.protected_record.ms,witness.protected_record.tag,
        status,!witness.valid?0:status?2:1};
    for(unsigned k=0;k<8;k++)if(out[k]!=expected[k]){
        fprintf(stderr,"FAIL %s output%u got%08x expected%08x\n",label,k,out[k],expected[k]);exit(1);
    }
    checks++;
}
int main(void)
{
    check(0,0,0,0,0,"reset-unavailable");
    check(2,0,0,0,0,"transform-unavailable");
    check(1,2,0x42c80000,12300,0,"publish-pass");
    const char *names[]={"pass","delivered-value","channel","sequence","record-time","tag",
        "value-plus-valid-tag","delivered-time","envelope-value","replay-valid-tag","identity-valid-tag","combined"};
    for(unsigned m=0;m<12;m++)check(3,0,0,0,m,names[m]);
    check(3,0,0,0,0,"consumer-cannot-write-witness");
    check(2,99,0,999,0,"authorized-transform-retains-identity-time");
    check(1,1,0x80000000,12400,0,"new-record-negative-zero");
    check(0,0,0,0,11,"reset-with-corrupt-inputs");
    check(1,0,0x3f800000,12500,0,"sequence-restarts-at-one");
    for(unsigned n=0;n<256;n++){
        check(1,rnd(),rnd(),rnd(),0,"random-record-crc");
        for(unsigned m=1;m<12;m++)check(3,0,0,0,m,names[m]);
        check(3,0,0,0,0,"witness-still-intact");
    }
    printf("PASS: %u software-oracle comparisons; all 8 outputs checked per cycle\n",checks);
    return 0;
}
