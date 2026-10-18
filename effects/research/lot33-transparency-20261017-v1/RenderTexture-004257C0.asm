004257C0 mov      rax, rsp
004257C3 mov      dword ptr [rax + 0x20], r9d
004257C7 sub      rsp, 0x48
004257CB mov      qword ptr [rax + 8], rbx
004257CF mov      ebx, edx
004257D1 mov      qword ptr [rax + 0x10], rbp
004257D5 mov      qword ptr [rax + 0x18], rsi
004257D9 mov      qword ptr [rax - 8], rdi
004257DD mov      rdi, qword ptr [rcx + 0x100]
004257E4 mov      qword ptr [rax - 0x10], r12
004257E8 mov      qword ptr [rax - 0x18], r13
004257EC mov      r13d, r9d
004257EF mov      qword ptr [rax - 0x28], r15
004257F3 mov      rcx, qword ptr [rdi]
004257F6 call     0x1403f6d50
004257FB mov      rdx, qword ptr [rdi]
004257FE cmp      dword ptr [rdx + 0x48], 0xc
00425802 jne      0x14042581a
00425804 movsxd   rax, dword ptr [rdi + 8]
00425808 lea      rcx, [rax + rax*2]
0042580C mov      rax, qword ptr [rdx + 0x40]
00425810 mov      edi, dword ptr [rax + rcx*4 + 4]
00425814 mov      esi, dword ptr [rax + rcx*4 + 8]
00425818 jmp      0x14042581e
0042581A xor      edi, edi
0042581C mov      esi, edi
0042581E mov      qword ptr [rsp + 0x28], r14
00425823 test     ebx, ebx
00425825 je       0x14042583a
00425827 cmp      ebx, -1
0042582A je       0x140425833
0042582C mov      ecx, ebx
0042582E call     0x140413140
00425833 mov      r14d, dword ptr [rsp + 0x68]
00425838 jmp      0x140425851
0042583A mov      ecx, 0xde1
0042583F call     0x140413290
00425844 mov      ecx, 0xff000000
00425849 call     0x140413200
0042584E mov      r14d, eax
00425851 call     0x140413450
00425856 mov      ecx, dword ptr [rsp + 0x78]
0042585A mov      eax, 8
0042585F mov      rdx, qword ptr [rip + 0x241cfa]
00425866 shr      ecx, 0x13
00425869 and      ecx, 1
0042586C cmp      dword ptr [rdx + 0x1dc], 0
00425873 cmovne   ecx, eax
00425876 call     0x140413220
0042587B mov      ecx, 2
00425880 call     0x1404130b0
00425885 test     ebx, ebx
00425887 je       0x140425892
00425889 mov      edx, esi
0042588B mov      ecx, edi
0042588D call     0x140413580
00425892 mov      ebp, dword ptr [rsp + 0x70]
00425896 mov      ecx, r13d
00425899 mov      edx, ebp
0042589B call     0x1404135a0
004258A0 lea      r12d, [rsi + 0x40]
004258A4 test     ebx, ebx
004258A6 je       0x1404258b2
004258A8 mov      edx, r12d
004258AB mov      ecx, edi
004258AD call     0x140413580
004258B2 lea      r15d, [rbp + 0x40]
004258B6 mov      ecx, r13d
004258B9 mov      edx, r15d
004258BC call     0x1404135a0
004258C1 lea      r13d, [rdi + 0x40]
004258C5 test     ebx, ebx
004258C7 je       0x1404258d3
004258C9 mov      edx, esi
004258CB mov      ecx, r13d
004258CE call     0x140413580
004258D3 mov      ecx, dword ptr [rsp + 0x68]
004258D7 mov      edx, ebp
004258D9 add      ecx, 0x40
004258DC call     0x1404135a0
004258E1 test     ebx, ebx
004258E3 je       0x1404258ef
004258E5 mov      edx, esi
004258E7 mov      ecx, r13d
004258EA call     0x140413580
004258EF mov      edx, ebp
004258F1 mov      ebp, dword ptr [rsp + 0x68]
004258F5 lea      esi, [rbp + 0x40]
004258F8 mov      ecx, esi
004258FA call     0x1404135a0
004258FF test     ebx, ebx
00425901 je       0x14042590d
00425903 mov      edx, r12d
00425906 mov      ecx, edi
00425908 call     0x140413580
0042590D mov      edx, r15d
00425910 mov      ecx, ebp
00425912 call     0x1404135a0
00425917 mov      rdi, qword ptr [rsp + 0x40]
0042591C mov      rbp, qword ptr [rsp + 0x58]
00425921 test     ebx, ebx
00425923 je       0x140425930
00425925 mov      edx, r12d
00425928 mov      ecx, r13d
0042592B call     0x140413580
00425930 mov      edx, r15d
00425933 mov      ecx, esi
00425935 call     0x1404135a0
0042593A call     0x1404132d0
0042593F mov      r15, qword ptr [rsp + 0x20]
00425944 test     ebx, ebx
00425946 mov      rbx, qword ptr [rsp + 0x50]
0042594B mov      r13, qword ptr [rsp + 0x30]
00425950 mov      r12, qword ptr [rsp + 0x38]
00425955 mov      rsi, qword ptr [rsp + 0x60]
0042595A jne      0x140425964
0042595C mov      ecx, r14d
0042595F call     0x140413200
00425964 mov      r14, qword ptr [rsp + 0x28]
00425969 add      rsp, 0x48
