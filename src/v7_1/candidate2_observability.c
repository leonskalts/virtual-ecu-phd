#include "clo_dsf_candidate2.h"
/* Five disjoint blocks cover all six storage bits. No NORMAL origin exists.
 * MEMORY's two storage bits are ONE logical atom, not extra evidence. */
const unsigned int c2_origin_blocks[5]={33U,2U,4U,8U,16U};
const unsigned int c2_origin_support[CLO_CHANNELS]={2U,4U,33U,4U|8U,16U,DS_THETA};
unsigned int c2_encode_origin_subset(unsigned int logical_mask)
{
    unsigned int encoded=0;
    for(unsigned int i=0;i<5;i++) if(logical_mask&(1U<<i)) encoded|=c2_origin_blocks[i];
    return encoded;
}
void c2_origin_betp(const ds_mass_t *m,double scores[5])
{
    for(unsigned int i=0;i<5;i++) scores[i]=0;
    for(unsigned int subset=1;subset<32;subset++) {
        unsigned int n=0;
        for(unsigned int i=0;i<5;i++) n+=(subset&(1U<<i))!=0;
        double share=m->mass[c2_encode_origin_subset(subset)]/n;
        for(unsigned int i=0;i<5;i++) if(subset&(1U<<i)) scores[i]+=share;
    }
}
