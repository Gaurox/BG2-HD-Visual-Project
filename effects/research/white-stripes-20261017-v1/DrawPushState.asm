00413450  cmp      dword ptr [rip + 0x317559], 1
00413457  je       0x140429740
0041345D  jmp      0x14042cde0
00413462  int3     
00413463  int3     
00413464  int3     
00413465  int3     
00413466  int3     
00413467  int3     
00413468  int3     
00413469  int3     
0041346A  int3     
0041346B  int3     
0041346C  int3     
0041346D  int3     
0041346E  int3     
0041346F  int3     
00413470  sub      rsp, 0x38
00413474  cmp      dword ptr [rip + 0x317535], 1
0041347B  mov      rax, qword ptr [rsp + 0x60]
00413480  mov      qword ptr [rsp + 0x20], rax
00413485  jne      0x140413491
00413487  call     0x140429760
0041348C  add      rsp, 0x38
00413490  ret      
00413491  call     0x14042ce00
00413496  add      rsp, 0x38
0041349A  ret      
0041349B  int3     
0041349C  int3     
0041349D  int3     
0041349E  int3     
0041349F  int3     
004134A0  cmp      dword ptr [rip + 0x317509], 1
004134A7  je       0x140429910
004134AD  jmp      0x14042ce80
004134B2  int3     
004134B3  int3     
004134B4  int3     
004134B5  int3     
004134B6  int3     
004134B7  int3     
004134B8  int3     
004134B9  int3     
004134BA  int3     
004134BB  int3     
004134BC  int3     
004134BD  int3     
004134BE  int3     
004134BF  int3     
004134C0  cmp      dword ptr [rip + 0x3174e9], 1
004134C7  je       0x140429b80
004134CD  jmp      0x14042ce90
004134D2  int3     
004134D3  int3     
004134D4  int3     
004134D5  int3     
004134D6  int3     
004134D7  int3     
004134D8  int3     
004134D9  int3     
004134DA  int3     
004134DB  int3     
004134DC  int3     
004134DD  int3     
004134DE  int3     
004134DF  int3     
004134E0  sub      rsp, 0x28
004134E4  mov      dword ptr [rip + 0x3174c6], ecx
004134EA  cmp      ecx, 1
004134ED  jne      0x1404134f6
004134EF  call     0x140429bf0
004134F4  jmp      0x1404134fb
004134F6  call     0x14042cea0
004134FB  movzx    ecx, al
004134FE  xor      edx, edx
00413500  mov      eax, dword ptr [rip + 0x3174aa]
00413506  test     cl, cl
00413508  cmove    eax, edx
0041350B  mov      dword ptr [rip + 0x31749f], eax
00413511  add      rsp, 0x28
00413515  ret      
00413516  int3     
00413517  int3     
00413518  int3     
00413519  int3     
0041351A  int3     
0041351B  int3     
0041351C  int3     
0041351D  int3     
0041351E  int3     
0041351F  int3     
00413520  cmp      dword ptr [rip + 0x317489], 1
00413527  je       0x1400255b0
0041352D  jmp      0x1400255b0
00413532  int3     
00413533  int3     
00413534  int3     
00413535  int3     
00413536  int3     
00413537  int3     
00413538  int3     
00413539  int3     
0041353A  int3     
0041353B  int3     
0041353C  int3     
0041353D  int3     
0041353E  int3     
0041353F  int3     
00413540  cmp      dword ptr [rip + 0x317469], 1
00413547  je       0x1400255b0
