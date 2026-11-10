00341860 mov      qword ptr [rsp + 0x18], rbx
00341865 push     rbp
00341866 push     rsi
00341867 push     rdi
00341868 push     r12
0034186A push     r13
0034186C push     r14
0034186E push     r15
00341870 lea      rbp, [rsp - 7]
00341875 sub      rsp, 0x100
0034187C mov      rax, qword ptr [rip + 0x323155]
00341883 xor      rax, rsp
00341886 mov      qword ptr [rbp - 1], rax
0034188A xor      eax, eax
0034188C mov      word ptr [rsp + 0x50], r9w
00341892 mov      dword ptr [rsp + 0x78], eax
00341896 mov      rsi, rcx
00341899 mov      dword ptr [rbp - 0x79], eax
0034189C mov      dword ptr [rsp + 0x70], r8d
003418A1 mov      qword ptr [rbp - 0x31], rdx
003418A5 call     0x140154160
003418AA lea      rax, [rip + 0x2572b7]
003418B1 lea      rcx, [rsi + 0x540]
003418B8 mov      qword ptr [rsi], rax
003418BB call     0x1403ff870
003418C0 lea      rcx, [rsi + 0x560]
003418C7 xor      edx, edx
003418C9 mov      r8d, 0x268
003418CF call     0x1404fab70
003418D4 mov      r14d, 7
003418DA lea      rbx, [rsi + 0x7c8]
003418E1 mov      edi, r14d
003418E4 lea      r12, [rip + 0x24b46d]
003418EB nop      dword ptr [rax + rax]
003418F0 mov      edx, 0xa
003418F5 mov      rcx, rbx
003418F8 call     0x1404073a0
003418FD mov      qword ptr [rbx], r12
00341900 add      rbx, 0x38
00341904 sub      rdi, 1
00341908 jne      0x1403418f0
0034190A mov      edi, 9
0034190F lea      rbx, [rsi + 0x950]
00341916 mov      r15d, edi
00341919 nop      dword ptr [rax]
00341920 mov      edx, 0xa
00341925 mov      rcx, rbx
00341928 call     0x1404073a0
0034192D mov      qword ptr [rbx], r12
00341930 add      rbx, 0x38
00341934 sub      r15, 1
00341938 jne      0x140341920
0034193A lea      edx, [r15 + 0xa]
0034193E lea      rcx, [rsi + 0xb48]
00341945 call     0x1404073a0
0034194A mov      qword ptr [rsi + 0xb48], r12
00341951 lea      rbx, [rsi + 0xc08]
00341958 lea      r15, [rip + 0x24b3f9]
0034195F nop      
00341960 mov      edx, 0xa
00341965 mov      rcx, rbx
00341968 call     0x1404073a0
0034196D mov      qword ptr [rbx], r15
00341970 add      rbx, 0x38
00341974 sub      r14, 1
00341978 jne      0x140341960
0034197A lea      rbx, [rsi + 0xd90]
00341981 mov      edx, 0xa
00341986 mov      rcx, rbx
00341989 call     0x1404073a0
0034198E mov      qword ptr [rbx], r15
00341991 add      rbx, 0x38
00341995 sub      rdi, 1
00341999 jne      0x140341981
0034199B lea      edx, [rdi + 0xa]
0034199E lea      rcx, [rsi + 0xf88]
003419A5 call     0x1404073a0
003419AA xor      edx, edx
003419AC mov      qword ptr [rsi + 0xf88], r15
003419B3 mov      r8d, 0x138
003419B9 lea      rcx, [rsi + 0xfc0]
003419C0 call     0x1404fab70
003419C5 xor      r14d, r14d
003419C8 mov      byte ptr [rsi + 0x10f8], 0xa
003419CF lea      rcx, [rsi + 0x1120]
003419D6 mov      word ptr [rsi + 0x10fa], r14w
003419DE mov      qword ptr [rsi + 0x1100], r14
003419E5 call     0x14014ec10
003419EA lea      rcx, [rsi + 0x1dc8]
003419F1 call     0x14014ec10
003419F6 lea      rcx, [rsi + 0x2a70]
003419FD call     0x14014ec10
00341A02 lea      rcx, [rsi + 0x3718]
00341A09 call     0x1403416a0
00341A0E mov      rax, qword ptr [rip + 0x31b0fb]
00341A15 lea      rcx, [rsi + 0x3938]
00341A1C mov      qword ptr [rsi + 0x3928], rax
00341A23 call     0x1401f3030
00341A28 lea      rcx, [rsi + 0x3a20]
00341A2F call     0x1403ff870
00341A34 lea      r15, [rsi + 0x3a30]
00341A3B mov      r12d, 2
00341A41 mov      rbx, r15
00341A44 mov      edi, r12d
00341A47 mov      rcx, rbx
00341A4A call     0x14040d580
00341A4F add      rbx, 0x20
00341A53 sub      rdi, 1
00341A57 jne      0x140341a47
00341A59 lea      rbx, [rsi + 0x3a78]
00341A60 mov      rdi, r12
00341A63 mov      rcx, rbx
00341A66 call     0x14040d580
00341A6B add      rbx, 0x20
00341A6F sub      rdi, 1
00341A73 jne      0x140341a63
00341A75 lea      rcx, [rsi + 0x3ac0]
00341A7C call     0x14040d580
00341A81 lea      rcx, [rsi + 0x3ae0]
00341A88 call     0x14040d580
00341A8D lea      rcx, [rsi + 0x3b00]
00341A94 call     0x14040d580
00341A99 lea      rcx, [rsi + 0x3b20]
00341AA0 call     0x14040d580
00341AA5 lea      rcx, [rsi + 0x3b40]
00341AAC call     0x14040d580
00341AB1 lea      rcx, [rsi + 0x3b68]
00341AB8 call     0x1403ff870
00341ABD mov      ecx, 0xffffffff
00341AC2 xor      r9d, r9d
00341AC5 mov      dword ptr [rsp + 0x40], ecx
00341AC9 xor      r8d, r8d
00341ACC mov      byte ptr [rsp + 0x38], r14b
00341AD1 lea      rcx, [rsi + 0x3bd8]
00341AD8 mov      byte ptr [rsp + 0x30], r14b
00341ADD xor      edx, edx
00341ADF mov      byte ptr [rsp + 0x28], r14b
00341AE4 mov      byte ptr [rsp + 0x20], r14b
00341AE9 call     0x14011ba20
00341AEE lea      rcx, [rsi + 0x3c70]
00341AF5 mov      qword ptr [rsi + 0x3c40], r14
00341AFC mov      word ptr [rsi + 0x3c4c], r14w
00341B04 mov      dword ptr [rsi + 0x3c48], r14d
00341B0B call     0x140410f70
00341B10 movzx    edx, word ptr [rip + 0x27eb65]
00341B17 lea      rcx, [rsi + 0x3da8]
00341B1E call     0x140421010
00341B23 lea      rcx, [rsi + 0x3de0]
00341B2A call     0x140410f70
00341B2F movzx    edx, word ptr [rip + 0x27eb46]
00341B36 lea      rcx, [rsi + 0x3f18]
00341B3D call     0x140421010
00341B42 lea      rcx, [rsi + 0x3f78]
00341B49 call     0x140410f70
00341B4E lea      rcx, [rsi + 0x40b8]
00341B55 call     0x140410f70
00341B5A lea      rcx, [rsi + 0x41f8]
00341B61 call     0x140410f70
00341B66 lea      rcx, [rsi + 0x4338]
00341B6D call     0x140410f70
00341B72 lea      rcx, [rsi + 0x4478]
00341B79 call     0x140410f70
00341B7E lea      rcx, [rsi + 0x45b8]
00341B85 call     0x140410f70
00341B8A lea      edx, [rdi + 0xa]
00341B8D lea      rcx, [rsi + 0x4768]
00341B94 call     0x1404073a0
00341B99 lea      rdi, [rip + 0x24b1b8]
00341BA0 mov      edx, 0xa
00341BA5 lea      rcx, [rsi + 0x47a0]
00341BAC mov      qword ptr [rsi + 0x4768], rdi
00341BB3 call     0x1404073a0
00341BB8 lea      rcx, [rsi + 0x4808]
00341BBF mov      qword ptr [rsi + 0x47a0], rdi
00341BC6 call     0x140410d80
00341BCB mov      edx, 0xa
00341BD0 lea      rcx, [rsi + 0x4958]
00341BD7 call     0x1404073a0
00341BDC lea      rax, [rip + 0x24b175]
00341BE3 mov      edx, 0xa
00341BE8 lea      rcx, [rsi + 0x49b0]
00341BEF mov      qword ptr [rsi + 0x4958], rax
00341BF6 call     0x1404073a0
00341BFB lea      rdi, [rip + 0x256e36]
00341C02 mov      qword ptr [rsi + 0x49e8], r14
00341C09 mov      edx, 0xa
00341C0E mov      qword ptr [rsi + 0x49b0], rdi
00341C15 lea      rcx, [rsi + 0x4a00]
00341C1C mov      qword ptr [rsi + 0x49f0], r14
00341C23 mov      qword ptr [rsi + 0x49f8], r14
00341C2A call     0x1404073a0
00341C2F mov      edx, 0xa
00341C34 mov      qword ptr [rsi + 0x4a00], rdi
00341C3B lea      rcx, [rsi + 0x4a50]
00341C42 mov      qword ptr [rsi + 0x4a38], r14
00341C49 mov      qword ptr [rsi + 0x4a40], r14
00341C50 mov      qword ptr [rsi + 0x4a48], r14
00341C57 call     0x1404073a0
00341C5C lea      rax, [rip + 0x24b0f5]
00341C63 lea      rcx, [rsi + 0x4a88]
00341C6A mov      qword ptr [rsi + 0x4a50], rax
00341C71 call     0x1404237a0
00341C76 lea      rax, [rip + 0x24f533]
00341C7D mov      ebx, 0xffffffff
00341C82 mov      dword ptr [rsp + 0x40], ebx
00341C86 lea      rcx, [rsi + 0x4b50]
00341C8D mov      byte ptr [rsp + 0x38], r14b
00341C92 xor      r9d, r9d
00341C95 mov      byte ptr [rsp + 0x30], r14b
00341C9A xor      r8d, r8d
00341C9D mov      byte ptr [rsp + 0x28], r14b
00341CA2 xor      edx, edx
00341CA4 mov      byte ptr [rsp + 0x20], r14b
00341CA9 mov      qword ptr [rsi + 0x4a88], rax
00341CB0 call     0x14011ba20
00341CB5 mov      dword ptr [rsp + 0x40], ebx
00341CB9 lea      rcx, [rsi + 0x4b68]
00341CC0 mov      byte ptr [rsp + 0x38], r14b
00341CC5 xor      r9d, r9d
00341CC8 mov      byte ptr [rsp + 0x30], r14b
00341CCD xor      r8d, r8d
00341CD0 mov      byte ptr [rsp + 0x28], r14b
00341CD5 xor      edx, edx
00341CD7 mov      byte ptr [rsp + 0x20], r14b
00341CDC call     0x14011ba20
00341CE1 lea      rcx, [rsi + 0x4bc8]
00341CE8 call     0x1403c1530
00341CED lea      rcx, [rsi + 0x4bf4]
00341CF4 call     0x1403c1530
00341CF9 lea      rcx, [rsi + 0x4c30]
00341D00 call     0x140164c50
00341D05 lea      rcx, [rsi + 0x4c64]
00341D0C call     0x1403ff870
00341D11 lea      rcx, [rsi + 0x4c6c]
00341D18 call     0x1403ff870
00341D1D lea      edx, [rbx + 0xb]
00341D20 lea      rcx, [rsi + 0x4cc0]
00341D27 call     0x1404073a0
00341D2C lea      rax, [rip + 0x24b025]
00341D33 lea      rdx, [rip + 0x26b506]
00341D3A mov      qword ptr [rsi + 0x4cc0], rax
00341D41 lea      rcx, [rsp + 0x68]
00341D46 call     0x1403ff7c0
00341D4B lea      rcx, [rsi + 0x4cf8]
00341D52 mov      rdx, qword ptr [rax]
00341D55 call     0x140410e10
00341D5A lea      rcx, [rsi + 0x4e68]
00341D61 call     0x1403ff870
00341D66 lea      edx, [rbx + 0xb]
00341D69 lea      rcx, [rsi + 0x4ec8]
00341D70 call     0x1404073a0
00341D75 lea      rax, [rip + 0x256de4]
00341D7C lea      rdi, [rsi + 0x4f28]
00341D83 mov      qword ptr [rsi + 0x4ec8], rax
00341D8A mov      rcx, rdi
00341D8D call     0x1403ff870
00341D92 lea      rcx, [rdi + 8]
00341D96 call     0x1404237a0
00341D9B lea      r14, [rip + 0x24f40e]
00341DA2 lea      rcx, [rdi + 0x28]
00341DA6 mov      qword ptr [rdi + 8], r14
00341DAA call     0x1404237a0
00341DAF mov      qword ptr [rdi + 0x28], r14
00341DB3 mov      rcx, rdi
00341DB6 mov      rax, qword ptr [rip + 0x31ad53]
00341DBD mov      qword ptr [rdi + 0x60], rax
00341DC1 call     0x140195f00
00341DC6 lea      rdi, [rsi + 0x4fb0]
00341DCD mov      rcx, rdi
00341DD0 call     0x1403ff870
00341DD5 lea      rcx, [rdi + 8]
00341DD9 call     0x1404237a0
00341DDE lea      rcx, [rdi + 0x28]
00341DE2 mov      qword ptr [rdi + 8], r14
00341DE6 call     0x1404237a0
00341DEB mov      qword ptr [rdi + 0x28], r14
00341DEF mov      rax, qword ptr [rip + 0x31ad1a]
00341DF6 mov      qword ptr [rdi + 0x60], rax
00341DFA mov      rcx, rdi
00341DFD call     0x140195f00
00341E02 mov      rax, qword ptr [rip + 0x31ad07]
00341E09 lea      rcx, [rsi + 0x5070]
00341E10 mov      qword ptr [rsi + 0x5048], rax
00341E17 xor      edx, edx
00341E19 mov      rax, qword ptr [rip + 0x31acf0]
00341E20 mov      r8d, 0x90
00341E26 mov      qword ptr [rsi + 0x5050], rax
00341E2D mov      rax, qword ptr [rip + 0x31acdc]
00341E34 mov      qword ptr [rsi + 0x5058], rax
00341E3B mov      rax, qword ptr [rip + 0x31acce]
00341E42 mov      qword ptr [rsi + 0x5060], rax
00341E49 call     0x1404fab70
00341E4E lea      rcx, [rsi + 0x5100]
00341E55 xor      edx, edx
00341E57 lea      r8d, [rbx + 0x71]
00341E5B call     0x1404fab70
00341E60 lea      edx, [rbx + 0xb]
00341E63 lea      rcx, [rsi + 0x5180]
00341E6A call     0x1404073a0
00341E6F lea      rax, [rip + 0x24aee2]
00341E76 lea      edx, [rbx + 0xb]
00341E79 mov      qword ptr [rsi + 0x5180], rax
00341E80 lea      rcx, [rsi + 0x51b8]
00341E87 call     0x1404073a0
00341E8C lea      rax, [rip + 0x24aec5]
00341E93 lea      edx, [rbx + 0xb]
00341E96 mov      qword ptr [rsi + 0x51b8], rax
00341E9D lea      rcx, [rsi + 0x5218]
00341EA4 call     0x1404073a0
00341EA9 lea      rax, [rip + 0x24aea8]
00341EB0 lea      rcx, [rsi + 0x5258]
00341EB7 mov      qword ptr [rsi + 0x5218], rax
00341EBE call     0x140343810
00341EC3 lea      edx, [rbx + 0xb]
00341EC6 lea      rcx, [rsi + 0x5340]
00341ECD call     0x1404073a0
00341ED2 xor      ebx, ebx
00341ED4 lea      rax, [rip + 0x24ae7d]
00341EDB mov      qword ptr [rsi + 0x5340], rax
00341EE2 mov      ecx, 0xfa8
00341EE7 mov      dword ptr [rsi + 0x52e8], ebx
00341EED mov      qword ptr [rsi + 0x5308], rbx
00341EF4 mov      dword ptr [rsi + 0x5310], ebx
00341EFA mov      dword ptr [rsi + 0x4ad4], ebx
00341F00 mov      byte ptr [rsi + 0x5314], 0x2a
00341F07 mov      qword ptr [rsi + 0x5318], rbx
00341F0E mov      qword ptr [rsi + 0x5320], rbx
00341F15 mov      dword ptr [rsi + 0x4ab4], ebx
00341F1B mov      dword ptr [rsi + 0x4f10], ebx
00341F21 call     0x1404f77c4
00341F26 test     rax, rax
00341F29 je       0x140341f5f
00341F2B mov      edi, 0x64
00341F30 lea      r14, [rax + 8]
00341F34 mov      qword ptr [rax], rdi
00341F37 mov      rbx, r14
00341F3A nop      word ptr [rax + rax]
00341F40 mov      rax, qword ptr [rip + 0x31abc9]
00341F47 lea      rcx, [rbx + 8]
00341F4B mov      qword ptr [rbx], rax
00341F4E call     0x14040d580
00341F53 lea      rbx, [rbx + 0x28]
00341F57 sub      rdi, 1
00341F5B jne      0x140341f40
00341F5D jmp      0x140341f62
00341F5F mov      r14, rbx
00341F62 mov      qword ptr [rsi + 0x4c78], r14
00341F69 lea      r8, [rip + 0x2a983d]
00341F70 xor      r14d, r14d
00341F73 lea      rdx, [rsp + 0x68]
00341F78 mov      qword ptr [rsi + 0x5250], r14
00341F7F lea      rcx, [rsi + 0x540]
00341F86 mov      qword ptr [rsi + 0x52e0], r14
00341F8D mov      edi, 1
00341F92 mov      word ptr [rsi + 0x4e8c], r14w
00341F9A mov      ebx, 0xffffffff
00341F9F mov      dword ptr [rsi + 0x4b9c], r14d
00341FA6 mov      byte ptr [rsi + 0x3f65], r14b
00341FAD mov      qword ptr [rsi + 0x49a4], r14
00341FB4 mov      qword ptr [rsi + 0x532c], r14
00341FBB mov      dword ptr [rsi + 0x4c4], r14d
00341FC2 mov      dword ptr [rsi + 0x5210], r14d
00341FC9 mov      byte ptr [rsi + 0x4cba], r14b
00341FD0 mov      byte ptr [rsi + 0x4762], r14b
00341FD7 mov      dword ptr [rsi + 0x5328], r14d
00341FDE mov      qword ptr [rsi + 0x5334], rdi
00341FE5 mov      dword ptr [rsi + 0x5214], ebx
00341FEB movzx    eax, byte ptr [rip + 0x25772d]
00341FF2 mov      byte ptr [rsi + 8], al
00341FF5 call     0x1403ff960
00341FFA movabs   rax, 0x3ff0000000000000
00342004 mov      qword ptr [rsp + 0x60], r14
00342009 mov      qword ptr [rsi + 0x46f8], rax
00342010 lea      rcx, [rsi + 0x3f8]
00342017 mov      eax, r14d
0034201A mov      qword ptr [rsp + 0x60], r14
0034201F mov      qword ptr [rsi + 0x4714], rax
00342026 lea      rdx, [rip + 0x325453]
0034202D mov      qword ptr [rsi + 0x471c], rax
00342034 mov      qword ptr [rsi + 0x4724], rax
0034203B mov      qword ptr [rsi + 0x472c], rax
00342042 mov      qword ptr [rsi + 0x4734], rax
00342049 mov      qword ptr [rsi + 0x473c], rax
00342050 movzx    eax, word ptr [rbp + 0x8f]
00342057 and      ax, 0xf
0034205B mov      qword ptr [rsp + 0x60], r14
00342060 mov      word ptr [rsi + 0x4754], ax
00342067 mov      word ptr [rsi + 0x4756], ax
0034206E mov      eax, 0x11
00342073 mov      qword ptr [rsp + 0x60], r14
00342078 mov      qword ptr [rsp + 0x60], r14
0034207D mov      word ptr [rsi + 0x499c], ax
00342084 mov      qword ptr [rsi + 0x46f0], r14
0034208B mov      byte ptr [rsi + 0x3a28], r14b
00342092 mov      dword ptr [rsi + 0x4e48], r14d
00342099 mov      qword ptr [rsp + 0x60], r14
0034209E mov      word ptr [rsi + 0x4710], bx
003420A5 mov      qword ptr [rsi + 0x4758], r14
003420AC mov      word ptr [rsi + 0x4760], r14w
003420B4 mov      word ptr [rsi + 0x47d8], r14w
003420BC mov      qword ptr [rsi + 0x47e8], r14
003420C3 mov      qword ptr [rsi + 0x47f0], r14
003420CA mov      byte ptr [rsi + 0x3930], r14b
003420D1 mov      dword ptr [rsi + 0x4bc0], r14d
003420D8 mov      dword ptr [rsi + 0x4cb4], r14d
003420DF mov      byte ptr [rsi + 0x4c74], r14b
003420E6 mov      qword ptr [rsi + 0x47dc], r14
003420ED mov      dword ptr [rsi + 0x49a0], r14d
003420F4 mov      dword ptr [rsi + 0x3e0], 0xffffffff
003420FE mov      word ptr [rsi + 0x3e4], bx
00342105 call     0x140116df0
0034210A mov      dword ptr [rsi + 0x3e8], r14d
00342111 lea      rcx, [rsi + 0x4bf4]
00342118 mov      dword ptr [rsi + 0x4b80], r14d
0034211F mov      dword ptr [rsi + 0x4ba0], r14d
00342126 mov      dword ptr [rsi + 0x47e4], 0x8000
00342130 mov      byte ptr [rsi + 0x4703], dil
00342137 mov      dword ptr [rsi + 0x51fc], r14d
0034213E mov      dword ptr [rsi + 0x4c20], ebx
00342144 mov      word ptr [rsi + 0x4c2c], r14w
0034214C mov      qword ptr [rsp + 0x60], 0xffffffffffffffff
00342155 mov      rax, qword ptr [rsp + 0x60]
0034215A mov      qword ptr [rsi + 0x4c24], rax
00342161 movzx    edx, byte ptr [rip + 0x26cc84]
00342168 call     0x1403c23a0
0034216D lea      rcx, [rsi + 0x30]
00342171 mov      dword ptr [rsi + 0x4f0c], ebx
00342177 lea      rdx, [rip + 0x31916a]
0034217E call     0x14011ea00
00342183 lea      rdx, [rip + 0x31915e]
0034218A lea      rcx, [rsi + 0x4b50]
00342191 call     0x14011ea00
00342196 lea      rdx, [rip + 0x31914b]
0034219D lea      rcx, [rsi + 0x4b68]
003421A4 call     0x14011ea00
003421A9 mov      dword ptr [rsi + 0x5170], r14d
003421B0 mov      eax, 0xfffffffe
003421B5 mov      qword ptr [rsi + 0x2f0], r14
003421BC mov      qword ptr [rsi + 0x2f8], r14
003421C3 mov      qword ptr [rsi + 0x300], r14
003421CA mov      qword ptr [rsi + 0x308], r14
003421D1 mov      qword ptr [rsi + 0x310], r14
003421D8 mov      qword ptr [rsi + 0x318], r14
003421DF mov      qword ptr [rsi + 0x320], r14
003421E6 mov      qword ptr [rsi + 0x4944], r14
003421ED mov      dword ptr [rsi + 0x494c], ebx
003421F3 mov      dword ptr [rsi + 0x4950], r14d
003421FA mov      word ptr [rsi + 0x4ab8], r14w
00342202 mov      dword ptr [rsi + 0x4b96], r14d
00342209 mov      qword ptr [rsi + 0x3a0], r14
00342210 mov      dword ptr [rsi + 0x480], r14d
00342217 mov      word ptr [rsi + 0x4b84], r14w
0034221F mov      dword ptr [rsi + 0x4b8c], r14d
00342226 mov      word ptr [rsi + 0x4b8a], r14w
0034222E mov      word ptr [rsi + 0x4990], bx
00342235 mov      dword ptr [rsi + 0x4994], r14d
0034223C mov      word ptr [rsi + 0x4b9a], ax
00342243 mov      dword ptr [rsi + 0x4bc4], r14d
0034224A mov      word ptr [rsi + 0x4ea2], r14w
00342252 mov      dword ptr [rsi + 0x4ea4], edi
00342258 mov      dword ptr [rsi + 0x4eac], r14d
0034225F mov      dword ptr [rsi + 0x5178], edi
00342265 mov      dword ptr [rsi + 0x4e88], r14d
0034226C mov      dword ptr [rsi + 0x4ac4], r14d
00342273 mov      qword ptr [rsi + 0x4bb4], r14
0034227A mov      dword ptr [rsi + 0x4bbc], r14d
00342281 mov      dword ptr [rsi + 0x520c], r14d
00342288 mov      byte ptr [rsi + 0x5038], r14b
0034228F mov      qword ptr [rsi + 0x4ac8], r14
00342296 mov      dword ptr [rsi + 0x4ad0], r14d
0034229D mov      dword ptr [rsi + 0x4ba4], r14d
003422A4 mov      qword ptr [rsi + 0x4ad8], r14
003422AB mov      qword ptr [rsi + 0x4ae0], r14
003422B2 mov      qword ptr [rsi + 0x4ae8], r14
003422B9 mov      qword ptr [rsi + 0x3b60], r14
003422C0 mov      qword ptr [rsi + 0x4c8c], r14
003422C7 mov      word ptr [rsi + 0x4c94], r14w
003422CF mov      qword ptr [rsi + 0x4c98], 0x7fff
003422DA mov      dword ptr [rsi + 0x3bd0], r14d
003422E1 mov      byte ptr [rsi + 0x4e5d], r14b
003422E8 mov      dword ptr [rsi + 0x4eb0], edi
003422EE mov      rax, qword ptr [rip + 0x325253]
003422F5 mov      rcx, qword ptr [rax + 0x1090]
003422FC mov      eax, dword ptr [rcx + 0x3fa0]
00342302 lea      rcx, [rbp - 0x69]
00342306 dec      eax
00342308 mov      dword ptr [rsi + 0x4e54], eax
0034230E mov      dword ptr [rsi + 0x3718], r14d
00342315 call     0x1403ff870
0034231A lea      rcx, [rbp - 0x5d]
0034231E call     0x1403ff870
00342323 lea      rcx, [rbp - 0x4d]
00342327 call     0x140164be0
0034232C lea      r8, [rip + 0x2a947a]
00342333 lea      rdx, [rsp + 0x68]
00342338 lea      rcx, [rbp - 0x5d]
0034233C call     0x1403ff960
00342341 mov      r8, rax
00342344 lea      rdx, [rsp + 0x60]
00342349 lea      rcx, [rbp - 0x69]
0034234D call     0x1403ff880
00342352 mov      dword ptr [rbp - 0x55], 0xffffffff
00342359 lea      rbx, [rsi + 0x373c]
00342360 mov      dword ptr [rbp - 0x61], 0xffffffff
00342367 lea      edi, [r14 + 4]
0034236B mov      word ptr [rbp - 0x51], r14w
00342370 mov      word ptr [rbp - 0x39], 0x100
00342376 nop      word ptr [rax + rax]
00342380 lea      rcx, [rbx - 0x20]
00342384 lea      r8, [rbp - 0x69]
00342388 lea      rdx, [rsp + 0x68]
0034238D call     0x1403ff880
00342392 mov      eax, dword ptr [rbp - 0x61]
00342395 lea      rcx, [rbx - 0x14]
00342399 lea      r8, [rbp - 0x5d]
0034239D mov      dword ptr [rbx - 0x18], eax
003423A0 lea      rdx, [rsp + 0x60]
003423A5 call     0x1403ff880
003423AA mov      eax, dword ptr [rbp - 0x55]
003423AD lea      rcx, [rbx + 2]
003423B1 mov      dword ptr [rbx - 0xc], eax
003423B4 lea      r8, [rbp - 0x47]
003423B8 movzx    eax, word ptr [rbp - 0x51]
003423BC lea      rdx, [rbp - 0x71]
003423C0 mov      word ptr [rbx - 8], ax
003423C4 movzx    eax, word ptr [rbp - 0x4d]
003423C8 mov      word ptr [rbx - 4], ax
003423CC movzx    eax, word ptr [rbp - 0x4b]
003423D0 mov      word ptr [rbx - 2], ax
003423D4 movzx    eax, word ptr [rbp - 0x49]
003423D8 mov      word ptr [rbx], ax
003423DB call     0x1403ff880
003423E0 movzx    eax, byte ptr [rbp - 0x3f]
003423E4 mov      byte ptr [rbx + 0xa], al
003423E7 lea      rbx, [rbx + 0x34]
003423EB movzx    eax, byte ptr [rbp - 0x3e]
003423EF mov      byte ptr [rbx - 0x29], al
003423F2 mov      eax, dword ptr [rbp - 0x3d]
003423F5 mov      dword ptr [rbx - 0x28], eax
003423F8 movzx    eax, byte ptr [rbp - 0x39]
003423FC mov      byte ptr [rbx - 0x24], al
003423FF movzx    eax, byte ptr [rbp - 0x38]
00342403 mov      byte ptr [rbx - 0x23], al
00342406 sub      rdi, 1
0034240A jne      0x140342380
00342410 lea      rbx, [rsi + 0x380c]
00342417 mov      edi, 3
0034241C nop      dword ptr [rax]
00342420 lea      rcx, [rbx - 0x20]
00342424 lea      r8, [rbp - 0x69]
00342428 lea      rdx, [rsp + 0x68]
0034242D call     0x1403ff880
00342432 mov      eax, dword ptr [rbp - 0x61]
00342435 lea      rcx, [rbx - 0x14]
00342439 lea      r8, [rbp - 0x5d]
0034243D mov      dword ptr [rbx - 0x18], eax
00342440 lea      rdx, [rsp + 0x60]
00342445 call     0x1403ff880
0034244A mov      eax, dword ptr [rbp - 0x55]
0034244D lea      rcx, [rbx + 2]
00342451 mov      dword ptr [rbx - 0xc], eax
00342454 lea      r8, [rbp - 0x47]
00342458 movzx    eax, word ptr [rbp - 0x51]
0034245C lea      rdx, [rbp - 0x71]
00342460 mov      word ptr [rbx - 8], ax
00342464 movzx    eax, word ptr [rbp - 0x4d]
00342468 mov      word ptr [rbx - 4], ax
0034246C movzx    eax, word ptr [rbp - 0x4b]
00342470 mov      word ptr [rbx - 2], ax
00342474 movzx    eax, word ptr [rbp - 0x49]
00342478 mov      word ptr [rbx], ax
0034247B call     0x1403ff880
00342480 movzx    eax, byte ptr [rbp - 0x3f]
00342484 mov      byte ptr [rbx + 0xa], al
00342487 lea      rbx, [rbx + 0x34]
0034248B movzx    eax, byte ptr [rbp - 0x3e]
0034248F mov      byte ptr [rbx - 0x29], al
00342492 mov      eax, dword ptr [rbp - 0x3d]
00342495 mov      dword ptr [rbx - 0x28], eax
00342498 movzx    eax, byte ptr [rbp - 0x39]
0034249C mov      byte ptr [rbx - 0x24], al
0034249F movzx    eax, byte ptr [rbp - 0x38]
003424A3 mov      byte ptr [rbx - 0x23], al
003424A6 sub      rdi, 1
003424AA jne      0x140342420
003424B0 lea      rbx, [rsi + 0x38a8]
003424B7 mov      edi, 3
003424BC nop      dword ptr [rax]
003424C0 lea      rcx, [rbx - 0x20]
003424C4 lea      r8, [rbp - 0x69]
003424C8 lea      rdx, [rsp + 0x68]
003424CD call     0x1403ff880
003424D2 mov      eax, dword ptr [rbp - 0x61]
003424D5 lea      rcx, [rbx - 0x14]
003424D9 lea      r8, [rbp - 0x5d]
003424DD mov      dword ptr [rbx - 0x18], eax
003424E0 lea      rdx, [rsp + 0x60]
003424E5 call     0x1403ff880
003424EA mov      eax, dword ptr [rbp - 0x55]
003424ED lea      rcx, [rbx + 2]
003424F1 mov      dword ptr [rbx - 0xc], eax
003424F4 lea      r8, [rbp - 0x47]
003424F8 movzx    eax, word ptr [rbp - 0x51]
003424FC lea      rdx, [rbp - 0x71]
00342500 mov      word ptr [rbx - 8], ax
00342504 movzx    eax, word ptr [rbp - 0x4d]
00342508 mov      word ptr [rbx - 4], ax
0034250C movzx    eax, word ptr [rbp - 0x4b]
00342510 mov      word ptr [rbx - 2], ax
00342514 movzx    eax, word ptr [rbp - 0x49]
00342518 mov      word ptr [rbx], ax
0034251B call     0x1403ff880
00342520 movzx    eax, byte ptr [rbp - 0x3f]
00342524 mov      byte ptr [rbx + 0xa], al
00342527 lea      rbx, [rbx + 0x34]
0034252B movzx    eax, byte ptr [rbp - 0x3e]
0034252F mov      byte ptr [rbx - 0x29], al
00342532 mov      eax, dword ptr [rbp - 0x3d]
00342535 mov      dword ptr [rbx - 0x28], eax
00342538 movzx    eax, byte ptr [rbp - 0x39]
0034253C mov      byte ptr [rbx - 0x24], al
0034253F movzx    eax, byte ptr [rbp - 0x38]
00342543 mov      byte ptr [rbx - 0x23], al
00342546 sub      rdi, 1
0034254A jne      0x1403424c0
00342550 call     0x14050933c
00342555 and      eax, 0x7fff
0034255A lea      ecx, [rax + rax*4]
0034255D shl      ecx, 2
00342560 sar      ecx, 0xf
00342563 inc      cl
00342565 mov      byte ptr [rsi + 0x4c80], cl
0034256B call     0x14050933c
00342570 and      eax, 0x7fff
00342575 lea      ecx, [rax + rax*4]
00342578 shl      ecx, 2
0034257B sar      ecx, 0xf
0034257E inc      cl
00342580 mov      byte ptr [rsi + 0x4c81], cl
00342586 call     0x14050933c
0034258B and      eax, 0x7fff
00342590 lea      ecx, [rax + rax*4]
00342593 shl      ecx, 2
00342596 sar      ecx, 0xf
00342599 inc      cl
0034259B mov      byte ptr [rsi + 0x4c82], cl
003425A1 call     0x14050933c
003425A6 and      eax, 0x7fff
003425AB lea      ecx, [rax + rax*4]
003425AE shl      ecx, 2
003425B1 sar      ecx, 0xf
003425B4 inc      cl
003425B6 mov      byte ptr [rsi + 0x4c83], cl
003425BC call     0x14050933c
003425C1 and      eax, 0x7fff
003425C6 lea      ecx, [rax + rax*4]
003425C9 shl      ecx, 2
003425CC sar      ecx, 0xf
003425CF inc      cl
003425D1 mov      byte ptr [rsi + 0x4c84], cl
003425D7 call     0x14050933c
003425DC and      eax, 0x7fff
003425E1 imul     ecx, eax, 0x64
003425E4 sar      ecx, 0xf
003425E7 mov      byte ptr [rsi + 0x4c85], cl
003425ED call     0x14050933c
003425F2 and      eax, 0x7fff
003425F7 imul     ecx, eax, 0x64
003425FA sar      ecx, 0xf
003425FD mov      byte ptr [rsi + 0x4c86], cl
00342603 call     0x14050933c
00342608 and      eax, 0x7fff
0034260D lea      ecx, [rax + rax*4]
00342610 shl      ecx, 2
00342613 sar      ecx, 0xf
00342616 mov      byte ptr [rsi + 0x4c87], cl
0034261C call     0x14050933c
00342621 and      eax, 0x7fff
00342626 lea      ecx, [rax + rax*4]
00342629 shl      ecx, 2
0034262C lea      eax, [rdi - 2]
0034262F sar      ecx, 0xf
00342632 mov      byte ptr [rsi + 0x4c88], cl
00342638 mov      qword ptr [rsi + 0x4b42], 0xfffe
00342643 mov      word ptr [rsi + 0x4b4a], r14w
0034264B mov      dword ptr [rsi + 0x4af4], 0xfffefffe
00342655 mov      dword ptr [rsi + 0x4af8], 0xfffefffe
0034265F mov      dword ptr [rsi + 0x4afc], 0xfffefffe
00342669 mov      dword ptr [rsi + 0x4b00], 0xfffefffe
00342673 mov      dword ptr [rsi + 0x4b04], 0xfffefffe
0034267D mov      dword ptr [rsi + 0x4b08], 0xfffefffe
00342687 mov      dword ptr [rsi + 0x4b0c], 0xfffefffe
00342691 mov      dword ptr [rsi + 0x4b10], 0xfffefffe
0034269B mov      dword ptr [rsi + 0x4b14], 0xfffefffe
003426A5 mov      dword ptr [rsi + 0x4b18], 0xfffefffe
003426AF mov      dword ptr [rsi + 0x4b1c], 0xfffefffe
003426B9 mov      dword ptr [rsi + 0x4b20], 0xfffefffe
003426C3 mov      dword ptr [rsi + 0x4b24], 0xfffefffe
003426CD mov      dword ptr [rsi + 0x4b28], 0xfffefffe
003426D7 mov      dword ptr [rsi + 0x4b2c], 0xfffefffe
003426E1 mov      dword ptr [rsi + 0x4b30], 0xfffefffe
003426EB mov      dword ptr [rsi + 0x4b34], 0xfffefffe
003426F5 mov      dword ptr [rsi + 0x4b38], 0xfffefffe
003426FF mov      dword ptr [rsi + 0x4b3c], 0xfffefffe
00342709 mov      word ptr [rsi + 0x4b40], ax
00342710 mov      qword ptr [rsi + 0x3b70], r14
00342717 mov      qword ptr [rsi + 0x3b78], r14
0034271E lea      rdx, [rsi + 0x48]
00342722 mov      qword ptr [rsi + 0x3b80], r14
00342729 xor      r9d, r9d
0034272C mov      qword ptr [rsi + 0x3b88], r14
00342733 mov      r8, rsi
00342736 mov      qword ptr [rsi + 0x3b90], r14
0034273D mov      qword ptr [rsi + 0x3b98], r14
00342744 mov      qword ptr [rsi + 0x3ba0], r14
0034274B mov      qword ptr [rsi + 0x3ba8], r14
00342752 mov      qword ptr [rsi + 0x3bb0], r14
00342759 mov      qword ptr [rsi + 0x3bb8], r14
00342760 mov      qword ptr [rsi + 0x3bc0], r14
00342767 mov      qword ptr [rsi + 0x3bc8], r14
0034276E mov      qword ptr [rsi + 0x493c], r14
00342775 mov      qword ptr [rsi + 0x4928], r14
0034277C mov      byte ptr [rsi + 0x4930], r14b
00342783 mov      qword ptr [rsp + 0x60], 0xffffffffffffffff
0034278C mov      rax, qword ptr [rsp + 0x60]
00342791 mov      qword ptr [rsi + 0x4934], rax
00342798 mov      qword ptr [rsi + 0x3c00], r14
0034279F mov      byte ptr [rsi + 0x3c08], r14b
003427A6 mov      dword ptr [rsi + 0x47f8], r14d
003427AD mov      qword ptr [rsi + 0x47fc], 0x1e1eff
003427B8 mov      byte ptr [rsi + 0x3c68], r14b
003427BF movups   xmm0, xmmword ptr [rip + 0x24e222]
003427C6 movups   xmmword ptr [rsi + 0x3c09], xmm0
003427CD movups   xmm1, xmmword ptr [rip + 0x24e22c]
003427D4 movups   xmmword ptr [rsi + 0x3c19], xmm1
003427DB movups   xmm0, xmmword ptr [rip + 0x24e21e]
003427E2 movups   xmmword ptr [rsi + 0x3c29], xmm0
003427E9 mov      rcx, qword ptr [rip + 0x324d58]
003427F0 mov      rcx, qword ptr [rcx + 0x1090]
003427F7 add      rcx, 0x64f8
003427FE call     0x14026ca60
00342803 test     al, al
00342805 je       0x140342818
00342807 mov      r8, qword ptr [rsi]
0034280A lea      edx, [rdi + 1]
0034280D mov      rcx, rsi
00342810 call     qword ptr [r8]
00342813 jmp      0x14034379b
00342818 mov      qword ptr [rsi + 0x4748], r14
0034281F lea      rdx, [rip + 0x26aa22]
00342826 mov      qword ptr [rsi + 0x3c58], r14
0034282D lea      rcx, [rsp + 0x58]
00342832 mov      qword ptr [rsi + 0x3c60], r14
00342839 mov      byte ptr [rsi + 0x3c6a], r14b
00342840 mov      dword ptr [rsi + 0x3dd8], r14d
00342847 mov      dword ptr [rsi + 0x3f48], r14d
0034284E mov      dword ptr [rsi + 0x3f70], 3
00342858 mov      dword ptr [rsi + 0x4f04], r14d
0034285F mov      byte ptr [rsi + 0x3a29], r14b
00342866 mov      byte ptr [rsi + 0x3f74], r14b
0034286D call     0x1403ff7c0
00342872 mov      rax, qword ptr [rsi + 0x4088]
00342879 cmp      rax, qword ptr [rsp + 0x58]
0034287E je       0x14034292f
00342884 cmp      qword ptr [rsi + 0x4080], r14
0034288B je       0x1403428b0
0034288D lea      rdx, [rip + 0x2a8f19]
00342894 lea      rcx, [rsi + 0x4088]
0034289B call     0x1403ffb60
003428A0 test     eax, eax
003428A2 je       0x1403428b0
003428A4 mov      rcx, qword ptr [rsi + 0x4080]
003428AB call     0x14001e1e0
003428B0 lea      rdx, [rip + 0x2a8ef6]
003428B7 lea      rcx, [rsp + 0x58]
003428BC call     0x1403ffa80
003428C1 test     eax, eax
003428C3 je       0x1403428e6
003428C5 lea      r8, [rip + 0x2a8ee1]
003428CC mov      qword ptr [rsi + 0x4080], r14
003428D3 lea      rdx, [rsp + 0x68]
003428D8 lea      rcx, [rsi + 0x4088]
003428DF call     0x1403ff960
003428E4 jmp      0x14034292f
003428E6 xor      r8d, r8d
003428E9 lea      rcx, [rsp + 0x58]
003428EE mov      edx, 0x3e8
003428F3 call     0x140403790
003428F8 lea      rdx, [rsp + 0x68]
003428FD lea      rcx, [rsi + 0x4088]
00342904 test     rax, rax
00342907 jne      0x14034291e
00342909 lea      r8, [rip + 0x2a8e9d]
00342910 mov      qword ptr [rsi + 0x4080], r14
00342917 call     0x1403ff960
0034291C jmp      0x14034292f
0034291E lea      r8, [rsp + 0x58]
00342923 mov      qword ptr [rsi + 0x4080], rax
0034292A call     0x1403ff880
0034292F lea      rdx, [rip + 0x26a91a]
00342936 mov      byte ptr [rsi + 0x40b0], r14b
0034293D lea      rcx, [rsp + 0x58]
00342942 call     0x1403ff7c0
00342947 mov      rax, qword ptr [rsi + 0x41c8]
0034294E cmp      rax, qword ptr [rsp + 0x58]
00342953 je       0x140342a04
00342959 cmp      qword ptr [rsi + 0x41c0], r14
00342960 je       0x140342985
00342962 lea      rdx, [rip + 0x2a8e44]
00342969 lea      rcx, [rsi + 0x41c8]
00342970 call     0x1403ffb60
00342975 test     eax, eax
00342977 je       0x140342985
00342979 mov      rcx, qword ptr [rsi + 0x41c0]
00342980 call     0x14001e1e0
00342985 lea      rdx, [rip + 0x2a8e21]
0034298C lea      rcx, [rsp + 0x58]
00342991 call     0x1403ffa80
00342996 test     eax, eax
00342998 je       0x1403429bb
0034299A lea      r8, [rip + 0x2a8e0c]
003429A1 mov      qword ptr [rsi + 0x41c0], r14
003429A8 lea      rdx, [rsp + 0x68]
003429AD lea      rcx, [rsi + 0x41c8]
003429B4 call     0x1403ff960
003429B9 jmp      0x140342a04
003429BB xor      r8d, r8d
003429BE lea      rcx, [rsp + 0x58]
003429C3 mov      edx, 0x3e8
003429C8 call     0x140403790
003429CD lea      rdx, [rsp + 0x68]
003429D2 lea      rcx, [rsi + 0x41c8]
003429D9 test     rax, rax
003429DC jne      0x1403429f3
003429DE lea      r8, [rip + 0x2a8dc8]
003429E5 mov      qword ptr [rsi + 0x41c0], r14
003429EC call     0x1403ff960
003429F1 jmp      0x140342a04
003429F3 lea      r8, [rsp + 0x58]
003429F8 mov      qword ptr [rsi + 0x41c0], rax
003429FF call     0x1403ff880
00342A04 lea      rdx, [rip + 0x26a855]
00342A0B mov      byte ptr [rsi + 0x41f0], r14b
00342A12 lea      rcx, [rsp + 0x58]
00342A17 call     0x1403ff7c0
00342A1C mov      rax, qword ptr [rsi + 0x4308]
00342A23 cmp      rax, qword ptr [rsp + 0x58]
00342A28 je       0x140342ad9
00342A2E cmp      qword ptr [rsi + 0x4300], r14
00342A35 je       0x140342a5a
00342A37 lea      rdx, [rip + 0x2a8d6f]
00342A3E lea      rcx, [rsi + 0x4308]
00342A45 call     0x1403ffb60
00342A4A test     eax, eax
00342A4C je       0x140342a5a
00342A4E mov      rcx, qword ptr [rsi + 0x4300]
00342A55 call     0x14001e1e0
00342A5A lea      rdx, [rip + 0x2a8d4c]
00342A61 lea      rcx, [rsp + 0x58]
00342A66 call     0x1403ffa80
00342A6B test     eax, eax
00342A6D je       0x140342a90
00342A6F lea      r8, [rip + 0x2a8d37]
00342A76 mov      qword ptr [rsi + 0x4300], r14
00342A7D lea      rdx, [rsp + 0x68]
00342A82 lea      rcx, [rsi + 0x4308]
00342A89 call     0x1403ff960
00342A8E jmp      0x140342ad9
00342A90 xor      r8d, r8d
00342A93 lea      rcx, [rsp + 0x58]
00342A98 mov      edx, 0x3e8
00342A9D call     0x140403790
00342AA2 lea      rdx, [rsp + 0x68]
00342AA7 lea      rcx, [rsi + 0x4308]
00342AAE test     rax, rax
00342AB1 jne      0x140342ac8
00342AB3 lea      r8, [rip + 0x2a8cf3]
00342ABA mov      qword ptr [rsi + 0x4300], r14
00342AC1 call     0x1403ff960
00342AC6 jmp      0x140342ad9
00342AC8 lea      r8, [rsp + 0x58]
00342ACD mov      qword ptr [rsi + 0x4300], rax
00342AD4 call     0x1403ff880
00342AD9 lea      rdx, [rip + 0x26a790]
00342AE0 mov      byte ptr [rsi + 0x4330], r14b
00342AE7 lea      rcx, [rsp + 0x58]
00342AEC call     0x1403ff7c0
00342AF1 mov      rax, qword ptr [rsi + 0x4448]
00342AF8 cmp      rax, qword ptr [rsp + 0x58]
00342AFD je       0x140342bae
00342B03 cmp      qword ptr [rsi + 0x4440], r14
00342B0A je       0x140342b2f
00342B0C lea      rdx, [rip + 0x2a8c9a]
00342B13 lea      rcx, [rsi + 0x4448]
00342B1A call     0x1403ffb60
00342B1F test     eax, eax
00342B21 je       0x140342b2f
00342B23 mov      rcx, qword ptr [rsi + 0x4440]
00342B2A call     0x14001e1e0
00342B2F lea      rdx, [rip + 0x2a8c77]
00342B36 lea      rcx, [rsp + 0x58]
00342B3B call     0x1403ffa80
00342B40 test     eax, eax
00342B42 je       0x140342b65
00342B44 lea      r8, [rip + 0x2a8c62]
00342B4B mov      qword ptr [rsi + 0x4440], r14
00342B52 lea      rdx, [rsp + 0x68]
00342B57 lea      rcx, [rsi + 0x4448]
00342B5E call     0x1403ff960
00342B63 jmp      0x140342bae
00342B65 xor      r8d, r8d
00342B68 lea      rcx, [rsp + 0x58]
00342B6D mov      edx, 0x3e8
00342B72 call     0x140403790
00342B77 lea      rdx, [rsp + 0x68]
00342B7C lea      rcx, [rsi + 0x4448]
00342B83 test     rax, rax
00342B86 jne      0x140342b9d
00342B88 lea      r8, [rip + 0x2a8c1e]
00342B8F mov      qword ptr [rsi + 0x4440], r14
00342B96 call     0x1403ff960
00342B9B jmp      0x140342bae
00342B9D lea      r8, [rsp + 0x58]
00342BA2 mov      qword ptr [rsi + 0x4440], rax
00342BA9 call     0x1403ff880
00342BAE lea      rdx, [rip + 0x26a6cb]
00342BB5 mov      byte ptr [rsi + 0x4470], r14b
00342BBC lea      rcx, [rsp + 0x58]
00342BC1 call     0x1403ff7c0
00342BC6 mov      rax, qword ptr [rsi + 0x4588]
00342BCD cmp      rax, qword ptr [rsp + 0x58]
00342BD2 je       0x140342c83
00342BD8 cmp      qword ptr [rsi + 0x4580], r14
00342BDF je       0x140342c04
00342BE1 lea      rdx, [rip + 0x2a8bc5]
00342BE8 lea      rcx, [rsi + 0x4588]
00342BEF call     0x1403ffb60
00342BF4 test     eax, eax
00342BF6 je       0x140342c04
00342BF8 mov      rcx, qword ptr [rsi + 0x4580]
00342BFF call     0x14001e1e0
00342C04 lea      rdx, [rip + 0x2a8ba2]
00342C0B lea      rcx, [rsp + 0x58]
00342C10 call     0x1403ffa80
00342C15 test     eax, eax
00342C17 je       0x140342c3a
00342C19 lea      r8, [rip + 0x2a8b8d]
00342C20 mov      qword ptr [rsi + 0x4580], r14
00342C27 lea      rdx, [rsp + 0x68]
00342C2C lea      rcx, [rsi + 0x4588]
00342C33 call     0x1403ff960
00342C38 jmp      0x140342c83
00342C3A xor      r8d, r8d
00342C3D lea      rcx, [rsp + 0x58]
00342C42 mov      edx, 0x3e8
00342C47 call     0x140403790
00342C4C lea      rdx, [rsp + 0x68]
00342C51 lea      rcx, [rsi + 0x4588]
00342C58 test     rax, rax
00342C5B jne      0x140342c72
00342C5D lea      r8, [rip + 0x2a8b49]
00342C64 mov      qword ptr [rsi + 0x4580], r14
00342C6B call     0x1403ff960
00342C70 jmp      0x140342c83
00342C72 lea      r8, [rsp + 0x58]
00342C77 mov      qword ptr [rsi + 0x4580], rax
00342C7E call     0x1403ff880
00342C83 lea      rdx, [rip + 0x26a5fe]
00342C8A mov      byte ptr [rsi + 0x45b0], r14b
00342C91 lea      rcx, [rsp + 0x58]
00342C96 call     0x1403ff7c0
00342C9B mov      rax, qword ptr [rsi + 0x46c8]
00342CA2 cmp      rax, qword ptr [rsp + 0x58]
00342CA7 je       0x140342d58
00342CAD cmp      qword ptr [rsi + 0x46c0], r14
00342CB4 je       0x140342cd9
00342CB6 lea      rdx, [rip + 0x2a8af0]
00342CBD lea      rcx, [rsi + 0x46c8]
00342CC4 call     0x1403ffb60
00342CC9 test     eax, eax
00342CCB je       0x140342cd9
00342CCD mov      rcx, qword ptr [rsi + 0x46c0]
00342CD4 call     0x14001e1e0
00342CD9 lea      rdx, [rip + 0x2a8acd]
00342CE0 lea      rcx, [rsp + 0x58]
00342CE5 call     0x1403ffa80
00342CEA test     eax, eax
00342CEC je       0x140342d0f
00342CEE lea      r8, [rip + 0x2a8ab8]
00342CF5 mov      qword ptr [rsi + 0x46c0], r14
00342CFC lea      rdx, [rsp + 0x68]
00342D01 lea      rcx, [rsi + 0x46c8]
00342D08 call     0x1403ff960
00342D0D jmp      0x140342d58
00342D0F xor      r8d, r8d
00342D12 lea      rcx, [rsp + 0x58]
00342D17 mov      edx, 0x3e8
00342D1C call     0x140403790
00342D21 lea      rdx, [rsp + 0x68]
00342D26 lea      rcx, [rsi + 0x46c8]
00342D2D test     rax, rax
00342D30 jne      0x140342d47
00342D32 lea      r8, [rip + 0x2a8a74]
00342D39 mov      qword ptr [rsi + 0x46c0], r14
00342D40 call     0x1403ff960
00342D45 jmp      0x140342d58
00342D47 lea      r8, [rsp + 0x58]
00342D4C mov      qword ptr [rsi + 0x46c0], rax
00342D53 call     0x1403ff880
00342D58 mov      rax, qword ptr [rip + 0x3247e9]
00342D5F lea      rcx, [rsi + 0x45b8]
00342D66 mov      rdx, qword ptr [rax + 0x1090]
00342D6D add      rdx, 0x9588
00342D74 call     0x140412390
00342D79 movzx    eax, word ptr [rsp + 0x50]
00342D7E mov      r8d, 0x268
00342D84 mov      r9d, dword ptr [rbp + 0x7f]
00342D88 mov      word ptr [rsi + 0x548], ax
00342D8F mov      eax, dword ptr [rbp + 0x67]
00342D92 mov      dword ptr [rsi + 0x54c], eax
00342D98 movzx    eax, word ptr [rbp + 0x6f]
00342D9C mov      word ptr [rsi + 0x550], ax
00342DA3 movzx    eax, word ptr [rbp + 0x77]
00342DA7 mov      word ptr [rsi + 0x552], ax
00342DAE mov      rax, qword ptr [rbp + 0x87]
00342DB5 mov      qword ptr [rsi + 0x554], rax
00342DBC mov      dword ptr [rsi + 0x55c], r9d
00342DC3 mov      rax, qword ptr [rip + 0x32477e]
00342DCA mov      edx, dword ptr [rip + 0x25b98c]
00342DD0 shr      edx, 1
00342DD2 mov      rcx, qword ptr [rax + 0x1090]
00342DD9 mov      eax, dword ptr [rcx + 0x3fa0]
00342DDF movzx    ecx, byte ptr [rip + 0x25b96e]
00342DE6 add      eax, edx
00342DE8 xor      edx, edx
00342DEA div      dword ptr [rip + 0x25b968]
00342DF0 mov      eax, edx
00342DF2 xor      edx, edx
00342DF4 div      ecx
00342DF6 movzx    ecx, byte ptr [rip + 0x25b958]
00342DFD xor      edx, edx
00342DFF div      ecx
00342E01 movzx    ecx, byte ptr [rip + 0x25b94e]
00342E08 xor      edx, edx
00342E0A div      ecx
00342E0C xor      edx, edx
00342E0E mov      ecx, eax
00342E10 mov      eax, 1
00342E15 shr      r9d, cl
00342E18 lea      rcx, [rsi + 0x560]
00342E1F and      r9d, 1
00342E23 mov      dword ptr [rsi + 0x3bf4], r9d
00342E2A mov      dword ptr [rsi + 0x3bf8], eax
00342E30 mov      dword ptr [rsi + 0x3bfc], eax
00342E36 call     0x1404fab70
00342E3B xor      eax, eax
00342E3D lea      rbx, [rsi + 0xbb8]
00342E44 lea      rdi, [rsi + 0xb80]
00342E4B xor      ecx, ecx
00342E4D mov      qword ptr [rdi], rax
00342E50 mov      qword ptr [rdi + 8], rax
00342E54 mov      qword ptr [rdi + 0x10], rax
00342E58 mov      qword ptr [rdi + 0x18], rax
00342E5C mov      qword ptr [rdi + 0x20], rax
00342E60 mov      qword ptr [rdi + 0x28], rax
00342E64 mov      qword ptr [rdi + 0x30], rax
00342E68 mov      qword ptr [rbx], rax
00342E6B mov      qword ptr [rbx + 8], rax
00342E6F mov      qword ptr [rbx + 0x10], rax
00342E73 mov      qword ptr [rbx + 0x18], rax
00342E77 mov      qword ptr [rbx + 0x20], rax
00342E7B mov      qword ptr [rbx + 0x28], rax
00342E7F mov      qword ptr [rbx + 0x30], rax
00342E83 mov      qword ptr [rbx + 0x38], rax
00342E87 mov      qword ptr [rbx + 0x40], rax
00342E8B mov      qword ptr [rsi + 0xc00], rax
00342E92 mov      qword ptr [rsi + 0x1110], r14
00342E99 mov      dword ptr [rsi + 0x1118], r14d
00342EA0 mov      rax, qword ptr [rdi]
00342EA3 test     rax, rax
00342EA6 jne      0x140342ecd
00342EA8 lea      ecx, [rax + 0x10]
00342EAB call     0x1404f7a88
00342EB0 test     rax, rax
00342EB3 je       0x140342ebe
00342EB5 xor      ecx, ecx
00342EB7 mov      qword ptr [rax], rcx
00342EBA mov      qword ptr [rax + 8], rcx
00342EBE mov      qword ptr [rdi], rax
00342EC1 xor      ecx, ecx
00342EC3 mov      qword ptr [rax], rcx
00342EC6 mov      qword ptr [rax + 8], rcx
00342ECA mov      rax, qword ptr [rdi]
00342ECD mov      word ptr [rax + 2], cx
00342ED1 mov      rax, qword ptr [rdi]
00342ED4 mov      word ptr [rax + 4], cx
00342ED8 mov      rax, qword ptr [rdi]
00342EDB mov      word ptr [rax], r14w
00342EDF inc      r14d
00342EE2 mov      rax, qword ptr [rdi]
00342EE5 add      rdi, 8
00342EE9 mov      word ptr [rax + 6], cx
00342EED cmp      r14d, 7
00342EF1 jl       0x140342ea0
00342EF3 xor      r14d, r14d
00342EF6 mov      edi, r14d
00342EF9 lea      ecx, [r14 + 1]
00342EFD nop      dword ptr [rax]
00342F00 mov      rax, qword ptr [rbx]
00342F03 test     rax, rax
00342F06 jne      0x140342f37
00342F08 lea      ecx, [rax + 0x10]
00342F0B call     0x1404f7a88
00342F10 test     rax, rax
00342F13 je       0x140342f20
00342F15 xor      ecx, ecx
00342F17 mov      qword ptr [rax], rcx
00342F1A mov      qword ptr [rax + 8], rcx
00342F1E jmp      0x140342f23
00342F20 mov      rax, r14
00342F23 xor      ecx, ecx
00342F25 mov      qword ptr [rbx], rax
00342F28 mov      qword ptr [rax], rcx
00342F2B mov      qword ptr [rax + 8], rcx
00342F2F mov      ecx, 1
00342F34 mov      rax, qword ptr [rbx]
00342F37 mov      word ptr [rax + 2], r14w
00342F3C mov      rax, qword ptr [rbx]
00342F3F mov      word ptr [rax + 4], r14w
00342F44 mov      rax, qword ptr [rbx]
00342F47 mov      word ptr [rax], di
00342F4A inc      edi
00342F4C mov      rax, qword ptr [rbx]
00342F4F add      rbx, 8
00342F53 mov      word ptr [rax + 6], cx
00342F57 cmp      edi, 9
00342F5A jl       0x140342f00
00342F5C mov      rax, qword ptr [rsi + 0xc00]
00342F63 test     rax, rax
00342F66 jne      0x140342f9a
00342F68 lea      ecx, [rax + 0x10]
00342F6B call     0x1404f7a88
00342F70 test     rax, rax
00342F73 je       0x140342f80
00342F75 xor      ecx, ecx
00342F77 mov      qword ptr [rax], rcx
00342F7A mov      qword ptr [rax + 8], rcx
00342F7E jmp      0x140342f83
00342F80 mov      rax, r14
00342F83 mov      qword ptr [rsi + 0xc00], rax
00342F8A xor      ecx, ecx
00342F8C mov      qword ptr [rax], rcx
00342F8F mov      qword ptr [rax + 8], rcx
00342F93 mov      rax, qword ptr [rsi + 0xc00]
00342F9A mov      word ptr [rax + 2], r14w
00342F9F lea      r8, [rip + 0x2a8807]
00342FA6 mov      rax, qword ptr [rsi + 0xc00]
00342FAD lea      rdx, [rsp + 0x68]
00342FB2 mov      ebx, 0xffffffff
00342FB7 lea      rcx, [rsi + 0x4c6c]
00342FBE mov      word ptr [rax + 4], r14w
00342FC3 mov      rax, qword ptr [rsi + 0xc00]
00342FCA mov      word ptr [rax], r14w
00342FCE mov      rax, qword ptr [rsi + 0xc00]
00342FD5 mov      word ptr [rax + 6], r12w
00342FDA mov      dword ptr [rsi + 0x4cac], r14d
00342FE1 mov      dword ptr [rsi + 0x4cb0], ebx
00342FE7 mov      byte ptr [rsi + 0x4e5c], 1
00342FEE call     0x1403ff960
00342FF3 mov      byte ptr [rsi + 0x4cb8], r14b
00342FFA lea      rcx, [rsi + 0x3bd8]
00343001 mov      edi, 1
00343006 mov      dword ptr [rsi + 0x4ca8], edi
0034300C mov      rax, qword ptr [rip + 0x324535]
00343013 mov      rdx, qword ptr [rax + 0x1090]
0034301A mov      eax, dword ptr [rdx + 0x3fa0]
00343020 lea      rdx, [rip + 0x3182d9]
00343027 mov      dword ptr [rsi + 0x4e34], eax
0034302D call     0x14011ea00
00343032 mov      dword ptr [rsi + 0x4e40], r14d
00343039 lea      r8, [rip + 0x2a876d]
00343040 mov      dword ptr [rsi + 0x4e44], edi
00343046 lea      rdx, [rsp + 0x68]
0034304B lea      rcx, [rsi + 0x4e68]
00343052 mov      qword ptr [rsi + 0x4e4c], r14
00343059 call     0x1403ff960
0034305E lea      ecx, [rbx + 0x11]
00343061 mov      dword ptr [rsi + 0x4e74], r14d
00343068 call     0x1404f7a88
0034306D test     rax, rax
00343070 je       0x14034307f
00343072 lea      edx, [rbx + 0x11]
00343075 mov      rcx, rax
00343078 call     0x140251ff0
0034307D jmp      0x140343082
0034307F mov      rax, r14
00343082 movzx    r9d, word ptr [rbp + 0x8f]
0034308A mov      rcx, rsi
0034308D mov      r8d, dword ptr [rsp + 0x70]
00343092 mov      rdx, qword ptr [rbp - 0x31]
00343096 mov      qword ptr [rsi + 0x4eb8], rax
0034309D mov      qword ptr [rsi + 0x4f18], r14
003430A4 mov      qword ptr [rsi + 0x4f20], r14
003430AB mov      dword ptr [rsi + 0x5208], r14d
003430B2 mov      qword ptr [rsi + 0x4e78], 0xffffffffffffffff
003430BD mov      qword ptr [rsi + 0x4e80], 0xffffffffffffffff
003430C8 mov      qword ptr [rsi + 0x4e90], r14
003430CF mov      qword ptr [rsi + 0x4e98], r14
003430D6 mov      word ptr [rsi + 0x4ea0], r14w
003430DE mov      qword ptr [rsi + 0x503c], r14
003430E5 movzx    eax, byte ptr [rip + 0x25baf6]
003430EC mov      byte ptr [rsi + 0x52f0], al
003430F2 mov      byte ptr [rsi + 0x5174], r14b
003430F9 mov      qword ptr [rsi + 0x51f0], r14
00343100 mov      byte ptr [rsi + 0x5200], r14b
00343107 mov      dword ptr [rsi + 0x5204], r14d
0034310E mov      dword ptr [rsi + 0x51f8], ebx
00343114 call     0x14037a3e0
00343119 cmp      dword ptr [rbp + 0x97], r14d
00343120 je       0x14034312a
00343122 mov      rcx, rsi
00343125 call     0x14037cc30
0034312A mov      rax, qword ptr [rip + 0x3199df]
00343131 lea      rcx, [rbp - 0x21]
00343135 mov      qword ptr [rbp - 0x29], rax
00343139 call     0x14040d580
0034313E mov      rcx, qword ptr [rip + 0x324403]
00343145 lea      r8, [rbp - 0x29]
00343149 mov      edx, dword ptr [rsi + 0x560]
0034314F add      rcx, 0x1150
00343156 xor      r9d, r9d
00343159 call     0x140417300
0034315E lea      rdx, [rbp - 0x29]
00343162 lea      rcx, [rsi + 0x3928]
00343169 call     0x1403fd770
0034316E lea      rcx, [rbp - 0x21]
00343172 call     0x14040d740
00343177 lea      rcx, [rbp - 0x29]
0034317B call     0x1403fd740
00343180 mov      rax, qword ptr [rip + 0x3243c1]
00343187 mov      rbx, qword ptr [rax + 0x1090]
0034318E movsxd   rdi, dword ptr [rbx + 0x3e10]
00343195 mov      ecx, dword ptr [rbx + 0x3ef0]
0034319B add      ecx, edi
0034319D cmp      edi, ecx
0034319F jge      0x1403431f1
003431A1 lea      r14, [rsi + 0x5fc]
003431A8 lea      r14, [r14 + rdi*4]
003431AC nop      dword ptr [rax]
003431B0 mov      edx, dword ptr [r14]
003431B3 xor      r9d, r9d
003431B6 movsxd   rax, edi
003431B9 lea      rcx, [rax + rax*4]
003431BD mov      rax, qword ptr [rsi + 0x4c78]
003431C4 lea      r8, [rax + rcx*8]
003431C8 mov      rcx, qword ptr [rip + 0x324379]
003431CF add      rcx, 0x1150
003431D6 call     0x140417300
003431DB mov      eax, dword ptr [rbx + 0x3ef0]
003431E1 lea      r14, [r14 + 4]
003431E5 add      eax, dword ptr [rbx + 0x3e10]
003431EB inc      edi
003431ED cmp      edi, eax
003431EF jl       0x1403431b0
003431F1 movsxd   rdi, dword ptr [rbx + 0x3e34]
003431F8 mov      ecx, dword ptr [rbx + 0x3f14]
003431FE add      ecx, edi
00343200 cmp      edi, ecx
00343202 jge      0x140343251
00343204 lea      r14, [rsi + 0x5fc]
0034320B lea      r14, [r14 + rdi*4]
0034320F nop      
00343210 mov      edx, dword ptr [r14]
00343213 xor      r9d, r9d
00343216 movsxd   rax, edi
00343219 lea      rcx, [rax + rax*4]
0034321D mov      rax, qword ptr [rsi + 0x4c78]
00343224 lea      r8, [rax + rcx*8]
00343228 mov      rcx, qword ptr [rip + 0x324319]
0034322F add      rcx, 0x1150
00343236 call     0x140417300
0034323B mov      eax, dword ptr [rbx + 0x3f14]
00343241 lea      r14, [r14 + 4]
00343245 add      eax, dword ptr [rbx + 0x3e34]
0034324B inc      edi
0034324D cmp      edi, eax
0034324F jl       0x140343210
00343251 mov      edx, 0xf
00343256 mov      rcx, r15
00343259 call     0x14040efe0
0034325E add      r15, 0x20
00343262 sub      r12, 1
00343266 jne      0x140343251
00343268 lea      edx, [r12 + 0xf]
0034326D mov      byte ptr [rsi + 0x3ab9], r12b
00343274 lea      rcx, [rsi + 0x3a78]
0034327B call     0x14040efe0
00343280 test     dword ptr [rsi + 0x580], 0xf000
0034328A mov      r15, r12
0034328D mov      eax, r15d
00343290 mov      r12d, 0xffffffff
00343296 setne    al
00343299 mov      rcx, rsi
0034329C mov      dword ptr [rsi + 0x3f68], eax
003432A2 mov      eax, 1
003432A7 mov      dword ptr [rsi + 0x3bf0], r12d
003432AE lea      edx, [r15 + 6]
003432B2 mov      dword ptr [rsi + 0x4ba4], eax
003432B8 mov      dword ptr [rsi + 0x4ac], r15d
003432BF mov      dword ptr [rsi + 0x4e38], r15d
003432C6 mov      word ptr [rsi + 0x4e3c], r15w
003432CE movzx    eax, byte ptr [rsi + 0x10f8]
003432D5 mov      byte ptr [rsi + 0x4c2e], al
003432DB movzx    eax, byte ptr [rsi + 0x10fa]
003432E2 mov      byte ptr [rsi + 0x4c2f], al
003432E8 call     0x1403752c0
003432ED mov      rcx, rsi
003432F0 call     0x14034dfd0
003432F5 mov      dword ptr [rsi + 0x4e58], r15d
003432FC mov      qword ptr [rsi + 0x4e60], r15
00343303 mov      rcx, qword ptr [rip + 0x324256]
0034330A cmp      byte ptr [rcx + 0x2c9], 1
00343311 jne      0x140343321
00343313 mov      eax, dword ptr [rsi + 0x50]
00343316 cmp      dword ptr [rcx + 0x374], eax
0034331C sete     al
0034331F jmp      0x140343323
00343321 mov      al, 1
00343323 mov      byte ptr [rsi + 0x4cb9], al
00343329 mov      r8d, 0x1e20
0034332F mov      dword ptr [rsi + 0x4e70], r15d
00343336 mov      edx, 0x1178
0034333B and      dword ptr [rsi + 0x568], 0x7fffffff
00343345 mov      edi, 0x1120
0034334A mov      rax, qword ptr [rip + 0x3241f7]
00343351 mov      r13d, 0x1dc8
00343357 mov      rcx, qword ptr [rax + 0x1090]
0034335E mov      eax, dword ptr [rsi + 0x4ea4]
00343364 test     eax, eax
00343366 cmove    edx, r8d
0034336A mov      r8d, edi
0034336D cmove    r8d, r13d
00343371 add      r8, rsi
00343374 movzx    r9d, byte ptr [rdx + rsi]
00343379 lea      rdx, [rsi + 0x30]
0034337D call     0x1402408b0
00343382 mov      r8d, dword ptr [rsi + 0x4e40]
00343389 mov      edx, eax
0034338B cmp      eax, r8d
0034338E jle      0x1403433be
00343390 cmp      dword ptr [rsi + 0x4ea4], r15d
00343397 mov      ecx, edi
00343399 cmove    ecx, r13d
0034339D mov      eax, dword ptr [rcx + rsi]
003433A0 bt       eax, 0xb
003433A4 jb       0x140343406
003433A6 test     al, al
003433A8 js       0x140343406
003433AA test     al, 0x40
003433AC jne      0x140343406
003433AE movzx    eax, word ptr [rsi + 0x57c]
003433B5 sub      ax, r8w
003433B9 add      ax, dx
003433BC jmp      0x140343409
003433BE jge      0x140343432
003433C0 mov      ecx, dword ptr [rsi + 0x4ea4]
003433C6 mov      rax, rdi
003433C9 test     ecx, ecx
003433CB cmove    rax, r13
003433CF test     dword ptr [rax + rsi], 0x800
003433D6 jne      0x140343406
003433D8 test     ecx, ecx
003433DA mov      rax, rdi
003433DD cmove    rax, r13
003433E1 test     byte ptr [rax + rsi], 0x80
003433E5 jne      0x140343406
003433E7 test     ecx, ecx
003433E9 mov      rax, rdi
003433EC cmove    rax, r13
003433F0 test     byte ptr [rax + rsi], 0x40
003433F4 jne      0x140343406
003433F6 movzx    eax, word ptr [rsi + 0x57c]
003433FD sub      ax, r8w
00343401 add      ax, dx
00343404 jmp      0x140343409
00343406 mov      eax, r15d
00343409 mov      word ptr [rsi + 0x57c], ax
00343410 movzx    ecx, dx
00343413 movzx    eax, dx
00343416 sub      ax, word ptr [rsi + 0x4e40]
0034341D add      word ptr [rsi + 0x1124], ax
00343424 sub      cx, word ptr [rsi + 0x4e40]
0034342B add      word ptr [rsi + 0x57e], cx
00343432 mov      dword ptr [rsi + 0x4e40], edx
00343438 lea      rcx, [rsi + 0x30]
0034343C mov      dword ptr [rsi + 0x4e44], r15d
00343443 mov      ebx, dword ptr [rsi + 0x4ea4]
00343449 call     0x14011dc40
0034344E test     ebx, ebx
00343450 mov      rcx, rdi
00343453 movzx    edx, al
00343456 cmove    rcx, r13
0034345A add      rcx, rsi
0034345D call     0x140152480
00343462 cmp      dword ptr [rsi + 0x4ea4], r15d
00343469 lea      rdx, [rsp + 0x70]
0034346E movzx    eax, al
00343471 mov      ecx, 0x1dcc
00343476 mov      dword ptr [rsp + 0x70], eax
0034347A mov      eax, 0x1124
0034347F cmove    eax, ecx
00343482 lea      rcx, [rsp + 0x50]
00343487 movsx    eax, word ptr [rax + rsi]
0034348B mov      dword ptr [rsp + 0x50], eax
0034348F call     0x140407bb0
00343494 mov      word ptr [rsi + 0x1124], ax
0034349B cmp      word ptr [rsi + 0x57c], r15w
003434A3 jg       0x1403434e2
003434A5 mov      ecx, dword ptr [rsi + 0x4ea4]
003434AB mov      rax, rdi
003434AE test     ecx, ecx
003434B0 cmove    rax, r13
003434B4 test     dword ptr [rax + rsi], 0x800
003434BB jne      0x1403434e2
003434BD test     ecx, ecx
003434BF cmove    rdi, r13
003434C3 mov      eax, dword ptr [rdi + rsi]
003434C6 test     al, 0x40
003434C8 jne      0x1403434e2
003434CA test     al, al
003434CC js       0x1403434e2
003434CE or       dword ptr [rsi + 0x578], 0x800
003434D8 or       dword ptr [rsi + 0x1120], 0x800
003434E2 mov      qword ptr [rsi + 0x4e78], 0xffffffffffffffff
003434ED mov      qword ptr [rsi + 0x4e80], 0xffffffffffffffff
003434F8 mov      qword ptr [rsi + 0x4e90], r15
003434FF mov      qword ptr [rsi + 0x4e98], r15
00343506 mov      word ptr [rsi + 0x4ea0], r15w
0034350E mov      qword ptr [rsi + 0x503c], r15
00343515 movzx    eax, byte ptr [rip + 0x25b6c6]
0034351C mov      byte ptr [rsi + 0x52f0], al
00343522 mov      byte ptr [rsi + 0x5174], r15b
00343529 mov      qword ptr [rsi + 0x51f0], r15
00343530 mov      dword ptr [rsi + 0x51f8], r12d
00343537 mov      byte ptr [rsi + 0x5200], r15b
0034353E mov      dword ptr [rsi + 0x5204], r15d
00343545 mov      qword ptr [rsi + 0x52f4], r15
0034354C mov      qword ptr [rsi + 0x52fc], r15
00343553 mov      word ptr [rsi + 0x5304], r15w
0034355B mov      dword ptr [rsi + 0x5378], r15d
00343562 mov      byte ptr [rsi + 0x533c], r15b
00343569 mov      rax, qword ptr [rip + 0x323ff0]
00343570 cmp      byte ptr [rax + 0x2c9], r15b
00343577 jne      0x14034378d
0034357D lea      rcx, [rbp - 0x79]
00343581 call     0x1403ff870
00343586 lea      rcx, [rbp - 0x31]
0034358A call     0x1403ff870
0034358F mov      rax, qword ptr [rip + 0x31957a]
00343596 mov      qword ptr [rsp + 0x58], rax
0034359B mov      qword ptr [rsp + 0x60], rax
003435A0 mov      qword ptr [rbp - 0x71], rax
003435A4 mov      rax, qword ptr [rip + 0x323f9d]
003435AB mov      r14, qword ptr [rax + 0x1090]
003435B2 mov      rcx, r14
003435B5 call     0x1402781f0
003435BA mov      ecx, eax
003435BC lea      rdx, [rsp + 0x68]
003435C1 call     0x140276700
003435C6 test     al, al
003435C8 jne      0x140343770
003435CE cmp      dword ptr [rip + 0x3e7453], 2
003435D5 je       0x140343770
003435DB mov      r8, qword ptr [rsp + 0x68]
003435E0 lea      rdx, [rsp + 0x70]
003435E5 add      r8, 0x594
003435EC lea      rcx, [rbp - 0x79]
003435F0 call     0x1403ff9a0
003435F5 lea      r8, [rsi + 0x594]
003435FC lea      rdx, [rsp + 0x70]
00343601 lea      rcx, [rbp - 0x31]
00343605 call     0x1403ff9a0
0034360A lea      rdx, [rsp + 0x70]
0034360F lea      rcx, [rbp - 0x79]
00343613 call     0x1403fff70
00343618 mov      rdx, rax
0034361B lea      rcx, [rsp + 0x60]
00343620 call     0x1403fd770
00343625 lea      rcx, [rsp + 0x70]
0034362A call     0x1403fd740
0034362F lea      rdx, [rsp + 0x70]
00343634 lea      rcx, [rbp - 0x31]
00343638 call     0x1403fff70
0034363D mov      rdx, rax
00343640 lea      rcx, [rbp - 0x71]
00343644 call     0x1403fd770
00343649 lea      rcx, [rsp + 0x70]
0034364E call     0x1403fd740
00343653 mov      rax, qword ptr [rsp + 0x60]
00343658 lea      rdx, [rsp + 0x70]
0034365D mov      ecx, dword ptr [rax - 8]
00343660 mov      dword ptr [rsp + 0x70], ecx
00343664 lea      rcx, [rsp + 0x50]
00343669 mov      dword ptr [rsp + 0x50], 8
00343671 call     0x140407bc0
00343676 lea      edi, [rax - 1]
00343679 mov      rax, qword ptr [rbp - 0x71]
0034367D mov      ecx, dword ptr [rax - 8]
00343680 dec      ecx
00343682 cmp      edi, ecx
00343684 jne      0x1403436c4
00343686 mov      r8d, edi
00343689 lea      rdx, [rsp + 0x70]
0034368E lea      rcx, [rbp - 0x71]
00343692 call     0x1403fef20
00343697 mov      r8d, edi
0034369A lea      rdx, [rsp + 0x78]
0034369F lea      rcx, [rsp + 0x60]
003436A4 mov      rbx, rax
003436A7 call     0x1403fef20
003436AC mov      rdx, qword ptr [rbx]
003436AF mov      edi, 3
003436B4 mov      rcx, qword ptr [rax]
003436B7 call     0x140503d4c
003436BC test     eax, eax
003436BE jne      0x1403436c8
003436C0 mov      bl, 1
003436C2 jmp      0x1403436ca
003436C4 mov      edi, dword ptr [rsp + 0x78]
003436C8 xor      bl, bl
003436CA test     dil, 2
003436CE je       0x1403436dd
003436D0 and      edi, 0xfffffffd
003436D3 lea      rcx, [rsp + 0x78]
003436D8 call     0x1403fd740
003436DD test     dil, 1
003436E1 je       0x1403436ed
003436E3 lea      rcx, [rsp + 0x70]
003436E8 call     0x1403fd740
003436ED test     bl, bl
003436EF je       0x140343770
003436F1 lea      rdx, [rsp + 0x58]
003436F6 lea      rcx, [rbp - 0x79]
003436FA call     0x1403ffe40
003436FF lea      rdx, [rip + 0x2576ca]
00343706 lea      rcx, [rsp + 0x78]
0034370B call     0x1403fd6b0
00343710 lea      rcx, [r14 + 0x16c0]
00343717 lea      r8, [rsp + 0x58]
0034371C lea      rdx, [rsp + 0x78]
00343721 call     0x1401151e0
00343726 mov      rdx, rax
00343729 lea      rcx, [rsp + 0x58]
0034372E call     0x1403fd770
00343733 lea      rcx, [rsp + 0x78]
00343738 call     0x1403fd740
0034373D lea      r8, [rsp + 0x58]
00343742 lea      rdx, [rsp + 0x78]
00343747 lea      rcx, [rbp - 0x79]
0034374B call     0x1403ff890
00343750 lea      rdx, [rsi + 0x594]
00343757 lea      rcx, [rbp - 0x79]
0034375B call     0x1403fff60
00343760 lea      rdx, [rsi + 0x58c]
00343767 lea      rcx, [rbp - 0x79]
0034376B call     0x1403fff60
00343770 lea      rcx, [rbp - 0x71]
00343774 call     0x1403fd740
00343779 lea      rcx, [rsp + 0x60]
0034377E call     0x1403fd740
00343783 lea      rcx, [rsp + 0x58]
00343788 call     0x1403fd740
0034378D mov      dword ptr [rsi + 0x537c], r15d
00343794 mov      byte ptr [rsi + 0x5384], 0
0034379B mov      rax, rsi
0034379E mov      rcx, qword ptr [rbp - 1]
003437A2 xor      rcx, rsp
003437A5 call     0x1404f77a0
003437AA mov      rbx, qword ptr [rsp + 0x150]
003437B2 add      rsp, 0x100
003437B9 pop      r15
003437BB pop      r14
003437BD pop      r13
003437BF pop      r12
003437C1 pop      rdi
003437C2 pop      rsi
003437C3 pop      rbp
003437C4 ret      
