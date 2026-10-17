0042D2F0  push     rdi
0042D2F2  sub      rsp, 0x30
0042D2F6  mov      rdi, rdx
0042D2F9  test     r8b, 2
0042D2FD  je       0x14042d308
0042D2FF  mov      eax, dword ptr [rsp + 0x60]
0042D303  shl      eax, 0x18
0042D306  jmp      0x14042d30d
0042D308  mov      eax, 0xff000000
0042D30D  mov      dword ptr [rsp + 0x20], eax
0042D311  call     0x140421450
0042D316  movzx    eax, byte ptr [rip + 0x19335d]
0042D31D  movzx    ecx, byte ptr [rip + 0x19246c]
0042D324  imul     ecx, dword ptr [rsp + 0x60]
0042D329  lea      r8, [rdi + rax*4]
0042D32D  mov      eax, 0x80808081
0042D332  mul      ecx
0042D334  mov      eax, dword ptr [r8]
0042D337  shr      edx, 7
0042D33A  and      eax, 0xffffff
0042D33F  shl      edx, 0x18
0042D342  or       edx, eax
0042D344  mov      dword ptr [r8], edx
0042D347  add      rsp, 0x30
0042D34B  pop      rdi
0042D34C  ret      
0042D34D  int3     
0042D34E  int3     
0042D34F  int3     
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
