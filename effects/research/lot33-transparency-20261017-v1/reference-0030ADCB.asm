0030ADCB mov      qword ptr [rsp + 0x98], rbx
0030ADD3 and      eax, 0xf00
0030ADD8 cmp      eax, 0x700
0030ADDD ja       0x14030b794
0030ADE3 je       0x14030b731
0030ADE9 cmp      eax, 0x300
0030ADEE ja       0x14030b2ab
0030ADF4 je       0x14030b207
0030ADFA test     eax, eax
0030ADFC je       0x14030af7f
0030AE02 cmp      eax, 0x100
0030AE07 je       0x14030aee5
0030AE0D cmp      eax, 0x200
0030AE12 jne      0x14030b3ea
0030AE18 lea      rdx, [rip + 0x2a0501]
0030AE1F lea      rcx, [rbp - 0x38]
0030AE23 call     0x1403ff7c0
0030AE28 mov      ebx, 1
0030AE2D lea      rcx, [rsi + 0xde8]
0030AE34 mov      r9d, ebx
0030AE37 lea      rdx, [rbp - 0x38]
0030AE3B mov      r8d, ebx
0030AE3E call     0x14014d080
0030AE43 lea      rdx, [rip + 0x2a04c6]
0030AE4A lea      rcx, [rbp - 0x38]
0030AE4E call     0x1403ff7c0
0030AE53 lea      rcx, [rsi + 0xf20]
0030AE5A mov      r9d, ebx
0030AE5D mov      r8d, ebx
0030AE60 lea      rdx, [rbp - 0x38]
0030AE64 call     0x14014d080
0030AE69 and      edi, 0xf0
0030AE6F je       0x14030aed0
0030AE71 cmp      edi, 0x10
0030AE74 je       0x14030aec1
0030AE76 cmp      edi, 0x20
0030AE79 je       0x14030aead
0030AE7B cmp      edi, 0x30
0030AE7E je       0x14030ae99
0030AE80 cmp      edi, 0x40
0030AE83 jne      0x14030aed9
0030AE85 mov      eax, 4
0030AE8A mov      word ptr [rsi + 0xf86], ax
0030AE91 movzx    edx, ax
0030AE94 jmp      0x14030b6d0
0030AE99 mov      eax, 3
0030AE9E mov      word ptr [rsi + 0xf86], ax
0030AEA5 movzx    edx, ax
0030AEA8 jmp      0x14030b6d0
0030AEAD mov      eax, 2
0030AEB2 mov      word ptr [rsi + 0xf86], ax
0030AEB9 movzx    edx, ax
0030AEBC jmp      0x14030b6d0
0030AEC1 mov      word ptr [rsi + 0xf86], bx
0030AEC8 movzx    edx, bx
0030AECB jmp      0x14030b6d0
0030AED0 xor      edi, edi
0030AED2 mov      word ptr [rsi + 0xf86], di
0030AED9 movzx    edx, word ptr [rsi + 0xf86]
0030AEE0 jmp      0x14030b6d0
0030AEE5 lea      rdx, [rip + 0x2a0414]
0030AEEC lea      rcx, [rbp - 0x38]
0030AEF0 call     0x1403ff7c0
0030AEF5 mov      ebx, 1
0030AEFA lea      rcx, [rsi + 0xde8]
0030AF01 mov      r9d, ebx
0030AF04 lea      rdx, [rbp - 0x38]
0030AF08 mov      r8d, ebx
0030AF0B call     0x14014d080
0030AF10 lea      rdx, [rip + 0x2a03f9]
0030AF17 lea      rcx, [rbp - 0x38]
0030AF1B call     0x1403ff7c0
0030AF20 lea      rcx, [rsi + 0xf20]
0030AF27 mov      r9d, ebx
0030AF2A mov      r8d, ebx
0030AF2D lea      rdx, [rbp - 0x38]
0030AF31 call     0x14014d080
0030AF36 xor      bl, bl
0030AF38 nop      dword ptr [rax + rax]
0030AF40 mov      rax, qword ptr [rip + 0x35c601]
0030AF47 mov      rcx, r12
0030AF4A movzx    r8d, byte ptr [r14]
0030AF4E movzx    edx, bl
0030AF51 mov      r9, qword ptr [rax + 0x1090]
0030AF58 add      r9, 0x63d8
0030AF5F call     0x1404221c0
0030AF64 inc      bl
0030AF66 lea      r14, [r14 + 1]
0030AF6A cmp      bl, 7
0030AF6D jb       0x14030af40
0030AF6F mov      rdx, r12
0030AF72 mov      rcx, r15
0030AF75 call     0x140412390
0030AF7A jmp      0x14030b6ab
0030AF7F and      edi, 0xf
0030AF82 je       0x14030b137
0030AF88 sub      edi, 1
0030AF8B je       0x14030b0d3
0030AF91 sub      edi, 1
0030AF94 je       0x14030b086
0030AF9A sub      edi, 1
0030AF9D je       0x14030aff6
0030AF9F cmp      edi, 1
0030AFA2 jne      0x14030b3da
0030AFA8 lea      rdx, [rip + 0x2a0321]
0030AFAF lea      rcx, [rbp - 0x38]
0030AFB3 call     0x1403ff7c0
0030AFB8 mov      ebx, edi
0030AFBA lea      rcx, [rsi + 0xde8]
0030AFC1 mov      r9d, ebx
0030AFC4 lea      rdx, [rbp - 0x38]
0030AFC8 mov      r8d, ebx
0030AFCB call     0x14014d080
0030AFD0 xor      edi, edi
0030AFD2 xor      edx, edx
0030AFD4 mov      rcx, r15
0030AFD7 mov      word ptr [rsi + 0xf86], di
0030AFDE call     0x140412380
0030AFE3 xor      edx, edx
0030AFE5 mov      rcx, r15
0030AFE8 call     0x140411610
0030AFED lea      rdx, [rip + 0x2a02fc]
0030AFF4 jmp      0x14030b05c
0030AFF6 lea      rdx, [rip + 0x2a02bb]
0030AFFD lea      rcx, [rbp - 0x38]
0030B001 call     0x1403ff7c0
0030B006 mov      ebx, 1
0030B00B lea      rcx, [rsi + 0xde8]
0030B012 mov      r9d, ebx
0030B015 lea      rdx, [rbp - 0x38]
0030B019 mov      r8d, ebx
0030B01C call     0x14014d080
0030B021 xor      edi, edi
0030B023 xor      edx, edx
0030B025 mov      rcx, r15
0030B028 mov      word ptr [rsi + 0xf86], di
0030B02F call     0x140412380
0030B034 xor      edx, edx
0030B036 mov      rcx, r15
0030B039 call     0x140411610
0030B03E lea      rcx, [rsi + 0x5f7]
0030B045 lea      r8, [rip + 0x2a0278]
0030B04C lea      rdx, [rbp - 0x38]
0030B050 call     0x1403ff960
0030B055 lea      rdx, [rip + 0x2a0284]
0030B05C lea      rcx, [rbp - 0x38]
0030B060 mov      dword ptr [rsi + 0xba8], ebx
0030B066 call     0x1403ff7c0
0030B06B lea      rcx, [rsi + 0xbb0]
0030B072 mov      r9d, ebx
0030B075 mov      r8d, ebx
0030B078 lea      rdx, [rbp - 0x38]
0030B07C call     0x14018aa40
0030B081 jmp      0x14030b3dc
0030B086 lea      rdx, [rip + 0x2a0243]
0030B08D lea      rcx, [rbp - 0x38]
0030B091 call     0x1403ff7c0
0030B096 mov      ebx, 1
0030B09B lea      rcx, [rsi + 0xde8]
0030B0A2 mov      r9d, ebx
0030B0A5 lea      rdx, [rbp - 0x38]
0030B0A9 mov      r8d, ebx
0030B0AC call     0x14014d080
0030B0B1 xor      edi, edi
0030B0B3 xor      edx, edx
0030B0B5 mov      rcx, r15
0030B0B8 mov      word ptr [rsi + 0xf86], di
0030B0BF call     0x140412380
0030B0C4 xor      edx, edx
0030B0C6 mov      rcx, r15
0030B0C9 call     0x140411610
0030B0CE jmp      0x14030b3dc
0030B0D3 lea      rdx, [rip + 0x2a01de]
0030B0DA lea      rcx, [rbp - 0x38]
0030B0DE call     0x1403ff7c0
0030B0E3 mov      ebx, 1
0030B0E8 lea      rcx, [rsi + 0xde8]
0030B0EF mov      r9d, ebx
0030B0F2 lea      rdx, [rbp - 0x38]
0030B0F6 mov      r8d, ebx
0030B0F9 call     0x14014d080
0030B0FE xor      edi, edi
0030B100 xor      edx, edx
0030B102 mov      rcx, r15
0030B105 mov      word ptr [rsi + 0xf86], di
0030B10C call     0x140412380
0030B111 xor      edx, edx
0030B113 mov      rcx, r15
0030B116 call     0x140411610
0030B11B lea      rcx, [rsi + 0x5f7]
0030B122 lea      r8, [rip + 0x2a019b]
0030B129 lea      rdx, [rbp - 0x38]
0030B12D call     0x1403ff960
0030B132 jmp      0x14030b3dc
0030B137 lea      rdx, [rip + 0x2a016a]
0030B13E lea      rcx, [rbp - 0x38]
0030B142 call     0x1403ff7c0
0030B147 mov      ebx, 1
0030B14C lea      rcx, [rsi + 0xde8]
0030B153 mov      r9d, ebx
0030B156 lea      rdx, [rbp - 0x38]
0030B15A mov      r8d, ebx
0030B15D call     0x14014d080
0030B162 xor      bl, bl
0030B164 nop      dword ptr [rax]
0030B168 nop      dword ptr [rax + rax]
0030B170 mov      rax, qword ptr [rip + 0x35c3d1]
0030B177 mov      rcx, r12
0030B17A movzx    r8d, byte ptr [r14]
0030B17E movzx    edx, bl
0030B181 mov      r9, qword ptr [rax + 0x1090]
0030B188 add      r9, 0x63d8
0030B18F call     0x1404221c0
0030B194 inc      bl
0030B196 lea      r14, [r14 + 1]
0030B19A cmp      bl, 7
0030B19D jb       0x14030b170
0030B19F mov      rdx, r12
0030B1A2 mov      rcx, r15
0030B1A5 call     0x140412390
0030B1AA xor      edi, edi
0030B1AC xor      edx, edx
0030B1AE mov      rcx, r15
0030B1B1 mov      word ptr [rsi + 0xf86], di
0030B1B8 call     0x140412380
0030B1BD movzx    edx, word ptr [r15 + 0x11a]
0030B1C5 mov      rcx, r15
0030B1C8 call     0x140411cc0
0030B1CD movzx    ebx, al
0030B1D0 call     0x14050933c
0030B1D5 mov      edx, eax
0030B1D7 mov      rcx, r15
0030B1DA and      edx, 0x7fff
0030B1E0 imul     edx, ebx
0030B1E3 shr      edx, 0xf
0030B1E6 call     0x140411610
0030B1EB lea      rcx, [rsi + 0x5f7]
0030B1F2 lea      r8, [rip + 0x2a00b7]
0030B1F9 lea      rdx, [rbp - 0x38]
0030B1FD call     0x1403ff960
0030B202 jmp      0x14030b3dc
0030B207 lea      rdx, [rip + 0x2a011a]
0030B20E lea      rcx, [rbp - 0x38]
0030B212 call     0x1403ff7c0
0030B217 mov      ebx, 1
0030B21C lea      rcx, [rsi + 0xde8]
0030B223 mov      r9d, ebx
0030B226 lea      rdx, [rbp - 0x38]
0030B22A mov      r8d, ebx
0030B22D call     0x14014d080
0030B232 xor      bl, bl
0030B234 nop      dword ptr [rax]
0030B238 nop      dword ptr [rax + rax]
0030B240 mov      rax, qword ptr [rip + 0x35c301]
0030B247 mov      rcx, r12
0030B24A movzx    r8d, byte ptr [r14]
0030B24E movzx    edx, bl
0030B251 mov      r9, qword ptr [rax + 0x1090]
0030B258 add      r9, 0x63d8
0030B25F call     0x1404221c0
0030B264 inc      bl
0030B266 lea      r14, [r14 + 1]
0030B26A cmp      bl, 7
0030B26D jb       0x14030b240
0030B26F mov      rdx, r12
0030B272 mov      rcx, r15
0030B275 call     0x140412390
0030B27A and      r13w, 0xf
0030B27F mov      rcx, r15
0030B282 movzx    edx, r13w
0030B286 mov      word ptr [rsi + 0xf86], r13w
0030B28E call     0x140412380
0030B293 xor      edx, edx
0030B295 mov      rcx, r15
0030B298 call     0x140411610
0030B29D xor      edi, edi
0030B29F mov      byte ptr [rsi + 0xf80], 1
0030B2A6 jmp      0x14030b3e3
0030B2AB cmp      eax, 0x400
0030B2B0 je       0x14030b644
0030B2B6 cmp      eax, 0x500
0030B2BB je       0x14030b45e
0030B2C1 cmp      eax, 0x600
0030B2C6 jne      0x14030b3ea
0030B2CC and      edi, 0xf0
0030B2D2 je       0x14030b34f
0030B2D4 cmp      edi, 0x10
0030B2D7 jne      0x14030b3da
0030B2DD lea      rdx, [rip + 0x2a008c]
0030B2E4 lea      rcx, [rbp - 0x38]
0030B2E8 call     0x1403ff7c0
0030B2ED mov      ebx, 1
0030B2F2 lea      rcx, [rsi + 0xde8]
0030B2F9 mov      r9d, ebx
0030B2FC lea      rdx, [rbp - 0x38]
0030B300 mov      r8d, ebx
0030B303 call     0x14014d080
0030B308 xor      edi, edi
0030B30A xor      edx, edx
0030B30C mov      rcx, r15
0030B30F mov      word ptr [rsi + 0xf86], di
0030B316 call     0x140412380
0030B31B xor      edx, edx
0030B31D mov      rcx, r15
0030B320 call     0x140411610
0030B325 call     0x14050933c
0030B32A and      eax, 0x7fff
0030B32F lea      eax, [rax + rax*2]
0030B332 cmp      eax, 0x8000
0030B337 jb       0x14030b340
0030B339 mov      byte ptr [rsi + 0xf81], dil
0030B340 mov      dword ptr [rsi + 0xf82], 0x1400c8
0030B34A jmp      0x14030b3dc
0030B34F lea      rdx, [rip + 0x29fffa]
0030B356 lea      rcx, [rbp - 0x38]
0030B35A call     0x1403ff7c0
0030B35F mov      ebx, 1
0030B364 lea      rcx, [rsi + 0xde8]
0030B36B mov      r9d, ebx
0030B36E lea      rdx, [rbp - 0x38]
0030B372 mov      r8d, ebx
0030B375 call     0x14014d080
0030B37A mov      edx, ebx
0030B37C mov      word ptr [rsi + 0xf86], bx
0030B383 mov      rcx, r15
0030B386 call     0x140412380
0030B38B xor      edx, edx
0030B38D mov      rcx, r15
0030B390 call     0x140411610
0030B395 xor      bl, bl
0030B397 nop      word ptr [rax + rax]
0030B3A0 mov      rax, qword ptr [rip + 0x35c1a1]
0030B3A7 mov      rcx, r12
0030B3AA movzx    r8d, byte ptr [r14]
0030B3AE movzx    edx, bl
0030B3B1 mov      r9, qword ptr [rax + 0x1090]
0030B3B8 add      r9, 0x63d8
0030B3BF call     0x1404221c0
0030B3C4 inc      bl
0030B3C6 lea      r14, [r14 + 1]
0030B3CA cmp      bl, 7
0030B3CD jb       0x14030b3a0
0030B3CF mov      rdx, r12
0030B3D2 mov      rcx, r15
0030B3D5 call     0x140412390
0030B3DA xor      edi, edi
0030B3DC mov      byte ptr [rsi + 0x5f6], 1
0030B3E3 mov      qword ptr [rsi + 0xcd8], rdi
0030B3EA mov      rbx, qword ptr [rsp + 0x98]
