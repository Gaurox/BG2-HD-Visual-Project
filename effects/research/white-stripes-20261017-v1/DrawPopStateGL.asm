0042CDB0  mov      eax, dword ptr [rip + 0x2b471e6]
0042CDB6  lea      rcx, [rip + 0x2b471cf]
0042CDBD  dec      eax
0042CDBF  mov      dword ptr [rip + 0x2b471d7], eax
0042CDC5  cdqe     
0042CDC7  mov      eax, dword ptr [rcx + rax*4]
0042CDCA  mov      dword ptr [rip + 0x2b4719c], eax
0042CDD0  ret      
0042CDD1  int3     
0042CDD2  int3     
0042CDD3  int3     
0042CDD4  int3     
0042CDD5  int3     
0042CDD6  int3     
0042CDD7  int3     
0042CDD8  int3     
0042CDD9  int3     
0042CDDA  int3     
0042CDDB  int3     
0042CDDC  int3     
0042CDDD  int3     
0042CDDE  int3     
0042CDDF  int3     
0042CDE0  movsxd   rcx, dword ptr [rip + 0x2b471b5]
0042CDE7  lea      rdx, [rip + 0x2b4719e]
0042CDEE  mov      eax, dword ptr [rip + 0x2b47178]
0042CDF4  mov      dword ptr [rdx + rcx*4], eax
0042CDF7  inc      dword ptr [rip + 0x2b4719f]
0042CDFD  ret      
0042CDFE  int3     
0042CDFF  int3     
0042CE00  mov      qword ptr [rsp + 8], rbx
0042CE05  mov      qword ptr [rsp + 0x10], rbp
0042CE0A  mov      qword ptr [rsp + 0x18], rsi
0042CE0F  push     rdi
0042CE10  sub      rsp, 0x40
0042CE14  mov      ebx, r9d
0042CE17  mov      edi, r8d
0042CE1A  mov      esi, edx
0042CE1C  mov      ebp, ecx
0042CE1E  call     0x14042b350
0042CE23  call     0x1405312fc
0042CE28  mov      rax, qword ptr [rsp + 0x70]
0042CE2D  mov      r9d, ebx
0042CE30  mov      qword ptr [rsp + 0x30], rax
0042CE35  mov      r8d, edi
0042CE38  mov      dword ptr [rsp + 0x28], 0x1401
0042CE40  mov      edx, esi
0042CE42  mov      ecx, ebp
0042CE44  mov      dword ptr [rsp + 0x20], 0x1908
0042CE4C  call     0x140531350
0042CE51  movsd    xmm0, qword ptr [rip + 0x1de5ef]
0042CE59  call     0x140531302
0042CE5E  mov      ecx, 0x4500
0042CE63  mov      rbx, qword ptr [rsp + 0x50]
0042CE68  mov      rbp, qword ptr [rsp + 0x58]
0042CE6D  mov      rsi, qword ptr [rsp + 0x60]
0042CE72  add      rsp, 0x40
0042CE76  pop      rdi
0042CE77  jmp      0x1405312c0
0042CE7C  int3     
0042CE7D  int3     
0042CE7E  int3     
0042CE7F  int3     
0042CE80  mov      dword ptr [rip + 0x2b471c6], edx
0042CE86  ret      
0042CE87  int3     
0042CE88  int3     
0042CE89  int3     
0042CE8A  int3     
0042CE8B  int3     
0042CE8C  int3     
0042CE8D  int3     
0042CE8E  int3     
0042CE8F  int3     
0042CE90  jmp      0x1405312d8
0042CE95  int3     
0042CE96  int3     
0042CE97  int3     
0042CE98  int3     
0042CE99  int3     
0042CE9A  int3     
0042CE9B  int3     
0042CE9C  int3     
0042CE9D  int3     
0042CE9E  int3     
0042CE9F  int3     
0042CEA0  test     ecx, ecx
0042CEA2  sete     al
0042CEA5  ret      
0042CEA6  int3     
0042CEA7  int3     
0042CEA8  int3     
0042CEA9  int3     
0042CEAA  int3     
0042CEAB  int3     
0042CEAC  int3     
0042CEAD  int3     
0042CEAE  int3     
0042CEAF  int3     
