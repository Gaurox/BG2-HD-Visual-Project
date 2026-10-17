0042A840  mov      eax, dword ptr [rip + 0x2b49726]
0042A846  shl      ecx, 0x15
0042A849  xor      ecx, eax
0042A84B  and      ecx, 0x3fe00000
0042A851  xor      eax, ecx
0042A853  mov      dword ptr [rip + 0x2b49713], eax
0042A859  ret      
0042A85A  int3     
0042A85B  int3     
0042A85C  int3     
0042A85D  int3     
0042A85E  int3     
0042A85F  int3     
0042A860  mov      eax, dword ptr [rip + 0x2b49706]
0042A866  and      edx, 0xf
0042A869  shl      edx, 4
0042A86C  and      ecx, 0xf
0042A86F  or       edx, ecx
0042A871  and      eax, 0xfffe01ff
0042A876  shl      edx, 9
0042A879  or       edx, eax
0042A87B  mov      dword ptr [rip + 0x2b496eb], edx
0042A881  ret      
0042A882  int3     
0042A883  int3     
0042A884  int3     
0042A885  int3     
0042A886  int3     
0042A887  int3     
0042A888  int3     
0042A889  int3     
0042A88A  int3     
0042A88B  int3     
0042A88C  int3     
0042A88D  int3     
0042A88E  int3     
0042A88F  int3     
0042A890  movss    dword ptr [rip + 0x2b497ac], xmm0
0042A898  ret      
0042A899  int3     
0042A89A  int3     
0042A89B  int3     
0042A89C  int3     
0042A89D  int3     
0042A89E  int3     
0042A89F  int3     
0042A8A0  movsxd   rax, dword ptr [rip + 0x2b49729]
0042A8A7  lea      rdx, [rip + 0x2b3167a]
0042A8AE  and      dword ptr [rip + 0x2b496b4], 0xffefffff
0042A8B8  movsd    xmm0, qword ptr [rip + 0x2b496ac]
0042A8C0  mov      dword ptr [rip + 0x2b496aa], 0xffffffff
0042A8CA  lea      rcx, [rax + rax*2]
0042A8CE  movsd    qword ptr [rdx + rcx*4], xmm0
0042A8D3  mov      eax, dword ptr [rip + 0x2b4969b]
0042A8D9  mov      dword ptr [rdx + rcx*4 + 8], eax
0042A8DD  inc      dword ptr [rip + 0x2b496ed]
0042A8E3  mov      dword ptr [rip + 0x2b49687], 0
0042A8ED  ret      
0042A8EE  int3     
0042A8EF  int3     
0042A8F0  mov      eax, dword ptr [rip + 0x2b49676]
0042A8F6  mov      edx, ecx
0042A8F8  shl      edx, 0x11
0042A8FB  mov      r8d, eax
0042A8FE  xor      edx, eax
0042A900  shr      r8d, 0x11
0042A904  and      edx, 0xe0000
0042A90A  and      r8d, 7
0042A90E  xor      edx, eax
0042A910  cmp      ecx, 8
0042A913  ja       0x14042a9ce
0042A919  movsxd   rax, ecx
0042A91C  lea      r9, [rip - 0x42a923]
0042A923  mov      ecx, dword ptr [r9 + rax*4 + 0x42a9dc]
0042A92B  add      rcx, r9
0042A92E  jmp      rcx
0042A930  and      edx, 0xfffffff0
0042A933  mov      dword ptr [rip + 0x2b49633], edx
0042A939  ret      
0042A93A  and      edx, 0xfffffff3
0042A93D  or       edx, 3
