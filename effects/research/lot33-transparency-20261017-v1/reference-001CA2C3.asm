001CA2C3 mov      qword ptr [rsp + 0xd0], rdi
001CA2CB lea      rdi, [rdx + 0xc]
001CA2CF cmp      dword ptr [rcx + 0x1c], ebx
001CA2D2 je       0x1401ca2e8
001CA2D4 mov      rax, qword ptr [rcx + 0x88]
001CA2DB mov      qword ptr [rbp - 0x19], rax
001CA2DF mov      dword ptr [rbp - 9], 0xffffffff
001CA2E6 jmp      0x1401ca2f5
001CA2E8 mov      rax, qword ptr [rdi]
001CA2EB mov      qword ptr [rbp - 0x19], rax
001CA2EF mov      eax, dword ptr [rdx + 0x48]
001CA2F2 mov      dword ptr [rbp - 9], eax
001CA2F5 mov      edx, dword ptr [rcx + 0x20]
001CA2F8 lea      r8, [rip - 0x1ca2ff]
001CA2FF mov      qword ptr [rsp + 0x80], r12
001CA307 lea      eax, [rdx - 0x20]
001CA30A cmp      eax, 7
001CA30D ja       0x1401ca75d
001CA313 mov      ecx, dword ptr [r8 + rax*4 + 0x1caa28]
001CA31B add      rcx, r8
001CA31E jmp      rcx
001CA320 mov      rax, qword ptr [rip + 0x49d239]
001CA327 cmp      byte ptr [rax + 0x2c9], 1
001CA32E jne      0x1401ca445
001CA334 mov      ebx, dword ptr [r13 + 0x48]
001CA338 lea      rdx, [rip + 0x3ceee9]
001CA33F lea      rcx, [rbp + 0xf]
001CA343 call     0x1403fd6b0
001CA348 mov      dword ptr [rsp + 0x38], 0xffffffff
001CA350 lea      r8, [rbp - 0x19]
001CA354 mov      dword ptr [rsp + 0x30], r14d
001CA359 mov      rcx, rax
001CA35C mov      dword ptr [rsp + 0x28], r14d
001CA361 mov      r9d, ebx
001CA364 mov      rdx, rsi
001CA367 mov      qword ptr [rsp + 0x20], rdi
001CA36C call     0x140258da0
001CA371 mov      rcx, qword ptr [r13 + 0x18]
001CA375 lea      rdx, [rbp - 9]
001CA379 mov      rax, qword ptr [rip + 0x492790]
001CA380 add      rcx, 0x204
001CA387 mov      qword ptr [rbp - 9], rax
001CA38B call     0x1403ffe40
001CA390 mov      ecx, 0x38
001CA395 call     0x1404f7a88
001CA39A mov      r12, rax
001CA39D test     rax, rax
001CA3A0 je       0x1401ca41b
001CA3A2 lea      rdx, [rip + 0x3cee7f]
001CA3A9 lea      rcx, [rbp + 0xf]
001CA3AD call     0x1403ff7c0
001CA3B2 mov      eax, dword ptr [r13 + 0x48]
001CA3B6 lea      rcx, [r12 + 0x10]
001CA3BB mov      rbx, qword ptr [rbp - 0x19]
001CA3BF mov      dword ptr [r12 + 0xc], eax
001CA3C4 mov      dword ptr [r12 + 8], eax
001CA3C9 lea      rax, [rip + 0x3c6430]
001CA3D0 mov      qword ptr [r12], rax
001CA3D4 call     0x1403ff870
001CA3D9 mov      rax, qword ptr [rip + 0x492730]
001CA3E0 lea      r8, [rbp + 0xf]
001CA3E4 lea      rdx, [rbp + 0x17]
001CA3E8 mov      qword ptr [r12 + 0x18], rax
001CA3ED lea      rcx, [r12 + 0x10]
001CA3F2 call     0x1403ff880
001CA3F7 lea      rdx, [rbp - 9]
001CA3FB lea      rcx, [r12 + 0x18]
001CA400 call     0x1403fd770
001CA405 mov      rax, qword ptr [rbp - 0x19]
001CA409 mov      qword ptr [r12 + 0x20], rax
001CA40E mov      qword ptr [r12 + 0x28], rbx
001CA413 mov      word ptr [r12 + 0x30], r14w
001CA419 jmp      0x1401ca41e
001CA41B mov      r12, r14
001CA41E mov      rcx, qword ptr [rip + 0x49d123]
001CA425 xor      r8d, r8d
001CA428 add      rcx, 0x1768
001CA42F mov      rdx, r12
001CA432 call     0x140204ec0
001CA437 lea      rcx, [rbp - 9]
001CA43B call     0x1403fd740
001CA440 jmp      0x1401ca9cd
001CA445 mov      ecx, 0x3b8
001CA44A call     0x1404f7a88
001CA44F test     rax, rax
001CA452 je       0x1401ca45f
001CA454 mov      rcx, rax
001CA457 call     0x140227b10
001CA45C mov      r14, rax
001CA45F mov      r8d, 0x43
001CA465 xor      edx, edx
001CA467 mov      rcx, r14
001CA46A call     0x140235d80
001CA46F sub      dword ptr [rbp - 0x15], 2
001CA473 mov      rcx, r14
001CA476 mov      rax, qword ptr [r14]
001CA479 mov      r8, qword ptr [rbp - 0x19]
001CA47D mov      rdx, qword ptr [r13 + 0x18]
001CA481 call     qword ptr [rax + 0x138]
001CA487 jmp      0x1401ca9cd
001CA48C mov      ecx, 0x3b8
001CA491 call     0x1404f7a88
001CA496 test     rax, rax
001CA499 je       0x1401ca4a6
001CA49B mov      rcx, rax
001CA49E call     0x140227b10
001CA4A3 mov      r14, rax
001CA4A6 mov      r8d, 0x41
001CA4AC jmp      0x1401ca465
001CA4AE mov      ecx, 0x3b8
001CA4B3 call     0x1404f7a88
001CA4B8 test     rax, rax
001CA4BB je       0x1401ca4c8
001CA4BD mov      rcx, rax
001CA4C0 call     0x140227b10
001CA4C5 mov      r14, rax
001CA4C8 mov      r8d, 0x45
001CA4CE jmp      0x1401ca465
001CA4D0 mov      ecx, 0x328
001CA4D5 call     0x1404f7a88
001CA4DA mov      rdi, rax
001CA4DD test     rax, rax
001CA4E0 je       0x1401ca533
001CA4E2 lea      rdx, [rip + 0x4212c4]
001CA4E9 lea      rcx, [rbp + 0xf]
001CA4ED call     0x1403fd6b0
001CA4F2 lea      rdx, [rip + 0x3ced3f]
001CA4F9 lea      rcx, [rbp + 0x17]
001CA4FD call     0x1403fd6b0
001CA502 movzx    eax, byte ptr [rip + 0x3d424b]
001CA509 lea      r8, [rbp + 0xf]
001CA50D add      ax, ax
001CA510 lea      rdx, [rbp + 0x17]
001CA514 mov      word ptr [rsp + 0x28], ax
001CA519 mov      r9b, 0xff
001CA51C mov      rcx, rdi
001CA51F mov      dword ptr [rsp + 0x20], r14d
001CA524 call     0x140227cd0
001CA529 mov      r12, rax
001CA52C mov      ebx, 3
001CA531 jmp      0x1401ca536
001CA533 mov      r12, r14
001CA536 test     bl, 2
001CA539 je       0x1401ca547
001CA53B and      ebx, 0xfffffffd
001CA53E lea      rcx, [rbp + 0x17]
001CA542 call     0x1403fd740
001CA547 test     bl, 1
001CA54A je       0x1401ca990
001CA550 lea      rcx, [rbp + 0xf]
001CA554 call     0x1403fd740
001CA559 jmp      0x1401ca990
001CA55E mov      ecx, 0x328
001CA563 call     0x1404f7a88
001CA568 mov      rdi, rax
001CA56B test     rax, rax
001CA56E je       0x1401ca5c4
001CA570 lea      rdx, [rip + 0x421236]
001CA577 lea      rcx, [rbp + 0x17]
001CA57B call     0x1403fd6b0
001CA580 lea      rdx, [rip + 0x3cecb9]
001CA587 lea      rcx, [rbp + 0xf]
001CA58B call     0x1403fd6b0
001CA590 movzx    eax, byte ptr [rip + 0x3d41bd]
001CA597 lea      r8, [rbp + 0x17]
001CA59B add      ax, ax
001CA59E lea      rdx, [rbp + 0xf]
001CA5A2 mov      word ptr [rsp + 0x28], ax
001CA5A7 mov      r9b, 0xff
001CA5AA mov      rcx, rdi
001CA5AD mov      dword ptr [rsp + 0x20], 1
001CA5B5 call     0x140227cd0
001CA5BA mov      r12, rax
001CA5BD mov      ebx, 0xc
001CA5C2 jmp      0x1401ca5c7
001CA5C4 mov      r12, r14
001CA5C7 test     bl, 8
001CA5CA je       0x1401ca5d8
001CA5CC and      ebx, 0xfffffff7
001CA5CF lea      rcx, [rbp + 0xf]
001CA5D3 call     0x1403fd740
001CA5D8 test     bl, 4
001CA5DB je       0x1401ca990
001CA5E1 lea      rcx, [rbp + 0x17]
001CA5E5 call     0x1403fd740
001CA5EA jmp      0x1401ca990
001CA5EF lea      rdx, [rip + 0x3cec52]
001CA5F6 mov      edi, 0x93
001CA5FB lea      rcx, [rbp + 7]
001CA5FF call     0x1403fd810
001CA604 lea      rdx, [rip + 0x3cec45]
001CA60B jmp      0x1401ca8e2
001CA610 mov      ebx, dword ptr [r13 + 0x48]
001CA614 lea      rdx, [rip + 0x3c62c5]
001CA61B lea      rcx, [rbp + 0xf]
001CA61F call     0x1403fd6b0
001CA624 mov      dword ptr [rsp + 0x38], 0xffffffff
001CA62C lea      r8, [rbp - 0x19]
001CA630 mov      dword ptr [rsp + 0x30], r14d
001CA635 mov      rcx, rax
001CA638 mov      dword ptr [rsp + 0x28], r14d
001CA63D mov      r9d, ebx
001CA640 mov      rdx, rsi
001CA643 mov      qword ptr [rsp + 0x20], rdi
001CA648 call     0x140258da0
001CA64D mov      rcx, qword ptr [r13 + 0x18]
001CA651 lea      rdx, [rbp - 9]
001CA655 mov      rax, qword ptr [rip + 0x4924b4]
001CA65C add      rcx, 0x204
001CA663 mov      qword ptr [rbp - 9], rax
001CA667 call     0x1403ffe40
001CA66C mov      ecx, 0x38
001CA671 call     0x1404f7a88
001CA676 mov      r12, rax
001CA679 test     rax, rax
001CA67C je       0x1401ca6f7
001CA67E lea      rdx, [rip + 0x3c625b]
001CA685 lea      rcx, [rbp + 0xf]
001CA689 call     0x1403ff7c0
001CA68E mov      eax, dword ptr [r13 + 0x48]
001CA692 lea      rcx, [r12 + 0x10]
001CA697 mov      rbx, qword ptr [rbp - 0x19]
001CA69B mov      dword ptr [r12 + 0xc], eax
001CA6A0 mov      dword ptr [r12 + 8], eax
001CA6A5 lea      rax, [rip + 0x3c6154]
001CA6AC mov      qword ptr [r12], rax
001CA6B0 call     0x1403ff870
001CA6B5 mov      rax, qword ptr [rip + 0x492454]
001CA6BC lea      r8, [rbp + 0xf]
001CA6C0 lea      rdx, [rbp + 0x17]
001CA6C4 mov      qword ptr [r12 + 0x18], rax
001CA6C9 lea      rcx, [r12 + 0x10]
001CA6CE call     0x1403ff880
001CA6D3 lea      rdx, [rbp - 9]
001CA6D7 lea      rcx, [r12 + 0x18]
001CA6DC call     0x1403fd770
001CA6E1 mov      rax, qword ptr [rbp - 0x19]
001CA6E5 mov      qword ptr [r12 + 0x20], rax
001CA6EA mov      qword ptr [r12 + 0x28], rbx
001CA6EF mov      word ptr [r12 + 0x30], r14w
001CA6F5 jmp      0x1401ca6fa
001CA6F7 mov      r12, r14
001CA6FA mov      rcx, qword ptr [rip + 0x49ce47]
001CA701 xor      r8d, r8d
001CA704 add      rcx, 0x1768
001CA70B mov      rdx, r12
001CA70E call     0x140204ec0
001CA713 lea      rcx, [rbp - 9]
001CA717 mov      dword ptr [r15 + 0x114], 1
001CA722 call     0x1403fd740
001CA727 jmp      0x1401ca9d8
001CA72C lea      rdx, [rip + 0x3ceb25]
001CA733 lea      rcx, [rbp + 7]
001CA737 call     0x1403fd810
001CA73C lea      rdx, [rip + 0x42106a]
001CA743 mov      edi, 0xcf
001CA748 lea      rcx, [rbp - 0x11]
001CA74C call     0x1403fd810
001CA751 lea      rdx, [rip + 0x3ceb10]
001CA758 jmp      0x1401ca8f2
001CA75D cmp      edx, 0x1e
001CA760 ja       0x1401ca82d
001CA766 mov      ecx, dword ptr [r8 + rdx*4 + 0x1caa48]
001CA76E add      rcx, r8
001CA771 jmp      rcx
001CA773 mov      edi, 0x76
001CA778 jmp      0x1401ca831
001CA77D mov      edi, 0x77
001CA782 jmp      0x1401ca831
001CA787 mov      edi, 0x78
001CA78C jmp      0x1401ca831
001CA791 mov      edi, 0x79
001CA796 jmp      0x1401ca831
001CA79B mov      edi, 0x7a
001CA7A0 jmp      0x1401ca831
001CA7A5 mov      edi, 0x7b
001CA7AA jmp      0x1401ca831
001CA7AF mov      edi, 0x7c
001CA7B4 jmp      0x1401ca831
001CA7B6 mov      edi, 0x7d
001CA7BB jmp      0x1401ca831
001CA7BD mov      edi, 0x7e
001CA7C2 jmp      0x1401ca831
001CA7C4 mov      edi, 0x7f
001CA7C9 jmp      0x1401ca831
001CA7CB mov      edi, 0x80
001CA7D0 jmp      0x1401ca831
001CA7D2 mov      edi, 0x81
001CA7D7 jmp      0x1401ca831
001CA7D9 mov      edi, 0x82
001CA7DE jmp      0x1401ca831
001CA7E0 mov      edi, 0x83
001CA7E5 jmp      0x1401ca831
001CA7E7 mov      edi, 0x84
001CA7EC jmp      0x1401ca831
001CA7EE mov      edi, 0x85
001CA7F3 jmp      0x1401ca831
001CA7F5 mov      edi, 0x86
001CA7FA jmp      0x1401ca831
001CA7FC mov      edi, 0x87
001CA801 jmp      0x1401ca831
001CA803 mov      edi, 0x88
001CA808 jmp      0x1401ca831
001CA80A mov      edi, 0x89
001CA80F jmp      0x1401ca831
001CA811 mov      edi, 0x8a
001CA816 jmp      0x1401ca831
001CA818 mov      edi, 0x8b
001CA81D jmp      0x1401ca831
001CA81F mov      edi, 0x8c
001CA824 jmp      0x1401ca831
001CA826 mov      edi, 0x8d
001CA82B jmp      0x1401ca831
001CA82D movzx    edi, word ptr [rbp - 9]
001CA831 and      edx, 3
001CA834 jne      0x1401ca866
001CA836 lea      rdx, [rip + 0x3cea0b]
001CA83D lea      rcx, [rbp + 7]
001CA841 call     0x1403fd810
001CA846 cmp      dword ptr [r15 + 0x20], 4
001CA84B lea      rcx, [rbp - 0x11]
001CA84F jb       0x1401ca85a
001CA851 lea      rdx, [rip + 0x3cea18]
001CA858 jmp      0x1401ca8b6
001CA85A lea      rdx, [rip + 0x420f4c]
001CA861 jmp      0x1401ca8e6
001CA866 cmp      edx, 1
001CA869 jne      0x1401ca88f
001CA86B lea      rdx, [rip + 0x3cea06]
001CA872 lea      rcx, [rbp + 7]
001CA876 call     0x1403fd810
001CA87B cmp      dword ptr [r15 + 0x20], 4
001CA880 lea      rcx, [rbp - 0x11]
001CA884 jb       0x1401ca85a
001CA886 lea      rdx, [rip + 0x3ce9f3]
001CA88D jmp      0x1401ca8b6
001CA88F cmp      edx, 2
001CA892 jne      0x1401ca8fb
001CA894 lea      rdx, [rip + 0x3ce9f5]
001CA89B lea      rcx, [rbp + 7]
001CA89F call     0x1403fd810
001CA8A4 cmp      dword ptr [r15 + 0x20], 4
001CA8A9 jb       0x1401ca8db
001CA8AB lea      rdx, [rip + 0x3ce9e6]
001CA8B2 lea      rcx, [rbp - 0x11]
001CA8B6 call     0x1403fd810
001CA8BB mov      rax, qword ptr [rbp - 0x11]
001CA8BF lea      rcx, [rbp - 0x11]
001CA8C3 mov      r8d, dword ptr [r15 + 0x20]
001CA8C7 shr      r8d, 2
001CA8CB add      r8b, 0x30
001CA8CF mov      edx, dword ptr [rax - 8]
001CA8D2 dec      edx
001CA8D4 call     0x1403fe730
001CA8D9 jmp      0x1401ca8eb
001CA8DB lea      rdx, [rip + 0x420ecb]
001CA8E2 lea      rcx, [rbp - 0x11]
001CA8E6 call     0x1403fd810
001CA8EB lea      rdx, [rip + 0x420ebb]
001CA8F2 lea      rcx, [rbp - 1]
001CA8F6 call     0x1403fd810
001CA8FB mov      ecx, 0x418
001CA900 call     0x1404f7a88
001CA905 test     rax, rax
001CA908 je       0x1401ca92f
001CA90A mov      byte ptr [rsp + 0x28], bl
001CA90E lea      r9, [rbp - 0x11]
001CA912 lea      r8, [rbp - 1]
001CA916 mov      dword ptr [rsp + 0x20], 8
001CA91E lea      rdx, [rbp + 7]
001CA922 mov      rcx, rax
001CA925 call     0x140227df0
001CA92A mov      r12, rax
001CA92D jmp      0x1401ca932
001CA92F mov      r12, r14
001CA932 mov      ecx, 0x28
001CA937 call     0x1404f7a88
001CA93C mov      rsi, rax
001CA93F test     rax, rax
001CA942 je       0x1401ca974
001CA944 mov      ebx, dword ptr [r13 + 0x48]
001CA948 mov      rdx, r13
001CA94B mov      rcx, r12
001CA94E call     0x14022f340
001CA953 mov      r8d, dword ptr [rbp - 9]
001CA957 lea      r9, [rbp - 0x19]
001CA95B mov      dword ptr [rsp + 0x30], ebx
001CA95F movzx    edx, di
001CA962 mov      dword ptr [rsp + 0x28], ebx
001CA966 mov      rcx, rsi
001CA969 mov      dword ptr [rsp + 0x20], eax
001CA96D call     0x140204300
001CA972 jmp      0x1401ca977
001CA974 mov      rax, r14
001CA977 mov      rcx, qword ptr [rip + 0x49cbca]
001CA97E xor      r8d, r8d
001CA981 add      rcx, 0x1768
001CA988 mov      rdx, rax
001CA98B call     0x140204ec0
001CA990 mov      ebx, dword ptr [r13 + 0x48]
001CA994 mov      rdx, r13
001CA997 mov      rdi, qword ptr [r13 + 0x18]
001CA99B mov      rcx, r12
001CA99E mov      rsi, qword ptr [r12]
001CA9A2 call     0x14022f340
001CA9A7 mov      r9d, dword ptr [rbp - 9]
001CA9AB mov      r8d, ebx
001CA9AE mov      word ptr [rsp + 0x30], r14w
001CA9B4 mov      rdx, rdi
001CA9B7 mov      dword ptr [rsp + 0x28], eax
001CA9BB mov      rcx, r12
001CA9BE mov      rax, qword ptr [rbp - 0x19]
001CA9C2 mov      qword ptr [rsp + 0x20], rax
001CA9C7 call     qword ptr [rsi + 0xd0]
001CA9CD mov      dword ptr [r15 + 0x114], 1
001CA9D8 mov      r12, qword ptr [rsp + 0x80]
001CA9E0 mov      rdi, qword ptr [rsp + 0xd0]
