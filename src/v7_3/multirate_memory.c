#include "multirate_memory.h"
void mr_memory_step(memory_diagnostic_t *s,unsigned now,unsigned nominal,memory_read_fn read,memory_write_fn write,void *ctx)
{
 if(!read||!write||(nominal!=250&&nominal!=500))return;
 unsigned interval=nominal==500?(s->checks%2?600:400):(s->checks%2?300:200);
 if(s->valid&&(now<s->checked_ms||now-s->checked_ms<interval))return;
 uint16_t saved=read(ctx);write(ctx,0);bool failed=read(ctx)!=0;
 write(ctx,UINT16_MAX);failed=(read(ctx)!=UINT16_MAX)||failed;
 write(ctx,saved);failed=(read(ctx)!=saved)||failed;
 s->checked_ms=now;s->checks++;s->operations+=7;s->valid=true;s->failed=failed;
}
