00233F20  mov      r11, rsp
00233F23  push     rbp
00233F24  push     r12
00233F26  push     r14
00233F28  lea      rbp, [r11 - 0x5f]
00233F2C  sub      rsp, 0xc0
00233F33  mov      rax, qword ptr [rip + 0x430a9e]
00233F3A  xor      rax, rsp
00233F3D  mov      qword ptr [rbp + 0x17], rax
00233F41  cmp      qword ptr [rcx + 0x18], 0
00233F46  mov      r12, r8
00233F49  mov      r14, rcx
00233F4C  je       0x140234505
00233F52  movzx    edx, byte ptr [rip + 0x38c726]
00233F59  mov      qword ptr [r11 + 0x10], rbx
00233F5D  mov      eax, edx
00233F5F  shl      eax, 0x10
00233F62  mov      ebx, edx
00233F64  shl      ebx, 8
00233F67  or       ebx, eax
00233F69  mov      qword ptr [r11 - 0x28], rdi
00233F6D  mov      rax, qword ptr [rcx]
00233F70  or       ebx, edx
00233F72  mov      qword ptr [r11 - 0x30], r13
00233F76  xor      r13d, r13d
00233F79  mov      qword ptr [rbp + 7], r13
00233F7D  call     qword ptr [rax + 0xf8]
00233F83  mov      edi, eax
00233F85  cmp      dword ptr [r14 + 0x21c], r13d
00233F8C  je       0x1402344ed
00233F92  movzx    ecx, byte ptr [rip + 0x36ac52]
00233F99  mov      eax, dword ptr [r14 + 0x10]
00233F9D  mov      r9, qword ptr [r14 + 0x18]
00233FA1  cdq      
00233FA2  mov      r10d, dword ptr [r14 + 0xc]
00233FA6  idiv     ecx
00233FA8  mov      qword ptr [rsp + 0xb8], rsi
00233FB0  lea      rsi, [r14 + 0xc]
00233FB4  movsx    ecx, word ptr [r9 + 0xbbc]
00233FBC  movsx    r8d, ax
00233FC0  mov      eax, r10d
00233FC3  imul     r8d, ecx
00233FC7  cdq      
00233FC8  movzx    ecx, byte ptr [rip + 0x36ac1b]
00233FCF  idiv     ecx
00233FD1  add      r8w, ax
00233FD5  movsx    rcx, r8w
00233FD9  test     ecx, ecx
00233FDB  js       0x1402344e5
00233FE1  cmp      ecx, dword ptr [r9 + 0xbb8]
00233FE8  jge      0x1402344e5
00233FEE  mov      rax, qword ptr [r9 + 0xbb0]
00233FF5  movzx    ecx, word ptr [rax + rcx*2]
00233FF9  test     word ptr [rip + 0x36abe8], cx
00234000  je       0x1402344e5
00234006  movzx    ecx, byte ptr [rip + 0x366ff3]
0023400D  lea      r8, [r14 + 0x100]
00234014  mov      eax, r10d
00234017  mov      dword ptr [rsp + 0x20], 1
0023401F  cdq      
00234020  idiv     ecx
00234022  movzx    ecx, byte ptr [rip + 0x366fd8]
00234029  mov      dword ptr [rbp - 0x29], eax
0023402C  mov      eax, dword ptr [r14 + 0x10]
00234030  cdq      
00234031  idiv     ecx
00234033  lea      rcx, [r9 + 0xa60]
0023403A  mov      r9b, 1
0023403D  lea      rdx, [rbp - 0x29]
00234041  mov      dword ptr [rbp - 0x25], eax
00234044  call     0x14024c9d0
00234049  cmp      al, byte ptr [rip + 0x366fb3]
0023404F  je       0x1402344e5
00234055  mov      qword ptr [rsp + 0xa0], r15
0023405D  cmp      dword ptr [r14 + 0x1f8], r13d
00234064  je       0x14023406a
00234066  bts      edi, 0x10
0023406A  mov      r15d, edi
0023406D  or       r15d, 4
00234071  cmp      dword ptr [r14 + 0x210], r13d
00234078  cmove    r15d, edi
0023407C  cmp      word ptr [r14 + 0x214], 1
00234085  jle      0x140234091
00234087  xor      edx, edx
00234089  mov      rcx, r14
0023408C  call     0x140235df0
00234091  mov      rax, qword ptr [r14 + 0x18]
00234095  mov      r9d, dword ptr [r14 + 0x14]
00234099  mov      qword ptr [rsp + 0x20], r13
0023409E  mov      edx, dword ptr [rax + 0x688]
002340A4  mov      r8d, dword ptr [rax + 0x68c]
002340AB  mov      ecx, dword ptr [rax + 0x648]
002340B1  sub      ecx, dword ptr [rax + 0x640]
002340B7  add      ecx, edx
002340B9  mov      dword ptr [rbp - 0x1d], edx
002340BC  mov      dword ptr [rbp - 0x21], ecx
002340BF  lea      rdx, [rbp - 9]
002340C3  mov      ecx, dword ptr [rax + 0x64c]
002340C9  sub      ecx, dword ptr [rax + 0x644]
002340CF  add      ecx, r8d
002340D2  mov      dword ptr [rbp - 0x29], r8d
002340D6  mov      dword ptr [rbp - 0x19], ecx
002340D9  lea      r8, [rbp - 0x39]
002340DD  mov      rcx, r14
002340E0  call     0x14022b7b0
002340E5  mov      edi, dword ptr [r14 + 0x14]
002340E9  lea      rdx, [rbp - 0x11]
002340ED  mov      rcx, r12
002340F0  call     0x14041d9c0
002340F5  mov      r9d, dword ptr [rbp + 3]
002340F9  mov      r12d, edi
002340FC  mov      eax, dword ptr [rbp - 0xd]
002340FF  cmp      r9d, eax
00234102  jl       0x140234131
00234104  sub      r9d, eax
00234107  mov      qword ptr [rsp + 0x20], r13
0023410C  lea      r8, [rbp - 0x39]
00234110  mov      rcx, r14
00234113  lea      rdx, [rbp - 9]
00234117  lea      eax, [r9 + 1]
0023411B  cmp      eax, edi
0023411D  cmovge   eax, edi
00234120  sub      edi, eax
00234122  mov      r9d, edi
00234125  call     0x14022b7b0
0023412A  mov      r9d, dword ptr [rbp + 3]
0023412E  mov      r12d, edi
00234131  mov      ecx, dword ptr [rsi]
00234133  mov      dword ptr [rbp - 0x31], ecx
00234136  cmp      dword ptr [r14 + 0x200], r13d
0023413D  jne      0x140234154
0023413F  cmp      dword ptr [r14 + 0x210], r13d
00234146  jne      0x140234154
00234148  mov      edx, dword ptr [r14 + 0x10]
0023414C  sub      edx, r12d
0023414F  mov      r12d, r13d
00234152  jmp      0x140234158
00234154  mov      edx, dword ptr [r14 + 0x10]
00234158  mov      dword ptr [rbp - 0x2d], edx
0023415B  cmp      dword ptr [r14 + 0x1fc], r13d
00234162  je       0x140234184
00234164  movzx    r8d, byte ptr [r14 + 0x28]
00234169  mov      rdx, rsi
0023416C  mov      rcx, qword ptr [r14 + 0x18]
00234170  call     0x140180c10
00234175  mov      edx, dword ptr [rbp - 0x2d]
00234178  mov      r9d, dword ptr [rbp + 3]
0023417C  add      edx, eax
0023417E  mov      ecx, dword ptr [rbp - 0x31]
00234181  mov      dword ptr [rbp - 0x2d], edx
00234184  movsx    r10d, word ptr [r14 + 0x216]
0023418C  movzx    eax, byte ptr [rip + 0x378d00]
00234193  mov      r11d, dword ptr [rbp - 1]
00234197  cmp      r10d, eax
0023419A  jle      0x1402341ac
0023419C  mov      r8d, dword ptr [rbp - 9]
002341A0  sub      r8d, r11d
002341A3  add      r8d, dword ptr [rbp - 0x39]
002341A7  add      r8d, ecx
002341AA  jmp      0x1402341b3
002341AC  mov      r8d, ecx
002341AF  sub      r8d, dword ptr [rbp - 0x39]
002341B3  cmp      word ptr [r14 + 0x214], 5
002341BC  mov      ecx, dword ptr [rbp - 5]
002341BF  movzx    esi, byte ptr [rip + 0x378cc9]
002341C6  movzx    r13d, byte ptr [rip + 0x378cc9]
002341CE  mov      dword ptr [rbp + 7], r8d
002341D2  jne      0x14023421d
002341D4  movzx    eax, sil
002341D8  cmp      r10d, eax
002341DB  jle      0x14023421d
002341DD  movzx    eax, r13b
002341E1  cmp      r10d, eax
002341E4  jge      0x14023421d
002341E6  cmp      dword ptr [r14 + 0x200], 0
002341EE  jne      0x140234207
002341F0  cmp      dword ptr [r14 + 0x210], 0
002341F8  jne      0x140234207
002341FA  sub      ecx, r9d
002341FD  add      ecx, dword ptr [rbp - 0x35]
00234200  add      ecx, edx
00234202  neg      r12d
00234205  jmp      0x140234222
00234207  mov      eax, r9d
0023420A  sub      eax, ecx
0023420C  mov      ecx, edx
0023420E  sub      eax, dword ptr [rbp - 0x35]
00234211  sub      ecx, eax
00234213  mov      dword ptr [rbp - 0x35], eax
00234216  sub      ecx, edi
00234218  neg      r12d
0023421B  jmp      0x140234222
0023421D  mov      ecx, edx
0023421F  sub      ecx, dword ptr [rbp - 0x35]
00234222  sub      r11d, dword ptr [rbp - 9]
00234226  mov      r10d, ecx
00234229  sub      r10d, dword ptr [rbp - 5]
0023422D  add      r10d, r9d
00234230  mov      dword ptr [rbp + 0xb], ecx
00234233  mov      dword ptr [rbp + 0x13], r10d
00234237  lea      edx, [r11 + r8]
0023423B  mov      dword ptr [rbp + 0xf], edx
0023423E  cmp      r8d, dword ptr [rbp - 0x21]
00234242  jge      0x1402344dd
00234248  cmp      edx, dword ptr [rbp - 0x1d]
0023424B  jl       0x1402344dd
00234251  cmp      ecx, dword ptr [rbp - 0x19]
00234254  jge      0x1402344dd
0023425A  cmp      r10d, dword ptr [rbp - 0x29]
0023425E  jl       0x1402344dd
00234264  cmp      dword ptr [r14 + 0x1f8], 0
0023426C  jne      0x140234278
0023426E  cmp      dword ptr [r14 + 0x200], 0
00234276  je       0x14023429b
00234278  movzx    r8d, byte ptr [r14 + 0x28]
0023427D  lea      rdx, [rbp - 0x31]
00234281  mov      rcx, qword ptr [r14 + 0x18]
00234285  call     0x140182ed0
0023428A  movzx    esi, byte ptr [rip + 0x378bfe]
00234291  mov      ebx, eax
00234293  movzx    r13d, byte ptr [rip + 0x378bfc]
0023429B  movsx    edx, word ptr [r14 + 0x216]
002342A3  movzx    ecx, byte ptr [rip + 0x378be9]
002342AA  cmp      edx, ecx
002342AC  jle      0x1402342b5
002342AE  or       r15d, dword ptr [rip + 0x36e097]
002342B5  cmp      word ptr [r14 + 0x214], 5
002342BE  jne      0x1402342d7
002342C0  movzx    eax, sil
002342C4  cmp      edx, eax
002342C6  jle      0x1402342d7
002342C8  movzx    eax, r13b
002342CC  cmp      edx, eax
002342CE  jge      0x1402342d7
002342D0  or       r15d, dword ptr [rip + 0x36e079]
002342D7  mov      rcx, qword ptr [r14 + 0x18]
002342DB  add      rcx, 0x5c8
002342E2  cmp      dword ptr [r14 + 0x200], 0
002342EA  je       0x140234333
002342EC  movzx    edx, byte ptr [r14 + 0x20c]
002342F4  lea      r9, [rbp - 0x39]
002342F8  mov      r8d, edx
002342FB  mov      dword ptr [rsp + 0x38], r15d
00234300  mov      eax, edx
00234302  shl      r8d, 8
00234306  shl      eax, 0x10
00234309  or       r8d, eax
0023430C  mov      dword ptr [rsp + 0x30], ebx
00234310  or       r8d, edx
00234313  lea      rax, [r14 + 0x204]
0023431A  mov      dword ptr [rsp + 0x28], r8d
0023431F  lea      rdx, [rbp - 9]
00234323  lea      r8, [rbp - 0x31]
00234327  mov      qword ptr [rsp + 0x20], rax
0023432C  call     0x1402a4090
00234331  jmp      0x14023436a
00234333  or       r15d, dword ptr [rip + 0x36e00a]
0023433A  lea      rax, [rbp - 0x39]
0023433E  mov      r8d, r15d
00234341  mov      qword ptr [rsp + 0x20], rax
00234346  lea      r9, [rbp - 0x31]
0023434A  lea      rdx, [rbp - 9]
0023434E  call     0x14029e1b0
00234353  mov      rcx, qword ptr [r14 + 0x18]
00234357  lea      rdx, [rbp - 9]
0023435B  add      rcx, 0x5c8
00234362  mov      r8d, r15d
00234365  call     0x14029e190
0023436A  test     eax, eax
0023436C  je       0x1402344dd
00234372  cmp      dword ptr [r14 + 0x1f8], 0
0023437A  je       0x14023438e
0023437C  mov      rcx, qword ptr [r14 + 0x1b8]
00234383  mov      edx, ebx
00234385  add      rcx, 8
00234389  call     0x140412690
0023438E  cmp      dword ptr [r14 + 0x210], 0
00234396  je       0x1402343c4
00234398  mov      rcx, qword ptr [r14 + 0x18]
0023439C  xor      r13d, r13d
0023439F  mov      r9d, dword ptr [rbp - 0x35]
002343A3  add      rcx, 0x5c8
002343AA  mov      r8d, dword ptr [rbp - 0x39]
002343AE  mov      rdx, qword ptr [r14 + 0x1c0]
002343B5  mov      dword ptr [rsp + 0x28], r13d
002343BA  mov      dword ptr [rsp + 0x20], r15d
002343BF  call     0x14029e260
002343C4  cmp      byte ptr [r14 + 0x340], 0
002343CC  je       0x14023441a
002343CE  mov      rcx, qword ptr [r14 + 0x320]
002343D5  mov      rsi, qword ptr [r14 + 0x18]
002343D9  call     0x1403f6d50
002343DE  mov      rbx, qword ptr [r14 + 0x320]
002343E5  mov      rcx, rbx
002343E8  call     0x1403f7890
002343ED  mov      rcx, rbx
002343F0  mov      edi, eax
002343F2  call     0x1403f78b0
002343F7  movzx    r9d, word ptr [rip + 0x38c279]
002343FF  mov      rdx, rax
00234402  mov      rcx, qword ptr [r14 + 0x1b8]
00234409  mov      r8d, edi
0023440C  call     0x1404123c0
00234411  lea      rcx, [rsi + 0x5c8]
00234418  jmp      0x140234425
0023441A  mov      rcx, qword ptr [r14 + 0x18]
0023441E  add      rcx, 0x5c8
00234425  mov      r9d, dword ptr [rbp - 0x35]
00234429  mov      r8d, dword ptr [rbp - 0x39]
0023442D  sub      r9d, r12d
00234430  mov      rdx, qword ptr [r14 + 0x1b8]
00234437  mov      dword ptr [rsp + 0x28], 0x80
0023443F  mov      dword ptr [rsp + 0x20], r15d
00234444  call     0x14029e260
00234449  movzx    eax, byte ptr [rip + 0x3652d9]
00234450  cmp      byte ptr [r14 + 0x62], al
00234454  je       0x14023448c
00234456  mov      rcx, qword ptr [r14 + 0x18]
0023445A  lea      rax, [rbp + 7]
0023445E  mov      r8d, dword ptr [rbp - 0x2d]
00234462  add      rcx, 0x5c8
00234469  mov      edx, dword ptr [rbp - 0x31]
0023446C  xor      r9d, r9d
0023446F  mov      dword ptr [rsp + 0x38], r15d
00234474  mov      byte ptr [rsp + 0x30], 0
00234479  mov      qword ptr [rsp + 0x28], rax
0023447E  lea      rax, [rbp - 0x39]
00234482  mov      qword ptr [rsp + 0x20], rax
00234487  call     0x14029e4c0
0023448C  mov      rcx, qword ptr [r14 + 0x18]
00234490  lea      r9, [rbp - 0x29]
00234494  add      rcx, 0x5c8
0023449B  mov      qword ptr [rbp - 0x29], 0
002344A3  xor      r8d, r8d
002344A6  mov      edx, r15d
002344A9  call     0x14029ea40
002344AE  mov      eax, dword ptr [rbp - 0x35]
002344B1  lea      rdx, [rbp - 9]
002344B5  mov      rcx, qword ptr [r14 + 0x18]
002344B9  mov      r9d, dword ptr [rbp - 0x2d]
002344BD  add      rcx, 0x5c8
002344C4  mov      r8d, dword ptr [rbp - 0x31]
002344C8  mov      dword ptr [rsp + 0x30], r15d
002344CD  mov      dword ptr [rsp + 0x28], eax
002344D1  mov      eax, dword ptr [rbp - 0x39]
002344D4  mov      dword ptr [rsp + 0x20], eax
002344D8  call     0x14029df60
002344DD  mov      r15, qword ptr [rsp + 0xa0]
002344E5  mov      rsi, qword ptr [rsp + 0xb8]
002344ED  mov      rdi, qword ptr [rsp + 0xb0]
002344F5  mov      rbx, qword ptr [rsp + 0xe8]
002344FD  mov      r13, qword ptr [rsp + 0xa8]
00234505  mov      rcx, qword ptr [rbp + 0x17]
00234509  xor      rcx, rsp
0023450C  call     0x1404f77a0
00234511  add      rsp, 0xc0
00234518  pop      r14
0023451A  pop      r12
0023451C  pop      rbp
0023451D  ret      
0023451E  int3     
0023451F  int3     
00234520  mov      r11, rsp
00234523  push     rbp
00234524  push     rbx
00234525  lea      rbp, [r11 - 0x5f]
00234529  sub      rsp, 0xc8
00234530  mov      rax, qword ptr [rip + 0x4304a1]
00234537  xor      rax, rsp
0023453A  mov      qword ptr [rbp + 0x27], rax
0023453E  mov      r9, qword ptr [rcx + 0x18]
00234542  mov      rbx, rcx
00234545  test     r9, r9
00234548  je       0x140234a06
0023454E  mov      qword ptr [r11 + 0x10], rsi
00234552  lea      rax, [r9 + 0x5c8]
00234559  mov      qword ptr [r11 + 0x20], r12
0023455D  mov      qword ptr [r11 - 0x20], r14
00234561  mov      qword ptr [r11 - 0x28], r15
00234565  mov      r15d, dword ptr [rcx + 0x118]
0023456C  movsx    ecx, word ptr [rcx + 0x216]
00234573  mov      qword ptr [rbp - 1], rax
00234577  movzx    eax, byte ptr [rip + 0x378915]
0023457E  cmp      ecx, eax
00234580  jle      0x140234589
00234582  or       r15d, dword ptr [rip + 0x36ddc3]
00234589  cmp      word ptr [rbx + 0x214], 5
00234591  jne      0x1402345b0
00234593  movzx    eax, byte ptr [rip + 0x3788f5]
0023459A  cmp      ecx, eax
0023459C  jle      0x1402345b0
0023459E  movzx    eax, byte ptr [rip + 0x3788f2]
002345A5  cmp      ecx, eax
002345A7  jge      0x1402345b0
002345A9  or       r15d, dword ptr [rip + 0x36dda0]
002345B0  mov      eax, dword ptr [r9 + 0x688]
002345B7  mov      ecx, dword ptr [r9 + 0x68c]
002345BE  mov      edx, dword ptr [r9 + 0x648]
002345C5  sub      edx, dword ptr [r9 + 0x640]
002345CC  movzx    r8d, byte ptr [rbx + 0x28]
002345D1  add      edx, eax
002345D3  mov      dword ptr [rbp - 0x1d], eax
002345D6  mov      eax, dword ptr [r9 + 0x64c]
002345DD  sub      eax, dword ptr [r9 + 0x644]
002345E4  add      eax, ecx
002345E6  mov      dword ptr [rbp - 0x15], ecx
002345E9  mov      dword ptr [rbp - 0x19], eax
002345EC  mov      rcx, r9
002345EF  mov      eax, dword ptr [rbx + 0xc]
002345F2  mov      dword ptr [rbp - 0x21], edx
002345F5  lea      rdx, [rbx + 0xc]
002345F9  mov      dword ptr [rbp - 0x39], eax
002345FC  call     0x140180c10
00234601  mov      ecx, dword ptr [rbx + 0x10]
00234604  lea      rdx, [rbp - 0x29]
00234608  sub      ecx, dword ptr [rbx + 0x14]
0023460B  add      eax, ecx
0023460D  mov      rcx, qword ptr [rbx + 0x1b8]
00234614  mov      dword ptr [rbp - 0x35], eax
00234617  call     0x140411660
0023461C  mov      rcx, qword ptr [rbx + 0x1b8]
00234623  lea      rdx, [rbp - 0x11]
00234627  call     0x140411780
0023462C  mov      r11d, dword ptr [rbp - 0x11]
00234630  xor      r14d, r14d
00234633  mov      r10d, dword ptr [rbp - 0xd]
00234637  xor      esi, esi
00234639  xor      r12b, r12b
0023463C  mov      qword ptr [rbp + 7], r14
00234640  mov      dword ptr [rbp + 0xf], r11d
00234644  mov      dword ptr [rbp + 0x13], r10d
00234648  cmp      byte ptr [rbx + 0x3b8], sil
0023464F  jbe      0x1402349e6
00234655  mov      r9d, dword ptr [rbp - 0x35]
00234659  mov      qword ptr [rsp + 0xf0], rdi
00234661  mov      qword ptr [rsp + 0xc0], r13
00234669  nop      dword ptr [rax]
