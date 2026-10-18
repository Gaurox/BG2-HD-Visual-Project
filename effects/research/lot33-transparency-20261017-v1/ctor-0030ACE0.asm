0030ACE0 push     rbp
0030ACE2 push     rsi
0030ACE3 push     r15
0030ACE5 mov      rbp, rsp
0030ACE8 sub      rsp, 0x60
0030ACEC mov      rax, qword ptr [rip + 0x359ce5]
0030ACF3 xor      rax, rsp
0030ACF6 mov      qword ptr [rbp - 0x30], rax
0030ACFA mov      qword ptr [rsp + 0x58], rdi
0030ACFF mov      rsi, rcx
0030AD02 mov      qword ptr [rsp + 0x50], r12
0030AD07 mov      qword ptr [rsp + 0x48], r13
0030AD0C mov      qword ptr [rsp + 0x40], r14
0030AD11 mov      r14, r8
0030AD14 mov      word ptr [rbp - 0x40], r9w
0030AD19 movzx    r13d, dx
0030AD1D call     0x1403074d0
0030AD22 lea      rax, [rip + 0x29e1d7]
0030AD29 lea      r15, [rsi + 0xce0]
0030AD30 mov      qword ptr [rsi], rax
0030AD33 mov      rcx, r15
0030AD36 call     0x140410f70
0030AD3B lea      rcx, [rsi + 0xe18]
0030AD42 call     0x140410f70
0030AD47 movzx    edx, word ptr [rip + 0x2b592e]
0030AD4E lea      r12, [rsi + 0xf50]
0030AD55 mov      rcx, r12
0030AD58 call     0x140421010
0030AD5D xor      ecx, ecx
0030AD5F mov      word ptr [rsi + 8], r13w
0030AD64 mov      dword ptr [rsi + 0xba8], ecx
0030AD6A lea      rax, [rip + 0x2e0a3c]
0030AD71 mov      byte ptr [rsi + 0xf8b], cl
0030AD77 mov      edx, r13d
0030AD7A mov      byte ptr [rsi + 0x5f5], cl
0030AD80 mov      edi, r13d
0030AD83 mov      qword ptr [rsi + 0xcd8], rcx
0030AD8A lea      rcx, [rip + 0x2a0467]
0030AD91 mov      qword ptr [rsi + 0xf80], 0x100
0030AD9C mov      byte ptr [rsi + 0x22], 0xff
0030ADA0 mov      qword ptr [rsi + 0x28], rax
0030ADA4 call     0x140400170
0030ADA9 mov      rdx, rax
0030ADAC lea      rcx, [rbp - 0x38]
0030ADB0 call     0x1403ff7c0
0030ADB5 mov      rcx, rsi
0030ADB8 mov      rdx, qword ptr [rax]
0030ADBB call     0x14033f4f0
0030ADC0 test     al, al
0030ADC2 jne      0x14030b3f2
0030ADC8 mov      eax, r13d
