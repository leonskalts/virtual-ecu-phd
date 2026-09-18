/* Written after mathematical freeze. Exact generic sparse product traversal:
 * validation, product order, conflict handling and normalization are unchanged. */
#include "clo_final_sparse_math.h"
bool final_sparse_combine(const ds_mass_t *a,const ds_mass_t *b,ds_rule_t rule,ds_mass_t *out,double *conflict)
{
 if(!ds_valid(a)||!ds_valid(b)||(rule!=DS_DEMPSTER&&rule!=DS_YAGER))return false;
 unsigned int indices[DS_SIZE],count=0;
 for(unsigned int j=1;j<DS_SIZE;j++)if(b->mass[j])indices[count++]=j;
 ds_mass_t result;ds_empty(&result);
 for(unsigned int i=1;i<DS_SIZE;i++) {
  if(!a->mass[i])continue;
  for(unsigned int k=0;k<count;k++){unsigned int j=indices[k];result.mass[i&j]+=a->mass[i]*b->mass[j];}
 }
 *conflict=result.mass[0];result.mass[0]=0;
 if(rule==DS_YAGER)result.mass[DS_THETA]+=*conflict;
 else if(1-*conflict<=1e-12){ds_vacuous(out);return false;}
 if(!ds_normalize(&result)){ds_vacuous(out);return false;}
 *out=result;return true;
}

/* Cached immutable partition/cardinality map; same logical accumulation order. */
static const unsigned int encoded[32]={0,33,2,35,4,37,6,39,8,41,10,43,12,45,14,47,16,49,18,51,20,53,22,55,24,57,26,59,28,61,30,63};
static const unsigned int cardinality[32]={0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4,1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5};
void final_cached_betp(const ds_mass_t *m,double scores[5])
{
 for(unsigned int i=0;i<5;i++)scores[i]=0;
 for(unsigned int subset=1;subset<32;subset++){double share=m->mass[encoded[subset]]/cardinality[subset];for(unsigned int i=0;i<5;i++)if(subset&(1U<<i))scores[i]+=share;}
}
