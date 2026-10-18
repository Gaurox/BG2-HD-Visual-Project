0032C910 push     rbp
0032C912 push     rsi
0032C913 push     rdi
0032C914 push     r12
0032C916 push     r13
0032C918 push     r14
0032C91A push     r15
0032C91C lea      rbp, [rsp - 7]
0032C921 sub      rsp, 0xa0
0032C928 mov      rax, qword ptr [rip + 0x3380a9]
0032C92F xor      rax, rsp
0032C932 mov      qword ptr [rbp - 9], rax
0032C936 mov      rax, qword ptr [rbp + 0x67]
0032C93A mov      rsi, rcx
0032C93D mov      rcx, qword ptr [rbp + 0x87]
0032C944 mov      r12, rdx
0032C947 movups   xmm0, xmmword ptr [r9]
0032C94B mov      edi, dword ptr [rbp + 0x9f]
0032C951 movzx    r13d, byte ptr [rbp + 0xa7]
0032C959 mov      r14, qword ptr [rbp + 0x6f]
0032C95D mov      qword ptr [rbp - 0x51], rcx
0032C961 mov      rcx, qword ptr [rbp + 0xaf]
0032C968 mov      qword ptr [rbp - 0x49], rcx
0032C96C mov      rcx, qword ptr [rax]
0032C96F mov      qword ptr [rbp - 0x59], rcx
0032C973 shr      rcx, 0x20
0032C977 add      ecx, edi
0032C979 movaps   xmmword ptr [rbp - 0x29], xmm0
0032C97D cmp      dword ptr [rip + 0x3e3394], 0
0032C984 mov      dword ptr [rbp - 0x55], ecx
0032C987 je       0x14032c9a4
0032C989 movzx    eax, byte ptr [rsi + 0x52a5]
0032C990 cmp      word ptr [rsi + 0x528a], ax
0032C997 jle      0x14032c9a4
0032C999 mov      eax, dword ptr [rbp + 0x77]
0032C99C or       eax, dword ptr [rip + 0x2759aa]
0032C9A2 jmp      0x14032c9a7
0032C9A4 mov      eax, dword ptr [rbp + 0x77]
0032C9A7 mov      ecx, 4
0032C9AC mov      qword ptr [rsp + 0x20], r14
0032C9B1 test     r13b, r13b
0032C9B4 lea      r9, [rbp - 0x59]
0032C9B8 mov      r15d, 6
0032C9BE lea      rdx, [rbp - 0x29]
0032C9C2 cmove    r15d, ecx
0032C9C6 mov      rcx, r12
0032C9C9 or       r15d, dword ptr [rip + 0x275974]
0032C9D0 or       r15d, eax
0032C9D3 mov      r8d, r15d
0032C9D6 call     0x14029e1b0
0032C9DB mov      r8d, r15d
0032C9DE lea      rdx, [rbp - 0x29]
0032C9E2 mov      rcx, r12
0032C9E5 call     0x14029e190
0032C9EA test     eax, eax
0032C9EC je       0x14032cfbf
0032C9F2 cmp      dword ptr [rsi + 0xba8], 0
