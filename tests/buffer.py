import ctypes
import platform

if platform.system() == 'Windows':
    libc = ctypes.cdll.LoadLibrary('msvcrt.dll')
else:
    libc = ctypes.cdll.LoadLibrary('libc.so.6')


libc.printf(b'Hello world %d.\n', ctypes.c_int(2017))

buf1 = ctypes.c_buffer(1024)
buf2 = ctypes.c_buffer(1024)

buf1.value = b'hello'
buf2.value = b'yes yes'

libc.strcat.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
libc.strcat.restype = ctypes.c_char_p

libc.strcat(buf1, buf2)

libc.printf(buf1)

libc.strcpy.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
libc.strcpy.restype = ctypes.c_char_p
libc.strcpy(buf1, b"runoob")

libc.printf(buf1)

libc.memcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
libc.memcpy.restype = ctypes.c_void_p

libc.printf('\n')

data_buffer = ctypes.c_buffer(5)
libc.memcpy(data_buffer, buf1, 5)
libc.printf(data_buffer)
libc.printf('\n')

libc.printf(data_buffer[2:])
libc.printf('\n')

print(data_buffer[2:])

print(ctypes.cast(ctypes.byref(data_buffer, 3), ctypes.c_char_p).value)
