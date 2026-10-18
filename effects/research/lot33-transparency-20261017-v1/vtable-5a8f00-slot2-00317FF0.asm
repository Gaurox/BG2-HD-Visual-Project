00317FF0 mov      qword ptr [rsp + 8], rbx
00317FF5 mov      qword ptr [rsp + 0x10], rsi
00317FFA mov      qword ptr [rsp + 0x18], rdi
00317FFF mov      qword ptr [rsp + 0x20], r14
00318004 mov      r11d, dword ptr [rsp + 0x28]
00318009 mov      rsi, r9
0031800C mov      r14, r8
0031800F mov      rdi, rdx
00318012 mov      rbx, rcx
00318015 test     r11d, r11d
00318018 jne      0x140318025
0031801A movzx    r11d, word ptr [rcx + 0xf82]
00318022 neg      r11d
00318025 mov      r10d, dword ptr [r8]
00318028 movzx    r8d, byte ptr [rcx + 0xf8a]
00318030 mov      ecx, dword ptr [r9]
00318033 mov      r9d, dword ptr [rsp + 0x30]
00318038 sub      ecx, r9d
0031803B add      ecx, r10d
0031803E sub      r10d, dword ptr [rsi]
00318041 cmp      word ptr [rbx + 0xf88], r8w
00318049 cmovg    r10d, ecx
0031804D mov      dword ptr [rdx], r10d
00318050 mov      edx, dword ptr [r14 + 4]
00318054 sub      edx, dword ptr [rsi + 4]
00318057 mov      rbx, qword ptr [rsp + 8]
0031805C lea      ecx, [r9 + r10]
00318060 mov      rsi, qword ptr [rsp + 0x10]
00318065 add      edx, r11d
00318068 mov      r14, qword ptr [rsp + 0x20]
0031806D mov      dword ptr [rdi + 8], ecx
00318070 mov      ecx, dword ptr [rsp + 0x38]
00318074 add      ecx, edx
00318076 mov      dword ptr [rdi + 4], edx
00318079 mov      dword ptr [rdi + 0xc], ecx
0031807C mov      rdi, qword ptr [rsp + 0x18]
00318081 ret      
