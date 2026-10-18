0032D020 push     rbx
0032D022 push     rsi
0032D023 push     r14
0032D025 push     r15
0032D027 sub      rsp, 0x88
0032D02E mov      rax, qword ptr [rip + 0x3379a3]
0032D035 xor      rax, rsp
0032D038 mov      qword ptr [rsp + 0x60], rax
0032D03D cmp      byte ptr [rcx + 0xf81], 0
0032D044 mov      r15, rdx
0032D047 mov      rbx, qword ptr [rsp + 0xf0]
0032D04F mov      rsi, rcx
0032D052 mov      rax, qword ptr [rsp + 0xd0]
0032D05A mov      r14, qword ptr [rsp + 0xd8]
0032D062 mov      qword ptr [rsp + 0x48], rbx
0032D067 je       0x14032d36f
0032D06D mov      qword ptr [rsp + 0xc0], rbp
0032D075 mov      qword ptr [rsp + 0x78], r12
0032D07A mov      r12d, dword ptr [rsp + 0x108]
0032D082 mov      qword ptr [rsp + 0x70], r13
0032D087 test     r12d, r12d
0032D08A jne      0x14032d097
0032D08C movzx    r12d, word ptr [rcx + 0xf82]
0032D094 neg      r12d
0032D097 mov      rax, qword ptr [rax]
0032D09A movups   xmm0, xmmword ptr [r9]
0032D09E mov      qword ptr [rsp + 0x40], rax
0032D0A3 shr      rax, 0x20
0032D0A7 add      eax, r12d
0032D0AA mov      dword ptr [rsp + 0x44], eax
0032D0AE movzx    eax, byte ptr [rcx + 0xf8a]
0032D0B5 cmp      word ptr [rcx + 0xf88], ax
0032D0BC mov      ecx, dword ptr [rsp + 0xe0]
0032D0C3 movups   xmmword ptr [rsp + 0x50], xmm0
0032D0C8 jle      0x14032d0d0
0032D0CA or       ecx, dword ptr [rip + 0x27527c]
0032D0D0 movzx    r8d, byte ptr [rsi + 0x5f4]
0032D0D8 mov      eax, ecx
0032D0DA movzx    r9d, byte ptr [rsi + 0x5f5]
0032D0E2 or       eax, 8
0032D0E5 mov      rdx, qword ptr [rsi + 0xcd8]
0032D0EC test     r8b, r8b
0032D0EF movzx    r13d, byte ptr [rsp + 0x110]
0032D0F8 cmove    eax, ecx
0032D0FB mov      ecx, eax
0032D0FD or       ecx, 0x2200
0032D103 test     r9b, r9b
0032D106 cmove    ecx, eax
0032D109 test     rdx, rdx
0032D10C jne      0x14032d12e
0032D10E movzx    eax, byte ptr [rsi + 0xf80]
0032D115 test     al, al
0032D117 jne      0x14032d12e
0032D119 test     r13b, r13b
0032D11C jne      0x14032d12e
0032D11E test     cl, 8
0032D121 jne      0x14032d12e
0032D123 or       ecx, dword ptr [rip + 0x27521f]
0032D129 or       ecx, 1
0032D12C jmp      0x14032d13b
0032D12E or       ecx, dword ptr [rip + 0x275210]
0032D134 movzx    eax, byte ptr [rsi + 0xf80]
0032D13B mov      ebp, ecx
0032D13D or       ebp, 4
0032D140 test     rdx, rdx
0032D143 cmove    ebp, ecx
0032D146 test     al, al
0032D148 jne      0x14032d14f
0032D14A test     r13b, r13b
0032D14D je       0x14032d152
0032D14F or       ebp, 2
0032D152 cmp      byte ptr [rsi + 0x5f6], 0
0032D159 jne      0x14032d165
0032D15B test     r8b, r8b
0032D15E jne      0x14032d165
0032D160 test     r9b, r9b
0032D163 je       0x14032d16b
0032D165 and      ebp, 0xfffcffff
0032D16B lea      r9, [rsp + 0x40]
0032D170 mov      qword ptr [rsp + 0x20], r14
0032D175 mov      r8d, ebp
0032D178 lea      rdx, [rsp + 0x50]
0032D17D mov      rcx, r15
0032D180 call     0x14029e1b0
0032D185 mov      r8d, ebp
0032D188 lea      rdx, [rsp + 0x50]
0032D18D mov      rcx, r15
0032D190 call     0x14029e190
0032D195 test     eax, eax
0032D197 je       0x14032d35d
0032D19D cmp      byte ptr [rsi + 0x5f6], 0
0032D1A4 mov      qword ptr [rsp + 0x80], rdi
0032D1AC jne      0x14032d1d7
0032D1AE cmp      byte ptr [rsi + 0x5f4], 0
0032D1B5 jne      0x14032d1d7
0032D1B7 cmp      byte ptr [rsi + 0x5f5], 0
0032D1BE jne      0x14032d1d7
0032D1C0 mov      rcx, qword ptr [rsi + 0xcd0]
0032D1C7 mov      edx, dword ptr [rsp + 0xe8]
0032D1CE add      rcx, 8
0032D1D2 call     0x140412690
0032D1D7 cmp      dword ptr [rsi + 0xba8], 0
0032D1DE je       0x14032d224
0032D1E0 mov      rcx, qword ptr [rsi + 0xcb0]
0032D1E7 call     0x1403f6d50
0032D1EC mov      rbx, qword ptr [rsi + 0xcb0]
0032D1F3 mov      rcx, rbx
0032D1F6 call     0x1403f7890
0032D1FB mov      rcx, rbx
0032D1FE mov      edi, eax
0032D200 call     0x1403f78b0
0032D205 movzx    r9d, word ptr [rip + 0x29346b]
0032D20D mov      rdx, rax
0032D210 mov      rcx, qword ptr [rsi + 0xcd0]
0032D217 mov      r8d, edi
0032D21A call     0x1404123c0
0032D21F mov      rbx, qword ptr [rsp + 0x48]
0032D224 mov      rdx, qword ptr [rsi + 0xcd8]
0032D22B xor      edi, edi
0032D22D test     rdx, rdx
0032D230 je       0x14032d24c
0032D232 mov      r9d, dword ptr [r14 + 4]
0032D236 mov      rcx, r15
0032D239 mov      r8d, dword ptr [r14]
0032D23C sub      r9d, r12d
0032D23F mov      dword ptr [rsp + 0x28], edi
0032D243 mov      dword ptr [rsp + 0x20], ebp
0032D247 call     0x14029e260
0032D24C cmp      byte ptr [rsi + 0xf80], dil
0032D253 je       0x14032d280
0032D255 test     r13b, r13b
0032D258 je       0x14032d279
0032D25A movzx    ecx, r13b
0032D25E mov      eax, 0x80808081
0032D263 shl      ecx, 7
0032D266 imul     ecx
0032D268 add      edx, ecx
0032D26A sar      edx, 7
0032D26D mov      ecx, edx
0032D26F shr      ecx, 0x1f
0032D272 sub      ecx, -0x80
0032D275 add      ecx, edx
0032D277 jmp      0x14032d28b
0032D279 mov      ecx, 0x80
0032D27E jmp      0x14032d28b
0032D280 movzx    ecx, r13b
0032D284 test     r13b, r13b
0032D287 jne      0x14032d28b
0032D289 mov      ecx, edi
0032D28B mov      r9d, dword ptr [r14 + 4]
0032D28F mov      r8d, dword ptr [r14]
0032D292 mov      rdx, qword ptr [rsi + 0xcd0]
0032D299 mov      dword ptr [rsp + 0x28], ecx
0032D29D mov      rcx, r15
0032D2A0 mov      dword ptr [rsp + 0x20], ebp
0032D2A4 call     0x14029e260
0032D2A9 mov      rax, qword ptr [rsi]
0032D2AC mov      rcx, rsi
0032D2AF call     qword ptr [rax + 0x78]
0032D2B2 cmp      al, byte ptr [rip + 0x26c471]
0032D2B8 je       0x14032d2e8
0032D2BA movzx    eax, byte ptr [rsp + 0xf8]
0032D2C2 xor      r9d, r9d
0032D2C5 mov      r8d, dword ptr [rsp + 0x44]
0032D2CA mov      rcx, r15
0032D2CD mov      edx, dword ptr [rsp + 0x40]
0032D2D1 mov      dword ptr [rsp + 0x38], ebp
0032D2D5 mov      byte ptr [rsp + 0x30], al
0032D2D9 mov      qword ptr [rsp + 0x28], rbx
0032D2DE mov      qword ptr [rsp + 0x20], r14
0032D2E3 call     0x14029e4c0
0032D2E8 lea      r9, [rsp + 0x48]
0032D2ED mov      edx, ebp
0032D2EF cmp      dword ptr [rsp + 0x100], edi
0032D2F6 je       0x14032d31b
0032D2F8 mov      ecx, dword ptr [r14]
0032D2FB lea      r8, [rsp + 0x50]
0032D300 add      ecx, dword ptr [rsp + 0x40]
0032D304 mov      rax, qword ptr [rsp + 0x40]
0032D309 shr      rax, 0x20
0032D30D add      eax, dword ptr [r14 + 4]
0032D311 mov      dword ptr [rsp + 0x4c], eax
0032D315 mov      dword ptr [rsp + 0x48], ecx
0032D319 jmp      0x14032d323
0032D31B mov      qword ptr [rsp + 0x48], rdi
0032D320 xor      r8d, r8d
0032D323 mov      rcx, r15
0032D326 call     0x14029ea40
0032D32B mov      eax, dword ptr [r14 + 4]
0032D32F lea      rdx, [rsp + 0x50]
0032D334 mov      r9d, dword ptr [rsp + 0x44]
0032D339 mov      rcx, r15
0032D33C mov      r8d, dword ptr [rsp + 0x40]
0032D341 mov      dword ptr [rsp + 0x30], ebp
0032D345 mov      dword ptr [rsp + 0x28], eax
0032D349 mov      eax, dword ptr [r14]
0032D34C mov      dword ptr [rsp + 0x20], eax
0032D350 call     0x14029df60
0032D355 mov      rdi, qword ptr [rsp + 0x80]
0032D35D mov      r12, qword ptr [rsp + 0x78]
0032D362 mov      rbp, qword ptr [rsp + 0xc0]
0032D36A mov      r13, qword ptr [rsp + 0x70]
0032D36F mov      rcx, qword ptr [rsp + 0x60]
0032D374 xor      rcx, rsp
0032D377 call     0x1404f77a0
0032D37C add      rsp, 0x88
0032D383 pop      r15
0032D385 pop      r14
0032D387 pop      rsi
0032D388 pop      rbx
0032D389 ret      
0032D38A int3     
0032D38B int3     
0032D38C int3     
0032D38D int3     
0032D38E int3     
0032D38F int3     
