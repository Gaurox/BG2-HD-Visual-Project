003BF880 push     rbp
003BF882 push     rbx
003BF883 push     rsi
003BF884 push     rdi
003BF885 push     r12
003BF887 push     r13
003BF889 push     r14
003BF88B push     r15
003BF88D lea      rbp, [rsp - 0x4e8]
003BF895 sub      rsp, 0x5e8
003BF89C mov      rax, qword ptr [rip + 0x2a5135]
003BF8A3 xor      rax, rsp
003BF8A6 mov      qword ptr [rbp + 0x4d0], rax
003BF8AD mov      rbx, qword ptr [rcx + 0x4a40]
003BF8B4 mov      rsi, rdx
003BF8B7 mov      qword ptr [rbp - 0x80], rdx
003BF8BB mov      r14, rcx
003BF8BE mov      qword ptr [rsp + 0x60], rcx
003BF8C3 lea      rdx, [rip + 0x22bee3]
003BF8CA lea      rcx, [rbp + 0x38]
003BF8CE mov      qword ptr [rbp - 0x20], r9
003BF8D2 mov      qword ptr [rbp - 0x78], r8
003BF8D6 call     0x1403ff7c0
003BF8DB mov      r13d, 1
003BF8E1 lea      rcx, [r14 + 0x4a00]
003BF8E8 mov      r8d, 0x118
003BF8EE mov      r9, rbx
003BF8F1 mov      rdx, r14
003BF8F4 mov      rax, qword ptr [rax]
003BF8F7 mov      qword ptr [rsp + 0x28], rax
003BF8FC mov      dword ptr [rsp + 0x20], r13d
003BF901 call     0x1401e80d0
003BF906 mov      rbx, qword ptr [r14 + 0x49f0]
003BF90D lea      rdx, [rip + 0x22be99]
003BF914 lea      rcx, [rbp + 0x38]
003BF918 call     0x1403ff7c0
003BF91D mov      r8d, 0x118
003BF923 lea      rcx, [r14 + 0x49b0]
003BF92A mov      r9, rbx
003BF92D mov      rdx, r14
003BF930 mov      rax, qword ptr [rax]
003BF933 mov      qword ptr [rsp + 0x28], rax
003BF938 mov      dword ptr [rsp + 0x20], r13d
003BF93D call     0x1401e80d0
003BF942 xor      edx, edx
003BF944 mov      rcx, rsi
003BF947 call     0x14024ed80
003BF94C mov      rdi, rax
003BF94F xor      eax, eax
003BF951 mov      qword ptr [rbp - 0x70], rax
003BF955 mov      r12d, eax
003BF958 test     rdi, rdi
003BF95B je       0x1403bf9d8
003BF95D mov      ebx, eax
003BF95F mov      qword ptr [rbp - 0x70], rax
003BF963 cmp      ax, word ptr [rdi + 0x1e]
003BF967 jae      0x1403bf9d8
003BF969 movabs   r15, 0xc0000140001
003BF973 nop      dword ptr [rax]
003BF977 nop      word ptr [rax + rax]
003BF980 xor      r9d, r9d
003BF983 mov      r8d, ebx
003BF986 xor      edx, edx
003BF988 mov      rcx, rsi
003BF98B call     0x14024ee30
003BF990 mov      r8, rax
003BF993 mov      ecx, dword ptr [rax + 0x10]
003BF996 cmp      ecx, 0xc0
003BF99C je       0x1403bf9d1
003BF99E cmp      ecx, 0x20
003BF9A1 je       0x1403bf9d1
003BF9A3 add      ecx, 0xffffff2a
003BF9A9 cmp      ecx, 0x2b
003BF9AC ja       0x1403bf9b4
003BF9AE bt       r15, rcx
003BF9B2 jb       0x1403bf9d1
003BF9B4 mov      rax, qword ptr [rax]
003BF9B7 mov      edx, r13d
003BF9BA mov      rcx, r8
003BF9BD call     qword ptr [rax]
003BF9BF movzx    eax, word ptr [rdi + 0x1e]
003BF9C3 inc      ebx
003BF9C5 cmp      ebx, eax
003BF9C7 jl       0x1403bf980
003BF9C9 xor      esi, esi
003BF9CB mov      qword ptr [rbp - 0x70], rsi
003BF9CF jmp      0x1403bf9da
003BF9D1 mov      r12, r13
003BF9D4 mov      qword ptr [rbp - 0x70], r13
003BF9D8 xor      esi, esi
003BF9DA mov      rbx, qword ptr [rbp + 0x38]
003BF9DE mov      r15d, 0xffffffff
003BF9E4 mov      dword ptr [rsp + 0x4c], r15d
003BF9E9 mov      qword ptr [rbp - 0x58], rbx
003BF9ED nop      dword ptr [rax]
003BF9F0 lea      rdx, [rip + 0x22bdb6]
003BF9F7 mov      dword ptr [rsp + 0x40], esi
003BF9FB lea      rcx, [rbp + 0x30]
003BF9FF mov      dword ptr [rsp + 0x48], esi
003BFA03 call     0x1403ff7c0
003BFA08 mov      dword ptr [rsp + 0x50], esi
003BFA0C mov      qword ptr [rbp - 0x40], rsi
003BFA10 call     0x14050933c
003BFA15 and      eax, 0x7fff
003BFA1A mov      dword ptr [rsp + 0x44], r13d
003BFA1F imul     edi, eax, 0x64
003BFA22 mov      rcx, r14
003BFA25 mov      esi, r13d
003BFA28 sar      edi, 0xf
003BFA2B call     0x140161920
003BFA30 lea      r13d, [rdi + 1]
003BFA34 mov      rcx, r14
003BFA37 add      r13d, dword ptr [rax + 0x22c]
003BFA3E call     0x14039cf10
003BFA43 test     eax, eax
003BFA45 jns      0x1403bfa8d
003BFA47 cmp      dword ptr [rbp + 0x550], 0
003BFA4E je       0x1403bfa8d
003BFA50 lea      rcx, [r14 + 0x30]
003BFA54 mov      dword ptr [rbp - 0x68], 1
003BFA5B call     0x14011dc40
003BFA60 mov      rcx, r14
003BFA63 movzx    edi, al
003BFA66 call     0x140161920
003BFA6B mov      rcx, rax
003BFA6E movzx    edx, dil
003BFA72 call     0x140153430
003BFA77 movzx    eax, al
003BFA7A lea      rdx, [rbp - 0x68]
003BFA7E lea      rcx, [rbp - 0x64]
003BFA82 mov      dword ptr [rbp - 0x64], eax
003BFA85 call     0x140407bb0
003BFA8A add      r13d, eax
003BFA8D movzx    eax, byte ptr [rip + 0x350394]
003BFA94 test     al, al
003BFA96 je       0x1403bfaa5
003BFA98 cmp      r15d, -1
003BFA9C jne      0x1403bfaa5
003BFA9E movzx    r13d, al
003BFAA2 shr      r13d, 1
003BFAA5 test     r12, r12
003BFAA8 mov      r12d, 0x64
003BFAAE cmovne   r13d, r12d
003BFAB2 xor      r15d, r15d
003BFAB5 mov      dword ptr [rsp + 0x58], r13d
003BFABA lea      ecx, [r12 - 0x44]
003BFABF call     0x1404f7a88
003BFAC4 xor      edx, edx
003BFAC6 mov      qword ptr [rsp + 0x68], rax
003BFACB lea      r9d, [r12 - 0x63]
003BFAD0 mov      rdi, rax
003BFAD3 test     rax, rax
003BFAD6 je       0x1403bfaf0
003BFAD8 mov      dword ptr [rax], edx
003BFADA mov      qword ptr [rax + 0x18], rdx
003BFADE mov      dword ptr [rax + 4], r12d
003BFAE2 mov      dword ptr [rax + 8], r12d
003BFAE6 mov      dword ptr [rax + 0xc], r12d
003BFAEA mov      qword ptr [rax + 0x10], r9
003BFAEE jmp      0x1403bfaf8
003BFAF0 mov      rdi, rdx
003BFAF3 mov      qword ptr [rsp + 0x68], rdx
003BFAF8 lea      r12d, [r13 - 1]
003BFAFC cmp      r12d, 0x62
003BFB00 ja       0x1403c023c
003BFB06 lea      r8, [rip - 0x3bfb0d]
003BFB0D movsxd   rax, r12d
003BFB10 mov      ecx, dword ptr [r8 + rax*4 + 0x3c1178]
003BFB18 add      rcx, r8
003BFB1B jmp      rcx
003BFB1D mov      dword ptr [rdi + 0x1c], r9d
003BFB21 mov      eax, 0x9b
003BFB26 mov      word ptr [rdi], ax
003BFB29 mov      r12d, esi
003BFB2C mov      rbx, qword ptr [r14 + 0xc]
003BFB30 mov      qword ptr [rbp - 0x58], rbx
003BFB34 mov      dword ptr [rsp + 0x48], r9d
003BFB39 mov      dword ptr [rsp + 0x50], r9d
003BFB3E mov      qword ptr [rbp - 0x18], r14
003BFB42 jmp      0x1403bfe85
003BFB47 mov      rax, qword ptr [rip + 0x2a7a12]
003BFB4E cmp      byte ptr [rax + 0x2c9], r15b
003BFB55 jne      0x1403bfcfb
003BFB5B mov      rcx, qword ptr [r14 + 0x18]
003BFB5F lea      r8, [rbp - 0x44]
003BFB63 lea      rdx, [rbp - 0x48]
003BFB67 mov      edi, dword ptr [rcx + 0x640]
003BFB6D mov      r14d, dword ptr [rcx + 0x644]
003BFB74 mov      esi, dword ptr [rcx + 0x648]
003BFB7A mov      r15d, dword ptr [rcx + 0x64c]
003BFB81 add      rcx, 0x5c8
003BFB88 call     0x14029fea0
003BFB8D call     0x14050933c
003BFB92 and      eax, 0x7fff
003BFB97 sub      esi, edi
003BFB99 imul     eax, esi
003BFB9C sar      eax, 0xf
003BFB9F mov      dword ptr [rsp + 0x78], eax
003BFBA3 call     0x14050933c
003BFBA8 mov      rcx, qword ptr [rbp - 0x48]
003BFBAC and      eax, 0x7fff
003BFBB1 add      dword ptr [rsp + 0x78], ecx
003BFBB5 sub      r15d, r14d
003BFBB8 shr      rcx, 0x20
003BFBBC mov      edx, 0xa
003BFBC1 imul     eax, r15d
003BFBC5 sar      eax, 0xf
003BFBC8 add      ecx, eax
003BFBCA mov      dword ptr [rsp + 0x7c], ecx
003BFBCE lea      rcx, [rbp + 0x58]
003BFBD2 call     0x1404073a0
003BFBD7 mov      r14, qword ptr [rsp + 0x60]
003BFBDC lea      rax, [rip + 0x1cd175]
003BFBE3 mov      qword ptr [rbp + 0x58], rax
003BFBE7 mov      rcx, r14
003BFBEA mov      rax, qword ptr [r14]
003BFBED call     qword ptr [rax + 0x140]
003BFBF3 mov      rdx, qword ptr [r14]
003BFBF6 mov      rcx, r14
003BFBF9 mov      rdi, rax
003BFBFC call     qword ptr [rdx + 0x150]
003BFC02 mov      rcx, qword ptr [r14 + 0x18]
003BFC06 lea      rdx, [r14 + 0xc]
003BFC0A xor      r15d, r15d
003BFC0D lea      r8, [rip + 0x29b6d4]
003BFC14 mov      dword ptr [rsp + 0x38], r15d
003BFC19 movzx    r9d, ax
003BFC1D lea      rax, [rbp + 0x58]
003BFC21 mov      dword ptr [rsp + 0x30], r15d
003BFC26 mov      qword ptr [rsp + 0x28], rax
003BFC2B mov      qword ptr [rsp + 0x20], rdi
003BFC30 call     0x14017f700
003BFC35 mov      rsi, qword ptr [rbp + 0x60]
003BFC39 test     rsi, rsi
003BFC3C je       0x1403bfca1
003BFC3E mov      ebx, 0x18
003BFC43 lea      r14, [rip + 0x1d0916]
003BFC4A nop      word ptr [rax + rax]
003BFC50 mov      edi, dword ptr [rsi + 0x10]
003BFC53 mov      rcx, rbx
003BFC56 mov      rsi, qword ptr [rsi]
003BFC59 call     0x1404f7a88
003BFC5E mov      rdx, rax
003BFC61 test     rax, rax
003BFC64 je       0x1403bfc7a
003BFC66 mov      rax, qword ptr [rsp + 0x78]
003BFC6B mov      qword ptr [rdx + 0x10], rax
003BFC6F mov      dword ptr [rdx + 0xc], edi
003BFC72 mov      dword ptr [rdx + 8], edi
003BFC75 mov      qword ptr [rdx], r14
003BFC78 jmp      0x1403bfc7d
003BFC7A mov      rdx, r15
003BFC7D mov      rcx, qword ptr [rip + 0x2a78c4]
003BFC84 xor      r8d, r8d
003BFC87 add      rcx, 0x1768
003BFC8E call     0x140204ec0
003BFC93 test     rsi, rsi
003BFC96 jne      0x1403bfc50
003BFC98 mov      rbx, qword ptr [rbp - 0x58]
003BFC9C mov      r14, qword ptr [rsp + 0x60]
003BFCA1 lea      rdx, [rip + 0x1eead0]
003BFCA8 lea      rcx, [rbp + 0x38]
003BFCAC call     0x1403ff7c0
003BFCB1 mov      dword ptr [rsp + 0x38], 1
003BFCB9 lea      r8, [rsp + 0x78]
003BFCBE mov      dword ptr [rsp + 0x30], r15d
003BFCC3 lea      rdx, [rbp + 0x38]
003BFCC7 mov      qword ptr [rsp + 0x28], r15
003BFCCC xor      r9d, r9d
003BFCCF mov      rcx, r14
003BFCD2 mov      dword ptr [rsp + 0x20], 0xffffffff
003BFCDA call     0x14016b9d0
003BFCDF lea      rcx, [rbp + 0x58]
003BFCE3 call     0x1404073d0
003BFCE8 mov      r8d, dword ptr [rsp + 0x40]
003BFCED xor      edx, edx
003BFCEF mov      dword ptr [rsp + 0x44], edx
003BFCF3 mov      eax, r8d
003BFCF6 jmp      0x1403bfe78
003BFCFB mov      r8d, r9d
003BFCFE mov      dword ptr [rsp + 0x40], r9d
003BFD03 mov      dword ptr [rsp + 0x44], edx
003BFD07 mov      eax, r9d
003BFD0A jmp      0x1403bfe78
003BFD0F mov      dword ptr [rsp + 0x44], edx
003BFD13 mov      dword ptr [rsp + 0x40], r9d
003BFD18 mov      rax, qword ptr [rip + 0x2a7829]
003BFD1F mov      rdx, qword ptr [rax + 0x1090]
003BFD26 movsx    ecx, word ptr [rdx + 0x33f0]
003BFD2D test     ecx, ecx
003BFD2F jle      0x1403c0220
003BFD35 movsx    eax, word ptr [rdx + 0x33f2]
003BFD3C cmp      r12d, eax
003BFD3F jge      0x1403c0220
003BFD45 test     r13d, r13d
003BFD48 jle      0x1403c0220
003BFD4E mov      rax, qword ptr [rdx + 0x33e0]
003BFD55 lea      rdx, [rbp + 0x90]
003BFD5C imul     r12d, ecx
003BFD60 movsxd   rcx, r12d
003BFD63 lea      r8, [rax + rcx*8]
003BFD67 lea      rcx, [rbp + 0x30]
003BFD6B call     0x1403ff890
003BFD70 jmp      0x1403bfe80
003BFD75 mov      r8, qword ptr [rbp - 0x80]
003BFD79 lea      rcx, [rbp + 0x30]
003BFD7D mov      r12d, edx
003BFD80 add      r8, 8
003BFD84 lea      rdx, [rbp + 0x378]
003BFD8B call     0x1403ff880
003BFD90 mov      eax, 1
003BFD95 mov      dword ptr [rsp + 0x40], eax
003BFD99 mov      dword ptr [rsp + 0x48], eax
003BFD9D mov      dword ptr [rdi + 0x18], eax
003BFDA0 jmp      0x1403bfe85
003BFDA5 mov      ecx, 0x18
003BFDAA call     0x1404f7a88
003BFDAF mov      rdi, rax
003BFDB2 test     rax, rax
003BFDB5 je       0x1403bfe03
003BFDB7 mov      eax, dword ptr [r14 + 0x48]
003BFDBB mov      rcx, qword ptr [r14 + 0x18]
003BFDBF mov      dword ptr [rdi + 0xc], eax
003BFDC2 mov      dword ptr [rdi + 8], eax
003BFDC5 lea      rax, [rip + 0x1cfd04]
003BFDCC mov      qword ptr [rdi], rax
003BFDCF mov      rax, qword ptr [rip + 0x29cd3a]
003BFDD6 mov      qword ptr [rdi + 0x10], rax
003BFDDA test     rcx, rcx
003BFDDD je       0x1403bfdf1
003BFDDF add      rcx, 0x204
003BFDE6 lea      rdx, [rdi + 0x10]
003BFDEA call     0x1403ffe40
003BFDEF jmp      0x1403bfe05
003BFDF1 lea      rdx, [rip + 0x22b9b5]
003BFDF8 lea      rcx, [rdi + 0x10]
003BFDFC call     0x1403fd810
003BFE01 jmp      0x1403bfe05
003BFE03 xor      edi, edi
003BFE05 mov      rcx, qword ptr [rip + 0x2a773c]
003BFE0C xor      r8d, r8d
003BFE0F add      rcx, 0x1768
003BFE16 mov      rdx, rdi
003BFE19 call     0x140204ec0
003BFE1E jmp      0x1403bfd18
003BFE23 mov      dword ptr [rsp + 0x44], edx
003BFE27 mov      r15d, r9d
003BFE2A jmp      0x1403bfd18
003BFE2F mov      r8, qword ptr [rbp - 0x80]
003BFE33 lea      rdx, [rbp + 0x4b0]
003BFE3A add      r8, 8
003BFE3E lea      rcx, [rbp + 0x30]
003BFE42 call     0x1403ff880
003BFE47 mov      eax, 1
003BFE4C mov      r12d, esi
003BFE4F mov      dword ptr [rsp + 0x40], eax
003BFE53 mov      dword ptr [rdi + 0x18], eax
003BFE56 jmp      0x1403bfe85
003BFE58 mov      rax, qword ptr [rip + 0x2a7701]
003BFE5F cmp      byte ptr [rax + 0x2c9], 1
003BFE66 jne      0x1403bfe76
003BFE68 mov      esi, edx
003BFE6A mov      dword ptr [rsp + 0x44], edx
003BFE6E mov      dword ptr [rsp + 0x48], r9d
003BFE73 mov      dword ptr [rdi + 0x10], edx
003BFE76 mov      eax, esi
003BFE78 test     eax, eax
003BFE7A jne      0x1403bfd18
003BFE80 mov      r12d, dword ptr [rsp + 0x44]
003BFE85 mov      rax, qword ptr [rip + 0x2a76bc]
003BFE8C lea      ecx, [r13 - 1]
003BFE90 mov      rdx, qword ptr [rax + 0x1090]
003BFE97 movsx    r8d, word ptr [rdx + 0x33f0]
003BFE9F cmp      r8d, 1
003BFEA3 jle      0x1403c0249
003BFEA9 movsx    eax, word ptr [rdx + 0x33f2]
003BFEB0 cmp      ecx, eax
003BFEB2 jge      0x1403c0249
003BFEB8 test     r13d, r13d
003BFEBB jle      0x1403c0249
003BFEC1 mov      rax, qword ptr [rdx + 0x33e0]
003BFEC8 imul     ecx, r8d
003BFECC add      rax, 8
003BFED0 movsxd   rcx, ecx
003BFED3 lea      rcx, [rax + rcx*8]
003BFED7 jmp      0x1403c0250
003BFEDC mov      r12d, edx
003BFEDF mov      dword ptr [rsp + 0x48], r9d
003BFEE4 mov      dword ptr [rdi + 0x10], edx
003BFEE7 jmp      0x1403bfe85
003BFEE9 mov      eax, 0x18
003BFEEE mov      dword ptr [rsp + 0x48], r9d
003BFEF3 mov      word ptr [rdi], ax
003BFEF6 mov      r15d, r9d
003BFEF9 mov      dword ptr [rdi + 0x18], r9d
003BFEFD mov      r12d, esi
003BFF00 mov      dword ptr [rdi + 0x1c], r9d
003BFF04 jmp      0x1403bfe85
003BFF09 mov      edx, 0xa
003BFF0E mov      dword ptr [rsp + 0x48], r9d
003BFF13 lea      rcx, [rbp + 0x58]
003BFF17 call     0x1404073a0
003BFF1C lea      rax, [rip + 0x1cce35]
003BFF23 mov      rcx, r14
003BFF26 mov      qword ptr [rbp + 0x58], rax
003BFF2A mov      rax, qword ptr [r14]
003BFF2D call     qword ptr [rax + 0x140]
003BFF33 mov      rdx, qword ptr [r14]
003BFF36 mov      rcx, r14
003BFF39 mov      rdi, rax
003BFF3C call     qword ptr [rdx + 0x150]
003BFF42 mov      rcx, qword ptr [r14 + 0x18]
003BFF46 lea      rdx, [r14 + 0xc]
003BFF4A xor      r12d, r12d
003BFF4D lea      r8, [rip + 0x29b394]
003BFF54 mov      dword ptr [rsp + 0x38], r12d
003BFF59 movzx    r9d, ax
003BFF5D lea      rax, [rbp + 0x58]
003BFF61 mov      dword ptr [rsp + 0x30], r12d
003BFF66 mov      qword ptr [rsp + 0x28], rax
003BFF6B mov      qword ptr [rsp + 0x20], rdi
003BFF70 call     0x14017f700
003BFF75 mov      edi, dword ptr [rbp + 0x70]
003BFF78 call     0x14050933c
003BFF7D mov      esi, eax
003BFF7F and      esi, 0x7fff
003BFF85 imul     esi, edi
003BFF88 mov      rdi, qword ptr [rbp + 0x60]
003BFF8C sar      esi, 0xf
003BFF8F test     rdi, rdi
003BFF92 je       0x1403bffd3
003BFF94 mov      ebx, dword ptr [rsp + 0x50]
003BFF98 lea      r13d, [r12 + 1]
003BFF9D nop      dword ptr [rax]
003BFFA0 lea      rax, [rdi]
003BFFA3 mov      rdi, qword ptr [rdi]
003BFFA6 test     esi, esi
003BFFA8 jne      0x1403bffbf
003BFFAA mov      ecx, dword ptr [rax + 0x10]
003BFFAD lea      rdx, [rbp - 0x18]
003BFFB1 mov      rdi, r12
003BFFB4 call     0x140276700
003BFFB9 test     al, al
003BFFBB cmove    ebx, r13d
003BFFBF dec      esi
003BFFC1 test     rdi, rdi
003BFFC4 jne      0x1403bffa0
003BFFC6 mov      r13d, dword ptr [rsp + 0x58]
003BFFCB mov      dword ptr [rsp + 0x50], ebx
003BFFCF mov      rbx, qword ptr [rbp - 0x58]
003BFFD3 lea      rcx, [rbp + 0x58]
003BFFD7 call     0x1404073d0
003BFFDC mov      rax, qword ptr [rsp + 0x68]
003BFFE1 mov      ecx, 1
003BFFE6 mov      dword ptr [rax + 0x18], ecx
003BFFE9 mov      dword ptr [rax + 0x1c], ecx
003BFFEC jmp      0x1403bfe80
003BFFF1 mov      rax, qword ptr [r14 + 0x18]
003BFFF5 test     byte ptr [rax + 0x40], 1
003BFFF9 je       0x1403c0047
003BFFFB call     0x14050933c
003C0000 mov      rcx, qword ptr [rip + 0x2a7541]
003C0007 and      eax, 0x7fff
003C000C mov      rdx, qword ptr [rcx + 0x1090]
003C0013 lea      r9d, [rax + rax]
003C0017 mov      rcx, qword ptr [rcx + 0x1110]
003C001E sar      r9d, 0xf
003C0022 add      rcx, 0x838
003C0029 inc      r9b
003C002C mov      r8d, dword ptr [rdx + 0x3fa0]
003C0033 mov      rdx, qword ptr [rdx + 0x65f8]
003C003A call     0x14025d4f0
003C003F mov      r12d, esi
003C0042 jmp      0x1403bfe85
003C0047 mov      r13d, 0x2e
003C004D mov      r12d, edx
003C0050 mov      edx, dword ptr [rsp + 0x4c]
003C0054 mov      eax, edx
003C0056 cmp      eax, -1
003C0059 lea      ecx, [rdx + 2]
003C005C mov      edx, 2
003C0061 cmovne   edx, ecx
003C0064 mov      dword ptr [rsp + 0x4c], edx
003C0068 jmp      0x1403bfe85
003C006D mov      dword ptr [rsp + 0x48], r9d
003C0072 jmp      0x1403bfd18
003C0077 mov      dword ptr [rsp + 0x48], r9d
003C007C mov      r12d, esi
003C007F mov      dword ptr [rdi + 8], 0x32
003C0086 jmp      0x1403bfe85
003C008B mov      dword ptr [rsp + 0x48], r9d
003C0090 mov      r12d, esi
003C0093 mov      dword ptr [rdi + 4], 0x32
003C009A jmp      0x1403bfe85
003C009F mov      dword ptr [rsp + 0x48], r9d
003C00A4 mov      r12d, esi
003C00A7 mov      dword ptr [rdi + 0x14], 0xffffffce
003C00AE jmp      0x1403bfe85
003C00B3 mov      edx, dword ptr [rsp + 0x4c]
003C00B7 mov      r12d, esi
003C00BA mov      eax, edx
003C00BC cmp      eax, -1
003C00BF lea      ecx, [rdx + 4]
003C00C2 mov      edx, 4
003C00C7 cmovne   edx, ecx
003C00CA mov      dword ptr [rsp + 0x4c], edx
003C00CE jmp      0x1403bfe85
003C00D3 mov      rax, qword ptr [rip + 0x29ca36]
003C00DA lea      rdx, [rsp + 0x58]
003C00DF mov      rdi, qword ptr [rbp - 0x80]
003C00E3 mov      qword ptr [rsp + 0x58], rax
003C00E8 lea      rcx, [rdi + 8]
003C00EC call     0x1403ffe40
003C00F1 mov      rcx, rdi
003C00F4 call     0x14024f3a0
003C00F9 movsx    r8d, ax
003C00FD lea      rdx, [rsp + 0x58]
003C0102 mov      rcx, r14
003C0105 call     0x1401565b0
003C010A mov      ecx, eax
003C010C mov      eax, 0x51eb851f
003C0111 imul     ecx
003C0113 sar      edx, 5
003C0116 mov      eax, edx
003C0118 shr      eax, 0x1f
003C011B add      edx, eax
003C011D imul     edi, edx, 0x64
003C0120 call     0x14050933c
003C0125 and      eax, 0x7fff
003C012A lea      r8, [rsp + 0x58]
003C012F lea      ecx, [rax + rax*4]
003C0132 lea      edx, [rcx + rcx]
003C0135 mov      rcx, r14
003C0138 sar      edx, 0xf
003C013B inc      edx
003C013D add      edx, edi
003C013F call     0x140156260
003C0144 lea      r8, [rsp + 0x58]
003C0149 lea      rdx, [rbp + 0x4b8]
003C0150 lea      rcx, [rbp + 0x30]
003C0154 call     0x1403ff890
003C0159 lea      rcx, [rsp + 0x58]
003C015E call     0x1403fd740
003C0163 mov      rax, qword ptr [rsp + 0x68]
003C0168 mov      ecx, 1
003C016D mov      r12d, esi
003C0170 mov      dword ptr [rax + 0x18], ecx
003C0173 mov      dword ptr [rax + 0x1c], ecx
003C0176 jmp      0x1403bfe85
003C017B mov      r15d, r9d
003C017E mov      dword ptr [rdi + 0x18], r9d
003C0182 jmp      0x1403bfd18
003C0187 mov      dword ptr [rsp + 0x48], r9d
003C018C xor      r8d, r8d
003C018F mov      edx, r9d
003C0192 mov      rcx, r14
003C0195 call     0x1403b1b90
003C019A mov      r12d, esi
003C019D jmp      0x1403bfe85
003C01A2 mov      dword ptr [rdi + 0x1c], r9d
003C01A6 jmp      0x1403bfd13
003C01AB mov      r15d, r9d
003C01AE mov      dword ptr [rsp + 0x44], edx
003C01B2 jmp      0x1403bfd18
003C01B7 mov      eax, 0x9b
003C01BC mov      dword ptr [rsp + 0x48], r9d
003C01C1 mov      word ptr [rdi], ax
003C01C4 mov      r12d, esi
003C01C7 mov      dword ptr [rdi + 0x1c], r9d
003C01CB jmp      0x1403bfe85
003C01D0 mov      r8, qword ptr [rbp - 0x80]
003C01D4 lea      rdx, [rbp + 0x4c0]
003C01DB add      r8, 8
003C01DF lea      rcx, [rbp + 0x30]
003C01E3 call     0x1403ff880
003C01E8 mov      dword ptr [rsp + 0x48], 1
003C01F0 mov      r12d, esi
003C01F3 jmp      0x1403bfe85
003C01F8 mov      dword ptr [rsp + 0x48], r9d
003C01FD mov      r12d, esi
003C0200 mov      dword ptr [rdi + 0x14], 4
003C0207 jmp      0x1403bfe85
003C020C mov      dword ptr [rsp + 0x48], r9d
003C0211 mov      r12d, esi
003C0214 mov      dword ptr [rdi + 0xc], 0xc8
003C021B jmp      0x1403bfe85
003C0220 lea      r8, [rdx + 0x33e8]
003C0227 lea      rdx, [rbp + 0x90]
003C022E lea      rcx, [rbp + 0x30]
003C0232 call     0x1403ff890
003C0237 jmp      0x1403bfe80
003C023C mov      dword ptr [rsp + 0x48], r9d
003C0241 mov      r12d, esi
003C0244 jmp      0x1403bfe85
003C0249 lea      rcx, [rdx + 0x33e8]
003C0250 mov      rcx, qword ptr [rcx]
003C0253 call     0x140503d20
003C0258 test     r15d, r15d
003C025B mov      r14d, eax
003C025E mov      r15, qword ptr [rbp - 0x78]
003C0262 je       0x1403c0334
003C0268 test     r15, r15
003C026B jne      0x1403c0334
003C0271 lea      edx, [r15 + 0xa]
003C0275 lea      rcx, [rbp - 0x10]
003C0279 call     0x1404073a0
003C027E mov      rsi, qword ptr [rsp + 0x60]
003C0283 lea      rax, [rip + 0x1ccace]
003C028A mov      rcx, rsi
003C028D mov      qword ptr [rbp - 0x10], rax
003C0291 mov      rdx, qword ptr [rsi]
003C0294 call     qword ptr [rdx + 0x140]
003C029A mov      rdx, qword ptr [rsi]
003C029D mov      rcx, rsi
003C02A0 mov      rdi, rax
003C02A3 call     qword ptr [rdx + 0x150]
003C02A9 mov      rcx, qword ptr [rsi + 0x18]
003C02AD lea      rdx, [rsi + 0xc]
003C02B1 xor      r13d, r13d
003C02B4 lea      r8, [rip + 0x29b02d]
003C02BB mov      dword ptr [rsp + 0x38], r13d
003C02C0 movzx    r9d, ax
003C02C4 lea      rax, [rbp - 0x10]
003C02C8 mov      dword ptr [rsp + 0x30], r13d
003C02CD mov      qword ptr [rsp + 0x28], rax
003C02D2 mov      qword ptr [rsp + 0x20], rdi
003C02D7 call     0x14017f700
003C02DC mov      edi, dword ptr [rbp + 8]
003C02DF call     0x14050933c
003C02E4 mov      esi, eax
003C02E6 and      esi, 0x7fff
003C02EC imul     esi, edi
003C02EF mov      rdi, qword ptr [rbp - 8]
003C02F3 sar      esi, 0xf
003C02F6 test     rdi, rdi
003C02F9 je       0x1403c032b
003C02FB nop      dword ptr [rax + rax]
003C0300 lea      rax, [rdi]
003C0303 mov      rdi, qword ptr [rdi]
003C0306 test     esi, esi
003C0308 jne      0x1403c0320
003C030A mov      ecx, dword ptr [rax + 0x10]
003C030D lea      rdx, [rbp - 0x40]
003C0311 mov      rdi, r13
003C0314 call     0x140276700
003C0319 test     al, al
003C031B cmove    r15, qword ptr [rbp - 0x40]
003C0320 dec      esi
003C0322 test     rdi, rdi
003C0325 jne      0x1403c0300
003C0327 mov      qword ptr [rbp - 0x78], r15
003C032B lea      rcx, [rbp - 0x10]
003C032F call     0x1404073d0
003C0334 lea      rdx, [rip + 0x22b472]
003C033B mov      r13, r15
003C033E lea      rcx, [rbp - 0x38]
003C0342 call     0x1403fd6b0
003C0347 lea      rax, [rbp - 0x38]
003C034B xor      r9d, r9d
003C034E mov      qword ptr [rsp + 0x38], rax
003C0353 xor      r8d, r8d
003C0356 xor      eax, eax
003C0358 mov      edx, 0xf000ca
003C035D mov      dword ptr [rsp + 0x30], eax
003C0361 mov      dword ptr [rsp + 0x28], r14d
003C0366 mov      r14, qword ptr [rsp + 0x60]
003C036B mov      rcx, r14
003C036E mov      dword ptr [rsp + 0x20], eax
003C0372 call     0x140398b70
003C0377 lea      rcx, [rbp - 0x38]
003C037B call     0x1403fd740
003C0380 mov      rcx, qword ptr [rbp - 0x20]
003C0384 mov      esi, dword ptr [rsp + 0x40]
003C0388 mov      rax, qword ptr [rcx]
003C038B mov      qword ptr [rsp + 0x70], rax
003C0390 test     esi, esi
003C0392 je       0x1403c03a0
003C0394 mov      rax, qword ptr [r14 + 0xc]
003C0398 mov      r13, r14
003C039B mov      qword ptr [rsp + 0x70], rax
003C03A0 test     r12d, r12d
003C03A3 je       0x1403c0f56
003C03A9 lea      rcx, [rbp + 0x28]
003C03AD call     0x1403ff870
003C03B2 call     0x14050933c
003C03B7 and      eax, 0x7fff
003C03BC imul     ecx, eax, 0x8b
003C03C2 sar      ecx, 0xf
003C03C5 cmp      ecx, 0x8a
003C03CB ja       0x1403c0d6e
003C03D1 movsxd   rax, ecx
003C03D4 lea      rdx, [rip - 0x3c03db]
003C03DB mov      ecx, dword ptr [rdx + rax*4 + 0x3c1304]
003C03E2 add      rcx, rdx
003C03E5 jmp      rcx
003C03E7 lea      r8, [rip + 0x1ee392]
003C03EE lea      rdx, [rbp + 0x98]
003C03F5 jmp      0x1403c0d7c
003C03FA lea      r8, [rip + 0x1ee387]
003C0401 lea      rdx, [rbp + 0xa0]
003C0408 jmp      0x1403c0d7c
003C040D lea      r8, [rip + 0x1ee37c]
003C0414 lea      rdx, [rbp + 0xa8]
003C041B jmp      0x1403c0d7c
003C0420 lea      r8, [rip + 0x1ee379]
003C0427 lea      rdx, [rbp + 0xb0]
003C042E jmp      0x1403c0d7c
003C0433 lea      r8, [rip + 0x1ee376]
003C043A lea      rdx, [rbp + 0xb8]
003C0441 jmp      0x1403c0d7c
003C0446 lea      r8, [rip + 0x1ee373]
003C044D lea      rdx, [rbp + 0xc0]
003C0454 jmp      0x1403c0d7c
003C0459 lea      r8, [rip + 0x1ee370]
003C0460 lea      rdx, [rbp + 0xc8]
003C0467 jmp      0x1403c0d7c
003C046C lea      r8, [rip + 0x1ee36d]
003C0473 lea      rdx, [rbp + 0xd0]
003C047A jmp      0x1403c0d7c
003C047F lea      r8, [rip + 0x1ee362]
003C0486 lea      rdx, [rbp + 0xd8]
003C048D jmp      0x1403c0d7c
003C0492 lea      r8, [rip + 0x1ee35f]
003C0499 lea      rdx, [rbp + 0xe0]
003C04A0 jmp      0x1403c0d7c
003C04A5 lea      r8, [rip + 0x1ee354]
003C04AC lea      rdx, [rbp + 0xe8]
003C04B3 jmp      0x1403c0d7c
003C04B8 lea      r8, [rip + 0x1ee351]
003C04BF lea      rdx, [rbp + 0xf0]
003C04C6 jmp      0x1403c0d7c
003C04CB lea      r8, [rip + 0x1ee34e]
003C04D2 lea      rdx, [rbp + 0xf8]
003C04D9 jmp      0x1403c0d7c
003C04DE lea      r8, [rip + 0x1ee34b]
003C04E5 lea      rdx, [rbp + 0x100]
003C04EC jmp      0x1403c0d7c
003C04F1 lea      r8, [rip + 0x1ee348]
003C04F8 lea      rdx, [rbp + 0x108]
003C04FF jmp      0x1403c0d7c
003C0504 lea      r8, [rip + 0x1ee345]
003C050B lea      rdx, [rbp + 0x110]
003C0512 jmp      0x1403c0d7c
003C0517 lea      r8, [rip + 0x1ee33a]
003C051E lea      rdx, [rbp + 0x118]
003C0525 jmp      0x1403c0d7c
003C052A lea      rdx, [rbp + 0x120]
003C0531 jmp      0x1403c0d75
003C0536 lea      r8, [rip + 0x1ee33b]
003C053D lea      rdx, [rbp + 0x128]
003C0544 jmp      0x1403c0d7c
003C0549 lea      r8, [rip + 0x1ee330]
003C0550 lea      rdx, [rbp + 0x130]
003C0557 jmp      0x1403c0d7c
003C055C lea      r8, [rip + 0x1ee32d]
003C0563 lea      rdx, [rbp + 0x138]
003C056A jmp      0x1403c0d7c
003C056F lea      r8, [rip + 0x1ee32a]
003C0576 lea      rdx, [rbp + 0x140]
003C057D jmp      0x1403c0d7c
003C0582 lea      r8, [rip + 0x1ee327]
003C0589 lea      rdx, [rbp + 0x148]
003C0590 jmp      0x1403c0d7c
003C0595 lea      r8, [rip + 0x1ee31c]
003C059C lea      rdx, [rbp + 0x150]
003C05A3 jmp      0x1403c0d7c
003C05A8 lea      r8, [rip + 0x1ee319]
003C05AF lea      rdx, [rbp + 0x158]
003C05B6 jmp      0x1403c0d7c
003C05BB lea      r8, [rip + 0x1ee30e]
003C05C2 lea      rdx, [rbp + 0x160]
003C05C9 jmp      0x1403c0d7c
003C05CE lea      r8, [rip + 0x1ee303]
003C05D5 lea      rdx, [rbp + 0x168]
003C05DC jmp      0x1403c0d7c
003C05E1 lea      r8, [rip + 0x1ee2f8]
003C05E8 lea      rdx, [rbp + 0x170]
003C05EF jmp      0x1403c0d7c
003C05F4 lea      r8, [rip + 0x1ee2ed]
003C05FB lea      rdx, [rbp + 0x178]
003C0602 jmp      0x1403c0d7c
003C0607 lea      r8, [rip + 0x1de39a]
003C060E lea      rdx, [rbp + 0x180]
003C0615 jmp      0x1403c0d7c
003C061A lea      r8, [rip + 0x1ee2cf]
003C0621 lea      rdx, [rbp + 0x188]
003C0628 jmp      0x1403c0d7c
003C062D lea      r8, [rip + 0x1ee2c4]
003C0634 lea      rdx, [rbp + 0x190]
003C063B jmp      0x1403c0d7c
003C0640 lea      r8, [rip + 0x1ee2b9]
003C0647 lea      rdx, [rbp + 0x198]
003C064E jmp      0x1403c0d7c
003C0653 lea      r8, [rip + 0x1ee2ae]
003C065A lea      rdx, [rbp + 0x1a0]
003C0661 jmp      0x1403c0d7c
003C0666 lea      r8, [rip + 0x1ee2a3]
003C066D lea      rdx, [rbp + 0x1a8]
003C0674 jmp      0x1403c0d7c
003C0679 lea      r8, [rip + 0x1ee2a0]
003C0680 lea      rdx, [rbp + 0x1b0]
003C0687 jmp      0x1403c0d7c
003C068C lea      r8, [rip + 0x1ee29d]
003C0693 lea      rdx, [rbp + 0x1b8]
003C069A jmp      0x1403c0d7c
003C069F lea      r8, [rip + 0x1de30e]
003C06A6 lea      rdx, [rbp + 0x1c0]
003C06AD jmp      0x1403c0d7c
003C06B2 lea      r8, [rip + 0x1de307]
003C06B9 lea      rdx, [rbp + 0x1c8]
003C06C0 jmp      0x1403c0d7c
003C06C5 lea      r8, [rip + 0x1ee274]
003C06CC lea      rdx, [rbp + 0x1d0]
003C06D3 jmp      0x1403c0d7c
003C06D8 lea      r8, [rip + 0x1ee271]
003C06DF lea      rdx, [rbp + 0x1d8]
003C06E6 jmp      0x1403c0d7c
003C06EB lea      r8, [rip + 0x1ee26e]
003C06F2 lea      rdx, [rbp + 0x1e0]
003C06F9 jmp      0x1403c0d7c
003C06FE lea      r8, [rip + 0x1ee26b]
003C0705 lea      rdx, [rbp + 0x1e8]
003C070C jmp      0x1403c0d7c
003C0711 lea      r8, [rip + 0x1ee268]
003C0718 lea      rdx, [rbp + 0x1f0]
003C071F jmp      0x1403c0d7c
003C0724 lea      r8, [rip + 0x1ee265]
003C072B lea      rdx, [rbp + 0x1f8]
003C0732 jmp      0x1403c0d7c
003C0737 lea      r8, [rip + 0x1ee262]
003C073E lea      rdx, [rbp + 0x200]
003C0745 jmp      0x1403c0d7c
003C074A lea      r8, [rip + 0x1ee25f]
003C0751 lea      rdx, [rbp + 0x208]
003C0758 jmp      0x1403c0d7c
003C075D lea      r8, [rip + 0x1ee25c]
003C0764 lea      rdx, [rbp + 0x210]
003C076B jmp      0x1403c0d7c
003C0770 lea      r8, [rip + 0x1ee259]
003C0777 lea      rdx, [rbp + 0x218]
003C077E jmp      0x1403c0d7c
003C0783 lea      r8, [rip + 0x1ee256]
003C078A lea      rdx, [rbp + 0x220]
003C0791 jmp      0x1403c0d7c
003C0796 lea      r8, [rip + 0x1ee253]
003C079D lea      rdx, [rbp + 0x228]
003C07A4 jmp      0x1403c0d7c
003C07A9 lea      r8, [rip + 0x1ee250]
003C07B0 lea      rdx, [rbp + 0x230]
003C07B7 jmp      0x1403c0d7c
003C07BC lea      r8, [rip + 0x1de26d]
003C07C3 lea      rdx, [rbp + 0x238]
003C07CA jmp      0x1403c0d7c
003C07CF lea      r8, [rip + 0x1ee23a]
003C07D6 lea      rdx, [rbp + 0x240]
003C07DD jmp      0x1403c0d7c
003C07E2 lea      r8, [rip + 0x1ee237]
003C07E9 lea      rdx, [rbp + 0x248]
003C07F0 jmp      0x1403c0d7c
003C07F5 lea      r8, [rip + 0x1ee234]
003C07FC lea      rdx, [rbp + 0x250]
003C0803 jmp      0x1403c0d7c
003C0808 lea      r8, [rip + 0x1ee231]
003C080F lea      rdx, [rbp + 0x258]
003C0816 jmp      0x1403c0d7c
003C081B lea      r8, [rip + 0x1ee22e]
003C0822 lea      rdx, [rbp + 0x260]
003C0829 jmp      0x1403c0d7c
003C082E lea      r8, [rip + 0x1e6e1b]
003C0835 lea      rdx, [rbp + 0x268]
003C083C jmp      0x1403c0d7c
003C0841 lea      r8, [rip + 0x1ee218]
003C0848 lea      rdx, [rbp + 0x270]
003C084F jmp      0x1403c0d7c
003C0854 lea      r8, [rip + 0x1ee215]
003C085B lea      rdx, [rbp + 0x278]
003C0862 jmp      0x1403c0d7c
003C0867 lea      r8, [rip + 0x1ee212]
003C086E lea      rdx, [rbp + 0x280]
003C0875 jmp      0x1403c0d7c
003C087A lea      r8, [rip + 0x1ee20f]
003C0881 lea      rdx, [rbp + 0x288]
003C0888 jmp      0x1403c0d7c
003C088D lea      r8, [rip + 0x1ee20c]
003C0894 lea      rdx, [rbp + 0x290]
003C089B jmp      0x1403c0d7c
003C08A0 lea      r8, [rip + 0x1ee201]
003C08A7 lea      rdx, [rbp + 0x298]
003C08AE jmp      0x1403c0d7c
003C08B3 lea      r8, [rip + 0x1ee1fe]
003C08BA lea      rdx, [rbp + 0x2a0]
003C08C1 jmp      0x1403c0d7c
003C08C6 lea      r8, [rip + 0x1ee1fb]
003C08CD lea      rdx, [rbp + 0x2a8]
003C08D4 jmp      0x1403c0d7c
003C08D9 lea      r8, [rip + 0x1ee1f8]
003C08E0 lea      rdx, [rbp + 0x2b0]
003C08E7 jmp      0x1403c0d7c
003C08EC lea      r8, [rip + 0x1de055]
003C08F3 lea      rdx, [rbp + 0x2b8]
003C08FA jmp      0x1403c0d7c
003C08FF lea      r8, [rip + 0x1ee1e2]
003C0906 lea      rdx, [rbp + 0x2c0]
003C090D jmp      0x1403c0d7c
003C0912 lea      r8, [rip + 0x1ddfff]
003C0919 lea      rdx, [rbp + 0x2c8]
003C0920 jmp      0x1403c0d7c
003C0925 lea      r8, [rip + 0x1de00c]
003C092C lea      rdx, [rbp + 0x2d0]
003C0933 jmp      0x1403c0d7c
003C0938 lea      r8, [rip + 0x1ee1b9]
003C093F lea      rdx, [rbp + 0x2d8]
003C0946 jmp      0x1403c0d7c
003C094B lea      r8, [rip + 0x1ee1b6]
003C0952 lea      rdx, [rbp + 0x2e0]
003C0959 jmp      0x1403c0d7c
003C095E lea      r8, [rip + 0x1ee1b3]
003C0965 lea      rdx, [rbp + 0x2e8]
003C096C jmp      0x1403c0d7c
003C0971 lea      r8, [rip + 0x1ee1b0]
003C0978 lea      rdx, [rbp + 0x2f0]
003C097F jmp      0x1403c0d7c
003C0984 lea      r8, [rip + 0x1ee1ad]
003C098B lea      rdx, [rbp + 0x2f8]
003C0992 jmp      0x1403c0d7c
003C0997 lea      r8, [rip + 0x1ee1aa]
003C099E lea      rdx, [rbp + 0x300]
003C09A5 jmp      0x1403c0d7c
003C09AA lea      r8, [rip + 0x1ee1a7]
003C09B1 lea      rdx, [rbp + 0x308]
003C09B8 jmp      0x1403c0d7c
003C09BD lea      r8, [rip + 0x1ee1a4]
003C09C4 lea      rdx, [rbp + 0x310]
003C09CB jmp      0x1403c0d7c
003C09D0 lea      r8, [rip + 0x1ee1a1]
003C09D7 lea      rdx, [rbp + 0x318]
003C09DE jmp      0x1403c0d7c
003C09E3 lea      r8, [rip + 0x1ee19e]
003C09EA lea      rdx, [rbp + 0x320]
003C09F1 jmp      0x1403c0d7c
003C09F6 lea      r8, [rip + 0x1d8743]
003C09FD lea      rdx, [rbp + 0x328]
003C0A04 jmp      0x1403c0d7c
003C0A09 lea      r8, [rip + 0x1ee188]
003C0A10 lea      rdx, [rbp + 0x330]
003C0A17 jmp      0x1403c0d7c
003C0A1C lea      r8, [rip + 0x1ee185]
003C0A23 lea      rdx, [rbp + 0x338]
003C0A2A jmp      0x1403c0d7c
003C0A2F lea      r8, [rip + 0x1ee182]
003C0A36 lea      rdx, [rbp + 0x340]
003C0A3D jmp      0x1403c0d7c
003C0A42 lea      r8, [rip + 0x1ee17f]
003C0A49 lea      rdx, [rbp + 0x348]
003C0A50 jmp      0x1403c0d7c
003C0A55 lea      r8, [rip + 0x1ee17c]
003C0A5C lea      rdx, [rbp + 0x350]
003C0A63 jmp      0x1403c0d7c
003C0A68 lea      r8, [rip + 0x1ee179]
003C0A6F lea      rdx, [rbp + 0x358]
003C0A76 jmp      0x1403c0d7c
003C0A7B lea      r8, [rip + 0x1ee176]
003C0A82 lea      rdx, [rbp + 0x360]
003C0A89 jmp      0x1403c0d7c
003C0A8E lea      r8, [rip + 0x1ee16f]
003C0A95 lea      rdx, [rbp + 0x368]
003C0A9C jmp      0x1403c0d7c
003C0AA1 lea      r8, [rip + 0x1dbf70]
003C0AA8 lea      rdx, [rbp + 0x370]
003C0AAF jmp      0x1403c0d7c
003C0AB4 lea      r8, [rip + 0x1ee155]
003C0ABB lea      rdx, [rbp + 0x420]
003C0AC2 jmp      0x1403c0d7c
003C0AC7 lea      r8, [rip + 0x1ed8aa]
003C0ACE lea      rdx, [rbp + 0x380]
003C0AD5 jmp      0x1403c0d7c
003C0ADA lea      r8, [rip + 0x1ee137]
003C0AE1 lea      rdx, [rbp + 0x388]
003C0AE8 jmp      0x1403c0d7c
003C0AED lea      r8, [rip + 0x1ee134]
003C0AF4 lea      rdx, [rbp + 0x390]
003C0AFB jmp      0x1403c0d7c
003C0B00 lea      r8, [rip + 0x1ddef9]
003C0B07 lea      rdx, [rbp + 0x398]
003C0B0E jmp      0x1403c0d7c
003C0B13 lea      r8, [rip + 0x1ee11e]
003C0B1A lea      rdx, [rbp + 0x3a0]
003C0B21 jmp      0x1403c0d7c
003C0B26 lea      r8, [rip + 0x1ee11b]
003C0B2D lea      rdx, [rbp + 0x3a8]
003C0B34 jmp      0x1403c0d7c
003C0B39 lea      r8, [rip + 0x1ee118]
003C0B40 lea      rdx, [rbp + 0x3b0]
003C0B47 jmp      0x1403c0d7c
003C0B4C lea      r8, [rip + 0x1d863d]
003C0B53 lea      rdx, [rbp + 0x3b8]
003C0B5A jmp      0x1403c0d7c
003C0B5F lea      r8, [rip + 0x1ee102]
003C0B66 lea      rdx, [rbp + 0x3c0]
003C0B6D jmp      0x1403c0d7c
003C0B72 lea      r8, [rip + 0x1d8627]
003C0B79 lea      rdx, [rbp + 0x3c8]
003C0B80 jmp      0x1403c0d7c
003C0B85 lea      r8, [rip + 0x1ee0ec]
003C0B8C lea      rdx, [rbp + 0x3d0]
003C0B93 jmp      0x1403c0d7c
003C0B98 lea      r8, [rip + 0x1ee0e9]
003C0B9F lea      rdx, [rbp + 0x3d8]
003C0BA6 jmp      0x1403c0d7c
003C0BAB lea      r8, [rip + 0x1ee0e6]
003C0BB2 lea      rdx, [rbp + 0x3e0]
003C0BB9 jmp      0x1403c0d7c
003C0BBE lea      r8, [rip + 0x1ee0e3]
003C0BC5 lea      rdx, [rbp + 0x3e8]
003C0BCC jmp      0x1403c0d7c
003C0BD1 lea      r8, [rip + 0x1d85d8]
003C0BD8 lea      rdx, [rbp + 0x3f0]
003C0BDF jmp      0x1403c0d7c
003C0BE4 lea      r8, [rip + 0x1ee0cd]
003C0BEB lea      rdx, [rbp + 0x3f8]
003C0BF2 jmp      0x1403c0d7c
003C0BF7 lea      r8, [rip + 0x1ee0ca]
003C0BFE lea      rdx, [rbp + 0x400]
003C0C05 jmp      0x1403c0d7c
003C0C0A lea      r8, [rip + 0x1ee0c7]
003C0C11 lea      rdx, [rbp + 0x408]
003C0C18 jmp      0x1403c0d7c
003C0C1D lea      r8, [rip + 0x1ee0c4]
003C0C24 lea      rdx, [rbp + 0x410]
003C0C2B jmp      0x1403c0d7c
003C0C30 lea      r8, [rip + 0x1ee0c1]
003C0C37 lea      rdx, [rbp + 0x418]
003C0C3E jmp      0x1403c0d7c
003C0C43 lea      r8, [rip + 0x1ee0be]
003C0C4A lea      rdx, [rbp + 0x4c8]
003C0C51 jmp      0x1403c0d7c
003C0C56 lea      r8, [rip + 0x1ce473]
003C0C5D lea      rdx, [rbp + 0x428]
003C0C64 jmp      0x1403c0d7c
003C0C69 lea      r8, [rip + 0x1ee0a8]
003C0C70 lea      rdx, [rbp + 0x430]
003C0C77 jmp      0x1403c0d7c
003C0C7C lea      r8, [rip + 0x1ee0a5]
003C0C83 lea      rdx, [rbp + 0x438]
003C0C8A jmp      0x1403c0d7c
003C0C8F lea      r8, [rip + 0x1ee0a2]
003C0C96 lea      rdx, [rbp + 0x440]
003C0C9D jmp      0x1403c0d7c
003C0CA2 lea      r8, [rip + 0x1ee09f]
003C0CA9 lea      rdx, [rbp + 0x448]
003C0CB0 jmp      0x1403c0d7c
003C0CB5 lea      r8, [rip + 0x1ed6ac]
003C0CBC lea      rdx, [rbp + 0x450]
003C0CC3 jmp      0x1403c0d7c
003C0CC8 lea      r8, [rip + 0x1ee089]
003C0CCF lea      rdx, [rbp + 0x458]
003C0CD6 jmp      0x1403c0d7c
003C0CDB lea      r8, [rip + 0x1ee086]
003C0CE2 lea      rdx, [rbp + 0x460]
003C0CE9 jmp      0x1403c0d7c
003C0CEE lea      r8, [rip + 0x1ee07b]
003C0CF5 lea      rdx, [rbp + 0x468]
003C0CFC jmp      0x1403c0d7c
003C0CFE lea      r8, [rip + 0x1ee073]
003C0D05 lea      rdx, [rbp + 0x470]
003C0D0C jmp      0x1403c0d7c
003C0D0E lea      r8, [rip + 0x1ee073]
003C0D15 lea      rdx, [rbp + 0x478]
003C0D1C jmp      0x1403c0d7c
003C0D1E lea      r8, [rip + 0x1ee073]
003C0D25 lea      rdx, [rbp + 0x480]
003C0D2C jmp      0x1403c0d7c
003C0D2E lea      r8, [rip + 0x1ee073]
003C0D35 lea      rdx, [rbp + 0x488]
003C0D3C jmp      0x1403c0d7c
003C0D3E lea      r8, [rip + 0x1ee073]
003C0D45 lea      rdx, [rbp + 0x490]
003C0D4C jmp      0x1403c0d7c
003C0D4E lea      r8, [rip + 0x1ee073]
003C0D55 lea      rdx, [rbp + 0x498]
003C0D5C jmp      0x1403c0d7c
003C0D5E lea      r8, [rip + 0x1ee06f]
003C0D65 lea      rdx, [rbp + 0x4a0]
003C0D6C jmp      0x1403c0d7c
003C0D6E lea      rdx, [rbp + 0x4a8]
003C0D75 lea      r8, [rip + 0x1edaec]
003C0D7C lea      rcx, [rbp + 0x28]
003C0D80 call     0x1403ff960
003C0D85 mov      rdx, qword ptr [rbp + 0x28]
003C0D89 lea      rcx, [rbp + 0x48]
003C0D8D mov      r12d, 1
003C0D93 mov      edi, r12d
003C0D96 call     0x140253990
003C0D9B lea      rcx, [rbp + 0x48]
003C0D9F call     0x1402547c0
003C0DA4 test     rax, rax
003C0DA7 je       0x1403c0dbb
003C0DA9 mov      edi, dword ptr [rax + 0x78]
003C0DAC mov      edx, r12d
003C0DAF mov      r8, qword ptr [rax]
003C0DB2 and      edi, r12d
003C0DB5 mov      rcx, rax
003C0DB8 call     qword ptr [r8]
003C0DBB mov      edx, 0xd7
003C0DC0 lea      rcx, [rbp + 0x58]
003C0DC4 call     0x1401ce0d0
003C0DC9 movzx    eax, word ptr [rip + 0x1d0958]
003C0DD0 lea      r9, [rbp - 0x30]
003C0DD4 mov      word ptr [rbp + 0x64], ax
003C0DD8 lea      rdx, [rbp - 0x28]
003C0DDC xor      eax, eax
003C0DDE mov      dword ptr [rbp + 0x66], 5
003C0DE5 test     edi, edi
003C0DE7 mov      qword ptr [rbp - 0x30], 0xffffffffffffffff
003C0DEF mov      r8d, 0xffffffff
003C0DF5 mov      qword ptr [rbp - 0x28], 0xffffffffffffffff
003C0DFD setne    al
003C0E00 mov      dword ptr [rsp + 0x20], 0xffffffff
003C0E08 lea      rcx, [rbp + 0x58]
003C0E0C mov      dword ptr [rbp + 0x60], eax
003C0E0F call     0x1401de3d0
003C0E14 lea      r8, [rbp + 0x28]
003C0E18 mov      r15, rax
003C0E1B lea      rdx, [rbp + 0x40]
003C0E1F lea      rcx, [rax + 0x30]
003C0E23 call     0x1403ff880
003C0E28 mov      rcx, qword ptr [r14 + 0xc]
003C0E2C mov      qword ptr [r15 + 0x80], rcx
003C0E33 mov      ecx, dword ptr [r14 + 0x48]
003C0E37 mov      dword ptr [r15 + 0x110], ecx
003C0E3E mov      dword ptr [r15 + 0x150], 0xffffffff
003C0E49 test     esi, esi
003C0E4B jne      0x1403c0f07
003C0E51 test     r13, r13
003C0E54 je       0x1403c0ec7
003C0E56 lea      ecx, [rsi + 0x20]
003C0E59 call     0x1404f7a88
003C0E5E mov      r14, rax
003C0E61 test     rax, rax
003C0E64 je       0x1403c0ea4
003C0E66 mov      rcx, qword ptr [rsp + 0x60]
003C0E6B mov      rax, qword ptr [r15]
003C0E6E mov      esi, dword ptr [r13 + 0x48]
003C0E72 mov      edi, dword ptr [rcx + 0x48]
003C0E75 mov      rcx, r15
003C0E78 call     qword ptr [rax + 8]
003C0E7B lea      rcx, [rip + 0x1cebde]
003C0E82 mov      dword ptr [r14 + 0xc], edi
003C0E86 mov      qword ptr [r14], rcx
003C0E89 mov      dword ptr [r14 + 8], esi
003C0E8D mov      qword ptr [r14 + 0x10], rax
003C0E91 mov      byte ptr [r14 + 0x1a], 0
003C0E96 movzx    eax, word ptr [rip + 0x1cdb07]
003C0E9D mov      word ptr [r14 + 0x18], ax
003C0EA2 jmp      0x1403c0ea7
003C0EA4 xor      r14d, r14d
003C0EA7 mov      rcx, qword ptr [rip + 0x2a669a]
003C0EAE xor      r8d, r8d
003C0EB1 add      rcx, 0x1768
003C0EB8 mov      rdx, r14
003C0EBB call     0x140204ec0
003C0EC0 mov      r14, qword ptr [rsp + 0x60]
003C0EC5 jmp      0x1403c0f07
003C0EC7 test     edi, edi
003C0EC9 jne      0x1403c0f07
003C0ECB mov      rax, qword ptr [r15]
003C0ECE mov      rcx, r15
003C0ED1 call     qword ptr [rax + 8]
003C0ED4 mov      rcx, qword ptr [rsp + 0x70]
003C0ED9 mov      r9d, r12d
003C0EDC mov      rdx, rax
003C0EDF mov      dword ptr [rsp + 0x20], r12d
003C0EE4 mov      qword ptr [rax + 0x88], rcx
003C0EEB mov      rcx, r14
003C0EEE mov      dword ptr [rax + 0x20], 2
003C0EF5 mov      r10, qword ptr [r14]
003C0EF8 movzx    r8d, byte ptr [rip + 0x1ebf63]
003C0F00 call     qword ptr [r10 + 0xe8]
003C0F07 mov      rax, qword ptr [r14]
003C0F0A mov      r9d, r12d
003C0F0D movzx    r8d, byte ptr [rip + 0x1ebf4e]
003C0F15 mov      rdx, r15
003C0F18 mov      rcx, r14
003C0F1B mov      dword ptr [rsp + 0x20], r12d
003C0F20 call     qword ptr [rax + 0xe8]
003C0F26 cmp      qword ptr [rbp + 0x48], 0
003C0F2B je       0x1403c0f4a
003C0F2D lea      rdx, [rip + 0x22a879]
003C0F34 lea      rcx, [rbp + 0x50]
003C0F38 call     0x1403ffb60
003C0F3D test     eax, eax
003C0F3F je       0x1403c0f4a
003C0F41 mov      rcx, qword ptr [rbp + 0x48]
003C0F45 call     0x14001e1e0
003C0F4A mov      r15, qword ptr [rbp - 0x78]
003C0F4E xor      esi, esi
003C0F50 mov      qword ptr [rbp + 0x48], rsi
003C0F54 jmp      0x1403c0f58
003C0F56 xor      esi, esi
003C0F58 lea      rdx, [rip + 0x22a84e]
003C0F5F lea      rcx, [rbp + 0x30]
003C0F63 call     0x1403ffb60
003C0F68 mov      rdi, qword ptr [rsp + 0x68]
003C0F6D test     eax, eax
003C0F6F je       0x1403c0fa9
003C0F71 mov      dword ptr [rsp + 0x38], esi
003C0F75 lea      rdx, [rbp + 0x30]
003C0F79 mov      dword ptr [rsp + 0x30], esi
003C0F7D xor      r9d, r9d
003C0F80 mov      qword ptr [rsp + 0x28], rdi
003C0F85 mov      rcx, r14
003C0F88 mov      dword ptr [rsp + 0x20], 0xffffffff
003C0F90 test     r13, r13
003C0F93 je       0x1403c0f9f
003C0F95 mov      r8, r13
003C0F98 call     0x14016abc0
003C0F9D jmp      0x1403c0fa9
003C0F9F lea      r8, [rsp + 0x70]
003C0FA4 call     0x14016b9d0
003C0FA9 cmp      dword ptr [rsp + 0x48], 0
003C0FAE je       0x1403c1008
003C0FB0 cmp      dword ptr [rsp + 0x50], 0
003C0FB5 mov      r8, r15
003C0FB8 mov      rax, qword ptr [rbp - 0x20]
003C0FBC mov      rax, qword ptr [rax]
003C0FBF mov      qword ptr [rsp + 0x70], rax
003C0FC4 je       0x1403c0fcf
003C0FC6 mov      r8, qword ptr [rbp - 0x18]
003C0FCA mov      qword ptr [rsp + 0x70], rbx
003C0FCF mov      rdx, qword ptr [rbp - 0x80]
003C0FD3 xor      r9d, r9d
003C0FD6 mov      dword ptr [rsp + 0x38], esi
003C0FDA add      rdx, 8
003C0FDE mov      dword ptr [rsp + 0x30], esi
003C0FE2 mov      rcx, r14
003C0FE5 mov      qword ptr [rsp + 0x28], rdi
003C0FEA mov      dword ptr [rsp + 0x20], 0xffffffff
003C0FF2 test     r8, r8
003C0FF5 je       0x1403c0ffe
003C0FF7 call     0x14016abc0
003C0FFC jmp      0x1403c1008
003C0FFE lea      r8, [rsp + 0x70]
003C1003 call     0x14016b9d0
003C1008 test     rdi, rdi
003C100B je       0x1403c101a
003C100D mov      edx, 0x20
003C1012 mov      rcx, rdi
003C1015 call     0x14045e690
003C101A mov      r15d, dword ptr [rsp + 0x4c]
003C101F mov      r13d, 1
003C1025 mov      r12, qword ptr [rbp - 0x70]
003C1029 mov      eax, r15d
003C102C dec      r15d
003C102F mov      dword ptr [rsp + 0x4c], r15d
003C1034 test     eax, eax
003C1036 jg       0x1403bf9f0
003C103C mov      ebx, dword ptr [r14 + 0x48]
003C1040 lea      rdx, [rip + 0x1edd99]
003C1047 mov      rdi, qword ptr [r14 + 0x18]
003C104B lea      rcx, [rbp + 0x40]
003C104F lea      r15, [r14 + 0xc]
003C1053 call     0x1403fd6b0
003C1058 mov      dword ptr [rsp + 0x38], 0xffffffff
003C1060 mov      r12d, 0x20
003C1066 mov      dword ptr [rsp + 0x30], esi
003C106A mov      rcx, rax
003C106D mov      dword ptr [rsp + 0x28], r12d
003C1072 mov      r9d, ebx
003C1075 mov      r8, r15
003C1078 mov      qword ptr [rsp + 0x20], r15
003C107D mov      rdx, rdi
003C1080 call     0x140258da0
003C1085 mov      rcx, qword ptr [r14 + 0x18]
003C1089 lea      rdx, [rbp - 0x50]
003C108D mov      rax, qword ptr [rip + 0x29ba7c]
003C1094 add      rcx, 0x204
003C109B mov      qword ptr [rbp - 0x50], rax
003C109F call     0x1403ffe40
003C10A4 lea      ecx, [r13 + 0x37]
003C10A8 call     0x1404f7a88
003C10AD mov      r14, rax
003C10B0 test     rax, rax
003C10B3 je       0x1403c1126
003C10B5 lea      rdx, [rip + 0x1edd24]
003C10BC lea      rcx, [rbp + 0x38]
003C10C0 call     0x1403ff7c0
003C10C5 mov      rbx, qword ptr [r15]
003C10C8 mov      rcx, qword ptr [rsp + 0x60]
003C10CD mov      eax, dword ptr [rcx + 0x48]
003C10D0 lea      rcx, [r14 + 0x10]
003C10D4 mov      dword ptr [r14 + 0xc], eax
003C10D8 mov      dword ptr [r14 + 8], eax
003C10DC lea      rax, [rip + 0x1cf71d]
003C10E3 mov      qword ptr [r14], rax
003C10E6 call     0x1403ff870
003C10EB mov      rax, qword ptr [rip + 0x29ba1e]
003C10F2 lea      r8, [rbp + 0x38]
003C10F6 lea      rdx, [rbp + 0x40]
003C10FA mov      qword ptr [r14 + 0x18], rax
003C10FE lea      rcx, [r14 + 0x10]
003C1102 call     0x1403ff880
003C1107 lea      rdx, [rbp - 0x50]
003C110B lea      rcx, [r14 + 0x18]
003C110F call     0x1403fd770
003C1114 mov      rax, qword ptr [r15]
003C1117 mov      qword ptr [r14 + 0x20], rax
003C111B mov      qword ptr [r14 + 0x28], rbx
003C111F mov      word ptr [r14 + 0x30], r12w
003C1124 jmp      0x1403c1129
003C1126 mov      r14, rsi
003C1129 mov      rcx, qword ptr [rip + 0x2a6418]
003C1130 xor      r8d, r8d
003C1133 add      rcx, 0x1768
003C113A mov      rdx, r14
003C113D call     0x140204ec0
003C1142 movzx    ebx, word ptr [rip + 0x1ce427]
003C1149 lea      rcx, [rbp - 0x50]
003C114D call     0x1403fd740
003C1152 movzx    eax, bx
003C1155 mov      rcx, qword ptr [rbp + 0x4d0]
003C115C xor      rcx, rsp
003C115F call     0x1404f77a0
003C1164 add      rsp, 0x5e8
003C116B pop      r15
003C116D pop      r14
003C116F pop      r13
003C1171 pop      r12
003C1173 pop      rdi
003C1174 pop      rsi
003C1175 pop      rbx
003C1176 pop      rbp
003C1177 ret      
003C1178 adc      edi, ebp
003C117A cmp      eax, dword ptr [rax]
003C117C adc      edi, ebp
003C117E cmp      eax, dword ptr [rax]
003C1180 adc      edi, ebp
003C1182 cmp      eax, dword ptr [rax]
003C1184 adc      edi, ebp
003C1186 cmp      eax, dword ptr [rax]
003C1188 adc      edi, ebp
003C118A cmp      eax, dword ptr [rax]
003C118C sbb      eax, 0x13003bfb
003C1191 std      
003C1192 cmp      eax, dword ptr [rax]
003C1194 adc      edi, ebp
003C1196 cmp      eax, dword ptr [rax]
003C1198 sti      
003C119A cmp      eax, dword ptr [rax]
003C119C paddw    mm7, qword ptr [rbx]
003C119F add      byte ptr [rdi], cl
003C11A1 std      
003C11A2 cmp      eax, dword ptr [rax]
003C11A4 sbb      ch, bh
003C11A6 cmp      eax, dword ptr [rax]
