import pathlib

import cffi  # type: ignore  # noqa

src_root = pathlib.Path(__file__).parent.joinpath('ext')
sources = [src_root.joinpath(s).as_posix() for s in
           ['CarrylessRangeCoder.c',
            'PPMdContext.c',
            'PPMdSubAllocator.c',
            'PPMdVariantI.c']]

ffibuilder = cffi.FFI()

# ----------- PPMd interfaces ---------------------
ffibuilder.cdef(r'''
typedef struct InStream InStream;
typedef struct InStream
{
	uint8_t (*nextByte)(InStream *self);
};
''')


ffibuilder.cdef(r'''
typedef struct PPMdCoreModel PPMdCoreModel;

struct PPMdCoreModel
{
	PPMdSubAllocator *alloc;

	CarrylessRangeCoder coder;
	uint32_t scale;

	PPMdState *FoundState; // found next state transition
	int OrderFall,InitEsc,RunLength,InitRL;
	uint8_t CharMask[256];
	uint8_t LastMaskIndex,EscCount,PrevSuccess;

	void (*RescalePPMdContext)(PPMdContext *self,PPMdCoreModel *model);
};
''')

# ----------- python binding API ---------------------
# ppmdpy.h
ffibuilder.cdef(r'''

typedef struct {
    /* Inherits from InStream */
    uint8_t (*nextByte)(InStream *self);
    int (*src_readinto)(char *buf, int size, void *userdata);
    void *userdata;
} RawReader;

extern "Python" int src_readinto(char *, int, void *);
extern "Python" void dst_write(char *, int, void *);

extern "Python" void *raw_alloc(size_t);
extern "Python" void raw_free(void *);
''')

# ---------------------------------------------------------------------------
ffibuilder.set_source('_ppmd', r'''
#include "PpmdPy.h"

static uint8_t nextByte(InStream *p)
{
    RawReader *br = p;
    char b;
    int size = br->src_readinto(&b, 1, br->userdata);
    if (size <= 0)
        return 0;
    return (uint8_t) b;
}

''', sources=sources, include_dirs=[src_root])

if __name__ == "__main__":  # not when running with setuptools
    ffibuilder.compile(verbose=True)
