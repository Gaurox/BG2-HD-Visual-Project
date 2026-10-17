0042D030  mov      qword ptr [rsp + 8], rbx
0042D035  mov      qword ptr [rsp + 0x10], rbp
0042D03A  mov      qword ptr [rsp + 0x18], rsi
0042D03F  mov      qword ptr [rsp + 0x20], rdi
0042D044  push     r14
0042D046  sub      rsp, 0x50
0042D04A  cmp      byte ptr [rip + 0x2b46f17], 0
0042D051  movzx    r14d, r9b
0042D055  mov      rbp, r8
0042D058  mov      edi, edx
0042D05A  mov      esi, ecx
0042D05C  jne      0x14042d06e
0042D05E  call     0x140400080
0042D063  mov      ecx, edi
0042D065  mov      esi, eax
0042D067  call     0x140400080
0042D06C  mov      edi, eax
0042D06E  mov      eax, dword ptr [rip + 0x2b46ef8]
0042D074  lea      rcx, [rip + 0x329fc5]
0042D07B  shr      rax, 0x15
0042D07F  and      eax, 0x1ff
0042D084  lea      rax, [rax + rax*4]
0042D088  lea      rbx, [rcx + rax*8]
0042D08C  mov      dword ptr [rbx + 4], esi
0042D08F  mov      dword ptr [rbx + 8], edi
0042D092  mov      r8d, dword ptr [rip + 0x2b46ed3]
0042D099  mov      ecx, r8d
0042D09C  mov      edx, dword ptr [rip + 0x2b46f42]
0042D0A2  mov      eax, edx
0042D0A4  shr      ecx, 0x15
0042D0A7  shr      eax, 0x15
0042D0AA  and      ecx, 0x1ff
0042D0B0  and      eax, 0x1ff
0042D0B5  cmp      eax, ecx
0042D0B7  je       0x14042d0e0
0042D0B9  mov      eax, edx
0042D0BB  xor      eax, r8d
0042D0BE  and      eax, 0x3fe00000
0042D0C3  xor      edx, eax
0042D0C5  mov      eax, dword ptr [rip + 0x2b46f1d]
0042D0CB  and      eax, 0xc03fffff
0042D0D0  mov      dword ptr [rip + 0x2b46f0e], edx
0042D0D6  bts      eax, 0x15
0042D0DA  mov      dword ptr [rip + 0x2b46f08], eax
0042D0E0  cmp      byte ptr [rbx + 0xc], 0
0042D0E4  jne      0x14042d0eb
0042D0E6  call     0x14042ca10
0042D0EB  test     r14b, r14b
0042D0EE  je       0x14042d100
0042D0F0  mov      ecx, 0x84c1
0042D0F5  call     qword ptr [rip + 0x329e4d]
0042D0FB  mov      edx, dword ptr [rbx + 0x24]
0042D0FE  jmp      0x14042d10d
0042D100  mov      ecx, 0x84c0
0042D105  call     qword ptr [rip + 0x329e3d]
0042D10B  mov      edx, dword ptr [rbx]
0042D10D  mov      ecx, 0xde1
0042D112  call     0x140531380
0042D117  mov      r8d, dword ptr [rbx + 0x20]
0042D11B  xor      edx, edx
0042D11D  mov      qword ptr [rsp + 0x40], rbp
0042D122  mov      r9d, esi
0042D125  mov      ecx, 0xde1
0042D12A  cmp      r8d, 0x1909
0042D131  jne      0x14042d142
0042D133  mov      dword ptr [rsp + 0x38], 0x1401
0042D13B  mov      dword ptr [rsp + 0x30], r8d
0042D140  jmp      0x14042d156
0042D142  mov      eax, dword ptr [rip + 0x2b46ed8]
0042D148  mov      dword ptr [rsp + 0x38], eax
0042D14C  mov      eax, dword ptr [rip + 0x2b46eca]
0042D152  mov      dword ptr [rsp + 0x30], eax
0042D156  mov      dword ptr [rsp + 0x28], 0
0042D15E  mov      dword ptr [rsp + 0x20], edi
0042D162  call     0x14053136e
0042D167  mov      rbx, qword ptr [rsp + 0x60]
0042D16C  mov      rbp, qword ptr [rsp + 0x68]
0042D171  mov      rsi, qword ptr [rsp + 0x70]
0042D176  mov      rdi, qword ptr [rsp + 0x78]
0042D17B  add      rsp, 0x50
0042D17F  pop      r14
0042D181  ret      
