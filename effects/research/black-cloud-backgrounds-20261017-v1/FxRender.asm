0029DF60  mov      qword ptr [rsp + 8], rbx
0029DF65  push     rdi
0029DF66  sub      rsp, 0x40
0029DF6A  mov      rax, qword ptr [rip + 0x3c95ef]
0029DF71  mov      ebx, r9d
0029DF74  mov      edi, r8d
0029DF77  mov      r11, rcx
0029DF7A  mov      r10, qword ptr [rax + 0x210]
0029DF81  cmp      byte ptr [r10 + 0x19], 0
0029DF86  jne      0x14029df98
0029DF88  mov      eax, 1
0029DF8D  mov      rbx, qword ptr [rsp + 0x50]
0029DF92  add      rsp, 0x40
0029DF96  pop      rdi
0029DF97  ret      
0029DF98  mov      r8d, dword ptr [rcx + 0x78]
0029DF9C  add      rcx, 0x78
0029DFA0  mov      eax, dword ptr [rsp + 0x80]
0029DFA7  mov      r9d, dword ptr [r11 + 0x7c]
0029DFAB  sub      r8d, dword ptr [r11 + 0xc0]
0029DFB2  sub      r9d, dword ptr [r11 + 0xc4]
0029DFB9  add      r8d, edi
0029DFBC  mov      dword ptr [rsp + 0x38], eax
0029DFC0  add      r9d, ebx
0029DFC3  mov      eax, dword ptr [rsp + 0x78]
0029DFC7  mov      qword ptr [rsp + 0x30], rcx
0029DFCC  mov      rcx, qword ptr [r11 + 0x38]
0029DFD0  mov      dword ptr [rsp + 0x28], eax
0029DFD4  mov      eax, dword ptr [rsp + 0x70]
0029DFD8  mov      dword ptr [rsp + 0x20], eax
0029DFDC  call     0x14041d540
0029DFE1  mov      rbx, qword ptr [rsp + 0x50]
0029DFE6  add      rsp, 0x40
0029DFEA  pop      rdi
0029DFEB  ret      
0029DFEC  int3     
0029DFED  int3     
0029DFEE  int3     
0029DFEF  int3     
0029DFF0  push     r12
0029DFF2  push     r13
0029DFF4  push     r15
0029DFF6  sub      rsp, 0x90
0029DFFD  mov      rax, qword ptr [rip + 0x3c69d4]
0029E004  xor      rax, rsp
0029E007  mov      qword ptr [rsp + 0x50], rax
0029E00C  mov      rax, qword ptr [rip + 0x3c954d]
0029E013  mov      r10, rcx
0029E016  mov      r13, qword ptr [rsp + 0xe8]
0029E01E  mov      r12d, r9d
0029E021  mov      r15d, r8d
0029E024  mov      r11, rdx
0029E027  mov      rcx, qword ptr [rax + 0x210]
0029E02E  cmp      byte ptr [rcx + 0x19], 0
0029E032  jne      0x14029e03e
0029E034  mov      eax, 1
0029E039  jmp      0x14029e16a
0029E03E  mov      qword ptr [rsp + 0x88], rbx
0029E046  mov      qword ptr [rsp + 0x80], rbp
0029E04E  mov      ebp, dword ptr [rsp + 0xd0]
0029E055  mov      ecx, ebp
0029E057  mov      qword ptr [rsp + 0x78], rsi
0029E05C  mov      esi, dword ptr [rsp + 0xe0]
0029E063  mov      qword ptr [rsp + 0x70], rdi
0029E068  mov      qword ptr [rsp + 0x68], r14
0029E06D  mov      r14d, dword ptr [rsp + 0xd8]
0029E075  mov      edx, r14d
0029E078  test     sil, 0x10
0029E07C  je       0x14029e087
0029E07E  mov      ecx, dword ptr [r11 + 8]
0029E082  sub      ecx, dword ptr [r11]
0029E085  sub      ecx, ebp
0029E087  test     sil, 0x20
0029E08B  je       0x14029e098
0029E08D  mov      edx, dword ptr [r11 + 0xc]
0029E091  sub      edx, dword ptr [r11 + 4]
0029E095  sub      edx, r14d
0029E098  mov      edi, dword ptr [r10 + 0x78]
0029E09C  mov      r8d, edi
0029E09F  sub      r8d, dword ptr [r10 + 0x60]
0029E0A3  mov      ebx, dword ptr [r10 + 0x7c]
0029E0A7  add      r8d, r15d
0029E0AA  mov      r9d, ebx
0029E0AD  sub      r9d, dword ptr [r10 + 0x64]
0029E0B1  add      r9d, r12d
0029E0B4  cmp      r8d, edi
0029E0B7  jl       0x14029e0d0
0029E0B9  cmp      r8d, dword ptr [r10 + 0x80]
0029E0C0  jg       0x14029e0d0
0029E0C2  cmp      r9d, ebx
0029E0C5  jl       0x14029e0d0
0029E0C7  cmp      r9d, dword ptr [r10 + 0x84]
0029E0CE  jle      0x14029e0d9
0029E0D0  mov      r8d, 0xffffffff
0029E0D6  mov      r9d, r8d
0029E0D9  sub      ebx, dword ptr [r10 + 0xc4]
0029E0E0  mov      eax, r8d
0029E0E3  sub      edi, dword ptr [r10 + 0xc0]
0029E0EA  sub      eax, ecx
0029E0EC  add      eax, dword ptr [r13]
0029E0F0  mov      dword ptr [rsp + 0x40], eax
0029E0F4  mov      eax, dword ptr [r13 + 4]
0029E0F8  sub      eax, edx
0029E0FA  mov      dword ptr [rsp + 0x38], esi
0029E0FE  add      eax, r9d
0029E101  mov      qword ptr [rsp + 0x30], r13
0029E106  mov      dword ptr [rsp + 0x44], eax
0029E10A  mov      eax, dword ptr [r13 + 8]
0029E10E  sub      eax, ecx
0029E110  mov      dword ptr [rsp + 0x28], r14d
0029E115  mov      rcx, qword ptr [r10 + 0x38]
0029E119  add      eax, r8d
0029E11C  mov      dword ptr [rsp + 0x48], eax
0029E120  lea      r8d, [r15 + rdi]
0029E124  mov      eax, dword ptr [r13 + 0xc]
0029E128  sub      eax, edx
0029E12A  mov      dword ptr [rsp + 0x20], ebp
0029E12E  add      eax, r9d
0029E131  mov      rdx, r11
0029E134  mov      dword ptr [rsp + 0x4c], eax
0029E138  lea      r9d, [r12 + rbx]
0029E13C  movups   xmm0, xmmword ptr [rsp + 0x40]
0029E141  movups   xmmword ptr [r13], xmm0
0029E146  call     0x14041d540
0029E14B  mov      r14, qword ptr [rsp + 0x68]
0029E150  mov      rdi, qword ptr [rsp + 0x70]
0029E155  mov      rsi, qword ptr [rsp + 0x78]
0029E15A  mov      rbp, qword ptr [rsp + 0x80]
0029E162  mov      rbx, qword ptr [rsp + 0x88]
0029E16A  mov      rcx, qword ptr [rsp + 0x50]
0029E16F  xor      rcx, rsp
0029E172  call     0x1404f77a0
0029E177  add      rsp, 0x90
0029E17E  pop      r15
0029E180  pop      r13
0029E182  pop      r12
0029E184  ret      
0029E185  int3     
0029E186  int3     
0029E187  int3     
0029E188  int3     
0029E189  int3     
0029E18A  int3     
0029E18B  int3     
0029E18C  int3     
0029E18D  int3     
0029E18E  int3     
0029E18F  int3     
0029E190  mov      rax, qword ptr [rip + 0x3c93c9]
0029E197  mov      rcx, qword ptr [rax + 0x210]
0029E19E  jmp      0x14041d5f0
0029E1A3  int3     
0029E1A4  int3     
0029E1A5  int3     
0029E1A6  int3     
0029E1A7  int3     
0029E1A8  int3     
0029E1A9  int3     
0029E1AA  int3     
0029E1AB  int3     
0029E1AC  int3     
0029E1AD  int3     
0029E1AE  int3     
0029E1AF  int3     
0029E1B0  sub      rsp, 0x68
0029E1B4  mov      rax, qword ptr [rip + 0x3c681d]
0029E1BB  xor      rax, rsp
0029E1BE  mov      qword ptr [rsp + 0x50], rax
0029E1C3  mov      r11, qword ptr [rsp + 0x90]
0029E1CB  mov      r10, r9
0029E1CE  test     r8b, r8b
0029E1D1  jns      0x14029e209
0029E1D3  mov      eax, dword ptr [rcx + 0x78]
0029E1D6  lea      r9, [rcx + 0x78]
0029E1DA  sub      eax, dword ptr [rcx + 0xc0]
0029E1E0  add      eax, dword ptr [r10]
0029E1E3  mov      dword ptr [rsp + 0x30], eax
0029E1E7  mov      eax, dword ptr [rcx + 0x7c]
0029E1EA  sub      eax, dword ptr [rcx + 0xc4]
0029E1F0  add      eax, dword ptr [r10 + 4]
0029E1F4  mov      qword ptr [rsp + 0x28], r9
0029E1F9  lea      r9, [rsp + 0x30]
0029E1FE  mov      dword ptr [rsp + 0x34], eax
0029E202  mov      qword ptr [rsp + 0x20], r11
0029E207  jmp      0x14029e237
0029E209  xor      eax, eax
0029E20B  lea      r9, [rsp + 0x38]
0029E210  mov      qword ptr [rsp + 0x30], rax
0029E215  xorps    xmm0, xmm0
0029E218  mov      qword ptr [rsp + 0x38], rax
0029E21D  lea      rax, [rsp + 0x40]
0029E222  mov      qword ptr [rsp + 0x28], rax
0029E227  lea      rax, [rsp + 0x30]
0029E22C  mov      qword ptr [rsp + 0x20], rax
0029E231  movdqu   xmmword ptr [rsp + 0x40], xmm0
0029E237  mov      rcx, qword ptr [rcx + 0x38]
0029E23B  call     0x1400b30c0
0029E240  mov      rcx, qword ptr [rsp + 0x50]
0029E245  xor      rcx, rsp
0029E248  call     0x1404f77a0
0029E24D  add      rsp, 0x68
0029E251  ret      
0029E252  int3     
0029E253  int3     
0029E254  int3     
0029E255  int3     
0029E256  int3     
0029E257  int3     
0029E258  int3     
0029E259  int3     
0029E25A  int3     
0029E25B  int3     
0029E25C  int3     
0029E25D  int3     
0029E25E  int3     
0029E25F  int3     
0029E260  push     rbx
0029E262  push     rdi
0029E263  push     r12
0029E265  push     r13
0029E267  push     r15
0029E269  sub      rsp, 0x50
0029E26D  mov      rcx, qword ptr [rip + 0x3c92ec]
0029E274  xor      edi, edi
0029E276  xor      ebx, ebx
0029E278  mov      r12d, r9d
0029E27B  mov      r13d, r8d
0029E27E  mov      r15, rdx
0029E281  mov      rax, qword ptr [rcx + 0x210]
0029E288  cmp      byte ptr [rax + 0x19], bl
0029E28B  jne      0x14029e29d
0029E28D  lea      eax, [rdi + 1]
0029E290  add      rsp, 0x50
0029E294  pop      r15
0029E296  pop      r13
0029E298  pop      r12
0029E29A  pop      rdi
0029E29B  pop      rbx
0029E29C  ret      
0029E29D  mov      rax, qword ptr [rip + 0x3c92a4]
0029E2A4  mov      qword ptr [rsp + 0x88], rsi
0029E2AC  mov      esi, dword ptr [rsp + 0xa0]
0029E2B3  mov      qword ptr [rsp + 0x90], r14
0029E2BB  mov      rdx, qword ptr [rax + 0x1090]
0029E2C2  cmp      dword ptr [rdx + 0x9698], ebx
0029E2C8  je       0x14029e2db
0029E2CA  bt       esi, 0xb
0029E2CE  jb       0x14029e2db
0029E2D0  bts      esi, 0x13
0029E2D4  mov      edi, 1
0029E2D9  jmp      0x14029e2f2
0029E2DB  cmp      dword ptr [rdx + 0x969c], ebx
0029E2E1  je       0x14029e2f2
0029E2E3  bt       esi, 0xc
0029E2E7  jb       0x14029e2f2
0029E2E9  bts      esi, 0x19
0029E2ED  mov      ebx, 1
0029E2F2  mov      qword ptr [rsp + 0x80], rbp
0029E2FA  bt       esi, 0x10
0029E2FE  jb       0x14029e431
0029E304  lea      rcx, [r15 + 8]
0029E308  call     0x1403f7a10
0029E30D  mov      ebp, eax
0029E30F  test     edi, edi
0029E311  je       0x14029e357
0029E313  mov      rcx, qword ptr [rip + 0x3c9246]
0029E31A  mov      r8, qword ptr [rcx + 0x210]
0029E321  mov      ecx, eax
0029E323  shr      ecx, 0x10
0029E326  movzx    edx, cl
0029E329  movzx    ecx, bp
0029E32C  shr      cx, 8
0029E330  add      dx, cx
0029E333  movzx    ecx, bpl
0029E337  add      dx, cx
0029E33A  shr      dx, 2
0029E33E  movzx    ecx, dl
0029E341  mov      edx, ecx
0029E343  mov      eax, ecx
0029E345  shl      edx, 8
0029E348  shl      eax, 0x10
0029E34B  or       edx, eax
0029E34D  or       edx, ecx
0029E34F  mov      rcx, r8
0029E352  jmp      0x14029e414
0029E357  test     ebx, ebx
0029E359  je       0x14029e404
