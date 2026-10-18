0032D020 push     rbx
0032D022 push     rsi
0032D023 push     r14
0032D025 push     r15
0032D027 sub      rsp, 0x88
0032D02E mov      rax, qword ptr [rip + 0x3379a3]
0032D035 xor      rax, rsp
0032D038 mov      qword ptr [rsp + 0x60], rax
0032D03D cmp      byte ptr [rcx + 0xf81], 0
0032D044 mov      r15, rdx
0032D047 mov      rbx, qword ptr [rsp + 0xf0]
0032D04F mov      rsi, rcx
0032D052 mov      rax, qword ptr [rsp + 0xd0]
0032D05A mov      r14, qword ptr [rsp + 0xd8]
0032D062 mov      qword ptr [rsp + 0x48], rbx
0032D067 je       0x14032d36f
