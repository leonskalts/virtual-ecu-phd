#ifndef TRIPLEX_PLUS_SEQUENTIAL_H
#define TRIPLEX_PLUS_SEQUENTIAL_H
#include <stdbool.h>
/* Six already-qualified runtime providers. Parameters fitted outside runtime. */
typedef struct {double score[6];} plus_oq_t;
void plus_oq_init(plus_oq_t *);
bool plus_oq_step(plus_oq_t *,const double[6],const unsigned char[6],const double[60],double,double);
void plus_oq_series(unsigned,const double *,const unsigned char *,const double *,double,double,double *,unsigned char *);
#endif
