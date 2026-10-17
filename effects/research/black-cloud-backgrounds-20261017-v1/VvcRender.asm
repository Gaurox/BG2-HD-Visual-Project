00254B00  mov      r11, rsp
00254B03  push     rbp
00254B04  push     rsi
00254B05  push     r15
00254B07  lea      rbp, [r11 - 0x5f]
00254B0B  sub      rsp, 0xd0
00254B12  mov      rax, qword ptr [rip + 0x40febf]
00254B19  xor      rax, rsp
00254B1C  mov      qword ptr [rbp + 0x1f], rax
00254B20  mov      rax, qword ptr [rip + 0x412a21]
00254B27  mov      rsi, rcx
00254B2A  mov      r15, rdx
00254B2D  mov      rcx, qword ptr [rax + 0x1090]
00254B34  cmp      dword ptr [rcx + 0x7e40], 0
00254B3B  jne      0x140255157
00254B41  cmp      dword ptr [rcx + 0x7dec], 0
00254B48  jne      0x140255157
00254B4E  mov      eax, dword ptr [rcx + 0x97f0]
00254B54  cmp      dword ptr [rsi + 0x3f8], eax
00254B5A  jl       0x140255157
00254B60  movzx    ecx, byte ptr [rip + 0x36bb18]
00254B67  mov      r10d, dword ptr [rsi + 0xc]
00254B6B  mov      edx, ecx
00254B6D  mov      qword ptr [r11 + 0x18], rbx
00254B71  mov      eax, ecx
00254B73  shl      eax, 0x10
00254B76  lea      rbx, [rsi + 0xc]
00254B7A  mov      qword ptr [r11 - 0x20], rdi
00254B7E  shl      edx, 8
00254B81  or       edx, eax
00254B83  mov      qword ptr [r11 - 0x28], r12
00254B87  mov      r12d, dword ptr [rsi + 0x78]
00254B8B  or       edx, ecx
00254B8D  mov      ecx, dword ptr [rip + 0x34d7b9]
00254B93  and      r12d, 2
00254B97  mov      qword ptr [r11 - 0x30], r13
00254B9B  mov      r13d, ecx
00254B9E  mov      qword ptr [r11 - 0x38], r14
00254BA2  not      ecx
00254BA4  mov      r14d, dword ptr [rsi + 0x70]
00254BA8  mov      eax, r14d
00254BAB  and      eax, 0x10000
00254BB0  mov      dword ptr [rbp - 0x31], edx
00254BB3  mov      dword ptr [rbp - 0x1d], eax
00254BB6  and      r13d, r14d
00254BB9  mov      eax, dword ptr [rip + 0x34d791]
00254BBF  mov      edi, r14d
00254BC2  mov      edx, eax
00254BC4  mov      dword ptr [rbp - 0x25], r12d
00254BC8  and      edx, r14d
00254BCB  mov      dword ptr [rbp - 1], r13d
00254BCF  and      edi, 4
00254BD2  mov      dword ptr [rbp - 0x21], edx
00254BD5  not      eax
00254BD7  mov      dword ptr [rbp - 0x19], edi
00254BDA  and      eax, ecx
00254BDC  and      r14d, eax
00254BDF  cmp      r10d, dword ptr [r15 + 0x678]
00254BE6  jge      0x1402550de
00254BEC  mov      r9d, dword ptr [rsi + 0x10]
00254BF0  cmp      r9d, dword ptr [r15 + 0x67c]
00254BF7  jge      0x1402550de
00254BFD  test     r10d, r10d
00254C00  js       0x1402550de
00254C06  test     r9d, r9d
00254C09  js       0x1402550de
00254C0F  movzx    ecx, byte ptr [rip + 0x349fd5]
00254C16  mov      eax, r9d
00254C19  cdq      
00254C1A  idiv     ecx
00254C1C  movsx    ecx, word ptr [r15 + 0xbbc]
00254C24  movsx    r8d, ax
00254C28  mov      eax, r10d
00254C2B  imul     r8d, ecx
00254C2F  cdq      
00254C30  movzx    ecx, byte ptr [rip + 0x349fb3]
00254C37  idiv     ecx
00254C39  add      ax, r8w
00254C3D  movsx    rax, ax
00254C41  test     eax, eax
00254C43  js       0x14025512f
00254C49  cmp      eax, dword ptr [r15 + 0xbb8]
00254C50  jge      0x14025512f
00254C56  mov      rcx, rax
00254C59  mov      rax, qword ptr [r15 + 0xbb0]
00254C60  movzx    ecx, word ptr [rax + rcx*2]
00254C64  test     word ptr [rip + 0x349f7d], cx
00254C6B  je       0x14025512f
00254C71  movzx    ecx, byte ptr [rip + 0x346388]
00254C78  lea      r8, [rsi + 0x3b0]
00254C7F  mov      eax, r10d
00254C82  mov      dword ptr [rsp + 0x20], 1
00254C8A  cdq      
00254C8B  idiv     ecx
00254C8D  movzx    ecx, byte ptr [rip + 0x34636d]
00254C94  mov      dword ptr [rbp - 0x39], eax
00254C97  mov      eax, r9d
00254C9A  cdq      
00254C9B  mov      r9b, 1
00254C9E  idiv     ecx
00254CA0  lea      rcx, [r15 + 0xa60]
00254CA7  lea      rdx, [rbp - 0x39]
00254CAB  mov      dword ptr [rbp - 0x35], eax
00254CAE  call     0x14024c9d0
00254CB3  cmp      al, byte ptr [rip + 0x346349]
00254CB9  je       0x14025512f
00254CBF  test     byte ptr [rsi + 0x78], 8
00254CC3  je       0x14025512f
00254CC9  cmp      dword ptr [rsi + 0x90], 1
00254CD0  jle      0x140254ce0
00254CD2  mov      edx, dword ptr [rsi + 0x3ac]
00254CD8  mov      rcx, rsi
00254CDB  call     0x1402551f0
00254CE0  mov      ecx, dword ptr [r15 + 0x688]
00254CE7  lea      r8, [rbp - 0x49]
00254CEB  mov      edx, dword ptr [r15 + 0x68c]
00254CF2  mov      eax, dword ptr [r15 + 0x648]
00254CF9  sub      eax, dword ptr [r15 + 0x640]
00254D00  add      eax, ecx
00254D02  mov      dword ptr [rbp - 0x11], ecx
00254D05  mov      dword ptr [rbp - 0x15], eax
00254D08  mov      rcx, rsi
00254D0B  mov      eax, dword ptr [r15 + 0x64c]
00254D12  sub      eax, dword ptr [r15 + 0x644]
00254D19  add      eax, edx
00254D1B  mov      dword ptr [rbp - 9], edx
00254D1E  lea      rdx, [rbp + 0xf]
00254D22  mov      dword ptr [rbp - 0xd], eax
00254D25  call     0x140253cd0
00254D2A  mov      edx, dword ptr [rbx]
00254D2C  mov      r11d, dword ptr [rsi + 0x14]
00254D30  mov      dword ptr [rbp - 0x41], edx
00254D33  mov      dword ptr [rbp - 0x29], r11d
00254D37  test     r12d, r12d
00254D3A  jne      0x140254d48
00254D3C  test     edi, edi
00254D3E  jne      0x140254d48
00254D40  mov      ecx, dword ptr [rsi + 0x10]
00254D43  sub      ecx, r11d
00254D46  jmp      0x140254d4e
00254D48  mov      ecx, dword ptr [rsi + 0x10]
00254D4B  mov      edi, r11d
00254D4E  test     byte ptr [rsi + 0x78], 4
00254D52  mov      dword ptr [rbp - 0x2d], edi
00254D55  mov      dword ptr [rbp - 0x3d], ecx
00254D58  je       0x140254d81
00254D5A  mov      rax, qword ptr [rsi]
00254D5D  mov      rcx, rsi
00254D60  call     qword ptr [rax + 0x40]
00254D63  mov      rdx, rbx
00254D66  mov      rcx, r15
00254D69  movzx    r8d, al
00254D6D  call     0x140180c10
00254D72  mov      ecx, dword ptr [rbp - 0x3d]
00254D75  mov      edx, dword ptr [rbp - 0x41]
00254D78  add      ecx, eax
00254D7A  mov      r11d, dword ptr [rbp - 0x29]
00254D7E  mov      dword ptr [rbp - 0x3d], ecx
00254D81  mov      r10d, dword ptr [rbp + 0x17]
00254D85  movzx    ebx, byte ptr [rip + 0x358107]
00254D8C  test     r13d, r13d
00254D8F  je       0x140254dac
00254D91  movzx    eax, bl
00254D94  cmp      dword ptr [rsi + 0x94], eax
00254D9A  jle      0x140254dac
00254D9C  mov      r13d, dword ptr [rbp + 0xf]
00254DA0  sub      r13d, r10d
00254DA3  add      r13d, dword ptr [rbp - 0x49]
00254DA7  add      r13d, edx
00254DAA  jmp      0x140254db3
00254DAC  mov      r13d, edx
00254DAF  sub      r13d, dword ptr [rbp - 0x49]
00254DB3  cmp      dword ptr [rbp - 0x21], 0
00254DB7  mov      r8d, dword ptr [rbp + 0x1b]
00254DBB  mov      r9d, dword ptr [rbp + 0x13]
00254DBF  je       0x140254e18
00254DC1  movzx    eax, byte ptr [rip + 0x3580c7]
00254DC8  mov      edx, dword ptr [rsi + 0x94]
00254DCE  cmp      edx, eax
00254DD0  jle      0x140254e18
00254DD2  movzx    eax, byte ptr [rip + 0x3580be]
00254DD9  cmp      edx, eax
00254DDB  jge      0x140254e18
00254DDD  test     r12d, r12d
00254DE0  jne      0x140254dfc
00254DE2  cmp      dword ptr [rbp - 0x19], r12d
00254DE6  jne      0x140254dfc
00254DE8  mov      r12d, r9d
00254DEB  sub      r12d, r8d
00254DEE  add      r12d, dword ptr [rbp - 0x45]
00254DF2  add      r12d, ecx
00254DF5  neg      edi
00254DF7  mov      dword ptr [rbp - 0x2d], edi
00254DFA  jmp      0x140254e1f
00254DFC  mov      eax, r8d
00254DFF  mov      r12d, ecx
00254E02  sub      eax, r9d
00254E05  sub      eax, dword ptr [rbp - 0x45]
00254E08  sub      r12d, eax
00254E0B  mov      dword ptr [rbp - 0x45], eax
00254E0E  sub      r12d, r11d
00254E11  neg      edi
00254E13  mov      dword ptr [rbp - 0x2d], edi
00254E16  jmp      0x140254e1f
00254E18  mov      r12d, ecx
00254E1B  sub      r12d, dword ptr [rbp - 0x45]
00254E1F  sub      r10d, dword ptr [rbp + 0xf]
00254E23  sub      r8d, r9d
00254E26  lea      ecx, [r10 + r13]
00254E2A  lea      eax, [r8 + r12]
00254E2E  mov      dword ptr [rbp - 0x29], ecx
00254E31  mov      dword ptr [rbp - 0x39], eax
00254E34  cmp      r13d, dword ptr [rbp - 0x15]
00254E38  jge      0x14025512f
00254E3E  cmp      ecx, dword ptr [rbp - 0x11]
00254E41  jl       0x14025512f
00254E47  cmp      r12d, dword ptr [rbp - 0xd]
00254E4B  jge      0x14025512f
00254E51  cmp      eax, dword ptr [rbp - 9]
00254E54  jl       0x14025512f
00254E5A  cmp      dword ptr [rbp - 0x1d], 0
00254E5E  jne      0x140254e69
00254E60  mov      r9d, dword ptr [rbp - 0x25]
00254E64  test     r9d, r9d
00254E67  je       0x140254e95
00254E69  mov      rax, qword ptr [rsi]
00254E6C  mov      rcx, rsi
00254E6F  call     qword ptr [rax + 0x40]
00254E72  lea      rdx, [rbp - 0x41]
00254E76  mov      rcx, r15
00254E79  movzx    r8d, al
00254E7D  call     0x140182ed0
00254E82  mov      r9d, dword ptr [rbp - 0x25]
00254E86  mov      r8d, eax
00254E89  movzx    ebx, byte ptr [rip + 0x358003]
00254E90  mov      dword ptr [rbp - 0x31], eax
00254E93  jmp      0x140254e99
00254E95  mov      r8d, dword ptr [rbp - 0x31]
00254E99  mov      edx, dword ptr [rsi + 0x94]
00254E9F  movzx    ecx, bl
00254EA2  cmp      edx, ecx
00254EA4  jle      0x140254eb3
00254EA6  cmp      dword ptr [rbp - 1], 0
00254EAA  je       0x140254eb3
00254EAC  or       r14d, dword ptr [rip + 0x34d499]
00254EB3  movzx    eax, byte ptr [rip + 0x357fd5]
00254EBA  cmp      edx, eax
00254EBC  jle      0x140254ed6
00254EBE  movzx    eax, byte ptr [rip + 0x357fd2]
00254EC5  cmp      edx, eax
00254EC7  jge      0x140254ed6
00254EC9  cmp      dword ptr [rbp - 0x21], 0
00254ECD  je       0x140254ed6
00254ECF  or       r14d, dword ptr [rip + 0x34d47a]
00254ED6  add      r15, 0x5c8
00254EDD  test     r9d, r9d
00254EE0  je       0x140254f2f
00254EE2  movzx    ecx, byte ptr [rsi + 0xb0]
00254EE9  lea      r9, [rbp - 0x49]
00254EED  mov      rax, qword ptr [rsi + 0xa8]
00254EF4  mov      edx, ecx
00254EF6  mov      qword ptr [rbp - 1], rax
00254EFA  mov      eax, ecx
00254EFC  shl      edx, 8
00254EFF  shl      eax, 0x10
00254F02  or       edx, eax
00254F04  mov      dword ptr [rsp + 0x38], r14d
00254F09  or       edx, ecx
00254F0B  mov      dword ptr [rsp + 0x30], r8d
00254F10  mov      dword ptr [rsp + 0x28], edx
00254F14  lea      rax, [rbp - 1]
00254F18  lea      rdx, [rbp + 0xf]
00254F1C  mov      qword ptr [rsp + 0x20], rax
00254F21  lea      r8, [rbp - 0x41]
00254F25  mov      rcx, r15
00254F28  call     0x1402a4090
00254F2D  jmp      0x140254f61
00254F2F  or       r14d, dword ptr [rip + 0x34d40e]
00254F36  lea      rax, [rbp - 0x49]
00254F3A  mov      r8d, r14d
00254F3D  mov      qword ptr [rsp + 0x20], rax
00254F42  lea      r9, [rbp - 0x41]
00254F46  mov      rcx, r15
00254F49  lea      rdx, [rbp + 0xf]
00254F4D  call     0x14029e1b0
00254F52  mov      r8d, r14d
00254F55  lea      rdx, [rbp + 0xf]
00254F59  mov      rcx, r15
00254F5C  call     0x14029e190
00254F61  test     eax, eax
00254F63  je       0x14025512f
00254F69  cmp      dword ptr [rbp - 0x1d], 0
00254F6D  je       0x140254f82
00254F6F  mov      rcx, qword ptr [rsi + 0x248]
00254F76  mov      edx, dword ptr [rbp - 0x31]
00254F79  add      rcx, 8
00254F7D  call     0x140412690
00254F82  cmp      dword ptr [rbp - 0x19], 0
00254F86  je       0x140254fac
00254F88  mov      r9d, dword ptr [rbp - 0x45]
00254F8C  mov      rcx, r15
00254F8F  mov      r8d, dword ptr [rbp - 0x49]
00254F93  mov      rdx, qword ptr [rsi + 0x250]
00254F9A  mov      dword ptr [rsp + 0x28], 0
00254FA2  mov      dword ptr [rsp + 0x20], r14d
00254FA7  call     0x14029e260
00254FAC  test     byte ptr [rsi + 0x78], 0x10
00254FB0  je       0x140254ff4
00254FB2  mov      rcx, qword ptr [rsi + 0x388]
00254FB9  call     0x1403f6d50
00254FBE  mov      rbx, qword ptr [rsi + 0x388]
00254FC5  mov      rcx, rbx
00254FC8  call     0x1403f7890
00254FCD  mov      rcx, rbx
00254FD0  mov      edi, eax
00254FD2  call     0x1403f78b0
00254FD7  movzx    r9d, word ptr [rip + 0x36b699]
00254FDF  mov      rdx, rax
00254FE2  mov      rcx, qword ptr [rsi + 0x248]
00254FE9  mov      r8d, edi
00254FEC  call     0x1404123c0
00254FF1  mov      edi, dword ptr [rbp - 0x2d]
00254FF4  mov      r9d, dword ptr [rbp - 0x45]
00254FF8  mov      rcx, r15
00254FFB  mov      r8d, dword ptr [rbp - 0x49]
00254FFF  sub      r9d, edi
00255002  mov      rdx, qword ptr [rsi + 0x248]
00255009  mov      dword ptr [rsp + 0x28], 0x80
00255011  mov      dword ptr [rsp + 0x20], r14d
00255016  call     0x14029e260
0025501B  mov      rdx, qword ptr [rsi + 0x3e0]
00255022  test     rdx, rdx
00255025  je       0x140255047
00255027  mov      r9d, dword ptr [rbp - 0x45]
0025502B  mov      rcx, r15
0025502E  mov      r8d, dword ptr [rbp - 0x49]
00255032  sub      r9d, edi
00255035  mov      dword ptr [rsp + 0x28], 0x80
0025503D  mov      dword ptr [rsp + 0x20], r14d
00255042  call     0x14029e4a0
00255047  test     byte ptr [rsi + 0x78], 0x40
0025504B  jne      0x14025509d
0025504D  mov      ecx, dword ptr [rsi + 0x14]
00255050  mov      r9d, ecx
00255053  mov      r8d, dword ptr [rbp - 0x3d]
00255057  neg      r9d
0025505A  mov      edx, dword ptr [rbp - 0x41]
0025505D  add      r8d, ecx
00255060  mov      dword ptr [rsp + 0x38], r14d
00255065  lea      eax, [rcx + r12]
00255069  mov      byte ptr [rsp + 0x30], 0
0025506E  mov      dword ptr [rbp + 3], eax
00255071  mov      eax, dword ptr [rbp - 0x29]
00255074  mov      dword ptr [rbp + 7], eax
00255077  mov      eax, dword ptr [rbp - 0x39]
0025507A  add      eax, ecx
0025507C  mov      dword ptr [rbp - 1], r13d
00255080  mov      dword ptr [rbp + 0xb], eax
00255083  mov      rcx, r15
00255086  lea      rax, [rbp - 1]
0025508A  mov      qword ptr [rsp + 0x28], rax
0025508F  lea      rax, [rbp - 0x49]
00255093  mov      qword ptr [rsp + 0x20], rax
00255098  call     0x14029e4c0
0025509D  xor      eax, eax
0025509F  lea      r9, [rbp - 0x39]
002550A3  xor      r8d, r8d
002550A6  mov      qword ptr [rbp - 0x39], rax
002550AA  mov      edx, r14d
002550AD  mov      rcx, r15
002550B0  call     0x14029ea40
002550B5  mov      eax, dword ptr [rbp - 0x45]
002550B8  lea      rdx, [rbp + 0xf]
002550BC  mov      r9d, dword ptr [rbp - 0x3d]
002550C0  mov      rcx, r15
002550C3  mov      r8d, dword ptr [rbp - 0x41]
002550C7  mov      dword ptr [rsp + 0x30], r14d
002550CC  mov      dword ptr [rsp + 0x28], eax
002550D0  mov      eax, dword ptr [rbp - 0x49]
002550D3  mov      dword ptr [rsp + 0x20], eax
002550D7  call     0x14029df60
002550DC  jmp      0x14025512f
002550DE  mov      rcx, qword ptr [rsi + 0x248]
002550E5  lea      rdx, [rbp - 1]
002550E9  mov      rax, qword ptr [rip + 0x407a20]
002550F0  add      rcx, 0x110
002550F7  mov      qword ptr [rbp - 0x39], rax
002550FB  call     0x1403fff70
00255100  mov      ecx, dword ptr [rsi + 0x10]
00255103  lea      rdx, [rip + 0x349a86]
0025510A  mov      r9d, dword ptr [rbx]
0025510D  mov      dword ptr [rsp + 0x20], ecx
00255111  lea      rcx, [rbp - 0x39]
00255115  mov      r8, qword ptr [rax]
00255118  call     0x1403fe9c0
0025511D  lea      rcx, [rbp - 1]
00255121  call     0x1403fd740
00255126  lea      rcx, [rbp - 0x39]
0025512A  call     0x1403fd740
0025512F  mov      r13, qword ptr [rsp + 0xb8]
00255137  mov      r12, qword ptr [rsp + 0xc0]
0025513F  mov      rdi, qword ptr [rsp + 0xc8]
00255147  mov      rbx, qword ptr [rsp + 0x100]
0025514F  mov      r14, qword ptr [rsp + 0xb0]
00255157  mov      rcx, qword ptr [rbp + 0x1f]
0025515B  xor      rcx, rsp
0025515E  call     0x1404f77a0
00255163  add      rsp, 0xd0
0025516A  pop      r15
0025516C  pop      rsi
0025516D  pop      rbp
0025516E  ret      
0025516F  int3     
00255170  push     rbx
00255172  sub      rsp, 0x20
00255176  mov      eax, dword ptr [rcx + 0x98]
0025517C  mov      r10, r8
0025517F  mov      rbx, rcx
00255182  test     al, 1
00255184  je       0x1402551a9
00255186  movzx    r8d, word ptr [rbx + 0x94]
0025518E  add      rcx, 0xc
00255192  mov      rdx, r9
00255195  call     0x140254740
0025519A  movsx    edx, ax
0025519D  mov      dword ptr [rbx + 0x3ac], edx
002551A3  add      rsp, 0x20
002551A7  pop      rbx
002551A8  ret      
002551A9  test     al, 2
002551AB  je       0x1402551be
002551AD  movsx    eax, word ptr [rsp + 0x50]
002551B2  mov      dword ptr [rcx + 0x3ac], eax
002551B8  add      rsp, 0x20
002551BC  pop      rbx
002551BD  ret      
002551BE  test     al, 8
002551C0  jne      0x1402551db
002551C2  movzx    r8d, word ptr [rcx + 0x94]
002551CA  mov      rcx, r10
002551CD  call     0x140254740
002551D2  movsx    ecx, ax
002551D5  mov      dword ptr [rbx + 0x3ac], ecx
002551DB  add      rsp, 0x20
002551DF  pop      rbx
002551E0  ret      
002551E1  int3     
002551E2  int3     
002551E3  int3     
002551E4  int3     
002551E5  int3     
002551E6  int3     
002551E7  int3     
002551E8  int3     
002551E9  int3     
002551EA  int3     
002551EB  int3     
002551EC  int3     
002551ED  int3     
002551EE  int3     
002551EF  int3     
