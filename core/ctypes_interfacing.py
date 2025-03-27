import ctypes
import os

lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "line_parsing.so"))

class BatchScanResult(ctypes.Structure):
    _fields_ = [("commentedBlock", ctypes.c_bool), ("validLines", ctypes.c_int)]

lib.scanBatch.argtypes = [ctypes.POINTER(ctypes.c_char_p),
                         ctypes.c_int,
                         ctypes.c_bool,
                         ctypes.c_int,
                         ctypes.c_char_p,
                         ctypes.c_int,
                         ctypes.c_char_p,
                         ctypes.c_int,
                         ctypes.c_char_p,
                         ctypes.c_int]

lib.scanBatch.restype = BatchScanResult