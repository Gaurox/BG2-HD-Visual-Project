00227800 mov      qword ptr [rsp + 0x10], rbx
00227805 push     rdi
00227806 sub      rsp, 0x30
0022780A mov      rax, qword ptr [rip + 0x43d1c7]
00227811 xor      rax, rsp
00227814 mov      qword ptr [rsp + 0x28], rax
00227819 mov      rdi, rcx
0022781C lea      rdx, [rip + 0x375245]
00227823 lea      rcx, [rsp + 0x20]
00227828 call     0x1403ff800
0022782D mov      rcx, rdi
00227830 mov      rdx, qword ptr [rax]
00227833 call     0x140227600
00227838 mov      rcx, qword ptr [rdi + 0x1b8]
0022783F lea      rax, [rip + 0x37418a]
00227846 xor      edx, edx
00227848 mov      qword ptr [rdi], rax
0022784B call     0x140412380
00227850 mov      rax, qword ptr [rip + 0x43fcf1]
00227857 lea      rcx, [rdi + 0x1c8]
0022785E xor      edx, edx
00227860 mov      r9, qword ptr [rax + 0x1090]
00227867 add      r9, 0x63d8
0022786E lea      r8d, [rdx + 0x47]
00227872 call     0x1404221c0
00227877 mov      rcx, qword ptr [rdi + 0x1b8]
0022787E lea      rdx, [rdi + 0x1c8]
00227885 call     0x140412390
0022788A xor      eax, eax
0022788C lea      rcx, [rdi + 0x140]
00227893 mov      qword ptr [rdi + 0x1f8], rax
0022789A lea      r8, [rip + 0x3c3f0c]
002278A1 mov      dword ptr [rdi + 0x200], eax
002278A7 lea      rdx, [rsp + 0x20]
002278AC mov      dword ptr [rdi + 0x210], eax
002278B2 mov      eax, 5
002278B7 mov      word ptr [rdi + 0x214], ax
002278BE call     0x1403ff960
002278C3 mov      eax, 0x37
002278C8 mov      dword ptr [rdi + 0x70], 0xffffffff
002278CF lea      rcx, [rdi + 0x178]
002278D6 mov      word ptr [rdi + 0x3b8], ax
002278DD lea      rdx, [rip + 0x3c3ec9]
002278E4 call     0x1403fd810
002278E9 mov      dword ptr [rsp + 0x20], 0x17
002278F1 mov      rax, rdi
002278F4 mov      dword ptr [rsp + 0x24], 0x32
002278FC mov      rcx, qword ptr [rsp + 0x20]
00227901 mov      qword ptr [rdi + 0x164], rcx
00227908 mov      dword ptr [rdi + 0x180], 0xffffffff
00227912 mov      rcx, qword ptr [rsp + 0x28]
00227917 xor      rcx, rsp
0022791A call     0x1404f77a0
0022791F mov      rbx, qword ptr [rsp + 0x48]
00227924 add      rsp, 0x30
00227928 pop      rdi
00227929 ret      
