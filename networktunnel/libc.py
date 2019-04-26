import ctypes
import platform

if platform.system() == 'Windows':
    libc = ctypes.cdll.LoadLibrary('msvcrt.dll')
else:
    libc = ctypes.cdll.LoadLibrary('libc.so.6')


libc.strcat.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
libc.strcat.restype = ctypes.c_char_p

libc.strcpy.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
libc.strcpy.restype = ctypes.c_char_p

libc.strlen.argtypes = [ctypes.c_char_p]
libc.strlen.restype = ctypes.c_size_t

libc.memcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
libc.memcpy.restype = ctypes.c_void_p
