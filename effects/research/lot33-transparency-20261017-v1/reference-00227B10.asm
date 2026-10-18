00227B10 mov      qword ptr [rsp + 0x10], rbx
00227B15 push     rdi
00227B16 sub      rsp, 0x30
00227B1A mov      rax, qword ptr [rip + 0x43ceb7]
00227B21 xor      rax, rsp
00227B24 mov      qword ptr [rsp + 0x28], rax
00227B29 mov      rdi, rcx
00227B2C lea      rdx, [rip + 0x371a81]
00227B33 lea      rcx, [rsp + 0x20]
00227B38 call     0x1403ff800
00227B3D mov      rcx, rdi
00227B40 mov      rdx, qword ptr [rax]
00227B43 call     0x140227600
00227B48 mov      rcx, qword ptr [rdi + 0x1b8]
00227B4F lea      rax, [rip + 0x373aca]
00227B56 xor      edx, edx
00227B58 mov      qword ptr [rdi], rax
00227B5B call     0x140412380
00227B60 mov      rax, qword ptr [rip + 0x43f9e1]
00227B67 lea      rcx, [rdi + 0x1c8]
00227B6E xor      edx, edx
00227B70 mov      r9, qword ptr [rax + 0x1090]
00227B77 add      r9, 0x63d8
00227B7E lea      r8d, [rdx + 0x43]
00227B82 call     0x1404221c0
00227B87 mov      rcx, qword ptr [rdi + 0x1b8]
00227B8E lea      rdx, [rdi + 0x1c8]
00227B95 call     0x140412390
00227B9A xor      eax, eax
00227B9C lea      rcx, [rdi + 0x140]
00227BA3 lea      r8, [rip + 0x3c3c03]
00227BAA mov      qword ptr [rdi + 0x1f8], rax
00227BB1 lea      rdx, [rsp + 0x20]
00227BB6 mov      dword ptr [rdi + 0x200], eax
00227BBC mov      dword ptr [rdi + 0x210], eax
00227BC2 call     0x1403ff960
00227BC7 mov      eax, 1
00227BCC mov      word ptr [rdi + 0x214], ax
00227BD3 mov      rax, rdi
00227BD6 mov      rcx, qword ptr [rsp + 0x28]
00227BDB xor      rcx, rsp
00227BDE call     0x1404f77a0
00227BE3 mov      rbx, qword ptr [rsp + 0x48]
00227BE8 add      rsp, 0x30
00227BEC pop      rdi
00227BED ret      
