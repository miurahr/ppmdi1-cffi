
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    uint8_t (*nextByte)(void *self);
    int (*src_readinto)(char *buf, int size, void *userdata);
    void *userdata;
} RawReader;
