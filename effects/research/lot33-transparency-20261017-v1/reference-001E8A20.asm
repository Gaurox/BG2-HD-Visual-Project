001E8A20 mov      qword ptr [rsp + 0x10], rbx
001E8A25 push     rbp
001E8A26 push     rsi
001E8A27 push     rdi
001E8A28 push     r12
001E8A2A push     r13
001E8A2C push     r14
001E8A2E push     r15
001E8A30 mov      rbp, rsp
001E8A33 sub      rsp, 0x40
001E8A37 mov      rax, qword ptr [rip + 0x47bf9a]
001E8A3E xor      rax, rsp
001E8A41 mov      qword ptr [rbp - 0x10], rax
001E8A45 mov      rbx, r9
001E8A48 movzx    esi, dl
001E8A4B movzx    edi, r8w
001E8A4F mov      r14, rcx
001E8A52 call     0x1401eca50
001E8A57 lea      rax, [rip + 0x3b0a72]
001E8A5E lea      r13, [r14 + 0x90]
001E8A65 mov      qword ptr [r14], rax
001E8A68 mov      rcx, r13
001E8A6B call     0x140410f70
001E8A70 movzx    edx, word ptr [rip + 0x3d7c05]
001E8A77 lea      rcx, [r14 + 0x1c8]
001E8A7E call     0x140421010
001E8A83 lea      r12, [r14 + 0x230]
001E8A8A mov      rcx, r12
001E8A8D call     0x14040d580
001E8A92 mov      rax, qword ptr [rip + 0x474077]
001E8A99 lea      r15, [r14 + 0x250]
001E8AA0 lea      rcx, [r14 + 0x290]
001E8AA7 mov      qword ptr [r15], rax
001E8AAA call     0x140410d80
001E8AAF lea      rcx, [r14 + 0x3b0]
001E8AB6 call     0x1403ff870
001E8ABB lea      rcx, [r14 + 0x3b8]
001E8AC2 call     0x1403ff870
001E8AC7 movzx    r8d, byte ptr [rbp + 0x68]
001E8ACC xor      ecx, ecx
001E8ACE mov      qword ptr [r14 + 0x258], rcx
001E8AD5 mov      eax, 1
001E8ADA mov      dword ptr [r14 + 0x264], eax
001E8AE1 mov      qword ptr [r14 + 0x268], rax
001E8AE8 mov      dword ptr [r14 + 0x288], ecx
001E8AEF mov      qword ptr [r14 + 0x270], rcx
001E8AF6 mov      dword ptr [r14 + 0x260], ecx
001E8AFD movsx    ecx, word ptr [rbp + 0x60]
001E8B01 mov      byte ptr [r14 + 8], 0x70
001E8B06 mov      eax, dword ptr [rbx]
001E8B08 mov      dword ptr [r14 + 0x84], eax
001E8B0F movzx    eax, word ptr [rbx + 4]
001E8B13 mov      word ptr [r14 + 0x88], ax
001E8B1B movzx    eax, byte ptr [rbx + 6]
001E8B1F mov      byte ptr [r14 + 0x8a], al
001E8B26 lea      eax, [rcx - 1]
001E8B29 cdq      
001E8B2A mov      dword ptr [r14 + 0x1fc], ecx
001E8B31 idiv     r8d
001E8B34 mov      dword ptr [r14 + 0x200], r8d
001E8B3B inc      al
001E8B3D mov      byte ptr [r14 + 0x204], al
001E8B44 movzx    eax, word ptr [rbp + 0x80]
001E8B4B mov      word ptr [r14 + 0x1f8], ax
001E8B53 movzx    eax, byte ptr [rbp + 0x70]
001E8B57 mov      byte ptr [r14 + 0x205], al
001E8B5E mov      eax, dword ptr [rbp + 0x88]
001E8B64 mov      dword ptr [r14 + 0x278], eax
001E8B6B movzx    eax, word ptr [rbp + 0x90]
001E8B72 mov      word ptr [r14 + 0x27c], ax
001E8B7A mov      rax, qword ptr [rbp + 0x98]
001E8B81 mov      rcx, qword ptr [rax]
001E8B84 mov      qword ptr [r14 + 0x280], rcx
001E8B8B lea      rcx, [r14 + 0x1c8]
001E8B92 movzx    eax, byte ptr [rip + 0x3b2467]
001E8B99 lea      eax, [rax + rax*2]
001E8B9C cdq      
001E8B9D sub      eax, edx
001E8B9F xor      edx, edx
001E8BA1 sar      eax, 1
001E8BA3 mov      word ptr [r14 + 0x8c], ax
001E8BAB mov      rax, qword ptr [rip + 0x47e996]
001E8BB2 movzx    r8d, byte ptr [rbx]
001E8BB6 mov      r9, qword ptr [rax + 0x1090]
001E8BBD add      r9, 0x63d8
001E8BC4 call     0x1404221c0
001E8BC9 mov      rax, qword ptr [rip + 0x47e978]
001E8BD0 lea      rcx, [r14 + 0x1c8]
001E8BD7 movzx    r8d, byte ptr [rbx + 1]
001E8BDC mov      edx, 1
001E8BE1 mov      r9, qword ptr [rax + 0x1090]
001E8BE8 add      r9, 0x63d8
001E8BEF call     0x1404221c0
001E8BF4 mov      word ptr [r14 + 0x3c0], di
001E8BFC mov      eax, dword ptr [rbp + 0x78]
001E8BFF xor      edi, edi
001E8C01 and      eax, 0x40
001E8C04 mov      dword ptr [r14 + 0x3c4], edi
001E8C0B mov      dword ptr [r14 + 0x3c8], eax
001E8C12 cmp      esi, 0xfe
001E8C18 ja       0x1401e9623
001E8C1E lea      rdx, [rip - 0x1e8c25]
001E8C25 movzx    eax, byte ptr [rdx + rsi + 0x1e969c]
001E8C2D mov      ecx, dword ptr [rdx + rax*4 + 0x1e964c]
001E8C34 add      rcx, rdx
001E8C37 jmp      rcx
001E8C39 lea      rdx, [rip + 0x402b6d]
001E8C40 mov      rcx, r15
001E8C43 call     0x1403fd810
001E8C48 mov      qword ptr [r14 + 0x264], rdi
001E8C4F mov      dword ptr [r14 + 0x260], edi
001E8C56 mov      dword ptr [r14 + 0x80], 0xf010f00
001E8C61 jmp      0x1401e9623
001E8C66 lea      rdx, [rip + 0x3b0933]
001E8C6D lea      rcx, [rbp - 0x20]
001E8C71 call     0x1403ff7c0
001E8C76 mov      edi, 1
001E8C7B lea      rdx, [rbp - 0x20]
001E8C7F mov      r9d, edi
001E8C82 mov      r8d, edi
001E8C85 mov      rcx, r12
001E8C88 call     0x14040ede0
001E8C8D lea      rdx, [rip + 0x402b19]
001E8C94 mov      rcx, r15
001E8C97 call     0x1403fd810
001E8C9C mov      rax, qword ptr [rip + 0x47e8a5]
001E8CA3 mov      rcx, qword ptr [rax + 0x1090]
001E8CAA cmp      dword ptr [rcx + 0x7e54], 0
001E8CB1 je       0x1401e8cc2
001E8CB3 cmp      dword ptr [rcx + 0x7d98], 0
001E8CBA je       0x1401e8cc2
001E8CBC mov      eax, edi
001E8CBE xor      esi, esi
001E8CC0 jmp      0x1401e8cc6
001E8CC2 xor      esi, esi
001E8CC4 mov      eax, esi
001E8CC6 lea      rcx, [rbp - 0x20]
001E8CCA test     eax, eax
001E8CCC je       0x1401e8e90
001E8CD2 lea      rdx, [rip + 0x3b08cf]
001E8CD9 mov      dword ptr [r14 + 0x80], 0x10001
001E8CE4 call     0x1403ff7c0
001E8CE9 mov      r9d, edi
001E8CEC lea      rdx, [rbp - 0x20]
001E8CF0 mov      r8d, edi
001E8CF3 lea      rcx, [r14 + 0x198]
001E8CFA call     0x14014d080
001E8CFF mov      dword ptr [r14 + 0x260], edi
001E8D06 mov      dword ptr [r14 + 0x268], esi
001E8D0D jmp      0x1401e8f91
001E8D12 lea      rdx, [rip + 0x3b0887]
001E8D19 lea      rcx, [rbp - 0x20]
001E8D1D call     0x1403ff7c0
001E8D22 mov      edi, 1
001E8D27 lea      rdx, [rbp - 0x20]
001E8D2B mov      r9d, edi
001E8D2E mov      r8d, edi
001E8D31 mov      rcx, r12
001E8D34 call     0x14040ede0
001E8D39 lea      rdx, [rip + 0x402a6d]
001E8D40 mov      rcx, r15
001E8D43 call     0x1403fd810
001E8D48 mov      rax, qword ptr [rip + 0x47e7f9]
001E8D4F mov      rcx, qword ptr [rax + 0x1090]
001E8D56 cmp      dword ptr [rcx + 0x7e54], 0
001E8D5D je       0x1401e8d6e
001E8D5F cmp      dword ptr [rcx + 0x7d98], 0
001E8D66 je       0x1401e8d6e
001E8D68 mov      eax, edi
001E8D6A xor      esi, esi
001E8D6C jmp      0x1401e8d72
001E8D6E xor      esi, esi
001E8D70 mov      eax, esi
001E8D72 lea      rcx, [rbp - 0x20]
001E8D76 test     eax, eax
001E8D78 je       0x1401e8e90
001E8D7E lea      rdx, [rip + 0x3b0823]
001E8D85 mov      dword ptr [r14 + 0x80], 0x30003
001E8D90 call     0x1403ff7c0
001E8D95 mov      r9d, edi
001E8D98 lea      rdx, [rbp - 0x20]
001E8D9C mov      r8d, edi
001E8D9F lea      rcx, [r14 + 0x198]
001E8DA6 call     0x14014d080
001E8DAB lea      rdx, [rip + 0x3b080e]
001E8DB2 mov      dword ptr [r14 + 0x260], edi
001E8DB9 lea      rcx, [rbp - 0x20]
001E8DBD mov      dword ptr [r14 + 0x268], esi
001E8DC4 mov      dword ptr [r14 + 0x288], edi
001E8DCB call     0x1403ff7c0
001E8DD0 mov      rax, qword ptr [r14 + 0x398]
001E8DD7 cmp      rax, qword ptr [rbp - 0x20]
001E8DDB je       0x1401e8f91
001E8DE1 cmp      qword ptr [r14 + 0x390], 0
001E8DE9 je       0x1401e8e0e
001E8DEB lea      rdx, [rip + 0x4029bb]
001E8DF2 lea      rcx, [r14 + 0x398]
001E8DF9 call     0x1403ffb60
001E8DFE test     eax, eax
001E8E00 je       0x1401e8e0e
001E8E02 mov      rcx, qword ptr [r14 + 0x390]
001E8E09 call     0x14001e1e0
001E8E0E lea      rdx, [rip + 0x402998]
001E8E15 lea      rcx, [rbp - 0x20]
001E8E19 call     0x1403ffa80
001E8E1E test     eax, eax
001E8E20 je       0x1401e8e45
001E8E22 lea      r8, [rip + 0x402984]
001E8E29 mov      qword ptr [r14 + 0x390], rsi
001E8E30 lea      rdx, [rbp - 0x18]
001E8E34 lea      rcx, [r14 + 0x398]
001E8E3B call     0x1403ff960
001E8E40 jmp      0x1401e8f91
001E8E45 xor      r8d, r8d
001E8E48 lea      rcx, [rbp - 0x20]
001E8E4C mov      edx, edi
001E8E4E call     0x140403790
001E8E53 lea      rdx, [rbp - 0x18]
001E8E57 lea      rcx, [r14 + 0x398]
001E8E5E test     rax, rax
001E8E61 jne      0x1401e8e7b
001E8E63 lea      r8, [rip + 0x402943]
001E8E6A mov      qword ptr [r14 + 0x390], rsi
001E8E71 call     0x1403ff960
001E8E76 jmp      0x1401e8f91
001E8E7B lea      r8, [rbp - 0x20]
001E8E7F mov      qword ptr [r14 + 0x390], rax
001E8E86 call     0x1403ff880
001E8E8B jmp      0x1401e8f91
001E8E90 lea      rdx, [rip + 0x3b071d]
001E8E97 mov      dword ptr [r14 + 0x80], 0
001E8EA2 call     0x1403ff7c0
001E8EA7 mov      r9d, edi
001E8EAA lea      rdx, [rbp - 0x20]
001E8EAE mov      r8d, edi
001E8EB1 lea      rcx, [r14 + 0x198]
001E8EB8 call     0x14014d080
001E8EBD lea      rdx, [r14 + 0x1c8]
001E8EC4 mov      rcx, r13
001E8EC7 call     0x140412390
001E8ECC jmp      0x1401e8f91
001E8ED1 lea      rdx, [rip + 0x3b06c8]
001E8ED8 lea      rcx, [rbp - 0x20]
001E8EDC call     0x1403ff7c0
001E8EE1 mov      edi, 1
001E8EE6 lea      rdx, [rbp - 0x20]
001E8EEA mov      r9d, edi
001E8EED mov      r8d, edi
001E8EF0 mov      rcx, r12
001E8EF3 call     0x14040ede0
001E8EF8 lea      rdx, [rip + 0x4028ae]
001E8EFF mov      rcx, r15
001E8F02 call     0x1403fd810
001E8F07 mov      rax, qword ptr [rip + 0x47e63a]
001E8F0E mov      rcx, qword ptr [rax + 0x1090]
001E8F15 cmp      dword ptr [rcx + 0x7e54], 0
001E8F1C je       0x1401e8f2d
001E8F1E cmp      dword ptr [rcx + 0x7d98], 0
001E8F25 je       0x1401e8f2d
001E8F27 mov      eax, edi
001E8F29 xor      esi, esi
001E8F2B jmp      0x1401e8f31
001E8F2D xor      esi, esi
001E8F2F mov      eax, esi
001E8F31 mov      dword ptr [r14 + 0x80], 0x20002
001E8F3C lea      rcx, [rbp - 0x20]
001E8F40 test     eax, eax
001E8F42 je       0x1401e8f6f
001E8F44 lea      rdx, [rip + 0x3b0685]
001E8F4B call     0x1403ff7c0
001E8F50 mov      r9d, edi
001E8F53 lea      rdx, [rbp - 0x20]
001E8F57 mov      r8d, edi
001E8F5A lea      rcx, [r14 + 0x198]
001E8F61 call     0x14014d080
001E8F66 mov      dword ptr [r14 + 0x260], edi
001E8F6D jmp      0x1401e8f91
001E8F6F lea      rdx, [rip + 0x3b066a]
001E8F76 call     0x1403ff7c0
001E8F7B mov      r9d, edi
001E8F7E lea      rdx, [rbp - 0x20]
001E8F82 mov      r8d, edi
001E8F85 lea      rcx, [r14 + 0x198]
001E8F8C call     0x14014d080
001E8F91 xor      edx, edx
001E8F93 mov      rcx, r13
001E8F96 call     0x140412380
001E8F9B xor      edx, edx
001E8F9D mov      rcx, r13
001E8FA0 call     0x140411610
001E8FA5 mov      word ptr [r14 + 0x1f8], si
001E8FAD jmp      0x1401e9623
001E8FB2 lea      rdx, [rip + 0x3b05e7]
001E8FB9 lea      rcx, [rbp - 0x20]
001E8FBD call     0x1403ff7c0
001E8FC2 mov      ebx, 1
001E8FC7 lea      rdx, [rbp - 0x20]
001E8FCB mov      r9d, ebx
001E8FCE mov      r8d, ebx
001E8FD1 mov      rcx, r12
001E8FD4 call     0x14040ede0
001E8FD9 lea      rdx, [rip + 0x4027cd]
001E8FE0 mov      rcx, r15
001E8FE3 call     0x1403fd810
001E8FE8 mov      rax, qword ptr [rip + 0x47e559]
001E8FEF mov      rcx, qword ptr [rax + 0x1090]
001E8FF6 cmp      dword ptr [rcx + 0x7e54], edi
001E8FFC je       0x1401e900d
001E8FFE cmp      dword ptr [rcx + 0x7d98], edi
001E9004 je       0x1401e900d
001E9006 mov      dword ptr [r14 + 0x260], ebx
001E900D xor      edx, edx
001E900F mov      dword ptr [r14 + 0x80], 0x40004
001E901A mov      rcx, r13
001E901D call     0x140412380
001E9022 xor      edx, edx
001E9024 mov      rcx, r13
001E9027 call     0x140411610
001E902C mov      word ptr [r14 + 0x1f8], di
001E9034 jmp      0x1401e9623
001E9039 lea      rdx, [rip + 0x3b05b0]
001E9040 lea      rcx, [rbp - 0x20]
001E9044 call     0x1403ff7c0
001E9049 mov      ebx, 1
001E904E lea      rdx, [rbp - 0x20]
001E9052 mov      r9d, ebx
001E9055 mov      r8d, ebx
001E9058 mov      rcx, r12
001E905B call     0x14040ede0
001E9060 lea      rdx, [rip + 0x3b0599]
001E9067 mov      rcx, r15
001E906A call     0x1403fd810
001E906F mov      dword ptr [r14 + 0x258], ebx
001E9076 mov      dword ptr [r14 + 0x80], 0x5200520
001E9081 movzx    eax, byte ptr [rip + 0x3b1f78]
001E9088 shl      ax, 2
001E908C mov      word ptr [r14 + 0x8c], ax
001E9094 jmp      0x1401e961c
001E9099 movzx    ecx, byte ptr [rip + 0x3b1f60]
001E90A0 lea      rdx, [rip + 0x3b0561]
001E90A7 movzx    eax, cx
001E90AA shl      ax, 3
001E90AE add      cx, ax
001E90B1 mov      word ptr [r14 + 0x8c], cx
001E90B9 lea      rcx, [rbp - 0x20]
001E90BD call     0x1403ff7c0
001E90C2 mov      edi, 1
001E90C7 lea      rdx, [rbp - 0x20]
001E90CB mov      r9d, edi
001E90CE mov      r8d, edi
001E90D1 mov      rcx, r12
001E90D4 call     0x14040ede0
001E90D9 lea      rdx, [rip + 0x3b0530]
001E90E0 mov      rcx, r15
001E90E3 call     0x1403fd810
001E90E8 lea      rdx, [rip + 0x3b04c5]
001E90EF mov      dword ptr [r14 + 0x258], edi
001E90F6 lea      rcx, [rbp - 0x20]
001E90FA mov      dword ptr [r14 + 0x80], 0x6100600
001E9105 call     0x1403ff7c0
001E910A lea      rcx, [r14 + 0x198]
001E9111 mov      r9d, edi
001E9114 mov      r8d, edi
001E9117 lea      rdx, [rbp - 0x20]
001E911B call     0x14014d080
001E9120 lea      rdx, [r14 + 0x1c8]
001E9127 mov      rcx, r13
001E912A call     0x140412390
001E912F xor      edx, edx
001E9131 mov      rcx, r13
001E9134 call     0x140412380
001E9139 xor      edx, edx
001E913B mov      rcx, r13
001E913E call     0x140411610
001E9143 mov      qword ptr [r14 + 0x260], rdi
001E914A jmp      0x1401e9623
001E914F movzx    ecx, byte ptr [rip + 0x3b1eaa]
001E9156 lea      rdx, [rip + 0x3b04bb]
001E915D movzx    eax, cx
001E9160 shl      ax, 2
001E9164 add      cx, ax
001E9167 mov      word ptr [r14 + 0x8c], cx
001E916F lea      rcx, [rbp - 0x20]
001E9173 call     0x1403ff7c0
001E9178 mov      ebx, 1
001E917D lea      rdx, [rbp - 0x20]
001E9181 mov      r9d, ebx
001E9184 mov      r8d, ebx
001E9187 mov      rcx, r12
001E918A call     0x14040ede0
001E918F lea      rdx, [rip + 0x3b0492]
001E9196 mov      rcx, r15
001E9199 call     0x1403fd810
001E919E mov      dword ptr [r14 + 0x258], ebx
001E91A5 mov      dword ptr [r14 + 0x80], 0x7100700
001E91B0 jmp      0x1401e9623
001E91B5 movzx    eax, byte ptr [rip + 0x3b1e44]
001E91BC lea      rdx, [rip + 0x3b046d]
001E91C3 shl      ax, 2
001E91C7 lea      rcx, [rbp - 0x20]
001E91CB mov      word ptr [r14 + 0x8c], ax
001E91D3 call     0x1403ff7c0
001E91D8 mov      ebx, 1
001E91DD lea      rdx, [rbp - 0x20]
001E91E1 mov      r9d, ebx
001E91E4 mov      r8d, ebx
001E91E7 mov      rcx, r12
001E91EA call     0x14040ede0
001E91EF lea      rdx, [rip + 0x3b0442]
001E91F6 mov      rcx, r15
001E91F9 call     0x1403fd810
001E91FE mov      dword ptr [r14 + 0x258], ebx
001E9205 mov      dword ptr [r14 + 0x80], 0x8100800
001E9210 jmp      0x1401e9623
001E9215 movzx    eax, byte ptr [rip + 0x3b1de4]
001E921C lea      rdx, [rip + 0x3b03e5]
001E9223 imul     eax, eax, 0xf
001E9226 lea      rcx, [rbp - 0x20]
001E922A mov      word ptr [r14 + 0x8c], ax
001E9232 call     0x1403ff7c0
001E9237 mov      ebx, 1
001E923C lea      rdx, [rbp - 0x20]
001E9240 mov      r9d, ebx
001E9243 mov      r8d, ebx
001E9246 mov      rcx, r12
001E9249 call     0x14040ede0
001E924E lea      rdx, [rip + 0x3b03eb]
001E9255 mov      rcx, r15
001E9258 call     0x1403fd810
001E925D mov      dword ptr [r14 + 0x258], ebx
001E9264 mov      dword ptr [r14 + 0x80], 0x9100900
001E926F mov      qword ptr [r14 + 0x260], rbx
001E9276 jmp      0x1401e9623
001E927B movzx    ecx, byte ptr [rip + 0x3b1d7e]
001E9282 lea      rdx, [rip + 0x402524]
001E9289 movzx    eax, cx
001E928C shl      ax, 2
001E9290 add      cx, ax
001E9293 mov      word ptr [r14 + 0x8c], cx
001E929B mov      rcx, r15
001E929E call     0x1403fd810
001E92A3 mov      ecx, 1
001E92A8 mov      dword ptr [r14 + 0x80], 0xc100c00
001E92B3 mov      dword ptr [r14 + 0x258], ecx
001E92BA mov      qword ptr [r14 + 0x260], rcx
001E92C1 jmp      0x1401e9623
001E92C6 movzx    eax, byte ptr [rip + 0x3b1d33]
001E92CD lea      rdx, [rip + 0x3b0334]
001E92D4 shl      ax, 2
001E92D8 lea      rcx, [rbp - 0x20]
001E92DC mov      word ptr [r14 + 0x8c], ax
001E92E4 call     0x1403ff7c0
001E92E9 mov      ebx, 1
001E92EE lea      rdx, [rbp - 0x20]
001E92F2 mov      r9d, ebx
001E92F5 mov      r8d, ebx
001E92F8 mov      rcx, r12
001E92FB call     0x14040ede0
001E9300 lea      rdx, [rip + 0x4024a6]
001E9307 mov      rcx, r15
001E930A call     0x1403fd810
001E930F lea      rdx, [rip + 0x3b0332]
001E9316 mov      dword ptr [r14 + 0x80], 0xa100a00
001E9321 lea      rcx, [rbp - 0x20]
001E9325 call     0x1403ff7c0
001E932A lea      rcx, [r14 + 0x198]
001E9331 mov      r9d, ebx
001E9334 mov      r8d, ebx
001E9337 lea      rdx, [rbp - 0x20]
001E933B call     0x14014d080
001E9340 xor      edx, edx
001E9342 mov      rcx, r13
001E9345 call     0x140412380
001E934A xor      edx, edx
001E934C mov      rcx, r13
001E934F call     0x140411610
001E9354 mov      qword ptr [r14 + 0x260], rbx
001E935B jmp      0x1401e9623
001E9360 movzx    ecx, byte ptr [rip + 0x3b1c99]
001E9367 lea      rdx, [rip + 0x3b029a]
001E936E movzx    eax, cx
001E9371 shl      ax, 2
001E9375 add      cx, ax
001E9378 mov      word ptr [r14 + 0x8c], cx
001E9380 lea      rcx, [rbp - 0x20]
001E9384 call     0x1403ff7c0
001E9389 mov      ebx, 1
001E938E lea      rdx, [rbp - 0x20]
001E9392 mov      r9d, ebx
001E9395 mov      r8d, ebx
001E9398 mov      rcx, r12
001E939B call     0x14040ede0
001E93A0 lea      rdx, [rip + 0x3b02b1]
001E93A7 mov      rcx, r15
001E93AA call     0x1403fd810
001E93AF lea      rdx, [rip + 0x3b02aa]
001E93B6 mov      dword ptr [r14 + 0x258], ebx
001E93BD mov      dword ptr [r14 + 0x80], 0xa110a01
001E93C8 jmp      0x1401e9321
001E93CD movzx    eax, byte ptr [rip + 0x3b1c2c]
001E93D4 lea      rdx, [rip + 0x3b0255]
001E93DB shl      ax, 2
001E93DF lea      rcx, [rbp - 0x20]
001E93E3 mov      word ptr [r14 + 0x8c], ax
001E93EB call     0x1403ff7c0
001E93F0 mov      ebx, 1
001E93F5 lea      rdx, [rbp - 0x20]
001E93F9 mov      r9d, ebx
001E93FC mov      r8d, ebx
001E93FF mov      rcx, r12
001E9402 call     0x14040ede0
001E9407 lea      rdx, [rip + 0x3b0262]
001E940E mov      rcx, r15
001E9411 call     0x1403fd810
001E9416 lea      rdx, [rip + 0x3b025b]
001E941D mov      dword ptr [r14 + 0x258], ebx
001E9424 lea      rcx, [rbp - 0x20]
001E9428 mov      dword ptr [r14 + 0x80], 0xa120a02
001E9433 call     0x1403ff7c0
001E9438 lea      rcx, [r14 + 0x198]
001E943F mov      r9d, ebx
001E9442 mov      r8d, ebx
001E9445 lea      rdx, [rbp - 0x20]
001E9449 call     0x14014d080
001E944E xor      edx, edx
001E9450 mov      rcx, r13
001E9453 call     0x140412380
001E9458 xor      edx, edx
001E945A mov      rcx, r13
001E945D call     0x140411610
001E9462 mov      dword ptr [r14 + 0x25c], ebx
001E9469 mov      qword ptr [r14 + 0x260], rbx
001E9470 jmp      0x1401e9623
001E9475 lea      rdx, [rip + 0x3b01b4]
001E947C lea      rcx, [rbp - 0x20]
001E9480 call     0x1403ff7c0
001E9485 mov      ebx, 1
001E948A lea      rdx, [rbp - 0x20]
001E948E mov      r9d, ebx
001E9491 mov      r8d, ebx
001E9494 mov      rcx, r12
001E9497 call     0x14040ede0
001E949C lea      rdx, [rip + 0x40230a]
001E94A3 mov      rcx, r15
001E94A6 call     0x1403fd810
001E94AB mov      dword ptr [r14 + 0x80], 0xb030b03
001E94B6 jmp      0x1401e9615
001E94BB movzx    ecx, byte ptr [rip + 0x3b1b3e]
001E94C2 lea      rdx, [rip + 0x3b0167]
001E94C9 movzx    eax, cx
001E94CC add      ax, ax
001E94CF add      cx, ax
001E94D2 mov      word ptr [r14 + 0x8c], cx
001E94DA lea      rcx, [rbp - 0x20]
001E94DE call     0x1403ff7c0
001E94E3 mov      ebx, 1
001E94E8 lea      rdx, [rbp - 0x20]
001E94EC mov      r9d, ebx
001E94EF mov      r8d, ebx
001E94F2 mov      rcx, r12
001E94F5 call     0x14040ede0
001E94FA lea      rdx, [rip + 0x4022ac]
001E9501 mov      rcx, r15
001E9504 call     0x1403fd810
001E9509 mov      dword ptr [r14 + 0x80], 0xb010b01
001E9514 jmp      0x1401e9615
001E9519 movzx    eax, byte ptr [rip + 0x3b1ae0]
001E9520 lea      rdx, [rip + 0x3b00e1]
001E9527 add      ax, ax
001E952A lea      rcx, [rbp - 0x20]
001E952E mov      word ptr [r14 + 0x8c], ax
001E9536 call     0x1403ff7c0
001E953B mov      ebx, 1
001E9540 lea      rdx, [rbp - 0x20]
001E9544 mov      r9d, ebx
001E9547 mov      r8d, ebx
001E954A mov      rcx, r12
001E954D call     0x14040ede0
001E9552 lea      rdx, [rip + 0x402254]
001E9559 mov      rcx, r15
001E955C call     0x1403fd810
001E9561 mov      dword ptr [r14 + 0x80], 0xa230a03
001E956C mov      qword ptr [r14 + 0x260], rbx
001E9573 jmp      0x1401e9623
001E9578 movzx    eax, byte ptr [rip + 0x3b1a81]
001E957F lea      rdx, [rip + 0x3b0082]
001E9586 add      ax, ax
001E9589 lea      rcx, [rbp - 0x20]
001E958D mov      word ptr [r14 + 0x8c], ax
001E9595 call     0x1403ff7c0
001E959A mov      ebx, 1
001E959F lea      rdx, [rbp - 0x20]
001E95A3 mov      r9d, ebx
001E95A6 mov      r8d, ebx
001E95A9 mov      rcx, r12
001E95AC call     0x14040ede0
001E95B1 lea      rdx, [rip + 0x4021f5]
001E95B8 mov      rcx, r15
001E95BB call     0x1403fd810
001E95C0 mov      dword ptr [r14 + 0x80], 0xa240a04
001E95CB mov      qword ptr [r14 + 0x260], rbx
001E95D2 jmp      0x1401e9623
001E95D4 lea      rdx, [rip + 0x3b002d]
001E95DB lea      rcx, [rbp - 0x20]
001E95DF call     0x1403ff7c0
001E95E4 mov      ebx, 1
001E95E9 lea      rdx, [rbp - 0x20]
001E95ED mov      r9d, ebx
001E95F0 mov      r8d, ebx
001E95F3 mov      rcx, r12
001E95F6 call     0x14040ede0
001E95FB lea      rdx, [rip + 0x4021ab]
001E9602 mov      rcx, r15
001E9605 call     0x1403fd810
001E960A mov      dword ptr [r14 + 0x80], 0xb040b04
001E9615 mov      dword ptr [r14 + 0x26c], ebx
001E961C mov      dword ptr [r14 + 0x260], ebx
001E9623 mov      rax, r14
001E9626 mov      rcx, qword ptr [rbp - 0x10]
001E962A xor      rcx, rsp
001E962D call     0x1404f77a0
001E9632 mov      rbx, qword ptr [rsp + 0x88]
001E963A add      rsp, 0x40
001E963E pop      r15
001E9640 pop      r14
001E9642 pop      r13
001E9644 pop      r12
001E9646 pop      rdi
001E9647 pop      rsi
001E9648 pop      rbp
001E9649 ret      
001E964A nop      
001E964C mov      word ptr [rsi], ds
001E964F add      byte ptr [rcx], bh
001E9651 nop      
