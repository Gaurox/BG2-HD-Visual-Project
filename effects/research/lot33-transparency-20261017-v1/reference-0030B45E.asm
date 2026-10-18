0030B45E and      edi, 0xf0
0030B464 je       0x14030b5be
0030B46A cmp      edi, 0x10
0030B46D je       0x14030b514
0030B473 cmp      edi, 0x20
0030B476 jne      0x14030b3da
0030B47C lea      rdx, [rip + 0x29fedd]
0030B483 lea      rcx, [rbp - 0x38]
0030B487 call     0x1403ff7c0
0030B48C mov      ebx, 1
0030B491 lea      rcx, [rsi + 0xde8]
0030B498 mov      r9d, ebx
0030B49B lea      rdx, [rbp - 0x38]
0030B49F mov      r8d, ebx
0030B4A2 call     0x14014d080
0030B4A7 movzx    eax, byte ptr [r14 + 1]
0030B4AC lea      rdx, [rip + 0x2b525d]
0030B4B3 lea      rcx, [rsi + 0xce8]
0030B4BA mov      edx, dword ptr [rdx + rax*4]
0030B4BD call     0x140412690
0030B4C2 xor      edi, edi
0030B4C4 xor      edx, edx
0030B4C6 mov      rcx, r15
0030B4C9 mov      word ptr [rsi + 0xf86], di
0030B4D0 call     0x140412380
0030B4D5 movzx    edx, word ptr [r15 + 0x11a]
0030B4DD mov      rcx, r15
0030B4E0 call     0x140411cc0
0030B4E5 movzx    ebx, al
0030B4E8 call     0x14050933c
0030B4ED mov      edx, eax
0030B4EF mov      rcx, r15
0030B4F2 and      edx, 0x7fff
0030B4F8 imul     edx, ebx
0030B4FB shr      edx, 0xf
0030B4FE call     0x140411610
0030B503 call     0x14050933c
0030B508 and      eax, 0x7fff
0030B50D add      eax, eax
0030B50F jmp      0x14030b5a7
0030B514 lea      rdx, [rip + 0x29fe35]
0030B51B lea      rcx, [rbp - 0x38]
0030B51F call     0x1403ff7c0
0030B524 mov      ebx, 1
0030B529 lea      rcx, [rsi + 0xde8]
0030B530 mov      r9d, ebx
0030B533 lea      rdx, [rbp - 0x38]
0030B537 mov      r8d, ebx
0030B53A call     0x14014d080
0030B53F xor      edi, edi
0030B541 xor      edx, edx
0030B543 mov      rcx, r15
0030B546 mov      word ptr [rsi + 0xf86], di
0030B54D call     0x140412380
0030B552 xor      edx, edx
0030B554 mov      rcx, r15
0030B557 call     0x140411610
0030B55C xor      bl, bl
0030B55E nop      
0030B560 mov      rax, qword ptr [rip + 0x35bfe1]
0030B567 mov      rcx, r12
0030B56A movzx    r8d, byte ptr [r14]
0030B56E movzx    edx, bl
0030B571 mov      r9, qword ptr [rax + 0x1090]
0030B578 add      r9, 0x63d8
0030B57F call     0x1404221c0
0030B584 inc      bl
0030B586 lea      r14, [r14 + 1]
0030B58A cmp      bl, 7
0030B58D jb       0x14030b560
0030B58F mov      rdx, r12
0030B592 mov      rcx, r15
0030B595 call     0x140412390
0030B59A call     0x14050933c
0030B59F and      eax, 0x7fff
0030B5A4 lea      eax, [rax + rax*2]
0030B5A7 cmp      eax, 0x8000
0030B5AC jae      0x14030b3dc
0030B5B2 mov      byte ptr [rsi + 0xf81], dil
0030B5B9 jmp      0x14030b3dc
0030B5BE lea      rdx, [rip + 0x29fd8b]
0030B5C5 lea      rcx, [rbp - 0x38]
0030B5C9 call     0x1403ff7c0
0030B5CE mov      ebx, 1
0030B5D3 lea      rcx, [rsi + 0xde8]
0030B5DA mov      r9d, ebx
0030B5DD lea      rdx, [rbp - 0x38]
0030B5E1 mov      r8d, ebx
0030B5E4 call     0x14014d080
0030B5E9 mov      edx, ebx
0030B5EB mov      word ptr [rsi + 0xf86], bx
0030B5F2 mov      rcx, r15
0030B5F5 call     0x140412380
0030B5FA xor      edx, edx
0030B5FC mov      rcx, r15
0030B5FF call     0x140411610
0030B604 xor      bl, bl
0030B606 nop      word ptr [rax + rax]
0030B610 mov      rax, qword ptr [rip + 0x35bf31]
0030B617 mov      rcx, r12
0030B61A movzx    r8d, byte ptr [r14]
0030B61E movzx    edx, bl
0030B621 mov      r9, qword ptr [rax + 0x1090]
0030B628 add      r9, 0x63d8
0030B62F call     0x1404221c0
0030B634 inc      bl
0030B636 lea      r14, [r14 + 1]
0030B63A cmp      bl, 7
0030B63D jb       0x14030b610
0030B63F jmp      0x14030b3cf
0030B644 mov      ebx, 1
0030B649 and      edi, 0xf0
0030B64F je       0x14030b65f
0030B651 cmp      edi, 0x10
0030B654 jne      0x14030b685
0030B656 lea      rdx, [rip + 0x29fce3]
0030B65D jmp      0x14030b666
0030B65F lea      rdx, [rip + 0x29fcce]
0030B666 lea      rcx, [rbp - 0x38]
0030B66A call     0x1403ff7c0
0030B66F mov      r9d, ebx
0030B672 lea      rdx, [rbp - 0x38]
0030B676 mov      r8d, ebx
0030B679 lea      rcx, [rsi + 0xde8]
0030B680 call     0x14014d080
0030B685 lea      rdx, [rip + 0x29fc84]
0030B68C lea      rcx, [rbp - 0x38]
0030B690 call     0x1403ff7c0
0030B695 lea      rcx, [rsi + 0xf20]
0030B69C mov      r9d, ebx
0030B69F mov      r8d, ebx
0030B6A2 lea      rdx, [rbp - 0x38]
0030B6A6 call     0x14014d080
0030B6AB mov      rcx, r15
0030B6AE call     0x140411af0
0030B6B3 movzx    ebx, ax
0030B6B6 call     0x14050933c
0030B6BB and      eax, 0x7fff
0030B6C0 imul     eax, ebx
0030B6C3 shr      eax, 0xf
0030B6C6 mov      word ptr [rsi + 0xf86], ax
0030B6CD movzx    edx, ax
0030B6D0 mov      rcx, r15
0030B6D3 call     0x140412380
0030B6D8 lea      r14, [rsi + 0xe18]
0030B6DF xor      edx, edx
0030B6E1 mov      rcx, r14
0030B6E4 call     0x140412380
0030B6E9 movzx    edx, word ptr [r15 + 0x11a]
0030B6F1 mov      rcx, r15
0030B6F4 call     0x140411cc0
0030B6F9 movzx    ebx, al
0030B6FC call     0x14050933c
0030B701 mov      edi, eax
0030B703 mov      rcx, r15
0030B706 and      edi, 0x7fff
0030B70C imul     edi, ebx
0030B70F shr      edi, 0xf
0030B712 movzx    edx, di
0030B715 call     0x140411610
0030B71A movzx    edx, di
0030B71D mov      rcx, r14
0030B720 call     0x140411610
0030B725 mov      qword ptr [rsi + 0xcd8], r14
0030B72C jmp      0x14030b3ea
0030B731 and      edi, 0xf0
0030B737 je       0x14030b747
0030B739 cmp      edi, 0x10
0030B73C jne      0x14030b772
0030B73E lea      rdx, [rip + 0x29fc43]
0030B745 jmp      0x14030b74e
0030B747 lea      rdx, [rip + 0x29fc32]
0030B74E lea      rcx, [rbp - 0x38]
0030B752 call     0x1403ff7c0
0030B757 mov      ebx, 1
0030B75C lea      rdx, [rbp - 0x38]
0030B760 mov      r9d, ebx
0030B763 lea      rcx, [rsi + 0xde8]
0030B76A mov      r8d, ebx
0030B76D call     0x14014d080
0030B772 xor      edi, edi
0030B774 xor      edx, edx
0030B776 mov      rcx, r15
0030B779 mov      word ptr [rsi + 0xf86], di
0030B780 call     0x140412380
0030B785 xor      edx, edx
0030B787 mov      rcx, r15
0030B78A call     0x140411610
0030B78F jmp      0x14030b3e3
0030B794 cmp      eax, 0xb00
0030B799 ja       0x14030bbbb
0030B79F je       0x14030bb09
0030B7A5 cmp      eax, 0x800
0030B7AA je       0x14030ba24
0030B7B0 cmp      eax, 0x900
0030B7B5 je       0x14030b96f
0030B7BB cmp      eax, 0xa00
0030B7C0 jne      0x14030b3ea
0030B7C6 mov      eax, edi
0030B7C8 and      eax, 0xf0
0030B7CD je       0x14030b8c9
0030B7D3 cmp      eax, 0x10
0030B7D6 je       0x14030b845
0030B7D8 cmp      eax, 0x20
0030B7DB jne      0x14030b931
0030B7E1 and      edi, 0xf
0030B7E4 sub      edi, 3
0030B7E7 je       0x14030b7f7
0030B7E9 cmp      edi, 1
0030B7EC jne      0x14030b822
0030B7EE lea      rdx, [rip + 0x29fbfb]
0030B7F5 jmp      0x14030b7fe
0030B7F7 lea      rdx, [rip + 0x29fbe2]
0030B7FE lea      rcx, [rbp - 0x38]
0030B802 call     0x1403ff7c0
0030B807 mov      ebx, 1
0030B80C lea      rdx, [rbp - 0x38]
0030B810 mov      r9d, ebx
0030B813 lea      rcx, [rsi + 0xde8]
0030B81A mov      r8d, ebx
0030B81D call     0x14014d080
0030B822 call     0x14050933c
0030B827 and      eax, 0x7fff
0030B82C add      eax, eax
0030B82E cmp      eax, 0x8000
0030B833 jb       0x14030b931
0030B839 mov      byte ptr [rsi + 0xf81], 0
0030B840 jmp      0x14030b931
0030B845 and      edi, 0xf
0030B848 je       0x14030b882
0030B84A sub      edi, 1
0030B84D je       0x14030b879
0030B84F sub      edi, 1
0030B852 je       0x14030b870
0030B854 sub      edi, 1
0030B857 je       0x14030b867
0030B859 cmp      edi, 1
0030B85C jne      0x14030b8ad
0030B85E lea      rdx, [rip + 0x29fb6b]
0030B865 jmp      0x14030b889
0030B867 lea      rdx, [rip + 0x29fb52]
0030B86E jmp      0x14030b889
0030B870 lea      rdx, [rip + 0x29fb39]
0030B877 jmp      0x14030b889
0030B879 lea      rdx, [rip + 0x28dde0]
0030B880 jmp      0x14030b889
0030B882 lea      rdx, [rip + 0x29fad7]
0030B889 lea      rcx, [rbp - 0x38]
0030B88D call     0x1403ff7c0
0030B892 mov      ebx, 1
0030B897 lea      rdx, [rbp - 0x38]
0030B89B mov      r9d, ebx
0030B89E lea      rcx, [rsi + 0xde8]
0030B8A5 mov      r8d, ebx
0030B8A8 call     0x14014d080
0030B8AD call     0x14050933c
0030B8B2 and      eax, 0x7fff
0030B8B7 add      eax, eax
0030B8B9 cmp      eax, 0x8000
0030B8BE jb       0x14030b931
0030B8C0 mov      byte ptr [rsi + 0xf81], 0
0030B8C7 jmp      0x14030b931
0030B8C9 and      edi, 0xf
0030B8CC je       0x14030b906
0030B8CE sub      edi, 1
0030B8D1 je       0x14030b8fd
0030B8D3 sub      edi, 1
0030B8D6 je       0x14030b8f4
0030B8D8 sub      edi, 1
0030B8DB je       0x14030b8eb
0030B8DD cmp      edi, 1
0030B8E0 jne      0x14030b931
0030B8E2 lea      rdx, [rip + 0x29fae7]
0030B8E9 jmp      0x14030b90d
0030B8EB lea      rdx, [rip + 0x29face]
0030B8F2 jmp      0x14030b90d
0030B8F4 lea      rdx, [rip + 0x29fab5]
0030B8FB jmp      0x14030b90d
0030B8FD lea      rdx, [rip + 0x28dd5c]
0030B904 jmp      0x14030b90d
0030B906 lea      rdx, [rip + 0x29fa53]
0030B90D lea      rcx, [rbp - 0x38]
0030B911 call     0x1403ff7c0
0030B916 mov      ebx, 1
0030B91B lea      rdx, [rbp - 0x38]
0030B91F mov      r9d, ebx
0030B922 lea      rcx, [rsi + 0xde8]
0030B929 mov      r8d, ebx
0030B92C call     0x14014d080
0030B931 mov      rcx, r15
0030B934 call     0x140411af0
0030B939 movzx    ebx, ax
0030B93C call     0x14050933c
0030B941 and      eax, 0x7fff
0030B946 mov      rcx, r15
0030B949 imul     eax, ebx
0030B94C shr      eax, 0xf
0030B94F movzx    edx, ax
0030B952 mov      word ptr [rsi + 0xf86], ax
0030B959 call     0x140412380
0030B95E xor      edx, edx
0030B960 mov      rcx, r15
0030B963 call     0x140411610
0030B968 xor      edi, edi
0030B96A jmp      0x14030b3e3
0030B96F and      edi, 0xf0
0030B975 je       0x14030b996
0030B977 cmp      edi, 0x10
0030B97A jne      0x14030b3da
0030B980 test     r13b, 0xf
0030B984 jne      0x14030b308
0030B98A lea      rdx, [rip + 0x29fa0f]
0030B991 jmp      0x14030b2e4
0030B996 mov      ebx, 1
0030B99B test     r13b, 0xf
0030B99F jne      0x14030b9c7
0030B9A1 lea      rdx, [rip + 0x29f9a8]
0030B9A8 lea      rcx, [rbp - 0x38]
0030B9AC call     0x1403ff7c0
0030B9B1 lea      rcx, [rsi + 0xde8]
0030B9B8 mov      r9d, ebx
0030B9BB mov      r8d, ebx
0030B9BE lea      rdx, [rbp - 0x38]
0030B9C2 call     0x14014d080
0030B9C7 mov      edx, ebx
0030B9C9 mov      word ptr [rsi + 0xf86], bx
0030B9D0 mov      rcx, r15
0030B9D3 call     0x140412380
0030B9D8 xor      edx, edx
0030B9DA mov      rcx, r15
0030B9DD call     0x140411610
0030B9E2 xor      bl, bl
0030B9E4 nop      dword ptr [rax]
0030B9E8 nop      dword ptr [rax + rax]
0030B9F0 mov      rax, qword ptr [rip + 0x35bb51]
0030B9F7 mov      rcx, r12
0030B9FA movzx    r8d, byte ptr [r14]
0030B9FE movzx    edx, bl
0030BA01 mov      r9, qword ptr [rax + 0x1090]
0030BA08 add      r9, 0x63d8
0030BA0F call     0x1404221c0
0030BA14 inc      bl
0030BA16 lea      r14, [r14 + 1]
0030BA1A cmp      bl, 7
0030BA1D jb       0x14030b9f0
0030BA1F jmp      0x14030b3cf
0030BA24 and      edi, 0xf0
0030BA2A je       0x14030ba79
0030BA2C cmp      edi, 0x10
0030BA2F jne      0x14030baa4
0030BA31 lea      rdx, [rip + 0x29f960]
0030BA38 lea      rcx, [rbp - 0x38]
0030BA3C call     0x1403ff7c0
0030BA41 mov      ebx, 1
0030BA46 lea      rcx, [rsi + 0xde8]
0030BA4D mov      r9d, ebx
0030BA50 lea      rdx, [rbp - 0x38]
0030BA54 mov      r8d, ebx
0030BA57 call     0x14014d080
0030BA5C call     0x14050933c
0030BA61 and      eax, 0x7fff
0030BA66 lea      eax, [rax + rax*2]
0030BA69 cmp      eax, 0x8000
0030BA6E jae      0x14030baa4
0030BA70 mov      byte ptr [rsi + 0xf81], 0
0030BA77 jmp      0x14030baa4
0030BA79 lea      rdx, [rip + 0x29f910]
0030BA80 lea      rcx, [rbp - 0x38]
0030BA84 call     0x1403ff7c0
0030BA89 mov      ebx, 1
0030BA8E lea      rcx, [rsi + 0xde8]
0030BA95 mov      r9d, ebx
0030BA98 lea      rdx, [rbp - 0x38]
0030BA9C mov      r8d, ebx
0030BA9F call     0x14014d080
0030BAA4 xor      edi, edi
0030BAA6 xor      edx, edx
0030BAA8 mov      rcx, r15
0030BAAB mov      word ptr [rsi + 0xf86], di
0030BAB2 call     0x140412380
0030BAB7 xor      bl, bl
0030BAB9 nop      dword ptr [rax]
0030BAC0 mov      rax, qword ptr [rip + 0x35ba81]
0030BAC7 mov      rcx, r12
0030BACA movzx    r8d, byte ptr [r14]
0030BACE movzx    edx, bl
0030BAD1 mov      r9, qword ptr [rax + 0x1090]
0030BAD8 add      r9, 0x63d8
0030BADF call     0x1404221c0
0030BAE4 inc      bl
0030BAE6 lea      r14, [r14 + 1]
0030BAEA cmp      bl, 7
0030BAED jb       0x14030bac0
0030BAEF mov      rdx, r12
0030BAF2 mov      rcx, r15
0030BAF5 call     0x140412390
0030BAFA xor      edx, edx
0030BAFC mov      rcx, r15
0030BAFF call     0x140411610
0030BB04 jmp      0x14030b3e3
0030BB09 and      edi, 0xf
0030BB0C je       0x14030bb4a
0030BB0E sub      edi, 1
0030BB11 je       0x14030bb41
0030BB13 sub      edi, 1
0030BB16 je       0x14030bb38
0030BB18 sub      edi, 1
0030BB1B je       0x14030bb2f
0030BB1D cmp      edi, 1
0030BB20 jne      0x14030b3da
0030BB26 lea      rdx, [rip + 0x29f913]
0030BB2D jmp      0x14030bb51
0030BB2F lea      rdx, [rip + 0x29f8fa]
0030BB36 jmp      0x14030bb51
0030BB38 lea      rdx, [rip + 0x29f8e1]
0030BB3F jmp      0x14030bb51
0030BB41 lea      rdx, [rip + 0x29f8c8]
0030BB48 jmp      0x14030bb51
0030BB4A lea      rdx, [rip + 0x29f8af]
0030BB51 lea      rcx, [rbp - 0x38]
0030BB55 call     0x1403ff7c0
0030BB5A mov      ebx, 1
0030BB5F lea      rcx, [rsi + 0xde8]
0030BB66 mov      r9d, ebx
0030BB69 lea      rdx, [rbp - 0x38]
0030BB6D mov      r8d, ebx
0030BB70 call     0x14014d080
0030BB75 xor      edi, edi
0030BB77 xor      edx, edx
0030BB79 mov      rcx, r15
0030BB7C mov      word ptr [rsi + 0xf86], di
0030BB83 call     0x140412380
0030BB88 movzx    edx, word ptr [r15 + 0x11a]
0030BB90 mov      rcx, r15
0030BB93 call     0x140411cc0
0030BB98 movzx    ebx, al
0030BB9B call     0x14050933c
0030BBA0 mov      edx, eax
0030BBA2 mov      rcx, r15
0030BBA5 and      edx, 0x7fff
0030BBAB imul     edx, ebx
0030BBAE shr      edx, 0xf
0030BBB1 call     0x140411610
0030BBB6 jmp      0x14030b3dc
0030BBBB cmp      eax, 0xc00
0030BBC0 je       0x14030bc35
0030BBC2 cmp      eax, 0xf00
0030BBC7 jne      0x14030b3ea
0030BBCD lea      rdx, [rip + 0x29f89c]
0030BBD4 lea      rcx, [rbp - 0x38]
0030BBD8 call     0x1403ff7c0
0030BBDD mov      ebx, 1
0030BBE2 lea      rcx, [rsi + 0xde8]
0030BBE9 mov      r9d, ebx
0030BBEC lea      rdx, [rbp - 0x38]
0030BBF0 mov      r8d, ebx
0030BBF3 call     0x14014d080
0030BBF8 xor      edi, edi
0030BBFA xor      edx, edx
0030BBFC mov      rcx, r15
0030BBFF mov      word ptr [rsi + 0xf86], di
0030BC06 call     0x140412380
0030BC0B xor      edx, edx
0030BC0D mov      rcx, r15
0030BC10 call     0x140411610
0030BC15 movzx    ecx, word ptr [rsi + 0xf84]
0030BC1C movzx    eax, cx
0030BC1F shl      ax, 2
0030BC23 add      cx, ax
0030BC26 add      cx, cx
0030BC29 mov      word ptr [rsi + 0xf82], cx
0030BC30 jmp      0x14030b3e3
0030BC35 and      edi, 0xf0
0030BC3B je       0x14030bcd6
0030BC41 cmp      edi, 0x10
0030BC44 jne      0x14030b3da
0030BC4A test     r13b, 0xf
0030BC4E jne      0x14030bc95
0030BC50 call     0x14050933c
0030BC55 and      eax, 0x7fff
0030BC5A lea      rcx, [rbp - 0x38]
0030BC5E add      eax, eax
0030BC60 lea      rdx, [rip + 0x29f7e9]
0030BC67 cmp      eax, 0x8000
0030BC6C jae      0x14030bc75
0030BC6E lea      rdx, [rip + 0x29f7eb]
0030BC75 call     0x1403ff7c0
0030BC7A mov      ebx, 1
0030BC7F lea      rdx, [rbp - 0x38]
0030BC83 mov      r9d, ebx
0030BC86 lea      rcx, [rsi + 0xde8]
0030BC8D mov      r8d, ebx
0030BC90 call     0x14014d080
0030BC95 xor      edi, edi
0030BC97 xor      edx, edx
0030BC99 mov      rcx, r15
0030BC9C mov      word ptr [rsi + 0xf86], di
0030BCA3 call     0x140412380
0030BCA8 xor      edx, edx
0030BCAA mov      rcx, r15
0030BCAD call     0x140411610
0030BCB2 call     0x14050933c
0030BCB7 and      eax, 0x7fff
0030BCBC lea      eax, [rax + rax*2]
0030BCBF cmp      eax, 0x8000
0030BCC4 jb       0x14030b3dc
0030BCCA mov      byte ptr [rsi + 0xf81], dil
0030BCD1 jmp      0x14030b3dc
0030BCD6 test     r13b, 0xf
0030BCDA jne      0x14030bd21
0030BCDC call     0x14050933c
0030BCE1 and      eax, 0x7fff
0030BCE6 lea      rcx, [rbp - 0x38]
0030BCEA add      eax, eax
0030BCEC lea      rdx, [rip + 0x29f75d]
0030BCF3 cmp      eax, 0x8000
0030BCF8 jae      0x14030bd01
0030BCFA lea      rdx, [rip + 0x29f75f]
0030BD01 call     0x1403ff7c0
0030BD06 mov      ebx, 1
0030BD0B lea      rdx, [rbp - 0x38]
0030BD0F mov      r9d, ebx
0030BD12 lea      rcx, [rsi + 0xde8]
0030BD19 mov      r8d, ebx
0030BD1C call     0x14014d080
0030BD21 xor      edi, edi
0030BD23 xor      edx, edx
0030BD25 mov      rcx, r15
0030BD28 mov      word ptr [rsi + 0xf86], di
0030BD2F call     0x140412380
0030BD34 xor      edx, edx
0030BD36 mov      rcx, r15
0030BD39 call     0x140411610
0030BD3E jmp      0x14030b3dc
