0042D350  push     rbp
0042D352  push     rbx
0042D353  push     rsi
0042D354  push     rdi
0042D355  push     r12
0042D357  push     r13
0042D359  push     r14
0042D35B  push     r15
0042D35D  lea      rbp, [rsp - 0x17]
0042D362  sub      rsp, 0xb8
0042D369  mov      rax, qword ptr [rip + 0x237668]
0042D370  xor      rax, rsp
0042D373  mov      qword ptr [rbp + 7], rax
0042D377  mov      eax, 1
0042D37C  mov      qword ptr [rbp - 0x31], rdx
0042D380  mov      dword ptr [rbp - 0x59], eax
0042D383  xor      r15d, r15d
0042D386  mov      rax, qword ptr [rip + 0x23a1d3]
0042D38D  mov      r14, rdx
0042D390  mov      dword ptr [rbp - 0x61], r15d
0042D394  mov      edx, r8d
0042D397  mov      dword ptr [rbp - 0x5d], r15d
0042D39B  mov      rbx, r9
0042D39E  mov      dword ptr [rbp - 0x55], r8d
0042D3A2  mov      r12, rcx
0042D3A5  mov      r13, qword ptr [rax + 0x210]
0042D3AC  call     0x1404212b0
0042D3B1  mov      dword ptr [rbp - 0x6d], eax
0042D3B4  mov      rcx, r12
0042D3B7  movzx    eax, byte ptr [r13 + 0x190]
0042D3BF  movzx    esi, r15w
0042D3C3  mov      byte ptr [rbp - 0x71], al
0042D3C6  movzx    edi, r15w
0042D3CA  movzx    eax, byte ptr [r13 + 0x194]
0042D3D2  mov      byte ptr [rbp - 0x70], al
0042D3D5  movzx    eax, byte ptr [r13 + 0x198]
0042D3DD  mov      byte ptr [rbp - 0x6f], al
0042D3E0  mov      dword ptr [rbp - 0x45], 0xff000000
0042D3E7  call     0x1404220e0
0042D3EC  mov      eax, dword ptr [rbp - 0x55]
0042D3EF  mov      ecx, eax
0042D3F1  mov      edx, dword ptr [rbp + 0x7f]
0042D3F4  and      ecx, 2
0042D3F7  mov      dword ptr [rbp - 0x39], ecx
0042D3FA  je       0x14042d404
0042D3FC  mov      ecx, edx
0042D3FE  shl      ecx, 0x18
0042D401  mov      dword ptr [rbp - 0x45], ecx
0042D404  mov      dword ptr [rsp + 0x28], eax
0042D408  lea      r9, [rbp - 0x61]
0042D40C  lea      rax, [rbp - 0x59]
0042D410  mov      r8, rbx
0042D413  lea      rdx, [rbp - 0x29]
0042D417  mov      qword ptr [rsp + 0x20], rax
0042D41C  mov      rcx, r12
0042D41F  call     0x1404212f0
0042D424  mov      dword ptr [rbp - 0x51], eax
0042D427  test     rbx, rbx
0042D42A  je       0x14042d516
0042D430  mov      r10, qword ptr [rbx + 0x10]
0042D434  test     r10, r10
0042D437  je       0x14042d516
0042D43D  movzx    r8d, byte ptr [rbx + 0x48]
0042D442  cmp      r8b, 1
0042D446  je       0x14042d4db
0042D44C  mov      rax, qword ptr [r12]
0042D450  xor      edx, edx
0042D452  movzx    r11d, r8b
0042D456  lea      ecx, [r11 + r11]
0042D45A  div      rcx
0042D45D  movzx    eax, r8b
0042D461  cmp      dx, ax
0042D464  jbe      0x14042d46f
0042D466  add      ax, ax
0042D469  sub      ax, dx
0042D46C  movzx    edx, ax
0042D46F  movzx    r9d, byte ptr [rip + 0x193208]
0042D477  movzx    ecx, byte ptr [r10]
0042D47B  mov      eax, r9d
0042D47E  sub      eax, ecx
0042D480  movzx    r8d, dx
0042D484  imul     eax, r8d
0042D488  mov      ecx, r9d
0042D48B  cdq      
0042D48C  idiv     r11d
0042D48F  sub      ecx, eax
0042D491  mov      eax, dword ptr [rbp - 0x29]
0042D494  imul     eax, ecx
0042D497  mov      dword ptr [rbp - 0x29], eax
0042D49A  mov      eax, r9d
0042D49D  movzx    ecx, byte ptr [r10 + 1]
0042D4A2  sub      eax, ecx
0042D4A4  mov      ecx, r9d
0042D4A7  imul     eax, r8d
0042D4AB  cdq      
0042D4AC  idiv     r11d
0042D4AF  sub      ecx, eax
0042D4B1  mov      eax, dword ptr [rbp - 0x25]
0042D4B4  imul     eax, ecx
0042D4B7  mov      dword ptr [rbp - 0x25], eax
0042D4BA  mov      eax, r9d
0042D4BD  movzx    ecx, byte ptr [r10 + 2]
0042D4C2  sub      eax, ecx
0042D4C4  imul     eax, r8d
0042D4C8  cdq      
0042D4C9  idiv     r11d
0042D4CC  sub      r9d, eax
0042D4CF  mov      eax, dword ptr [rbp - 0x21]
0042D4D2  imul     eax, r9d
0042D4D6  mov      dword ptr [rbp - 0x21], eax
0042D4D9  jmp      0x14042d504
0042D4DB  movzx    eax, byte ptr [r10]
0042D4DF  mov      ecx, dword ptr [rbp - 0x29]
0042D4E2  imul     ecx, eax
0042D4E5  mov      dword ptr [rbp - 0x29], ecx
0042D4E8  movzx    eax, byte ptr [r10 + 1]
0042D4ED  mov      ecx, dword ptr [rbp - 0x25]
0042D4F0  imul     ecx, eax
0042D4F3  mov      dword ptr [rbp - 0x25], ecx
0042D4F6  movzx    eax, byte ptr [r10 + 2]
0042D4FB  mov      ecx, dword ptr [rbp - 0x21]
0042D4FE  imul     ecx, eax
0042D501  mov      dword ptr [rbp - 0x21], ecx
0042D504  add      dword ptr [rbp - 0x61], 8
0042D508  imul     eax, dword ptr [rbp - 0x59], 0xff
0042D50F  mov      byte ptr [rbp - 0x51], 1
0042D513  mov      dword ptr [rbp - 0x59], eax
0042D516  mov      eax, dword ptr [rbp - 0x55]
0042D519  lea      r9, [rbp - 0x5d]
0042D51D  mov      r8, rbx
0042D520  mov      dword ptr [rsp + 0x20], eax
0042D524  lea      rdx, [rbp - 0x19]
0042D528  mov      rcx, r12
0042D52B  call     0x140421120
0042D530  mov      dword ptr [rbp - 0x4d], eax
0042D533  test     rbx, rbx
0042D536  je       0x14042d609
0042D53C  mov      r9, qword ptr [rbx + 0x50]
0042D540  test     r9, r9
0042D543  je       0x14042d609
0042D549  movzx    r8d, byte ptr [rbx + 0x88]
0042D551  cmp      r8b, 2
0042D555  jb       0x14042d5c5
0042D557  mov      rax, qword ptr [r12]
0042D55B  xor      edx, edx
0042D55D  movzx    r10d, r8b
0042D561  lea      ecx, [r10 + r10]
0042D565  div      rcx
0042D568  movzx    eax, r8b
0042D56C  mov      rsi, rdx
0042D56F  cmp      dx, ax
0042D572  jbe      0x14042d57a
0042D574  lea      esi, [rax + rax]
0042D577  sub      si, dx
0042D57A  movzx    eax, byte ptr [r9]
0042D57E  xor      edx, edx
0042D580  movzx    r8d, si
0042D584  imul     eax, r8d
0042D588  div      r10d
0042D58B  xor      edx, edx
0042D58D  not      al
0042D58F  movzx    ecx, al
0042D592  mov      eax, dword ptr [rbp - 0x19]
0042D595  imul     eax, ecx
0042D598  mov      dword ptr [rbp - 0x19], eax
0042D59B  movzx    eax, byte ptr [r9 + 1]
0042D5A0  imul     eax, r8d
0042D5A4  div      r10d
0042D5A7  xor      edx, edx
0042D5A9  not      al
0042D5AB  movzx    ecx, al
0042D5AE  mov      eax, dword ptr [rbp - 0x15]
0042D5B1  imul     eax, ecx
0042D5B4  mov      dword ptr [rbp - 0x15], eax
0042D5B7  movzx    eax, byte ptr [r9 + 2]
0042D5BC  imul     eax, r8d
0042D5C0  div      r10d
0042D5C3  jmp      0x14042d5f3
0042D5C5  movzx    eax, byte ptr [r9]
0042D5C9  not      al
0042D5CB  movzx    esi, r8b
0042D5CF  movzx    ecx, al
0042D5D2  mov      eax, dword ptr [rbp - 0x19]
0042D5D5  imul     eax, ecx
0042D5D8  mov      dword ptr [rbp - 0x19], eax
0042D5DB  movzx    eax, byte ptr [r9 + 1]
0042D5E0  not      al
0042D5E2  movzx    ecx, al
0042D5E5  mov      eax, dword ptr [rbp - 0x15]
0042D5E8  imul     eax, ecx
0042D5EB  mov      dword ptr [rbp - 0x15], eax
0042D5EE  movzx    eax, byte ptr [r9 + 2]
0042D5F3  not      al
0042D5F5  mov      byte ptr [rbp - 0x4d], 1
0042D5F9  movzx    ecx, al
0042D5FC  mov      eax, dword ptr [rbp - 0x11]
0042D5FF  imul     eax, ecx
0042D602  add      dword ptr [rbp - 0x5d], 8
0042D606  mov      dword ptr [rbp - 0x11], eax
0042D609  mov      r9d, dword ptr [rbp - 0x55]
0042D60D  lea      rdx, [rbp - 9]
0042D611  mov      r8, rbx
0042D614  mov      rcx, r12
0042D617  call     0x140421200
0042D61C  mov      dword ptr [rbp - 0x49], eax
0042D61F  test     rbx, rbx
0042D622  je       0x14042d754
0042D628  mov      r9, qword ptr [rbx + 0x90]
0042D62F  test     r9, r9
0042D632  je       0x14042d6bd
0042D638  movzx    r8d, byte ptr [rbx + 0xc8]
0042D640  cmp      r8b, 1
0042D644  je       0x14042d69d
0042D646  mov      rax, qword ptr [r12]
0042D64A  xor      edx, edx
0042D64C  movzx    ecx, r8b
0042D650  add      rcx, rcx
0042D653  div      rcx
0042D656  movzx    eax, r8b
0042D65A  mov      rdi, rdx
0042D65D  cmp      dx, ax
0042D660  jbe      0x14042d668
0042D662  lea      edi, [rax + rax]
0042D665  sub      di, dx
0042D668  movzx    eax, byte ptr [r9]
0042D66C  xor      edx, edx
0042D66E  movzx    ecx, di
0042D671  imul     eax, ecx
0042D674  movzx    r8d, r8b
0042D678  div      r8d
0042D67B  xor      edx, edx
0042D67D  add      dword ptr [rbp - 9], eax
0042D680  movzx    eax, byte ptr [r9 + 1]
0042D685  imul     eax, ecx
0042D688  div      r8d
0042D68B  xor      edx, edx
0042D68D  add      dword ptr [rbp - 5], eax
0042D690  movzx    eax, byte ptr [r9 + 2]
0042D695  imul     eax, ecx
0042D698  div      r8d
0042D69B  jmp      0x14042d6b6
0042D69D  movzx    eax, byte ptr [r9]
0042D6A1  mov      edi, 1
0042D6A6  add      dword ptr [rbp - 9], eax
0042D6A9  movzx    eax, byte ptr [r9 + 1]
0042D6AE  add      dword ptr [rbp - 5], eax
0042D6B1  movzx    eax, byte ptr [r9 + 2]
0042D6B6  add      dword ptr [rbp - 1], eax
0042D6B9  mov      byte ptr [rbp - 0x49], 1
0042D6BD  movzx    eax, byte ptr [rbx + 0xcf]
0042D6C4  test     byte ptr [rip + 0x22faa2], al
0042D6CA  je       0x14042d754
0042D6D0  test     di, di
0042D6D3  jne      0x14042d7ab
0042D6D9  test     si, si
0042D6DC  je       0x14042d754
0042D6DE  movzx    r9d, byte ptr [rbx + 0x88]
0042D6E6  movzx    r8d, si
0042D6EA  mov      ecx, dword ptr [rbp - 0x59]
0042D6ED  mov      eax, ecx
0042D6EF  sub      eax, dword ptr [rbp - 0x29]
0042D6F2  imul     eax, r8d
0042D6F6  cdq      
0042D6F7  idiv     r9d
0042D6FA  add      dword ptr [rbp - 0x29], eax
0042D6FD  mov      eax, ecx
0042D6FF  sub      eax, dword ptr [rbp - 0x25]
0042D702  sub      ecx, dword ptr [rbp - 0x21]
0042D705  imul     eax, r8d
0042D709  imul     ecx, r8d
0042D70D  cdq      
0042D70E  idiv     r9d
0042D711  add      dword ptr [rbp - 0x25], eax
0042D714  mov      eax, ecx
0042D716  cdq      
0042D717  idiv     r9d
0042D71A  add      dword ptr [rbp - 0x21], eax
0042D71D  movzx    eax, byte ptr [rip + 0x22f54a]
0042D724  cmp      byte ptr [r13 + 0x19], al
0042D728  je       0x14042d754
0042D72A  mov      edx, dword ptr [rbp - 0x29]
0042D72D  mov      rcx, r13
0042D730  call     0x14041d270
0042D735  mov      edx, dword ptr [rbp - 0x25]
0042D738  mov      rcx, r13
0042D73B  mov      dword ptr [rbp - 0x29], eax
0042D73E  call     0x14041d270
0042D743  mov      edx, dword ptr [rbp - 0x21]
0042D746  mov      rcx, r13
0042D749  mov      dword ptr [rbp - 0x25], eax
0042D74C  call     0x14041d270
0042D751  mov      dword ptr [rbp - 0x21], eax
0042D754  movsxd   rax, dword ptr [rbp - 0x6d]
0042D758  test     rax, rax
0042D75B  jle      0x14042d810
0042D761  movzx    edi, byte ptr [rbp - 0x6f]
0042D765  mov      rbx, r15
0042D768  movzx    esi, byte ptr [rbp - 0x70]
0042D76C  movzx    r14d, byte ptr [rbp - 0x71]
0042D771  movzx    eax, byte ptr [rip + 0x192f02]
0042D778  cmp      r15d, eax
0042D77B  jne      0x14042d7c5
0042D77D  xor      edx, edx
0042D77F  mov      rcx, r13
0042D782  call     0x14041d130
0042D787  mov      ecx, eax
0042D789  movzx    r8d, ax
0042D78D  shr      ecx, 0x10
0042D790  movzx    edx, cl
0042D793  mov      ecx, edi
0042D795  shl      edx, cl
0042D797  mov      ecx, esi
0042D799  shr      r8d, 8
0042D79D  shl      r8d, cl
0042D7A0  mov      ecx, r14d
0042D7A3  or       edx, r8d
0042D7A6  movzx    eax, al
0042D7A9  jmp      0x14042d7e9
0042D7AB  cmp      di, si
0042D7AE  jbe      0x14042d6de
0042D7B4  movzx    r9d, byte ptr [rbx + 0xc8]
0042D7BC  movzx    r8d, di
0042D7C0  jmp      0x14042d6ea
0042D7C5  mov      rax, qword ptr [r12 + 0x10]
0042D7CA  mov      ecx, r14d
0042D7CD  movzx    edx, byte ptr [rax + rbx*4 + 2]
0042D7D2  lea      r8, [rax + rbx*4]
0042D7D6  movzx    eax, byte ptr [rax + rbx*4 + 1]
0042D7DB  shl      edx, cl
0042D7DD  mov      ecx, esi
0042D7DF  shl      eax, cl
0042D7E1  mov      ecx, edi
0042D7E3  or       edx, eax
0042D7E5  movzx    eax, byte ptr [r8]
0042D7E9  shl      eax, cl
0042D7EB  inc      r15d
0042D7EE  or       edx, eax
0042D7F0  mov      rax, qword ptr [rbp - 0x31]
0042D7F4  or       edx, 0xff000000
0042D7FA  mov      dword ptr [rax + rbx*4], edx
0042D7FD  inc      rbx
0042D800  movsxd   rcx, dword ptr [rbp - 0x6d]
0042D804  cmp      rbx, rcx
0042D807  jl       0x14042d771
0042D80D  mov      r14, rax
0042D810  cmp      r15d, dword ptr [r12 + 0x18]
0042D815  jge      0x14042da59
0042D81B  mov      edx, dword ptr [rbp - 0x55]
0042D81E  mov      ecx, edx
0042D820  mov      r8d, dword ptr [rbp - 0x61]
0042D824  and      ecx, 0x80000
0042D82A  mov      r9d, dword ptr [rbp - 0x5d]
0042D82E  and      edx, 0x2000000
0042D834  movsxd   rax, r15d
0042D837  mov      dword ptr [rbp - 0x41], edx
0042D83A  mov      dword ptr [rbp - 0x3d], ecx
0042D83D  lea      r13, [rax*4]
0042D845  mov      rax, qword ptr [r12 + 0x10]
0042D84A  movzx    ebx, byte ptr [rax + r13 + 3]
0042D850  movzx    esi, byte ptr [rax + r13 + 2]
0042D856  movzx    r14d, byte ptr [rax + r13 + 1]
0042D85C  movzx    edi, byte ptr [rax + r13]
0042D861  mov      byte ptr [rbp - 0x65], bl
0042D864  test     ecx, ecx
0042D866  je       0x14042d883
0042D868  movzx    ecx, dil
0042D86C  movzx    eax, r14b
0042D870  add      ecx, eax
0042D872  movzx    esi, sil
0042D876  add      esi, ecx
0042D878  shr      esi, 2
0042D87B  movzx    r14d, sil
0042D87F  movzx    edi, sil
0042D883  test     edx, edx
0042D885  je       0x14042d8fb
0042D887  movzx    edi, dil
0042D88B  lea      rdx, [rbp - 0x6d]
0042D88F  movzx    eax, r14b
0042D893  lea      rcx, [rbp - 0x69]
0042D897  add      edi, eax
0042D899  mov      dword ptr [rbp - 0x69], 0xff
0042D8A0  movzx    eax, sil
0042D8A4  add      edi, eax
0042D8A6  shr      edi, 2
0042D8A9  movzx    ebx, dil
0042D8AD  lea      eax, [rbx + 0x15]
0042D8B0  mov      dword ptr [rbp - 0x6d], eax
0042D8B3  call     0x140407bc0
0042D8B8  lea      rdx, [rbp - 0x69]
0042D8BC  mov      dword ptr [rbp - 0x69], ebx
0042D8BF  lea      rcx, [rbp - 0x6d]
0042D8C3  mov      dword ptr [rbp - 0x6d], 0xff
0042D8CA  movzx    esi, al
0042D8CD  call     0x140407bc0
0042D8D2  lea      rdx, [rbp - 0x69]
0042D8D6  mov      dword ptr [rbp - 0x69], 0x20
0042D8DD  lea      rcx, [rbp - 0x6d]
0042D8E1  mov      dword ptr [rbp - 0x6d], ebx
0042D8E4  mov      r14d, eax
0042D8E7  call     0x140407bc0
0042D8EC  mov      r8d, dword ptr [rbp - 0x61]
0042D8F0  sub      dil, al
0042D8F3  mov      r9d, dword ptr [rbp - 0x5d]
0042D8F7  movzx    ebx, byte ptr [rbp - 0x65]
0042D8FB  cmp      byte ptr [rbp - 0x51], 0
0042D8FF  je       0x14042d924
0042D901  mov      ecx, r8d
0042D904  movzx    esi, sil
0042D908  imul     esi, dword ptr [rbp - 0x29]
0042D90C  movzx    r14d, r14b
0042D910  imul     r14d, dword ptr [rbp - 0x25]
0042D915  movzx    edi, dil
0042D919  imul     edi, dword ptr [rbp - 0x21]
0042D91D  sar      esi, cl
0042D91F  sar      r14d, cl
0042D922  sar      edi, cl
0042D924  cmp      byte ptr [rbp - 0x4d], 0
0042D928  je       0x14042d95f
0042D92A  not      sil
0042D92D  not      r14b
0042D930  not      dil
0042D933  movzx    esi, sil
0042D937  imul     esi, dword ptr [rbp - 0x19]
0042D93B  mov      ecx, r9d
0042D93E  movzx    r14d, r14b
0042D942  imul     r14d, dword ptr [rbp - 0x15]
0042D947  movzx    edi, dil
0042D94B  imul     edi, dword ptr [rbp - 0x11]
0042D94F  sar      esi, cl
0042D951  not      sil
0042D954  sar      r14d, cl
0042D957  not      r14b
0042D95A  sar      edi, cl
0042D95C  not      dil
0042D95F  cmp      byte ptr [rbp - 0x49], 0
0042D963  je       0x14042d9f3
0042D969  movzx    ecx, byte ptr [rip + 0x192d0e]
0042D970  lea      rdx, [rbp - 0x69]
0042D974  movzx    eax, sil
0042D978  imul     eax, dword ptr [rbp - 9]
0042D97C  mov      dword ptr [rbp - 0x6d], 0xff
0042D983  sar      eax, cl
0042D985  lea      rcx, [rbp - 0x6d]
0042D989  mov      dword ptr [rbp - 0x69], eax
0042D98C  call     0x140407bc0
0042D991  movzx    ecx, byte ptr [rip + 0x192ce6]
0042D998  lea      rdx, [rbp - 0x69]
0042D99C  movzx    esi, al
0042D99F  mov      dword ptr [rbp - 0x6d], 0xff
0042D9A6  movzx    eax, r14b
0042D9AA  imul     eax, dword ptr [rbp - 5]
0042D9AE  sar      eax, cl
0042D9B0  lea      rcx, [rbp - 0x6d]
0042D9B4  mov      dword ptr [rbp - 0x69], eax
0042D9B7  call     0x140407bc0
0042D9BC  movzx    ecx, byte ptr [rip + 0x192cbb]
0042D9C3  lea      rdx, [rbp - 0x69]
0042D9C7  movzx    r14d, al
0042D9CB  mov      dword ptr [rbp - 0x6d], 0xff
0042D9D2  movzx    eax, dil
0042D9D6  imul     eax, dword ptr [rbp - 1]
0042D9DA  sar      eax, cl
0042D9DC  lea      rcx, [rbp - 0x6d]
0042D9E0  mov      dword ptr [rbp - 0x69], eax
0042D9E3  call     0x140407bc0
0042D9E8  mov      r8d, dword ptr [rbp - 0x61]
0042D9EC  movzx    edi, al
0042D9EF  mov      r9d, dword ptr [rbp - 0x5d]
0042D9F3  movzx    ecx, byte ptr [rbp - 0x71]
0042D9F7  lea      eax, [rbx - 1]
0042D9FA  movzx    edx, sil
0042D9FE  shl      edx, cl
0042DA00  movzx    ecx, byte ptr [rbp - 0x70]
0042DA04  cmp      al, 0xfd
0042DA06  movzx    eax, r14b
0042DA0A  ja       0x14042da26
0042DA0C  shl      eax, cl
0042DA0E  movzx    ecx, byte ptr [rbp - 0x6f]
0042DA12  or       edx, eax
0042DA14  movzx    eax, dil
0042DA18  shl      eax, cl
0042DA1A  or       edx, eax
0042DA1C  movzx    eax, bl
0042DA1F  shl      eax, 0x18
0042DA22  or       edx, eax
0042DA24  jmp      0x14042da39
0042DA26  shl      eax, cl
0042DA28  movzx    ecx, byte ptr [rbp - 0x6f]
0042DA2C  or       edx, eax
0042DA2E  movzx    eax, dil
0042DA32  shl      eax, cl
0042DA34  or       edx, eax
0042DA36  or       edx, dword ptr [rbp - 0x45]
0042DA39  mov      r14, qword ptr [rbp - 0x31]
0042DA3D  inc      r15d
0042DA40  mov      ecx, dword ptr [rbp - 0x3d]
0042DA43  mov      dword ptr [r14 + r13], edx
0042DA47  add      r13, 4
0042DA4B  mov      edx, dword ptr [rbp - 0x41]
0042DA4E  cmp      r15d, dword ptr [r12 + 0x18]
0042DA53  jl       0x14042d845
0042DA59  mov      r8d, dword ptr [rbp - 0x55]
0042DA5D  test     r8b, 1
0042DA61  je       0x14042da88
0042DA63  movzx    eax, byte ptr [rip + 0x192c11]
0042DA6A  lea      rdx, [rax*4]
0042DA72  mov      rax, qword ptr [r12 + 0x10]
0042DA77  mov      ecx, dword ptr [rdx + rax]
0042DA7A  cmp      ecx, dword ptr [rip + 0x192bf0]
0042DA80  jne      0x14042da88
0042DA82  mov      byte ptr [rdx + r14 + 3], 0
0042DA88  test     r8b, 4
0042DA8C  je       0x14042dae6
0042DA8E  cmp      dword ptr [rbp - 0x39], 0
0042DA92  movzx    eax, byte ptr [rip + 0x192be1]
0042DA99  je       0x14042dac6
0042DA9B  movzx    ecx, byte ptr [rip + 0x191cee]
0042DAA2  lea      r8, [r14 + rax*4]
0042DAA6  imul     ecx, dword ptr [rbp + 0x7f]
0042DAAA  mov      eax, 0x80808081
0042DAAF  mul      ecx
0042DAB1  mov      eax, dword ptr [r8]
0042DAB4  shr      edx, 7
0042DAB7  and      eax, 0xffffff
0042DABC  shl      edx, 0x18
0042DABF  or       edx, eax
0042DAC1  mov      dword ptr [r8], edx
0042DAC4  jmp      0x14042dae6
0042DAC6  lea      rcx, [r14 + rax*4]
0042DACA  mov      edx, 0xff000000
0042DACF  movzx    eax, byte ptr [rip + 0x191cba]
0042DAD6  shl      eax, 0x18
0042DAD9  sub      edx, eax
0042DADB  mov      eax, dword ptr [rcx]
0042DADD  and      eax, 0xffffff
0042DAE2  or       edx, eax
0042DAE4  mov      dword ptr [rcx], edx
0042DAE6  mov      rcx, qword ptr [rbp + 7]
0042DAEA  xor      rcx, rsp
0042DAED  call     0x1404f77a0
0042DAF2  add      rsp, 0xb8
0042DAF9  pop      r15
0042DAFB  pop      r14
0042DAFD  pop      r13
0042DAFF  pop      r12
0042DB01  pop      rdi
0042DB02  pop      rsi
0042DB03  pop      rbx
0042DB04  pop      rbp
0042DB05  ret      
0042DB06  int3     
0042DB07  int3     
0042DB08  int3     
0042DB09  int3     
0042DB0A  int3     
0042DB0B  int3     
0042DB0C  int3     
0042DB0D  int3     
0042DB0E  int3     
0042DB0F  int3     
0042DB10  sub      rsp, 8
0042DB14  sub      r9d, r8d
0042DB17  mov      eax, r9d
0042DB1A  inc      r9d
0042DB1D  test     eax, eax
0042DB1F  js       0x14042db3e
0042DB21  movsxd   rax, r8d
0042DB24  mov      qword ptr [rsp], rdi
0042DB28  lea      rdi, [rdx + rax*4]
0042DB2C  test     r9d, r9d
0042DB2F  jle      0x14042db3a
0042DB31  mov      eax, dword ptr [rsp + 0x30]
0042DB35  movsxd   rcx, r9d
0042DB38  rep stosd dword ptr [rdi], eax
0042DB3A  mov      rdi, qword ptr [rsp]
0042DB3E  add      rsp, 8
0042DB42  ret      
0042DB43  int3     
0042DB44  int3     
0042DB45  int3     
0042DB46  int3     
0042DB47  int3     
0042DB48  int3     
0042DB49  int3     
0042DB4A  int3     
0042DB4B  int3     
0042DB4C  int3     
0042DB4D  int3     
0042DB4E  int3     
0042DB4F  int3     
0042DB50  sub      r9d, r8d
0042DB53  mov      eax, r9d
0042DB56  inc      r9d
0042DB59  test     eax, eax
0042DB5B  js       0x14042dc81
0042DB61  movsxd   rax, r8d
0042DB64  lea      rax, [rdx + rax*4]
0042DB68  xor      edx, edx
0042DB6A  test     r9d, r9d
0042DB6D  jle      0x14042dc81
0042DB73  cmp      r9d, 0x10
0042DB77  jb       0x14042dc46
0042DB7D  mov      ecx, r9d
0042DB80  and      ecx, 0x8000000f
0042DB86  jge      0x14042db8f
0042DB88  dec      ecx
0042DB8A  or       ecx, 0xfffffff0
0042DB8D  inc      ecx
0042DB8F  movdqa   xmm4, xmmword ptr [rip + 0x193aa9]
0042DB97  mov      r8d, r9d
0042DB9A  movdqa   xmm5, xmmword ptr [rip + 0x193a7e]
0042DBA2  sub      r8d, ecx
0042DBA5  mov      ecx, 1
0042DBAA  movd     xmm3, ecx
0042DBAE  nop      
0042DBB0  movdqu   xmm1, xmmword ptr [rax]
0042DBB4  add      edx, 0x10
0042DBB7  movdqa   xmm0, xmm5
0042DBBB  pand     xmm0, xmm1
0042DBBF  movdqa   xmm2, xmm1
0042DBC3  psrld    xmm2, xmm3
0042DBC7  pand     xmm2, xmm4
0042DBCB  por      xmm2, xmm0
0042DBCF  movdqa   xmm0, xmm5
0042DBD3  movdqu   xmmword ptr [rax], xmm2
0042DBD7  movdqu   xmm1, xmmword ptr [rax + 0x10]
0042DBDC  pand     xmm0, xmm1
0042DBE0  movdqa   xmm2, xmm1
0042DBE4  psrld    xmm2, xmm3
0042DBE8  pand     xmm2, xmm4
0042DBEC  por      xmm2, xmm0
0042DBF0  movdqa   xmm0, xmm5
0042DBF4  movdqu   xmmword ptr [rax + 0x10], xmm2
0042DBF9  movdqu   xmm1, xmmword ptr [rax + 0x20]
0042DBFE  pand     xmm0, xmm1
0042DC02  movdqa   xmm2, xmm1
0042DC06  psrld    xmm2, xmm3
0042DC0A  pand     xmm2, xmm4
0042DC0E  por      xmm2, xmm0
0042DC12  movdqa   xmm0, xmm5
0042DC16  movdqu   xmmword ptr [rax + 0x20], xmm2
0042DC1B  movdqu   xmm1, xmmword ptr [rax + 0x30]
0042DC20  movdqa   xmm2, xmm1
0042DC24  pand     xmm0, xmm1
0042DC28  psrld    xmm2, xmm3
0042DC2C  pand     xmm2, xmm4
0042DC30  por      xmm2, xmm0
0042DC34  movdqu   xmmword ptr [rax + 0x30], xmm2
0042DC39  add      rax, 0x40
0042DC3D  cmp      edx, r8d
0042DC40  jl       0x14042dbb0
0042DC46  cmp      edx, r9d
0042DC49  jge      0x14042dc81
0042DC4B  sub      r9d, edx
0042DC4E  mov      r8d, r9d
0042DC51  nop      dword ptr [rax]
0042DC55  nop      word ptr [rax + rax]
0042DC60  mov      ecx, dword ptr [rax]
0042DC62  lea      rax, [rax + 4]
0042DC66  mov      edx, ecx
0042DC68  and      ecx, 0xffffff
0042DC6E  shr      edx, 1
0042DC70  and      edx, 0x7f000000
0042DC76  or       edx, ecx
0042DC78  mov      dword ptr [rax - 4], edx
0042DC7B  sub      r8, 1
0042DC7F  jne      0x14042dc60
0042DC81  ret      
0042DC82  int3     
0042DC83  int3     
0042DC84  int3     
0042DC85  int3     
0042DC86  int3     
0042DC87  int3     
0042DC88  int3     
0042DC89  int3     
0042DC8A  int3     
0042DC8B  int3     
0042DC8C  int3     
0042DC8D  int3     
0042DC8E  int3     
0042DC8F  int3     
0042DC90  sub      r9d, r8d
0042DC93  mov      r10, rdx
0042DC96  mov      eax, r9d
0042DC99  inc      r9d
0042DC9C  test     eax, eax
0042DC9E  js       0x14042dce2
0042DCA0  mov      rax, qword ptr [rsp + 0x30]
0042DCA5  mov      ecx, dword ptr [rax + 8]
0042DCA8  sub      ecx, dword ptr [rax]
0042DCAA  movsxd   rax, r8d
0042DCAD  movsxd   rdx, ecx
0042DCB0  sub      rdx, rax
0042DCB3  lea      r8, [r10 + rdx*4]
0042DCB7  test     r9d, r9d
0042DCBA  jle      0x14042dce2
0042DCBC  mov      edx, r9d
0042DCBF  nop      
0042DCC0  mov      eax, dword ptr [r8]
0042DCC3  lea      r8, [r8 - 4]
0042DCC7  mov      ecx, eax
0042DCC9  and      eax, 0xffffff
0042DCCE  shr      ecx, 1
0042DCD0  and      ecx, 0x7f000000
0042DCD6  or       ecx, eax
0042DCD8  mov      dword ptr [r8 + 4], ecx
0042DCDC  sub      rdx, 1
0042DCE0  jne      0x14042dcc0
0042DCE2  ret      
0042DCE3  int3     
0042DCE4  int3     
0042DCE5  int3     
0042DCE6  int3     
0042DCE7  int3     
0042DCE8  int3     
0042DCE9  int3     
0042DCEA  int3     
0042DCEB  int3     
0042DCEC  int3     
0042DCED  int3     
0042DCEE  int3     
0042DCEF  int3     
0042DCF0  sub      r9d, r8d
0042DCF3  mov      r10, rdx
0042DCF6  mov      eax, r9d
0042DCF9  inc      r9d
0042DCFC  test     eax, eax
0042DCFE  js       0x14042dd2f
0042DD00  mov      rax, qword ptr [rsp + 0x30]
0042DD05  mov      ecx, dword ptr [rax + 8]
0042DD08  sub      ecx, dword ptr [rax]
0042DD0A  movsxd   rax, r8d
0042DD0D  movsxd   rdx, ecx
0042DD10  sub      rdx, rax
0042DD13  lea      rax, [r10 + rdx*4]
0042DD17  test     r9d, r9d
0042DD1A  jle      0x14042dd2f
0042DD1C  mov      edx, dword ptr [rsp + 0x28]
0042DD20  mov      ecx, r9d
0042DD23  mov      dword ptr [rax], edx
0042DD25  lea      rax, [rax - 4]
0042DD29  sub      rcx, 1
0042DD2D  jne      0x14042dd23
0042DD2F  ret      
0042DD30  sub      rsp, 8
0042DD34  mov      r10d, dword ptr [rsp + 0x30]
0042DD39  sub      r9d, r8d
0042DD3C  mov      eax, r9d
0042DD3F  inc      r9d
0042DD42  movd     xmm1, r10d
0042DD47  pshufd   xmm1, xmm1, 0
0042DD4C  test     eax, eax
0042DD4E  js       0x14042ddc9
0042DD50  movsxd   rax, r8d
0042DD53  mov      qword ptr [rsp], rdi
0042DD57  lea      rdi, [rdx + rax*4]
0042DD5B  xor      eax, eax
0042DD5D  test     r9d, r9d
0042DD60  jle      0x14042ddc5
0042DD62  cmp      r9d, 0x10
0042DD66  jb       0x14042ddae
0042DD68  mov      ecx, r9d
0042DD6B  and      ecx, 0x8000000f
0042DD71  jge      0x14042dd7a
0042DD73  dec      ecx
0042DD75  or       ecx, 0xfffffff0
0042DD78  inc      ecx
0042DD7A  movdqa   xmm0, xmmword ptr [rip + 0x1938ae]
0042DD82  mov      edx, r9d
0042DD85  sub      edx, ecx
0042DD87  por      xmm0, xmm1
0042DD8B  nop      dword ptr [rax + rax]
0042DD90  movdqu   xmmword ptr [rdi], xmm0
0042DD94  add      eax, 0x10
0042DD97  movdqu   xmmword ptr [rdi + 0x10], xmm0
0042DD9C  movdqu   xmmword ptr [rdi + 0x20], xmm0
0042DDA1  movdqu   xmmword ptr [rdi + 0x30], xmm0
0042DDA6  add      rdi, 0x40
0042DDAA  cmp      eax, edx
0042DDAC  jl       0x14042dd90
0042DDAE  cmp      eax, r9d
0042DDB1  jge      0x14042ddc5
0042DDB3  sub      r9d, eax
0042DDB6  or       r10d, 0x4f000000
0042DDBD  mov      ecx, r9d
0042DDC0  mov      eax, r10d
0042DDC3  rep stosd dword ptr [rdi], eax
0042DDC5  mov      rdi, qword ptr [rsp]
0042DDC9  add      rsp, 8
0042DDCD  ret      
0042DDCE  int3     
0042DDCF  int3     
0042DDD0  sub      r9d, r8d
0042DDD3  mov      r10, rdx
0042DDD6  mov      eax, r9d
0042DDD9  inc      r9d
0042DDDC  test     eax, eax
0042DDDE  js       0x14042de1c
0042DDE0  mov      rax, qword ptr [rsp + 0x30]
0042DDE5  mov      ecx, dword ptr [rax + 8]
0042DDE8  sub      ecx, dword ptr [rax]
0042DDEA  movsxd   rax, r8d
0042DDED  movsxd   rdx, ecx
0042DDF0  sub      rdx, rax
0042DDF3  lea      rax, [r10 + rdx*4]
0042DDF7  test     r9d, r9d
0042DDFA  jle      0x14042de1c
0042DDFC  mov      edx, dword ptr [rsp + 0x28]
0042DE00  or       edx, 0x4f000000
0042DE06  mov      ecx, r9d
0042DE09  nop      dword ptr [rax]
0042DE10  mov      dword ptr [rax], edx
0042DE12  lea      rax, [rax - 4]
0042DE16  sub      rcx, 1
0042DE1A  jne      0x14042de10
0042DE1C  ret      
0042DE1D  int3     
0042DE1E  int3     
0042DE1F  int3     
0042DE20  mov      qword ptr [rsp + 0x10], rbx
0042DE25  mov      qword ptr [rsp + 0x18], rdi
0042DE2A  push     rbp
0042DE2B  mov      rbp, rsp
0042DE2E  sub      rsp, 0x30
0042DE32  mov      rbx, r9
0042DE35  sub      ecx, 1
0042DE38  je       0x14042df57
0042DE3E  sub      ecx, 2
0042DE41  je       0x14042ded7
0042DE47  cmp      ecx, 2
0042DE4A  je       0x14042de5e
0042DE4C  xor      eax, eax
0042DE4E  mov      rbx, qword ptr [rsp + 0x48]
0042DE53  mov      rdi, qword ptr [rsp + 0x50]
0042DE58  add      rsp, 0x30
0042DE5C  pop      rbp
0042DE5D  ret      
0042DE5E  mov      eax, edx
0042DE60  mov      dword ptr [rbp - 8], 1
0042DE67  cdq      
0042DE68  mov      dword ptr [rbp - 0x10], 1
0042DE6F  and      edx, 3
0042DE72  lea      rcx, [rbp - 0x10]
0042DE76  add      eax, edx
0042DE78  sar      eax, 2
0042DE7B  mov      dword ptr [rbp - 0xc], eax
0042DE7E  mov      eax, r8d
0042DE81  cdq      
0042DE82  and      edx, 3
0042DE85  add      eax, edx
0042DE87  lea      rdx, [rbp + 0x10]
0042DE8B  sar      eax, 2
0042DE8E  mov      dword ptr [rbp + 0x10], eax
0042DE91  call     0x140407bb0
0042DE96  lea      rdx, [rbp - 0xc]
0042DE9A  mov      edi, eax
0042DE9C  lea      rcx, [rbp - 8]
0042DEA0  call     0x140407bb0
0042DEA5  imul     edi, eax
0042DEA8  test     edi, edi
0042DEAA  jle      0x14042dec2
0042DEAC  add      rbx, 8
0042DEB0  mov      rcx, rbx
0042DEB3  call     0x14042ec20
0042DEB8  add      rbx, 0x10
0042DEBC  sub      rdi, 1
0042DEC0  jne      0x14042deb0
0042DEC2  mov      eax, 0x87ee
0042DEC7  mov      rbx, qword ptr [rsp + 0x48]
0042DECC  mov      rdi, qword ptr [rsp + 0x50]
0042DED1  add      rsp, 0x30
0042DED5  pop      rbp
0042DED6  ret      
0042DED7  mov      eax, edx
0042DED9  mov      dword ptr [rbp - 0x10], 1
0042DEE0  cdq      
0042DEE1  mov      dword ptr [rbp - 8], 1
0042DEE8  and      edx, 3
0042DEEB  lea      rcx, [rbp - 8]
0042DEEF  add      eax, edx
0042DEF1  sar      eax, 2
0042DEF4  mov      dword ptr [rbp - 0xc], eax
0042DEF7  mov      eax, r8d
0042DEFA  cdq      
0042DEFB  and      edx, 3
0042DEFE  add      eax, edx
0042DF00  lea      rdx, [rbp + 0x10]
0042DF04  sar      eax, 2
0042DF07  mov      dword ptr [rbp + 0x10], eax
0042DF0A  call     0x140407bb0
0042DF0F  lea      rdx, [rbp - 0xc]
0042DF13  mov      edi, eax
0042DF15  lea      rcx, [rbp - 0x10]
0042DF19  call     0x140407bb0
0042DF1E  imul     edi, eax
0042DF21  test     edi, edi
0042DF23  jle      0x14042df42
0042DF25  add      rbx, 8
0042DF29  nop      dword ptr [rax]
0042DF30  mov      rcx, rbx
0042DF33  call     0x14042ec20
0042DF38  add      rbx, 0x10
0042DF3C  sub      rdi, 1
0042DF40  jne      0x14042df30
0042DF42  mov      eax, 0x8c93
0042DF47  mov      rbx, qword ptr [rsp + 0x48]
0042DF4C  mov      rdi, qword ptr [rsp + 0x50]
0042DF51  add      rsp, 0x30
0042DF55  pop      rbp
0042DF56  ret      
0042DF57  mov      eax, edx
0042DF59  mov      dword ptr [rbp - 0x10], 1
0042DF60  cdq      
0042DF61  mov      dword ptr [rbp - 8], 1
0042DF68  and      edx, 3
0042DF6B  lea      rcx, [rbp - 8]
0042DF6F  add      eax, edx
0042DF71  sar      eax, 2
0042DF74  mov      dword ptr [rbp - 0xc], eax
0042DF77  mov      eax, r8d
0042DF7A  cdq      
0042DF7B  and      edx, 3
0042DF7E  add      eax, edx
0042DF80  lea      rdx, [rbp + 0x10]
0042DF84  sar      eax, 2
0042DF87  mov      dword ptr [rbp + 0x10], eax
0042DF8A  call     0x140407bb0
0042DF8F  lea      rdx, [rbp - 0xc]
0042DF93  mov      edi, eax
0042DF95  lea      rcx, [rbp - 0x10]
0042DF99  call     0x140407bb0
0042DF9E  imul     edi, eax
0042DFA1  test     edi, edi
0042DFA3  jle      0x14042dfb7
0042DFA5  mov      rcx, rbx
0042DFA8  call     0x14042ec20
0042DFAD  add      rbx, 8
0042DFB1  sub      rdi, 1
0042DFB5  jne      0x14042dfa5
0042DFB7  mov      rbx, qword ptr [rsp + 0x48]
0042DFBC  mov      eax, 0x8c92
0042DFC1  mov      rdi, qword ptr [rsp + 0x50]
0042DFC6  add      rsp, 0x30
0042DFCA  pop      rbp
0042DFCB  ret      
0042DFCC  int3     
0042DFCD  int3     
0042DFCE  int3     
0042DFCF  int3     
0042DFD0  mov      eax, ecx
0042DFD2  mov      r10, r9
0042DFD5  imul     edx, r8d
0042DFD9  xor      r9d, r9d
0042DFDC  mov      rcx, r10
0042DFDF  add      rdx, rax
0042DFE2  mov      rax, qword ptr [rsp + 0x28]
0042DFE7  lea      rdx, [rax + rdx*4]
0042DFEB  jmp      0x14042dff0
0042DFF0  mov      qword ptr [rsp + 0x20], r9
0042DFF5  mov      dword ptr [rsp + 0x18], r8d
0042DFFA  mov      qword ptr [rsp + 0x10], rdx
0042DFFF  push     rbx
0042E000  push     rbp
0042E001  push     rsi
0042E002  push     rdi
0042E003  push     r12
0042E005  push     r13
0042E007  push     r14
0042E009  push     r15
0042E00B  sub      rsp, 0x18
0042E00F  movzx    edi, word ptr [rcx]
0042E012  mov      rsi, rcx
0042E015  movzx    ebx, word ptr [rcx + 2]
0042E019  mov      eax, edi
0042E01B  shr      eax, 0xb
0042E01E  mov      r11d, edi
0042E021  imul     r10d, eax, 0xff
0042E028  and      r11d, 0x1f
0042E02C  mov      eax, edi
0042E02E  mov      edx, ebx
0042E030  shr      eax, 5
0042E033  and      edx, 0x1f
0042E036  and      eax, 0x3f
0042E039  imul     ecx, eax, 0xff
0042E03F  imul     eax, r11d, 0xff
0042E046  add      r10d, 0x10
0042E04A  mov      ebp, r10d
0042E04D  shr      ebp, 5
0042E050  add      ebp, r10d
0042E053  add      ecx, 0x20
0042E056  shr      ebp, 5
0042E059  add      eax, 0x10
0042E05C  mov      r14d, ecx
0042E05F  mov      r15d, eax
0042E062  shr      r14d, 6
0042E066  add      r14d, ecx
0042E069  shr      r15d, 5
0042E06D  add      r15d, eax
0042E070  shr      r14d, 6
0042E074  mov      eax, ebx
0042E076  shr      r15d, 5
0042E07A  shr      eax, 0xb
0042E07D  imul     ecx, eax, 0xff
0042E083  mov      eax, ebx
0042E085  shr      eax, 5
0042E088  and      eax, 0x3f
0042E08B  add      ecx, 0x10
0042E08E  mov      r12d, ecx
0042E091  shr      r12d, 5
0042E095  add      r12d, ecx
0042E098  imul     ecx, eax, 0xff
0042E09E  imul     eax, edx, 0xff
0042E0A4  shr      r12d, 5
0042E0A8  add      ecx, 0x20
0042E0AB  add      eax, 0x10
0042E0AE  mov      r13d, ecx
0042E0B1  shr      r13d, 6
0042E0B5  mov      edx, eax
0042E0B7  shr      edx, 5
0042E0BA  add      r13d, ecx
0042E0BD  add      edx, eax
0042E0BF  shr      r13d, 6
0042E0C3  mov      eax, dword ptr [rsi + 4]
0042E0C6  xor      esi, esi
0042E0C8  shr      edx, 5
0042E0CB  mov      dword ptr [rsp + 0x60], edx
0042E0CF  mov      dword ptr [rsp + 4], eax
0042E0D3  mov      dword ptr [rsp], esi
0042E0D6  cmp      di, bx
0042E0D9  jbe      0x14042e25b
0042E0DF  mov      rdi, r9
0042E0E2  mov      r11d, esi
0042E0E5  lea      ebx, [rsi*8]
0042E0EC  mov      esi, dword ptr [rsp + 4]
0042E0F0  xor      r10d, r10d
0042E0F3  imul     r11d, r8d
0042E0F7  test     r9, r9
0042E0FA  je       0x14042e103
0042E0FC  movzx    r9d, byte ptr [r10 + rdi]
0042E101  jmp      0x14042e106
0042E103  mov      r9b, 0xff
0042E106  mov      eax, esi
0042E108  mov      ecx, ebx
0042E10A  shr      eax, cl
0042E10C  xor      r8d, r8d
0042E10F  and      eax, 3
0042E112  je       0x14042e1f6
0042E118  sub      eax, 1
0042E11B  je       0x14042e1d7
0042E121  sub      eax, 1
0042E124  je       0x14042e18e
0042E126  cmp      eax, 1
0042E129  jne      0x14042e21b
0042E12F  movzx    ecx, dl
0042E132  movzx    eax, r15b
0042E136  lea      edx, [rax + rcx*2]
0042E139  movzx    ecx, r13b
0042E13D  mov      eax, 0xaaaaaaab
0042E142  mul      edx
0042E144  movzx    eax, r9b
0042E148  shl      eax, 8
0042E14B  shr      edx, 1
0042E14D  movzx    r8d, dl
0042E151  or       r8d, eax
0042E154  movzx    eax, r14b
0042E158  shl      r8d, 8
0042E15C  lea      edx, [rax + rcx*2]
0042E15F  mov      eax, 0xaaaaaaab
0042E164  mul      edx
0042E166  movzx    ecx, r12b
0042E16A  shr      edx, 1
0042E16C  movzx    eax, dl
0042E16F  or       r8d, eax
0042E172  movzx    eax, bpl
0042E176  lea      edx, [rax + rcx*2]
0042E179  mov      eax, 0xaaaaaaab
0042E17E  mul      edx
0042E180  shr      edx, 1
0042E182  movzx    eax, dl
0042E185  mov      edx, dword ptr [rsp + 0x60]
0042E189  jmp      0x14042e214
0042E18E  movzx    eax, dl
0042E191  movzx    ecx, r15b
0042E195  lea      edx, [rax + rcx*2]
0042E198  movzx    ecx, r14b
0042E19C  mov      eax, 0xaaaaaaab
0042E1A1  mul      edx
0042E1A3  movzx    eax, r9b
0042E1A7  shl      eax, 8
0042E1AA  shr      edx, 1
0042E1AC  movzx    r8d, dl
0042E1B0  or       r8d, eax
0042E1B3  movzx    eax, r13b
0042E1B7  shl      r8d, 8
0042E1BB  lea      edx, [rax + rcx*2]
0042E1BE  mov      eax, 0xaaaaaaab
0042E1C3  mul      edx
0042E1C5  movzx    ecx, bpl
0042E1C9  shr      edx, 1
0042E1CB  movzx    eax, dl
0042E1CE  or       r8d, eax
0042E1D1  movzx    eax, r12b
0042E1D5  jmp      0x14042e176
0042E1D7  movzx    eax, dl
0042E1DA  movzx    r8d, r9b
0042E1DE  shl      r8d, 8
0042E1E2  or       r8d, eax
0042E1E5  movzx    eax, r13b
0042E1E9  shl      r8d, 8
0042E1ED  or       r8d, eax
0042E1F0  movzx    eax, r12b
0042E1F4  jmp      0x14042e214
0042E1F6  movzx    eax, r15b
0042E1FA  movzx    r8d, r9b
0042E1FE  shl      r8d, 8
0042E202  or       r8d, eax
0042E205  movzx    eax, r14b
0042E209  shl      r8d, 8
0042E20D  or       r8d, eax
0042E210  movzx    eax, bpl
0042E214  shl      r8d, 8
0042E218  or       r8d, eax
0042E21B  mov      rcx, qword ptr [rsp + 0x68]
0042E220  add      ebx, 2
0042E223  mov      r9, qword ptr [rsp + 0x78]
0042E228  inc      r10
0042E22B  mov      dword ptr [rcx + r11*4], r8d
0042E22F  inc      r11d
0042E232  cmp      r10, 4
0042E236  jl       0x14042e0f7
0042E23C  mov      esi, dword ptr [rsp]
0042E23F  add      rdi, 4
0042E243  mov      r8d, dword ptr [rsp + 0x70]
0042E248  inc      esi
0042E24A  mov      dword ptr [rsp], esi
0042E24D  cmp      esi, 4
0042E250  jl       0x14042e0e2
0042E256  jmp      0x14042e37a
0042E25B  mov      edi, dword ptr [rsp + 0x60]
0042E25F  mov      rbx, r9
0042E262  nop      dword ptr [rax]
0042E266  nop      word ptr [rax + rax]
0042E270  mov      r10d, esi
0042E273  lea      r11d, [rsi*8]
0042E27B  mov      esi, dword ptr [rsp + 4]
0042E27F  xor      r8d, r8d
0042E282  imul     r10d, dword ptr [rsp + 0x70]
0042E288  test     r9, r9
0042E28B  je       0x14042e294
0042E28D  movzx    r9d, byte ptr [rbx + r8]
0042E292  jmp      0x14042e297
0042E294  mov      r9b, 0xff
0042E297  mov      edx, esi
0042E299  mov      ecx, r11d
0042E29C  shr      edx, cl
0042E29E  xor      eax, eax
0042E2A0  and      edx, 3
0042E2A3  je       0x14042e324
0042E2A5  sub      edx, 1
0042E2A8  je       0x14042e308
0042E2AA  sub      edx, 1
0042E2AD  je       0x14042e2cf
0042E2AF  mov      r9, qword ptr [rsp + 0x78]
0042E2B4  cmp      edx, 1
0042E2B7  jne      0x14042e348
0042E2BD  test     r9, r9
0042E2C0  je       0x14042e2c7
0042E2C2  movzx    eax, byte ptr [rbx + r8]
0042E2C7  movzx    eax, al
0042E2CA  shl      eax, 0x18
0042E2CD  jmp      0x14042e348
0042E2CF  movzx    ecx, r15b
0042E2D3  movzx    eax, dil
0042E2D7  add      eax, ecx
0042E2D9  movzx    edx, r13b
0042E2DD  shr      eax, 1
0042E2DF  movzx    ecx, r9b
0042E2E3  shl      ecx, 8
0042E2E6  or       eax, ecx
0042E2E8  movzx    ecx, r14b
0042E2EC  add      edx, ecx
0042E2EE  shl      eax, 8
0042E2F1  shr      edx, 1
0042E2F3  or       eax, edx
0042E2F5  movzx    ecx, bpl
0042E2F9  movzx    edx, r12b
0042E2FD  add      edx, ecx
0042E2FF  shl      eax, 8
0042E302  shr      edx, 1
0042E304  or       eax, edx
0042E306  jmp      0x14042e343
0042E308  movzx    ecx, dil
0042E30C  movzx    eax, r9b
0042E310  shl      eax, 8
0042E313  or       eax, ecx
0042E315  movzx    ecx, r13b
0042E319  shl      eax, 8
0042E31C  or       eax, ecx
0042E31E  movzx    ecx, r12b
0042E322  jmp      0x14042e33e
0042E324  movzx    ecx, r15b
0042E328  movzx    eax, r9b
0042E32C  shl      eax, 8
0042E32F  or       eax, ecx
0042E331  movzx    ecx, r14b
0042E335  shl      eax, 8
0042E338  or       eax, ecx
0042E33A  movzx    ecx, bpl
0042E33E  shl      eax, 8
0042E341  or       eax, ecx
0042E343  mov      r9, qword ptr [rsp + 0x78]
0042E348  mov      rdx, qword ptr [rsp + 0x68]
0042E34D  add      r11d, 2
0042E351  inc      r8
0042E354  mov      dword ptr [rdx + r10*4], eax
0042E358  inc      r10d
0042E35B  cmp      r8, 4
0042E35F  jl       0x14042e288
0042E365  mov      esi, dword ptr [rsp]
0042E368  add      rbx, 4
0042E36C  inc      esi
0042E36E  mov      dword ptr [rsp], esi
0042E371  cmp      esi, 4
0042E374  jl       0x14042e270
0042E37A  add      rsp, 0x18
0042E37E  pop      r15
0042E380  pop      r14
0042E382  pop      r13
0042E384  pop      r12
0042E386  pop      rdi
0042E387  pop      rsi
0042E388  pop      rbp
0042E389  pop      rbx
0042E38A  ret      
0042E38B  int3     
0042E38C  int3     
0042E38D  int3     
0042E38E  int3     
0042E38F  int3     
0042E390  mov      qword ptr [rsp + 0x20], rbx
0042E395  push     rbp
0042E396  push     rsi
0042E397  push     rdi
0042E398  push     r12
0042E39A  push     r13
0042E39C  push     r14
0042E39E  push     r15
0042E3A0  sub      rsp, 0x40
0042E3A4  mov      rax, qword ptr [rip + 0x23662d]
0042E3AB  xor      rax, rsp
0042E3AE  mov      qword ptr [rsp + 0x30], rax
0042E3B3  mov      rax, qword ptr [rsp + 0xa0]
0042E3BB  mov      r10d, edx
0042E3BE  mov      qword ptr [rsp + 0x18], rax
0042E3C3  mov      r12d, r8d
0042E3C6  movzx    edx, word ptr [r9]
0042E3CA  mov      rbx, r9
0042E3CD  movzx    eax, byte ptr [r9]
0042E3D1  and      al, 0xf
0042E3D3  mov      r11d, ecx
0042E3D6  movzx    eax, al
0042E3D9  mov      dword ptr [rsp + 8], r8d
0042E3DE  imul     r8d, eax, 0x11
0042E3E2  movzx    eax, dl
0042E3E5  shr      al, 4
0042E3E8  and      al, 0xf
0042E3EA  movzx    eax, al
0042E3ED  imul     ecx, eax, 0x11
0042E3F0  movzx    eax, dx
0042E3F3  shr      ax, 8
0042E3F7  and      al, 0xf
0042E3F9  shr      dx, 0xc
0042E3FD  movzx    eax, al
0042E400  mov      byte ptr [rsp + 0x20], r8b
0042E405  mov      byte ptr [rsp + 0x21], cl
0042E409  imul     ecx, eax, 0x11
0042E40C  movzx    eax, dl
0042E40F  movzx    edx, word ptr [r9 + 2]
0042E414  mov      byte ptr [rsp + 0x22], cl
0042E418  imul     ecx, eax, 0x11
0042E41B  movzx    eax, byte ptr [r9 + 2]
0042E420  and      al, 0xf
0042E422  movzx    eax, al
0042E425  mov      byte ptr [rsp + 0x23], cl
0042E429  imul     ecx, eax, 0x11
0042E42C  movzx    eax, dl
0042E42F  shr      al, 4
0042E432  and      al, 0xf
0042E434  movzx    eax, al
0042E437  mov      byte ptr [rsp + 0x24], cl
0042E43B  imul     ecx, eax, 0x11
0042E43E  movzx    eax, dx
0042E441  shr      ax, 8
0042E445  and      al, 0xf
0042E447  shr      dx, 0xc
0042E44B  movzx    eax, al
0042E44E  mov      byte ptr [rsp + 0x25], cl
0042E452  imul     ecx, eax, 0x11
0042E455  movzx    eax, dl
0042E458  movzx    edx, word ptr [r9 + 4]
0042E45D  mov      byte ptr [rsp + 0x26], cl
0042E461  imul     ecx, eax, 0x11
0042E464  movzx    eax, byte ptr [r9 + 4]
0042E469  and      al, 0xf
0042E46B  movzx    eax, al
0042E46E  mov      byte ptr [rsp + 0x27], cl
0042E472  imul     ecx, eax, 0x11
0042E475  movzx    eax, dl
0042E478  shr      al, 4
0042E47B  and      al, 0xf
0042E47D  movzx    eax, al
0042E480  mov      byte ptr [rsp + 0x28], cl
0042E484  imul     ecx, eax, 0x11
0042E487  movzx    eax, dx
0042E48A  shr      ax, 8
0042E48E  and      al, 0xf
0042E490  shr      dx, 0xc
0042E494  movzx    eax, al
0042E497  mov      byte ptr [rsp + 0x29], cl
0042E49B  imul     ecx, eax, 0x11
0042E49E  movzx    eax, dl
0042E4A1  movzx    edx, word ptr [r9 + 6]
0042E4A6  mov      byte ptr [rsp + 0x2a], cl
0042E4AA  imul     ecx, eax, 0x11
0042E4AD  movzx    eax, byte ptr [r9 + 6]
0042E4B2  and      al, 0xf
0042E4B4  movzx    eax, al
0042E4B7  mov      byte ptr [rsp + 0x2b], cl
0042E4BB  imul     ecx, eax, 0x11
0042E4BE  movzx    eax, dl
0042E4C1  shr      al, 4
0042E4C4  mov      byte ptr [rsp + 0x2c], cl
0042E4C8  movzx    r9d, word ptr [r9 + 8]
0042E4CD  and      al, 0xf
0042E4CF  movzx    r8d, word ptr [rbx + 0xa]
0042E4D4  mov      r13d, r12d
0042E4D7  movzx    eax, al
0042E4DA  imul     ecx, eax, 0x11
0042E4DD  movzx    eax, dx
0042E4E0  shr      ax, 8
0042E4E4  and      al, 0xf
0042E4E6  shr      dx, 0xc
0042E4EA  movzx    eax, al
0042E4ED  imul     r13d, r10d
0042E4F1  mov      byte ptr [rsp + 0x2d], cl
0042E4F5  imul     ecx, eax, 0x11
0042E4F8  movzx    eax, dl
0042E4FB  mov      edx, r9d
0042E4FE  and      edx, 0x1f
0042E501  add      r13, r11
0042E504  mov      byte ptr [rsp + 0x2e], cl
0042E508  imul     ecx, eax, 0x11
0042E50B  mov      eax, r9d
0042E50E  shr      eax, 0xb
0042E511  mov      byte ptr [rsp + 0x2f], cl
0042E515  imul     ecx, eax, 0xff
0042E51B  mov      eax, r9d
0042E51E  shr      eax, 5
0042E521  and      eax, 0x3f
0042E524  add      ecx, 0x10
0042E527  mov      r11d, ecx
0042E52A  shr      r11d, 5
0042E52E  add      r11d, ecx
0042E531  imul     ecx, eax, 0xff
0042E537  imul     eax, edx, 0xff
0042E53D  mov      edx, r8d
0042E540  and      edx, 0x1f
0042E543  shr      r11d, 5
0042E547  add      ecx, 0x20
0042E54A  add      eax, 0x10
0042E54D  mov      edi, ecx
0042E54F  mov      esi, eax
0042E551  shr      edi, 6
0042E554  add      edi, ecx
0042E556  shr      esi, 5
0042E559  add      esi, eax
0042E55B  shr      edi, 6
0042E55E  mov      eax, r8d
0042E561  shr      esi, 5
0042E564  shr      eax, 0xb
0042E567  imul     ecx, eax, 0xff
0042E56D  mov      eax, r8d
0042E570  shr      eax, 5
0042E573  and      eax, 0x3f
0042E576  add      ecx, 0x10
0042E579  mov      ebp, ecx
0042E57B  shr      ebp, 5
0042E57E  add      ebp, ecx
0042E580  imul     ecx, eax, 0xff
0042E586  imul     eax, edx, 0xff
0042E58C  shr      ebp, 5
0042E58F  add      ecx, 0x20
0042E592  add      eax, 0x10
0042E595  mov      r14d, ecx
0042E598  shr      r14d, 6
0042E59C  mov      r15d, eax
0042E59F  shr      r15d, 5
0042E5A3  add      r14d, ecx
0042E5A6  add      r15d, eax
0042E5A9  shr      r14d, 6
0042E5AD  mov      eax, dword ptr [rbx + 0xc]
0042E5B0  xor      ecx, ecx
0042E5B2  shr      r15d, 5
0042E5B6  mov      dword ptr [rsp + 4], eax
0042E5BA  mov      dword ptr [rsp], ecx
0042E5BD  cmp      r9w, r8w
0042E5C1  jbe      0x14042e756
0042E5C7  lea      rdx, [rsp + 0x20]
0042E5CC  mov      qword ptr [rsp + 0x10], rdx
0042E5D1  mov      ebx, r12d
0042E5D4  xor      r10d, r10d
0042E5D7  imul     ebx, ecx
0042E5DA  lea      r12d, [rcx*8]
0042E5E2  nop      dword ptr [rax]
0042E5E6  nop      word ptr [rax + rax]
0042E5F0  movzx    r9d, byte ptr [r10 + rdx]
0042E5F5  mov      ecx, r12d
0042E5F8  shr      eax, cl
0042E5FA  xor      r8d, r8d
0042E5FD  and      eax, 3
0042E600  je       0x14042e6e8
0042E606  sub      eax, 1
0042E609  je       0x14042e6c8
0042E60F  sub      eax, 1
0042E612  je       0x14042e67e
0042E614  cmp      eax, 1
0042E617  jne      0x14042e70d
0042E61D  movzx    ecx, r15b
0042E621  movzx    eax, sil
0042E625  lea      edx, [rax + rcx*2]
0042E628  movzx    ecx, r14b
0042E62C  mov      eax, 0xaaaaaaab
0042E631  mul      edx
0042E633  movzx    eax, r9b
0042E637  shl      eax, 8
0042E63A  shr      edx, 1
0042E63C  movzx    r8d, dl
0042E640  or       r8d, eax
0042E643  movzx    eax, dil
0042E647  shl      r8d, 8
0042E64B  lea      edx, [rax + rcx*2]
0042E64E  mov      eax, 0xaaaaaaab
0042E653  mul      edx
0042E655  movzx    ecx, bpl
0042E659  shr      edx, 1
0042E65B  movzx    eax, dl
0042E65E  or       r8d, eax
0042E661  movzx    eax, r11b
0042E665  lea      edx, [rax + rcx*2]
0042E668  mov      eax, 0xaaaaaaab
0042E66D  mul      edx
0042E66F  shr      edx, 1
0042E671  movzx    eax, dl
0042E674  mov      rdx, qword ptr [rsp + 0x10]
0042E679  jmp      0x14042e706
0042E67E  movzx    ecx, sil
0042E682  movzx    eax, r15b
0042E686  lea      edx, [rax + rcx*2]
0042E689  movzx    ecx, dil
0042E68D  mov      eax, 0xaaaaaaab
0042E692  mul      edx
0042E694  movzx    eax, r9b
0042E698  shl      eax, 8
0042E69B  shr      edx, 1
0042E69D  movzx    r8d, dl
0042E6A1  or       r8d, eax
0042E6A4  movzx    eax, r14b
0042E6A8  shl      r8d, 8
0042E6AC  lea      edx, [rax + rcx*2]
0042E6AF  mov      eax, 0xaaaaaaab
0042E6B4  mul      edx
0042E6B6  movzx    ecx, r11b
0042E6BA  shr      edx, 1
0042E6BC  movzx    eax, dl
0042E6BF  or       r8d, eax
0042E6C2  movzx    eax, bpl
0042E6C6  jmp      0x14042e665
0042E6C8  movzx    eax, r15b
0042E6CC  movzx    r8d, r9b
0042E6D0  shl      r8d, 8
0042E6D4  or       r8d, eax
0042E6D7  movzx    eax, r14b
0042E6DB  shl      r8d, 8
0042E6DF  or       r8d, eax
0042E6E2  movzx    eax, bpl
0042E6E6  jmp      0x14042e706
0042E6E8  movzx    eax, sil
0042E6EC  movzx    r8d, r9b
0042E6F0  shl      r8d, 8
0042E6F4  or       r8d, eax
0042E6F7  movzx    eax, dil
0042E6FB  shl      r8d, 8
0042E6FF  or       r8d, eax
0042E702  movzx    eax, r11b
0042E706  shl      r8d, 8
0042E70A  or       r8d, eax
0042E70D  mov      rcx, qword ptr [rsp + 0x18]
0042E712  add      r12d, 2
0042E716  mov      eax, ebx
0042E718  inc      r10
0042E71B  add      rax, r13
0042E71E  inc      ebx
0042E720  mov      dword ptr [rcx + rax*4], r8d
0042E724  mov      eax, dword ptr [rsp + 4]
0042E728  cmp      r10, 4
0042E72C  jl       0x14042e5f0
0042E732  mov      ecx, dword ptr [rsp]
0042E735  add      rdx, 4
0042E739  mov      r12d, dword ptr [rsp + 8]
0042E73E  inc      ecx
0042E740  mov      dword ptr [rsp], ecx
0042E743  mov      qword ptr [rsp + 0x10], rdx
0042E748  cmp      ecx, 4
0042E74B  jl       0x14042e5d1
0042E751  jmp      0x14042e856
0042E756  lea      r10, [rsp + 0x20]
0042E75B  nop      dword ptr [rax + rax]
0042E760  mov      r9d, r12d
0042E763  lea      ebx, [rcx*8]
0042E76A  imul     r9d, ecx
0042E76E  mov      r12d, 4
0042E774  nop      dword ptr [rax]
0042E778  nop      dword ptr [rax + rax]
0042E780  movzx    r8d, byte ptr [r10]
0042E784  mov      ecx, ebx
0042E786  shr      eax, cl
0042E788  xor      edx, edx
0042E78A  and      eax, 3
0042E78D  je       0x14042e7fc
0042E78F  sub      eax, 1
0042E792  je       0x14042e7e0
0042E794  sub      eax, 1
0042E797  je       0x14042e7a7
0042E799  cmp      eax, 1
0042E79C  jne      0x14042e81b
0042E79E  movzx    edx, r8b
0042E7A2  shl      edx, 0x18
0042E7A5  jmp      0x14042e81b
0042E7A7  movzx    eax, sil
0042E7AB  movzx    edx, r15b
0042E7AF  add      edx, eax
0042E7B1  movzx    ecx, r14b
0042E7B5  shr      edx, 1
0042E7B7  movzx    eax, r8b
0042E7BB  shl      eax, 8
0042E7BE  or       edx, eax
0042E7C0  movzx    eax, dil
0042E7C4  add      ecx, eax
0042E7C6  shl      edx, 8
0042E7C9  shr      ecx, 1
0042E7CB  or       edx, ecx
0042E7CD  movzx    eax, r11b
0042E7D1  movzx    ecx, bpl
0042E7D5  add      ecx, eax
0042E7D7  shl      edx, 8
0042E7DA  shr      ecx, 1
0042E7DC  or       edx, ecx
0042E7DE  jmp      0x14042e81b
0042E7E0  movzx    eax, r15b
0042E7E4  movzx    edx, r8b
0042E7E8  shl      edx, 8
0042E7EB  or       edx, eax
0042E7ED  movzx    eax, r14b
0042E7F1  shl      edx, 8
0042E7F4  or       edx, eax
0042E7F6  movzx    eax, bpl
0042E7FA  jmp      0x14042e816
0042E7FC  movzx    eax, sil
0042E800  movzx    edx, r8b
0042E804  shl      edx, 8
0042E807  or       edx, eax
0042E809  movzx    eax, dil
0042E80D  shl      edx, 8
0042E810  or       edx, eax
0042E812  movzx    eax, r11b
0042E816  shl      edx, 8
0042E819  or       edx, eax
0042E81B  mov      rcx, qword ptr [rsp + 0x18]
0042E820  add      ebx, 2
0042E823  mov      eax, r9d
0042E826  inc      r10
0042E829  add      rax, r13
0042E82C  inc      r9d
0042E82F  mov      dword ptr [rcx + rax*4], edx
0042E832  mov      eax, dword ptr [rsp + 4]
0042E836  sub      r12, 1
0042E83A  jne      0x14042e780
0042E840  mov      ecx, dword ptr [rsp]
0042E843  mov      r12d, dword ptr [rsp + 8]
0042E848  inc      ecx
0042E84A  mov      dword ptr [rsp], ecx
0042E84D  cmp      ecx, 4
0042E850  jl       0x14042e760
0042E856  mov      rcx, qword ptr [rsp + 0x30]
0042E85B  xor      rcx, rsp
0042E85E  call     0x1404f77a0
0042E863  mov      rbx, qword ptr [rsp + 0x98]
0042E86B  add      rsp, 0x40
0042E86F  pop      r15
0042E871  pop      r14
0042E873  pop      r13
0042E875  pop      r12
0042E877  pop      rdi
0042E878  pop      rsi
0042E879  pop      rbp
0042E87A  ret      
0042E87B  int3     
0042E87C  int3     
0042E87D  int3     
0042E87E  int3     
0042E87F  int3     
0042E880  mov      dword ptr [rsp + 0x18], r8d
0042E885  mov      dword ptr [rsp + 0x10], edx
0042E889  mov      dword ptr [rsp + 8], ecx
0042E88D  push     rbx
0042E88E  push     rbp
0042E88F  push     rsi
0042E890  push     rdi
0042E891  push     r12
0042E893  push     r13
0042E895  push     r14
0042E897  push     r15
0042E899  sub      rsp, 0x18
0042E89D  movzx    edx, word ptr [r9 + 8]
0042E8A2  mov      edi, r8d
0042E8A5  movzx    eax, byte ptr [r9 + 6]
0042E8AA  movzx    ecx, byte ptr [r9 + 3]
0042E8AF  movzx    r8d, byte ptr [r9 + 7]
0042E8B4  movzx    r11d, byte ptr [r9]
0042E8B8  movzx    ebx, byte ptr [r9 + 1]
0042E8BD  shl      cx, 8
0042E8C1  shl      r8d, 8
0042E8C5  or       r8d, eax
0042E8C8  movzx    eax, byte ptr [r9 + 5]
0042E8CD  shl      r8d, 8
0042E8D1  or       r8d, eax
0042E8D4  movzx    eax, byte ptr [r9 + 4]
0042E8D9  shl      r8d, 8
0042E8DD  or       r8d, eax
0042E8E0  movzx    eax, byte ptr [r9 + 2]
0042E8E5  or       cx, ax
0042E8E8  mov      dword ptr [rsp + 4], r8d
0042E8ED  mov      word ptr [rsp + 0x78], cx
0042E8F2  mov      eax, edx
0042E8F4  shr      eax, 0xb
0042E8F7  imul     ecx, eax, 0xff
0042E8FD  mov      eax, edx
0042E8FF  shr      eax, 5
0042E902  and      edx, 0x1f
0042E905  and      eax, 0x3f
0042E908  add      ecx, 0x10
0042E90B  mov      esi, ecx
0042E90D  shr      esi, 5
0042E910  add      esi, ecx
0042E912  imul     ecx, eax, 0xff
0042E918  imul     eax, edx, 0xff
0042E91E  movzx    edx, word ptr [r9 + 0xa]
0042E923  shr      esi, 5
0042E926  add      ecx, 0x20
0042E929  add      eax, 0x10
0042E92C  mov      ebp, ecx
0042E92E  mov      r14d, eax
0042E931  shr      ebp, 6
0042E934  add      ebp, ecx
0042E936  shr      r14d, 5
0042E93A  add      r14d, eax
0042E93D  shr      ebp, 6
0042E940  mov      eax, edx
0042E942  shr      r14d, 5
0042E946  shr      eax, 0xb
0042E949  imul     ecx, eax, 0xff
0042E94F  mov      eax, edx
0042E951  shr      eax, 5
0042E954  and      edx, 0x1f
0042E957  and      eax, 0x3f
0042E95A  add      ecx, 0x10
0042E95D  mov      r15d, ecx
0042E960  shr      r15d, 5
0042E964  add      r15d, ecx
0042E967  imul     ecx, eax, 0xff
0042E96D  imul     eax, edx, 0xff
0042E973  shr      r15d, 5
0042E977  add      ecx, 0x20
0042E97A  add      eax, 0x10
0042E97D  mov      r12d, ecx
0042E980  mov      r13d, eax
0042E983  shr      r12d, 6
0042E987  shr      r13d, 5
0042E98B  add      r12d, ecx
0042E98E  add      r13d, eax
0042E991  shr      r12d, 6
0042E995  mov      eax, dword ptr [r9 + 0xc]
0042E999  shr      r13d, 5
0042E99D  mov      dword ptr [rsp + 8], eax
0042E9A1  xor      eax, eax
0042E9A3  mov      dword ptr [rsp], eax
0042E9A6  nop      word ptr [rax + rax]
0042E9B0  lea      r10d, [rax*4]
0042E9B8  add      eax, dword ptr [rsp + 0x68]
0042E9BC  imul     eax, edi
0042E9BF  mov      edi, 4
0042E9C4  sub      eax, r10d
0042E9C7  add      eax, dword ptr [rsp + 0x60]
0042E9CB  mov      dword ptr [rsp + 0xc], eax
0042E9CF  nop      
0042E9D0  lea      ecx, [r10 + r10*2]
0042E9D4  cmp      ecx, 0xc
0042E9D7  jg       0x14042e9e1
0042E9D9  movzx    r9d, word ptr [rsp + 0x78]
0042E9DF  jmp      0x14042ea03
0042E9E1  cmp      ecx, 0xf
0042E9E4  jne      0x14042e9fd
0042E9E6  movzx    r9d, word ptr [rsp + 0x78]
0042E9EC  mov      eax, r8d
0042E9EF  and      eax, 3
0042E9F2  shr      r9d, 0xf
0042E9F6  add      eax, eax
0042E9F8  or       r9d, eax
0042E9FB  jmp      0x14042ea0a
0042E9FD  add      ecx, -0x10
0042EA00  mov      r9d, r8d
0042EA03  shr      r9d, cl
0042EA06  and      r9d, 7
0042EA0A  test     r9d, r9d
0042EA0D  jne      0x14042ea18
0042EA0F  movzx    r9d, r11b
0042EA13  jmp      0x14042eaa9
0042EA18  cmp      r9d, 1
0042EA1C  jne      0x14042ea27
0042EA1E  movzx    r9d, bl
0042EA22  jmp      0x14042eaa9
0042EA27  cmp      r11b, bl
0042EA2A  jbe      0x14042ea65
0042EA2C  lea      ecx, [r9 - 1]
0042EA30  movzx    eax, r11b
0042EA34  mov      r8d, 8
0042EA3A  sub      r8d, r9d
0042EA3D  imul     r8d, eax
0042EA41  movzx    eax, bl
0042EA44  imul     ecx, eax
0042EA47  mov      eax, 0x92492493
0042EA4C  add      r8d, ecx
0042EA4F  imul     r8d
0042EA52  lea      r9d, [r8 + rdx]
0042EA56  sar      r9d, 2
0042EA5A  mov      eax, r9d
0042EA5D  shr      eax, 0x1f
0042EA60  add      r9d, eax
0042EA63  jmp      0x14042eaa9
0042EA65  cmp      r9d, 6
0042EA69  jne      0x14042ea70
0042EA6B  xor      r9b, r9b
0042EA6E  jmp      0x14042eaa9
0042EA70  cmp      r9d, 7
0042EA74  jne      0x14042ea7b
0042EA76  mov      r9b, 0xff
0042EA79  jmp      0x14042eaa9
0042EA7B  lea      ecx, [r9 - 1]
0042EA7F  movzx    eax, r11b
0042EA83  mov      edx, 6
0042EA88  sub      edx, r9d
0042EA8B  imul     edx, eax
0042EA8E  movzx    eax, bl
0042EA91  imul     ecx, eax
0042EA94  mov      eax, 0x66666667
0042EA99  add      edx, ecx
0042EA9B  imul     edx
0042EA9D  sar      edx, 1
0042EA9F  mov      r9d, edx
0042EAA2  shr      r9d, 0x1f
0042EAA6  add      r9d, edx
0042EAA9  mov      edx, dword ptr [rsp + 8]
0042EAAD  lea      ecx, [r10 + r10]
0042EAB1  shr      edx, cl
0042EAB3  xor      r8d, r8d
0042EAB6  and      edx, 3
0042EAB9  je       0x14042ebab
0042EABF  sub      edx, 1
0042EAC2  je       0x14042eb8b
0042EAC8  sub      edx, 1
0042EACB  je       0x14042eb32
0042EACD  cmp      edx, 1
0042EAD0  jne      0x14042ebd0
0042EAD6  movzx    ecx, r13b
0042EADA  movzx    eax, r14b
0042EADE  lea      edx, [rax + rcx*2]
0042EAE1  movzx    ecx, r12b
0042EAE5  mov      eax, 0xaaaaaaab
0042EAEA  mul      edx
0042EAEC  movzx    eax, r9b
0042EAF0  shl      eax, 8
0042EAF3  shr      edx, 1
0042EAF5  movzx    r8d, dl
0042EAF9  or       r8d, eax
0042EAFC  movzx    eax, bpl
0042EB00  shl      r8d, 8
0042EB04  lea      edx, [rax + rcx*2]
0042EB07  mov      eax, 0xaaaaaaab
0042EB0C  mul      edx
0042EB0E  movzx    ecx, r15b
0042EB12  shr      edx, 1
0042EB14  movzx    eax, dl
0042EB17  or       r8d, eax
0042EB1A  movzx    eax, sil
0042EB1E  lea      edx, [rax + rcx*2]
0042EB21  mov      eax, 0xaaaaaaab
0042EB26  mul      edx
0042EB28  shr      edx, 1
0042EB2A  movzx    eax, dl
0042EB2D  jmp      0x14042ebc9
0042EB32  movzx    ecx, r14b
0042EB36  movzx    eax, r13b
0042EB3A  lea      edx, [rax + rcx*2]
0042EB3D  movzx    ecx, bpl
0042EB41  mov      eax, 0xaaaaaaab
0042EB46  mul      edx
0042EB48  movzx    eax, r9b
0042EB4C  shl      eax, 8
