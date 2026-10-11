#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void method_reset(void);
void method_step(const double*,const double*,double*);
void stack_call(void*,void(*)(const double*,const double*,double*),const double*,const double*,double*);
int main(void){uint32_t n;const size_t cap=1024*1024;unsigned char*stack=aligned_alloc(16,cap);if(!stack)return 5;
while(fread(&n,sizeof(n),1,stdin)==1){double*in=malloc((size_t)n*85*sizeof(double));double*out=calloc((size_t)n*8,sizeof(double));if(!in||!out||fread(in,85*sizeof(double),n,stdin)!=n)return 2;
/* Warm dynamic binding before watermarking; reset removes warm-up state. */
method_reset();if(n)method_step(in,in+67,out);method_reset();memset(stack,0xa5,cap);
for(unsigned i=0;i<n;i++)stack_call(stack+cap,method_step,in+85*i,in+85*i+67,out+8*i);
size_t low=0;while(low<cap&&stack[low]==0xa5)low++;uint64_t used=cap-low;if(!low)return 6;
if(fwrite(out,8*sizeof(double),n,stdout)!=n||fwrite(&used,sizeof(used),1,stdout)!=1)return 3;fflush(stdout);free(in);free(out);}free(stack);return ferror(stdin)?4:0;}
