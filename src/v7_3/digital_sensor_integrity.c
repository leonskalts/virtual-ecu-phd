#include "digital_sensor_integrity.h"
#include <string.h>
/* CRC-32 covers canonical little-endian words; no struct padding or pointers.
 * The protected record models an isolated driver mailbox. CRC is not a MAC.
 * Independent protected storage, NOT secrecy of the polynomial, is the trust
 * assumption. Producer and legitimate transform API alone may update it. */
uint32_t di_tag(const di_record_t *r){
 uint32_t crc=~0U,v[4]={r->channel,r->bits,r->sequence,r->ms};
 for(unsigned i=0;i<4;i++)for(unsigned b=0;b<4;b++){
  crc^=(v[i]>>(8*b))&255U;
  for(unsigned k=0;k<8;k++)crc=(crc>>1)^((0U-(crc&1U))&0xedb88320U);
 }
 return ~crc;
}
void di_publish(di_witness_t *w,di_record_t *r,unsigned channel,float value,unsigned ms){
 di_record_t p={.channel=channel,.sequence=w->valid?w->protected_record.sequence+1:1,.ms=ms};
 memcpy(&p.bits,&value,sizeof p.bits);p.tag=di_tag(&p);w->protected_record=p;w->valid=true;*r=p;
}
void di_transform(di_witness_t *w,di_record_t *r,float offset){
 if(!w->valid)return;
 float v;memcpy(&v,&w->protected_record.bits,sizeof v);v+=offset;
 memcpy(&w->protected_record.bits,&v,sizeof v);w->protected_record.tag=di_tag(&w->protected_record);
 /* Update only envelope integrity, never overwrite the delivered value. */
 *r=w->protected_record;
}
unsigned di_verify(const di_witness_t *w,const di_record_t *r,float value,unsigned ms){
 if(!w->valid)return 0;
 uint32_t bits;memcpy(&bits,&value,sizeof bits);
 const di_record_t *p=&w->protected_record;unsigned status=0;
 if(p->tag!=di_tag(p)||r->tag!=di_tag(r))status|=4;
 if(bits!=p->bits||r->bits!=p->bits||r->tag!=p->tag||r->channel!=p->channel)status|=1;
 if(ms!=p->ms||r->sequence!=p->sequence||r->ms!=p->ms)status|=2;
 return status;
}
