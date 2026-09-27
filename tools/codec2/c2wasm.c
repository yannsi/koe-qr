#include "codec2.h"
#include <stdlib.h>
#define EXPORT(n) __attribute__((export_name(n)))
static struct CODEC2 *c2 = 0;
EXPORT("c2_create") int c2_create(int mode){ if(c2){codec2_destroy(c2);c2=0;} c2=codec2_create(mode); return c2?1:0; }
EXPORT("c2_spf") int c2_spf(void){ return codec2_samples_per_frame(c2); }
EXPORT("c2_bpf") int c2_bpf(void){ return codec2_bytes_per_frame(c2); }
EXPORT("c2_bits") int c2_bits(void){ return codec2_bits_per_frame(c2); }
EXPORT("c2_enc") void c2_enc(unsigned char *bits, short *speech){ codec2_encode(c2,bits,speech); }
EXPORT("c2_dec") void c2_dec(short *speech, const unsigned char *bits){ codec2_decode(c2,speech,bits); }
EXPORT("c2_malloc") void* c2_malloc(int n){ return malloc(n); }
EXPORT("c2_free") void c2_free(void *p){ free(p); }
