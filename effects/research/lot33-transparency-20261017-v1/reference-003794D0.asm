003794D0 mov      qword ptr [rsp + 0x18], rbx
003794D5 push     rbp
003794D6 push     rsi
003794D7 push     r12
003794D9 push     r14
003794DB push     r15
003794DD mov      rbp, rsp
003794E0 sub      rsp, 0x40
003794E4 mov      rax, qword ptr [rip + 0x2eb4ed]
003794EB xor      rax, rsp
003794EE mov      qword ptr [rbp - 0x10], rax
003794F2 mov      rsi, rcx
003794F5 movzx    r15d, r9b
003794F9 lea      rcx, [rbp - 0x20]
003794FD movzx    r14d, r8b
00379501 movzx    ebx, dl
00379504 call     0x1403ff870
00379509 mov      rcx, qword ptr [rsi + 0x3c58]
00379510 xor      r12d, r12d
00379513 mov      byte ptr [rsi + 0x3c6a], 0
0037951A test     rcx, rcx
0037951D je       0x14037953e
0037951F call     0x14045e690
00379524 mov      rcx, qword ptr [rsi + 0x3c60]
0037952B mov      qword ptr [rsi + 0x3c58], r12
00379532 call     0x14045e690
00379537 mov      qword ptr [rsi + 0x3c60], r12
0037953E mov      qword ptr [rsp + 0x78], rdi
00379543 mov      dword ptr [rsi + 0x3f48], r12d
0037954A mov      dword ptr [rsi + 0x3dd8], r12d
00379551 mov      word ptr [rsi + 0x3c6c], 0x100
0037955A mov      byte ptr [rsi + 0x3c69], r12b
00379561 mov      byte ptr [rsi + 0x3c6b], 1
00379568 movzx    ecx, bl
0037956B test     bl, bl
0037956D je       0x140379c69
00379573 sub      ecx, 1
00379576 je       0x140379a2b
0037957C sub      ecx, 1
0037957F je       0x140379849
00379585 sub      ecx, 1
00379588 je       0x1403795f3
0037958A cmp      ecx, 1
0037958D jne      0x140379d57
00379593 mov      rax, qword ptr [rip + 0x2edfae]
0037959A lea      rdx, [rbp - 0x18]
0037959E lea      rcx, [rbp - 0x20]
003795A2 mov      r8, qword ptr [rax + 0x1090]
003795A9 add      r8, 0x3d60
003795B0 call     0x1403ff880
003795B5 lea      rcx, [rbp - 0x20]
003795B9 call     0x140400020
003795BE test     eax, eax
003795C0 je       0x1403795e7
003795C2 lea      rdx, [rip + 0x288d9f]
003795C9 lea      rcx, [rbp - 0x20]
003795CD call     0x1403ffb60
003795D2 test     eax, eax
003795D4 je       0x1403795e7
003795D6 mov      rdx, qword ptr [rbp - 0x20]
003795DA mov      rcx, rsi
003795DD call     0x14034a700
003795E2 jmp      0x140379d57
003795E7 mov      byte ptr [rsi + 0x3c6b], r12b
003795EE jmp      0x140379d57
003795F3 mov      rax, qword ptr [rip + 0x2edf4e]
003795FA lea      rdx, [rbp - 0x18]
003795FE lea      rcx, [rbp - 0x20]
00379602 mov      r8, qword ptr [rax + 0x1090]
00379609 add      r8, 0x3d50
00379610 call     0x1403ff880
00379615 lea      rcx, [rbp - 0x20]
00379619 call     0x140400020
0037961E test     eax, eax
00379620 je       0x140379647
00379622 lea      rdx, [rip + 0x288d3f]
00379629 lea      rcx, [rbp - 0x20]
0037962D call     0x1403ffb60
00379632 test     eax, eax
00379634 je       0x140379647
00379636 mov      rdx, qword ptr [rbp - 0x20]
0037963A mov      rcx, rsi
0037963D call     0x14034a700
00379642 jmp      0x1403796f0
00379647 lea      rdx, [rip + 0x23410a]
0037964E lea      rcx, [rbp - 0x18]
00379652 call     0x1403ff7c0
00379657 mov      r9d, 1
0037965D lea      rcx, [rsi + 0x3ee8]
00379664 mov      r8d, r9d
00379667 lea      rdx, [rbp - 0x18]
0037966B call     0x14014d080
00379670 mov      rax, qword ptr [rip + 0x2eded1]
00379677 lea      rcx, [rsi + 0x3f18]
0037967E xor      edx, edx
00379680 mov      r9, qword ptr [rax + 0x1090]
00379687 add      r9, 0x63d8
0037968E lea      r8d, [rdx + 0x47]
00379692 call     0x1404221c0
00379697 mov      rax, qword ptr [rip + 0x2edeaa]
0037969E lea      rcx, [rsi + 0x3f18]
003796A5 mov      edx, 1
003796AA mov      r9, qword ptr [rax + 0x1090]
003796B1 add      r9, 0x63d8
003796B8 lea      r8d, [rdx + 0x40]
003796BC call     0x1404221c0
003796C1 lea      rdx, [rsi + 0x3f18]
003796C8 lea      rcx, [rsi + 0x3de0]
003796CF call     0x140412390
003796D4 xor      edx, edx
003796D6 lea      rcx, [rsi + 0x3de0]
003796DD call     0x140412380
003796E2 xor      edx, edx
003796E4 lea      rcx, [rsi + 0x3de0]
003796EB call     0x140411610
003796F0 mov      rax, qword ptr [rip + 0x2ede51]
003796F7 lea      rdx, [rbp - 0x18]
003796FB lea      rcx, [rbp - 0x20]
003796FF mov      r8, qword ptr [rax + 0x1090]
00379706 add      r8, 0x3cd0
0037970D call     0x1403ff880
00379712 lea      rcx, [rbp - 0x20]
00379716 call     0x140400020
0037971B test     eax, eax
0037971D je       0x140379763
0037971F lea      rdx, [rip + 0x288c42]
00379726 lea      rcx, [rbp - 0x20]
0037972A call     0x1403ffb60
0037972F test     eax, eax
00379731 je       0x140379763
00379733 mov      r9d, 1
00379739 lea      rcx, [rsi + 0x3d78]
00379740 mov      r8d, r9d
00379743 lea      rdx, [rbp - 0x20]
00379747 call     0x14014d080
0037974C mov      eax, 0x208
00379751 lea      rdi, [rsi + 0x3c70]
00379758 mov      dword ptr [rsi + 0x3dd8], eax
0037975E jmp      0x1403797f3
00379763 lea      rdx, [rip + 0x233ffa]
0037976A lea      rcx, [rbp - 0x18]
0037976E call     0x1403ff7c0
00379773 mov      r9d, 1
00379779 lea      rcx, [rsi + 0x3d78]
00379780 mov      r8d, r9d
00379783 lea      rdx, [rbp - 0x18]
00379787 call     0x14014d080
0037978C mov      rax, qword ptr [rip + 0x2eddb5]
00379793 lea      rcx, [rsi + 0x3da8]
0037979A xor      edx, edx
0037979C mov      r9, qword ptr [rax + 0x1090]
003797A3 add      r9, 0x63d8
003797AA lea      r8d, [rdx + 0x47]
003797AE call     0x1404221c0
003797B3 mov      rax, qword ptr [rip + 0x2edd8e]
003797BA lea      rcx, [rsi + 0x3da8]
003797C1 mov      edx, 1
003797C6 mov      r9, qword ptr [rax + 0x1090]
003797CD add      r9, 0x63d8
003797D4 lea      r8d, [rdx + 0x40]
003797D8 call     0x1404221c0
003797DD lea      rdi, [rsi + 0x3c70]
003797E4 mov      rcx, rdi
003797E7 lea      rdx, [rsi + 0x3da8]
003797EE call     0x140412390
003797F3 xor      edx, edx
003797F5 mov      rcx, rdi
003797F8 call     0x140412380
003797FD lea      rcx, [rsi + 0x3c70]
00379804 mov      byte ptr [rsi + 0x3c69], 1
0037980B movzx    edx, word ptr [rcx + 0x11a]
00379812 call     0x140411cc0
00379817 mov      byte ptr [rsi + 0x3c6b], al
0037981D mov      byte ptr [rsi + 0x3f64], 1
00379824 movzx    ecx, r14b
00379828 test     r14b, r14b
0037982B je       0x14037983b
0037982D sub      ecx, 1
00379830 je       0x14037983b
00379832 cmp      ecx, 1
00379835 jne      0x140379d57
0037983B mov      word ptr [rsi + 0x3c6c], 0x100
00379844 jmp      0x140379d57
00379849 mov      rax, qword ptr [rip + 0x2edcf8]
00379850 lea      rdx, [rbp - 0x18]
00379854 lea      rcx, [rbp - 0x20]
00379858 mov      r8, qword ptr [rax + 0x1090]
0037985F add      r8, 0x3d48
00379866 call     0x1403ff880
0037986B lea      rcx, [rbp - 0x20]
0037986F call     0x140400020
00379874 test     eax, eax
00379876 je       0x14037989a
00379878 lea      rdx, [rip + 0x288ae9]
0037987F lea      rcx, [rbp - 0x20]
00379883 call     0x1403ffb60
00379888 test     eax, eax
0037988A je       0x14037989a
0037988C mov      rdx, qword ptr [rbp - 0x20]
00379890 mov      rcx, rsi
00379893 call     0x14034a700
00379898 jmp      0x140379902
0037989A lea      rdx, [rip + 0x233ecf]
003798A1 lea      rcx, [rbp - 0x18]
003798A5 call     0x1403ff7c0
003798AA mov      r9d, 1
003798B0 lea      rcx, [rsi + 0x3ee8]
003798B7 mov      r8d, r9d
003798BA lea      rdx, [rbp - 0x18]
003798BE call     0x14014d080
003798C3 mov      dword ptr [rsi + 0x3f48], 8
003798CD lea      rcx, [rsi + 0x3de0]
003798D4 movzx    r9d, word ptr [rip + 0x246d9c]
003798DC xor      r8d, r8d
003798DF xor      edx, edx
003798E1 call     0x1404123c0
003798E6 xor      edx, edx
003798E8 lea      rcx, [rsi + 0x3de0]
003798EF call     0x140412380
003798F4 xor      edx, edx
003798F6 lea      rcx, [rsi + 0x3de0]
003798FD call     0x140411610
00379902 mov      rax, qword ptr [rip + 0x2edc3f]
00379909 lea      rdx, [rbp - 0x18]
0037990D lea      rcx, [rbp - 0x20]
00379911 mov      r8, qword ptr [rax + 0x1090]
00379918 add      r8, 0x3cc8
0037991F call     0x1403ff880
00379924 lea      rcx, [rbp - 0x20]
00379928 call     0x140400020
0037992D test     eax, eax
0037992F je       0x14037996c
00379931 lea      rdx, [rip + 0x288a30]
00379938 lea      rcx, [rbp - 0x20]
0037993C call     0x1403ffb60
00379941 test     eax, eax
00379943 je       0x14037996c
00379945 mov      r9d, 1
0037994B lea      rcx, [rsi + 0x3d78]
00379952 mov      r8d, r9d
00379955 lea      rdx, [rbp - 0x20]
00379959 call     0x14014d080
0037995E mov      eax, 0x208
00379963 lea      rbx, [rsi + 0x3c70]
0037996A jmp      0x1403799b6
0037996C lea      rdx, [rip + 0x233e0d]
00379973 lea      rcx, [rbp - 0x18]
00379977 call     0x1403ff7c0
0037997C mov      r9d, 1
00379982 lea      rcx, [rsi + 0x3d78]
00379989 mov      r8d, r9d
0037998C lea      rdx, [rbp - 0x18]
00379990 call     0x14014d080
00379995 movzx    r9d, word ptr [rip + 0x246cdb]
0037999D lea      rbx, [rsi + 0x3c70]
003799A4 mov      rcx, rbx
003799A7 xor      r8d, r8d
003799AA xor      edx, edx
003799AC call     0x1404123c0
003799B1 mov      eax, 8
003799B6 xor      edx, edx
003799B8 mov      dword ptr [rsi + 0x3dd8], eax
003799BE mov      rcx, rbx
003799C1 call     0x140412380
003799C6 mov      rcx, rbx
003799C9 call     0x140411af0
003799CE lea      rcx, [rsi + 0x3c70]
003799D5 mov      byte ptr [rsi + 0x3c69], al
003799DB movzx    edx, word ptr [rcx + 0x11a]
003799E2 call     0x140411cc0
003799E7 mov      byte ptr [rsi + 0x3f64], r12b
003799EE mov      byte ptr [rsi + 0x3c6b], al
003799F4 movzx    ecx, r14b
003799F8 test     r14b, r14b
003799FB je       0x140379c5b
00379A01 sub      ecx, 1
00379A04 je       0x140379a1d
00379A06 cmp      ecx, 1
00379A09 jne      0x140379d57
00379A0F mov      word ptr [rsi + 0x3c6c], 0x200
00379A18 jmp      0x140379d57
00379A1D mov      word ptr [rsi + 0x3c6c], 0x3ff
00379A26 jmp      0x140379d57
00379A2B mov      rax, qword ptr [rip + 0x2edb16]
00379A32 lea      rdx, [rbp - 0x18]
00379A36 lea      rcx, [rbp - 0x20]
00379A3A mov      r8, qword ptr [rax + 0x1090]
00379A41 add      r8, 0x3d20
00379A48 call     0x1403ff880
00379A4D lea      rcx, [rbp - 0x20]
00379A51 call     0x140400020
00379A56 test     eax, eax
00379A58 je       0x140379a7f
00379A5A lea      rdx, [rip + 0x288907]
00379A61 lea      rcx, [rbp - 0x20]
00379A65 call     0x1403ffb60
00379A6A test     eax, eax
00379A6C je       0x140379a7f
00379A6E mov      rdx, qword ptr [rbp - 0x20]
00379A72 mov      rcx, rsi
00379A75 call     0x14034a700
00379A7A jmp      0x140379b28
00379A7F lea      rdx, [rip + 0x233cd2]
00379A86 lea      rcx, [rbp - 0x18]
00379A8A call     0x1403ff7c0
00379A8F mov      r9d, 1
00379A95 lea      rcx, [rsi + 0x3ee8]
00379A9C mov      r8d, r9d
00379A9F lea      rdx, [rbp - 0x18]
00379AA3 call     0x14014d080
00379AA8 mov      rax, qword ptr [rip + 0x2eda99]
00379AAF lea      rcx, [rsi + 0x3f18]
00379AB6 xor      edx, edx
00379AB8 mov      r9, qword ptr [rax + 0x1090]
00379ABF add      r9, 0x63d8
00379AC6 lea      r8d, [rdx + 0x43]
00379ACA call     0x1404221c0
00379ACF mov      rax, qword ptr [rip + 0x2eda72]
00379AD6 lea      rcx, [rsi + 0x3f18]
00379ADD mov      edx, 1
00379AE2 mov      r9, qword ptr [rax + 0x1090]
00379AE9 add      r9, 0x63d8
00379AF0 lea      r8d, [rdx + 0x40]
00379AF4 call     0x1404221c0
00379AF9 lea      rdx, [rsi + 0x3f18]
00379B00 lea      rcx, [rsi + 0x3de0]
00379B07 call     0x140412390
00379B0C xor      edx, edx
00379B0E lea      rcx, [rsi + 0x3de0]
00379B15 call     0x140412380
00379B1A xor      edx, edx
00379B1C lea      rcx, [rsi + 0x3de0]
00379B23 call     0x140411610
00379B28 mov      rax, qword ptr [rip + 0x2eda19]
00379B2F lea      rdx, [rbp - 0x18]
00379B33 lea      rcx, [rbp - 0x20]
00379B37 mov      r8, qword ptr [rax + 0x1090]
00379B3E add      r8, 0x3ca0
00379B45 call     0x1403ff880
00379B4A lea      rcx, [rbp - 0x20]
00379B4E call     0x140400020
00379B53 test     eax, eax
00379B55 je       0x140379b9b
00379B57 lea      rdx, [rip + 0x28880a]
00379B5E lea      rcx, [rbp - 0x20]
00379B62 call     0x1403ffb60
00379B67 test     eax, eax
00379B69 je       0x140379b9b
00379B6B mov      r9d, 1
00379B71 lea      rcx, [rsi + 0x3d78]
00379B78 mov      r8d, r9d
00379B7B lea      rdx, [rbp - 0x20]
00379B7F call     0x14014d080
00379B84 mov      eax, 0x208
00379B89 lea      rdi, [rsi + 0x3c70]
00379B90 mov      dword ptr [rsi + 0x3dd8], eax
00379B96 jmp      0x140379c2b
00379B9B lea      rdx, [rip + 0x233bc2]
00379BA2 lea      rcx, [rbp - 0x18]
00379BA6 call     0x1403ff7c0
00379BAB mov      r9d, 1
00379BB1 lea      rcx, [rsi + 0x3d78]
00379BB8 mov      r8d, r9d
00379BBB lea      rdx, [rbp - 0x18]
00379BBF call     0x14014d080
00379BC4 mov      rax, qword ptr [rip + 0x2ed97d]
00379BCB lea      rcx, [rsi + 0x3da8]
00379BD2 xor      edx, edx
00379BD4 mov      r9, qword ptr [rax + 0x1090]
00379BDB add      r9, 0x63d8
00379BE2 lea      r8d, [rdx + 0x43]
00379BE6 call     0x1404221c0
00379BEB mov      rax, qword ptr [rip + 0x2ed956]
00379BF2 lea      rcx, [rsi + 0x3da8]
00379BF9 mov      edx, 1
00379BFE mov      r9, qword ptr [rax + 0x1090]
00379C05 add      r9, 0x63d8
00379C0C lea      r8d, [rdx + 0x40]
00379C10 call     0x1404221c0
00379C15 lea      rdi, [rsi + 0x3c70]
00379C1C mov      rcx, rdi
00379C1F lea      rdx, [rsi + 0x3da8]
00379C26 call     0x140412390
00379C2B xor      edx, edx
00379C2D mov      rcx, rdi
00379C30 call     0x140412380
00379C35 lea      rcx, [rsi + 0x3c70]
00379C3C mov      byte ptr [rsi + 0x3c69], 1
00379C43 movzx    edx, word ptr [rcx + 0x11a]
00379C4A call     0x140411cc0
00379C4F mov      byte ptr [rsi + 0x3f64], 1
00379C56 jmp      0x1403799ee
00379C5B mov      word ptr [rsi + 0x3c6c], 0x4fe
00379C64 jmp      0x140379d57
00379C69 test     byte ptr [rsi + 0x3c48], 2
00379C70 mov      rax, qword ptr [rip + 0x2ed8d1]
00379C77 mov      rdi, qword ptr [rax + 0x1090]
00379C7E je       0x140379c89
00379C80 movzx    eax, byte ptr [rsi + 0x3c4f]
00379C87 jmp      0x140379c96
00379C89 mov      rcx, qword ptr [rsi + 0x3c40]
00379C90 mov      rax, qword ptr [rcx]
00379C93 call     qword ptr [rax + 0x68]
00379C96 lea      r9, [rdi + 0x63d8]
00379C9D movzx    r8d, al
00379CA1 xor      edx, edx
00379CA3 lea      rcx, [rsi + 0x3f18]
00379CAA call     0x1404221c0
00379CAF lea      rdx, [rsi + 0x3f18]
00379CB6 lea      rcx, [rsi + 0x3de0]
00379CBD call     0x140412390
00379CC2 movzx    eax, r14b
00379CC6 cmp      ax, word ptr [rip + 0x2211bf]
00379CCD jne      0x140379cd8
00379CCF lea      rdx, [rip + 0x233a5e]
00379CD6 jmp      0x140379d19
00379CD8 cmp      ax, word ptr [rip + 0x2211a9]
00379CDF jne      0x140379cea
00379CE1 lea      rdx, [rip + 0x233a54]
00379CE8 jmp      0x140379d19
00379CEA cmp      ax, word ptr [rip + 0x221193]
00379CF1 je       0x140379d12
00379CF3 cmp      ax, word ptr [rip + 0x22119a]
00379CFA je       0x140379d12
00379CFC cmp      ax, word ptr [rip + 0x22118d]
00379D03 jne      0x140379e8b
00379D09 lea      rdx, [rip + 0x233a40]
00379D10 jmp      0x140379d19
00379D12 lea      rdx, [rip + 0x233a2b]
00379D19 lea      rcx, [rbp - 0x18]
00379D1D call     0x1403ff7c0
00379D22 mov      r9d, 1
00379D28 lea      rdx, [rbp - 0x18]
00379D2C mov      r8d, r9d
00379D2F lea      rcx, [rsi + 0x3ee8]
00379D36 call     0x14014d080
00379D3B xor      edx, edx
00379D3D lea      rcx, [rsi + 0x3de0]
00379D44 call     0x140412380
00379D49 xor      edx, edx
00379D4B lea      rcx, [rsi + 0x3de0]
00379D52 call     0x140411610
00379D57 movsx    edx, byte ptr [rsi + 0x3c6c]
00379D5E movzx    ecx, byte ptr [rsi + 0x3c6d]
00379D65 dec      edx
00379D67 movzx    r8d, byte ptr [rsi + 0x3c6b]
00379D6F add      edx, ecx
00379D71 imul     edx, r8d
00379D75 test     edx, edx
00379D77 jle      0x140379e3f
00379D7D movsxd   rcx, edx
00379D80 mov      eax, 2
00379D85 mul      rcx
00379D88 mov      rbx, 0xffffffffffffffff
00379D8F cmovo    rax, rbx
00379D93 mov      rcx, rax
00379D96 call     0x1404f77c4
00379D9B mov      qword ptr [rsi + 0x3c58], rax
00379DA2 test     rax, rax
00379DA5 je       0x140379e8b
00379DAB movzx    edx, byte ptr [rsi + 0x3c6d]
00379DB2 mov      eax, 8
00379DB7 movzx    ecx, byte ptr [rsi + 0x3c6b]
00379DBE dec      edx
00379DC0 movsx    r8d, byte ptr [rsi + 0x3c6c]
00379DC8 add      r8d, edx
00379DCB imul     r8d, ecx
00379DCF movsxd   rcx, r8d
00379DD2 mul      rcx
00379DD5 cmovo    rax, rbx
00379DD9 mov      rcx, rax
00379DDC call     0x1404f77c4
00379DE1 mov      r9, qword ptr [rsi + 0x3c58]
00379DE8 mov      qword ptr [rsi + 0x3c60], rax
00379DEF test     rax, rax
00379DF2 jne      0x140379e08
00379DF4 mov      rcx, r9
00379DF7 call     0x14045e690
00379DFC mov      qword ptr [rsi + 0x3c58], r12
00379E03 jmp      0x140379e8b
00379E08 movzx    ecx, byte ptr [rsi + 0x3c6d]
00379E0F movsx    edx, byte ptr [rsi + 0x3c6c]
00379E16 dec      ecx
00379E18 movzx    eax, byte ptr [rsi + 0x3c6b]
00379E1F add      edx, ecx
00379E21 imul     edx, eax
00379E24 mov      rcx, r9
00379E27 movsxd   r8, edx
00379E2A mov      edx, 0xff
00379E2F add      r8, r8
00379E32 call     0x1404fab70
00379E37 movzx    r8d, byte ptr [rsi + 0x3c6b]
00379E3F test     r8b, r8b
00379E42 je       0x140379e6c
00379E44 movzx    edx, word ptr [rsi + 0x3efa]
00379E4B lea      rcx, [rsi + 0x3de0]
00379E52 call     0x140411cc0
00379E57 movzx    ecx, byte ptr [rsi + 0x3c6b]
00379E5E sub      cl, 2
00379E61 add      cl, al
00379E63 add      cl, r15b
00379E66 mov      byte ptr [rsi + 0x3c6a], cl
00379E6C mov      rcx, qword ptr [rsi + 0x3c40]
00379E73 lea      r8, [rsi + 0x3f5c]
00379E7A mov      r9d, dword ptr [rsi + 0x14]
00379E7E lea      rdx, [rsi + 0x3f4c]
00379E85 mov      rax, qword ptr [rcx]
00379E88 call     qword ptr [rax + 8]
00379E8B mov      rdi, qword ptr [rsp + 0x78]
00379E90 mov      rcx, qword ptr [rbp - 0x10]
00379E94 xor      rcx, rsp
00379E97 call     0x1404f77a0
00379E9C mov      rbx, qword ptr [rsp + 0x80]
00379EA4 add      rsp, 0x40
00379EA8 pop      r15
00379EAA pop      r14
00379EAC pop      r12
00379EAE pop      rsi
00379EAF pop      rbp
00379EB0 ret      
