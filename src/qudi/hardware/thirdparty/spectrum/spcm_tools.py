from ctypes import *

# load registers for easier access
from py_header.regs import *


#
# **************************************************************************
# pvAllocMemPageAligned: creates a buffer for DMA that's page-aligned 
# **************************************************************************
#
def pvAllocMemPageAligned (qwBytes):
    dwAlignment = 4096
    dwMask = dwAlignment - 1

    # allocate non-aligned, slightly larger buffer
    qwRequiredNonAlignedBytes = qwBytes * sizeof (c_char) + dwMask
    pvNonAlignedBuf = (c_char * qwRequiredNonAlignedBytes)()

    # get offset of next aligned address in non-aligned buffer
    misalignment = addressof (pvNonAlignedBuf) & dwMask
    if misalignment:
        dwOffset = dwAlignment - misalignment
    else:
        dwOffset = 0
    return(c_char * qwBytes).from_buffer(pvNonAlignedBuf, dwOffset)

