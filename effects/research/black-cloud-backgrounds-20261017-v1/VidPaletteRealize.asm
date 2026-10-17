00421430  movzx    r10d, word ptr [rcx + 0x20]
00421435  test     r10d, r10d
00421438  je       0x140421445
0042143A  cmp      r10d, 1
0042143E  jne      0x14042144a
00421440  jmp      0x14042d2f0
00421445  jmp      0x14042d350
0042144A  ret      
0042144B  int3     
0042144C  int3     
0042144D  int3     
0042144E  int3     
0042144F  int3     
00421450  mov      qword ptr [rsp + 0x18], rbx
00421455  push     rbp
00421456  push     rsi
00421457  push     rdi
00421458  push     r12
0042145A  push     r13
0042145C  push     r14
0042145E  push     r15
00421460  lea      rbp, [rsp - 0x40]
00421465  sub      rsp, 0x140
0042146C  mov      rax, qword ptr [rip + 0x243565]
00421473  xor      rax, rsp
00421476  mov      qword ptr [rbp + 0x30], rax
0042147A  mov      rax, qword ptr [rip + 0x2460df]
00421481  mov      ebx, r8d
00421484  mov      r15, rcx
00421487  mov      qword ptr [rsp + 0x70], rcx
0042148C  mov      ecx, 0x400
00421491  mov      qword ptr [rbp - 0x28], r9
00421495  mov      r13, r9
00421498  mov      dword ptr [rbp - 0x7c], ebx
0042149B  mov      rsi, qword ptr [rax + 0x210]
004214A2  mov      qword ptr [rbp - 0x30], rsi
004214A6  mov      qword ptr [rbp - 0x48], rdx
004214AA  call     0x1404f77c4
004214AF  xor      edx, edx
004214B1  mov      qword ptr [rbp - 0x58], rax
004214B5  mov      r8d, 0x400
004214BB  mov      rcx, rax
004214BE  mov      rdi, rax
004214C1  call     0x1404fab70
004214C6  mov      word ptr [rdi + 1], 0xff
004214CC  xor      r12d, r12d
004214CF  mov      byte ptr [rdi], 0
004214D2  mov      word ptr [rdi + 5], 0
004214D8  mov      byte ptr [rdi + 4], 0
004214DC  mov      word ptr [rdi + 9], 0
004214E2  mov      byte ptr [rdi + 8], 0
004214E6  mov      word ptr [rdi + 0xd], 0
004214EC  mov      byte ptr [rdi + 0xc], 0
004214F0  mov      rdx, qword ptr [r15 + 8]
004214F4  mov      qword ptr [rbp - 0x60], r12
004214F8  mov      word ptr [rbp - 0x68], r12w
004214FD  test     rdx, rdx
00421500  jne      0x140421519
00421502  call     0x14050933c
00421507  and      eax, 0x7fff
0042150C  imul     edx, eax, 0x7fff
00421512  sar      edx, 0xf
00421515  mov      qword ptr [r15 + 8], rdx
00421519  mov      rax, qword ptr [rip + 0x246040]
00421520  movsxd   rcx, dword ptr [rax + 0xfa0]
00421527  add      rcx, rdx
0042152A  mov      qword ptr [r15], rcx
0042152D  mov      rax, qword ptr [rip + 0x24602c]
00421534  mov      rcx, qword ptr [rax + 0x210]
0042153B  call     0x14041d9e0
00421540  mov      ecx, ebx
00421542  mov      r11d, 0x10
00421548  and      ecx, 0x10000
0042154E  mov      dword ptr [rsp + 0x48], r11d
00421553  mov      r14d, 0xff
00421559  bt       ebx, 0x11
0042155D  jae      0x1404215f1
00421563  movzx    edx, byte ptr [r13]
00421568  movzx    r8d, byte ptr [r13 + 1]
0042156D  movzx    r9d, byte ptr [r13 + 2]
00421572  test     ecx, ecx
00421574  je       0x1404215c1
00421576  movzx    ecx, ax
00421579  lea      edi, [r11 - 0xf]
0042157D  shr      ecx, 8
00421580  imul     ecx, r8d
00421584  movzx    r10d, al
00421588  imul     r10d, edx
0042158C  shr      eax, 0x10
0042158F  mov      dword ptr [rsp + 0x40], r11d
00421594  mov      dword ptr [rsp + 0x38], ecx
00421598  mov      dword ptr [rbp + 0x14], ecx
0042159B  movzx    ecx, al
0042159E  imul     ecx, r9d
004215A2  mov      dword ptr [rsp + 0x34], r10d
004215A7  mov      dword ptr [rbp + 0x10], r10d
004215AB  mov      byte ptr [rsp + 0x2c], 1
004215B0  mov      dword ptr [rsp + 0x3c], ecx
004215B4  mov      dword ptr [rbp + 0x18], ecx
004215B7  mov      ecx, 0xfe01
004215BC  jmp      0x140421653
004215C1  mov      dword ptr [rsp + 0x34], edx
004215C5  mov      ecx, r14d
004215C8  mov      dword ptr [rbp + 0x10], edx
004215CB  mov      edi, 1
004215D0  mov      dword ptr [rsp + 0x38], r8d
004215D5  mov      dword ptr [rbp + 0x14], r8d
004215D9  mov      dword ptr [rsp + 0x3c], r9d
004215DE  mov      dword ptr [rbp + 0x18], r9d
004215E2  mov      dword ptr [rsp + 0x40], 8
004215EA  mov      byte ptr [rsp + 0x2c], 1
004215EF  jmp      0x140421653
004215F1  mov      edi, 1
004215F6  test     ecx, ecx
004215F8  je       0x140421630
004215FA  movzx    edx, al
004215FD  mov      ecx, r14d
00421600  mov      dword ptr [rsp + 0x34], edx
00421604  mov      dword ptr [rbp + 0x10], edx
00421607  movzx    edx, ax
0042160A  shr      edx, 8
0042160D  shr      eax, 0x10
00421610  mov      dword ptr [rsp + 0x38], edx
00421614  mov      dword ptr [rbp + 0x14], edx
00421617  movzx    edx, al
0042161A  mov      dword ptr [rsp + 0x3c], edx
0042161E  mov      dword ptr [rbp + 0x18], edx
00421621  mov      dword ptr [rsp + 0x40], 8
00421629  mov      byte ptr [rsp + 0x2c], dil
0042162E  jmp      0x140421653
00421630  mov      edx, edi
00421632  mov      dword ptr [rsp + 0x38], edi
00421636  mov      dword ptr [rsp + 0x34], edx
0042163A  mov      ecx, edi
0042163C  mov      dword ptr [rbp + 0x10], edx
0042163F  mov      dword ptr [rbp + 0x14], edi
00421642  mov      dword ptr [rsp + 0x3c], edi
00421646  mov      dword ptr [rbp + 0x18], edi
00421649  mov      dword ptr [rsp + 0x40], r12d
0042164E  mov      byte ptr [rsp + 0x2c], r12b
00421653  mov      rax, qword ptr [rip + 0x245f06]
0042165A  mov      dword ptr [rsp + 0x30], ecx
0042165E  mov      r10, qword ptr [rax + 0x210]
00421665  movzx    ecx, byte ptr [r10 + 0x180]
0042166D  bt       ebx, 0x12
00421671  jae      0x1404216db
00421673  movzx    eax, byte ptr [r13 + 4]
00421678  not      al
0042167A  movzx    edx, al
0042167D  movzx    eax, byte ptr [r13 + 5]
00421682  not      al
00421684  movzx    r8d, al
00421688  movzx    eax, byte ptr [r13 + 6]
0042168D  not      al
0042168F  movzx    r9d, al
00421693  test     cl, cl
00421695  je       0x1404216be
00421697  not      cl
00421699  mov      byte ptr [rsp + 0x2d], 1
0042169E  movzx    ecx, cl
004216A1  mov      eax, ecx
004216A3  imul     eax, edx
004216A6  mov      dword ptr [rsp + 0x44], eax
004216AA  mov      eax, ecx
004216AC  imul     eax, r8d
004216B0  imul     ecx, r9d
004216B4  mov      dword ptr [rsp + 0x4c], eax
004216B8  mov      dword ptr [rsp + 0x50], ecx
004216BC  jmp      0x140421715
004216BE  mov      dword ptr [rsp + 0x44], edx
004216C2  mov      dword ptr [rsp + 0x4c], r8d
004216C7  mov      dword ptr [rsp + 0x50], r9d
004216CC  mov      dword ptr [rsp + 0x48], 8
004216D4  mov      byte ptr [rsp + 0x2d], 1
004216D9  jmp      0x140421715
004216DB  test     cl, cl
004216DD  je       0x1404216ff
004216DF  not      cl
004216E1  mov      dword ptr [rsp + 0x48], 8
004216E9  movzx    ecx, cl
004216EC  mov      dword ptr [rsp + 0x44], ecx
004216F0  mov      dword ptr [rsp + 0x4c], ecx
004216F4  mov      dword ptr [rsp + 0x50], ecx
004216F8  mov      byte ptr [rsp + 0x2d], 1
004216FD  jmp      0x140421715
004216FF  mov      dword ptr [rsp + 0x44], edi
00421703  mov      dword ptr [rsp + 0x4c], edi
00421707  mov      dword ptr [rsp + 0x50], edi
0042170B  mov      dword ptr [rsp + 0x48], r12d
00421710  mov      byte ptr [rsp + 0x2d], r12b
00421715  movzx    eax, byte ptr [r10 + 0x181]
0042171D  bt       ebx, 0x15
00421721  jae      0x14042175d
00421723  movzx    ecx, byte ptr [r13 + 8]
00421728  movzx    edx, byte ptr [r13 + 9]
0042172D  movzx    r8d, byte ptr [r13 + 0xa]
00421732  test     al, al
00421734  je       0x140421740
00421736  movzx    eax, al
00421739  add      ecx, eax
0042173B  add      edx, eax
0042173D  add      r8d, eax
00421740  lea      eax, [rcx + 8]
00421743  mov      byte ptr [rsp + 0x20], 1
00421748  mov      dword ptr [rsp + 0x60], eax
0042174C  lea      ecx, [rdx + 8]
0042174F  lea      eax, [r8 + 8]
00421753  mov      dword ptr [rsp + 0x64], ecx
00421757  mov      dword ptr [rsp + 0x68], eax
0042175B  jmp      0x140421797
0042175D  test     al, al
0042175F  je       0x14042177a
00421761  movzx    eax, al
00421764  add      eax, 8
00421767  mov      byte ptr [rsp + 0x20], 1
0042176C  mov      dword ptr [rsp + 0x60], eax
00421770  mov      dword ptr [rsp + 0x64], eax
00421774  mov      dword ptr [rsp + 0x68], eax
00421778  jmp      0x140421797
0042177A  mov      dword ptr [rsp + 0x60], 8
00421782  mov      dword ptr [rsp + 0x64], 8
0042178A  mov      dword ptr [rsp + 0x68], 8
00421792  mov      byte ptr [rsp + 0x20], r12b
00421797  test     bl, 1
0042179A  je       0x1404217a6
0042179C  mov      rax, qword ptr [rbp - 0x48]
004217A0  mov      byte ptr [rax + 3], r12b
004217A4  jmp      0x1404217a9
004217A6  mov      edi, r12d
004217A9  mov      ebx, edi
004217AB  nop      dword ptr [rax + rax]
004217B0  cmp      rbx, 1
004217B4  jne      0x1404217ef
004217B6  xor      edx, edx
004217B8  mov      rcx, rsi
004217BB  call     0x14041d130
004217C0  mov      ecx, dword ptr [rsi + 0x194]
004217C6  movzx    r8d, ax
004217CA  shr      r8d, 8
004217CE  shl      r8d, cl
004217D1  mov      ecx, eax
004217D3  shr      ecx, 0x10
004217D6  movzx    edx, cl
004217D9  mov      ecx, dword ptr [rsi + 0x198]
004217DF  shl      edx, cl
004217E1  mov      ecx, dword ptr [rsi + 0x190]
004217E7  or       r8d, edx
004217EA  movzx    eax, al
004217ED  jmp      0x14042181d
004217EF  mov      rax, qword ptr [r15 + 0x10]
004217F3  mov      ecx, dword ptr [rsi + 0x194]
004217F9  lea      rdx, [rax + rbx*4]
004217FD  movzx    r8d, byte ptr [rdx + 1]
00421802  movzx    eax, byte ptr [rdx + 2]
00421806  shl      r8d, cl
00421809  mov      ecx, dword ptr [rsi + 0x190]
0042180F  shl      eax, cl
00421811  mov      ecx, dword ptr [rsi + 0x198]
00421817  or       r8d, eax
0042181A  movzx    eax, byte ptr [rdx]
0042181D  shl      eax, cl
0042181F  inc      edi
00421821  or       r8d, eax
00421824  mov      rax, qword ptr [rbp - 0x48]
00421828  or       r8d, dword ptr [rbp + 0xa0]
0042182F  mov      dword ptr [rax + rbx*4], r8d
00421833  inc      rbx
00421836  cmp      rbx, 4
0042183A  jl       0x1404217b0
00421840  mov      ecx, dword ptr [rbp - 0x7c]
00421843  lea      r15, [r13 + 0x50]
00421847  and      ecx, 0x80000
0042184D  movsxd   rbx, edi
00421850  mov      dword ptr [rbp - 0x4c], ecx
00421853  movzx    eax, r12w
00421857  mov      ecx, dword ptr [rbp - 0x7c]
0042185A  mov      rdi, r12
0042185D  and      ecx, 0x2000000
00421863  mov      word ptr [rsp + 0x2e], ax
00421868  mov      dword ptr [rbp - 0x50], ecx
0042186B  movzx    ecx, byte ptr [rsp + 0x20]
00421870  mov      dword ptr [rsp + 0x54], ecx
00421874  movzx    ecx, byte ptr [rsp + 0x20]
00421879  mov      dword ptr [rsp + 0x58], ecx
0042187D  movzx    ecx, byte ptr [rsp + 0x20]
00421882  mov      dword ptr [rsp + 0x5c], ecx
00421886  mov      qword ptr [rbp - 0x40], rbx
0042188A  mov      qword ptr [rbp - 0x38], r12
0042188E  jmp      0x140421896
00421890  mov      r14d, 0xff
00421896  mov      r9, qword ptr [r15 - 0x40]
0042189A  test     r9, r9
0042189D  je       0x140421956
004218A3  movzx    r10d, byte ptr [rdi + r13 + 0x48]
004218A9  cmp      r10b, 1
004218AD  je       0x14042193f
004218B3  movzx    ecx, al
004218B6  movzx    r11d, r10b
004218BA  mov      eax, 1
004218BF  xor      edx, edx
004218C1  shl      eax, cl
004218C3  mov      rcx, qword ptr [rsp + 0x70]
004218C8  cdqe     
004218CA  lea      r8d, [r11 + r11]
004218CE  add      rax, qword ptr [rcx]
004218D1  div      r8
004218D4  movzx    eax, r10b
004218D8  cmp      dx, ax
004218DB  jbe      0x1404218e6
004218DD  add      ax, ax
004218E0  sub      ax, dx
004218E3  movzx    edx, ax
004218E6  movzx    ecx, byte ptr [r9]
004218EA  mov      eax, r14d
004218ED  sub      eax, ecx
004218EF  movzx    r8d, dx
004218F3  movzx    ecx, byte ptr [r9 + 1]
004218F8  mov      r10d, r14d
004218FB  imul     eax, r8d
004218FF  cdq      
00421900  idiv     r11d
00421903  sub      r10d, eax
00421906  mov      eax, r14d
00421909  sub      eax, ecx
0042190B  mov      dword ptr [rbp - 0x78], r10d
0042190F  movzx    ecx, byte ptr [r9 + 2]
00421914  mov      r10d, r14d
00421917  imul     eax, r8d
0042191B  cdq      
0042191C  idiv     r11d
0042191F  sub      r10d, eax
00421922  mov      eax, r14d
00421925  sub      eax, ecx
00421927  mov      dword ptr [rbp - 0x74], r10d
0042192B  imul     eax, r8d
0042192F  mov      ecx, r14d
00421932  cdq      
00421933  idiv     r11d
00421936  sub      ecx, eax
00421938  movzx    eax, word ptr [rsp + 0x2e]
0042193D  jmp      0x140421953
0042193F  movzx    ecx, byte ptr [r9]
00421943  mov      dword ptr [rbp - 0x78], ecx
00421946  movzx    ecx, byte ptr [r9 + 1]
0042194B  mov      dword ptr [rbp - 0x74], ecx
0042194E  movzx    ecx, byte ptr [r9 + 2]
00421953  mov      dword ptr [rbp - 0x70], ecx
00421956  mov      r9, qword ptr [r15]
00421959  mov      r14, qword ptr [rsp + 0x70]
0042195E  test     r9, r9
00421961  je       0x140421a25
00421967  movzx    r10d, byte ptr [rdi + r13 + 0x88]
00421970  cmp      r10b, 2
00421974  jb       0x1404219fd
0042197A  movzx    ecx, al
0042197D  movzx    r11d, r10b
00421981  mov      eax, 1
00421986  xor      edx, edx
00421988  shl      eax, cl
0042198A  cdqe     
0042198C  add      rax, qword ptr [r14]
0042198F  lea      r8d, [r11 + r11]
00421993  div      r8
00421996  movzx    eax, r10b
0042199A  movzx    r12d, dx
0042199E  mov      qword ptr [rbp - 0x60], r12
004219A2  cmp      dx, ax
004219A5  jbe      0x1404219b5
004219A7  add      ax, ax
004219AA  sub      ax, dx
004219AD  movzx    r12d, ax
004219B1  mov      qword ptr [rbp - 0x60], r12
004219B5  movzx    eax, byte ptr [r9]
004219B9  xor      edx, edx
004219BB  movzx    ecx, r12w
004219BF  imul     eax, ecx
004219C2  div      r11d
004219C5  xor      edx, edx
004219C7  mov      r8d, eax
004219CA  movzx    eax, byte ptr [r9 + 1]
004219CF  imul     eax, ecx
004219D2  not      r8b
004219D5  mov      dword ptr [rsp + 0x54], r8d
004219DA  div      r11d
004219DD  xor      edx, edx
004219DF  mov      r8d, eax
004219E2  movzx    eax, byte ptr [r9 + 2]
004219E7  imul     eax, ecx
004219EA  not      r8b
004219ED  mov      dword ptr [rsp + 0x58], r8d
004219F2  div      r11d
004219F5  not      al
004219F7  mov      dword ptr [rsp + 0x5c], eax
004219FB  jmp      0x140421a25
004219FD  movzx    eax, byte ptr [r9]
00421A01  not      al
00421A03  movzx    r12d, r10b
00421A07  mov      byte ptr [rsp + 0x54], al
00421A0B  movzx    eax, byte ptr [r9 + 1]
00421A10  not      al
00421A12  mov      qword ptr [rbp - 0x60], r12
00421A16  mov      byte ptr [rsp + 0x58], al
00421A1A  movzx    eax, byte ptr [r9 + 2]
00421A1F  not      al
00421A21  mov      byte ptr [rsp + 0x5c], al
00421A25  mov      r10, qword ptr [r15 + 0x40]
00421A29  test     r10, r10
00421A2C  je       0x140421ada
00421A32  movzx    r9d, byte ptr [rdi + r13 + 0xc8]
00421A3B  cmp      r9b, 1
00421A3F  jbe      0x140421ab7
00421A41  movzx    ecx, byte ptr [rsp + 0x2e]
00421A46  lea      r8d, [r9 + r9]
00421A4A  mov      eax, 1
00421A4F  xor      edx, edx
00421A51  shl      eax, cl
00421A53  mov      r11d, r9d
00421A56  cdqe     
00421A58  add      rax, qword ptr [r14]
00421A5B  div      r8
00421A5E  mov      qword ptr [rbp - 0x68], rdx
00421A62  mov      r8, rdx
00421A65  cmp      dx, r9w
00421A69  jbe      0x140421a77
00421A6B  lea      r8d, [r9 + r9]
00421A6F  sub      r8w, dx
00421A73  mov      qword ptr [rbp - 0x68], r8
00421A77  movzx    eax, byte ptr [r10]
00421A7B  xor      edx, edx
00421A7D  movzx    ecx, r8w
00421A81  imul     eax, ecx
00421A84  div      r11d
00421A87  xor      edx, edx
00421A89  add      eax, 8
00421A8C  mov      dword ptr [rsp + 0x78], eax
00421A90  movzx    eax, byte ptr [r10 + 1]
00421A95  imul     eax, ecx
00421A98  div      r11d
00421A9B  xor      edx, edx
00421A9D  add      eax, 8
00421AA0  mov      dword ptr [rsp + 0x7c], eax
00421AA4  movzx    eax, byte ptr [r10 + 2]
00421AA9  imul     eax, ecx
00421AAC  div      r11d
00421AAF  lea      ecx, [rax + 8]
00421AB2  mov      dword ptr [rbp - 0x80], ecx
00421AB5  jmp      0x140421ade
00421AB7  movzx    eax, byte ptr [r10]
00421ABB  movzx    r8d, r9w
00421ABF  mov      dword ptr [rsp + 0x78], eax
00421AC3  movzx    eax, byte ptr [r10 + 1]
00421AC8  mov      dword ptr [rsp + 0x7c], eax
00421ACC  movzx    eax, byte ptr [r10 + 2]
00421AD1  mov      dword ptr [rbp - 0x80], eax
00421AD4  mov      qword ptr [rbp - 0x68], r8
00421AD8  jmp      0x140421ade
00421ADA  mov      r8, qword ptr [rbp - 0x68]
00421ADE  lea      rax, [rip + 0x23b687]
00421AE5  movzx    eax, byte ptr [rdi + rax]
00421AE9  test     byte ptr [r13 + 0xcf], al
00421AF0  je       0x140421bce
00421AF6  test     r8w, r8w
00421AFA  jne      0x140421b75
00421AFC  test     r12w, r12w
00421B00  je       0x140421bce
00421B06  mov      r10d, dword ptr [rsp + 0x30]
00421B0B  mov      eax, r10d
00421B0E  sub      eax, dword ptr [rsp + 0x34]
00421B12  movzx    r8d, byte ptr [rdi + r13 + 0x88]
00421B1B  movzx    ecx, r12w
00421B1F  imul     eax, ecx
00421B22  cdq      
00421B23  idiv     r8d
00421B26  add      eax, dword ptr [rsp + 0x34]
00421B2A  mov      dword ptr [rbp + 0x20], eax
00421B2D  mov      eax, r10d
00421B30  sub      eax, dword ptr [rsp + 0x38]
00421B34  imul     eax, ecx
00421B37  cdq      
00421B38  idiv     r8d
00421B3B  add      eax, dword ptr [rsp + 0x38]
00421B3F  mov      dword ptr [rbp + 0x24], eax
00421B42  mov      eax, r10d
00421B45  sub      eax, dword ptr [rsp + 0x3c]
00421B49  lea      r13, [rbp + 0x20]
00421B4D  imul     eax, ecx
00421B50  cdq      
00421B51  idiv     r8d
00421B54  add      eax, dword ptr [rsp + 0x3c]
00421B58  mov      dword ptr [rbp + 0x28], eax
00421B5B  movzx    eax, byte ptr [rip + 0x23b10c]
00421B62  cmp      byte ptr [rsi + 0x19], al
00421B65  je       0x140421bd2
00421B67  lea      rdx, [rbp + 0x20]
00421B6B  mov      rcx, rsi
00421B6E  call     0x14001e1e0
00421B73  jmp      0x140421bd2
00421B75  cmp      r8w, r12w
00421B79  jbe      0x140421b06
00421B7B  movzx    eax, byte ptr [rdi + r13 + 0xc8]
00421B84  test     al, al
00421B86  je       0x140421b06
00421B8C  mov      r11d, dword ptr [rsp + 0x30]
00421B91  mov      r10d, dword ptr [rsp + 0x34]
00421B96  movzx    ecx, r8w
00421B9A  movzx    r8d, al
00421B9E  mov      eax, r11d
00421BA1  sub      eax, r10d
00421BA4  imul     eax, ecx
00421BA7  cdq      
00421BA8  idiv     r8d
00421BAB  add      eax, r10d
00421BAE  mov      dword ptr [rbp + 0x20], eax
00421BB1  mov      eax, r11d
00421BB4  sub      eax, dword ptr [rsp + 0x38]
00421BB8  imul     eax, ecx
00421BBB  cdq      
00421BBC  idiv     r8d
00421BBF  add      eax, dword ptr [rsp + 0x38]
00421BC3  mov      dword ptr [rbp + 0x24], eax
00421BC6  mov      eax, r11d
00421BC9  jmp      0x140421b45
00421BCE  lea      r13, [rbp + 0x10]
00421BD2  mov      r12d, 0xc
00421BD8  nop      dword ptr [rax + rax]
00421BE0  cmp      dword ptr [rbp - 0x4c], 0
00421BE4  mov      rax, qword ptr [r14 + 0x10]
00421BE8  movzx    edi, byte ptr [rax + rbx*4 + 2]
00421BED  movzx    r14d, byte ptr [rax + rbx*4 + 1]
00421BF3  movzx    esi, byte ptr [rax + rbx*4]
00421BF7  je       0x140421c15
00421BF9  movzx    eax, r14b
00421BFD  movzx    ecx, sil
00421C01  add      ecx, eax
00421C03  movzx    eax, dil
00421C07  lea      edi, [rax + rcx]
00421C0A  shr      edi, 2
00421C0D  movzx    r14d, dil
00421C11  movzx    esi, dil
00421C15  cmp      dword ptr [rbp - 0x50], 0
00421C19  je       0x140421c93
00421C1B  movzx    eax, r14b
00421C1F  lea      rdx, [rsp + 0x24]
00421C24  movzx    esi, sil
00421C28  lea      rcx, [rsp + 0x28]
00421C2D  add      esi, eax
00421C2F  mov      r14d, 0xff
00421C35  movzx    eax, dil
00421C39  add      esi, eax
00421C3B  mov      dword ptr [rsp + 0x28], r14d
00421C40  shr      esi, 2
00421C43  movzx    ebx, sil
00421C47  lea      eax, [rbx + 0x15]
00421C4A  mov      dword ptr [rsp + 0x24], eax
00421C4E  call     0x140407bc0
00421C53  lea      rdx, [rsp + 0x28]
00421C58  mov      dword ptr [rsp + 0x28], ebx
00421C5C  lea      rcx, [rsp + 0x24]
00421C61  mov      dword ptr [rsp + 0x24], r14d
00421C66  movzx    edi, al
00421C69  call     0x140407bc0
00421C6E  lea      rdx, [rsp + 0x28]
00421C73  mov      dword ptr [rsp + 0x28], 0x20
00421C7B  lea      rcx, [rsp + 0x24]
00421C80  mov      dword ptr [rsp + 0x24], ebx
00421C84  mov      r14d, eax
00421C87  call     0x140407bc0
00421C8C  mov      rbx, qword ptr [rbp - 0x40]
00421C90  sub      sil, al
00421C93  cmp      qword ptr [r15 - 0x40], 0
00421C98  je       0x140421cc0
00421C9A  movzx    edi, dil
00421C9E  imul     edi, dword ptr [rbp - 0x78]
00421CA2  movzx    r14d, r14b
00421CA6  imul     r14d, dword ptr [rbp - 0x74]
00421CAB  movzx    eax, sil
00421CAF  imul     eax, dword ptr [rbp - 0x70]
00421CB3  sar      edi, 8
00421CB6  sar      r14d, 8
00421CBA  sar      eax, 8
00421CBD  movzx    esi, al
00421CC0  cmp      qword ptr [r15], 0
00421CC4  je       0x140421d07
00421CC6  movzx    eax, byte ptr [rsp + 0x54]
00421CCB  not      dil
00421CCE  not      r14b
00421CD1  movzx    edi, dil
00421CD5  imul     edi, eax
00421CD8  not      sil
00421CDB  movzx    eax, byte ptr [rsp + 0x58]
00421CE0  movzx    r14d, r14b
00421CE4  imul     r14d, eax
00421CE8  movzx    eax, byte ptr [rsp + 0x5c]
00421CED  movzx    esi, sil
00421CF1  imul     esi, eax
00421CF4  shr      edi, 8
00421CF7  shr      r14d, 8
00421CFB  not      dil
00421CFE  not      r14b
00421D01  shr      esi, 8
00421D04  not      sil
00421D07  cmp      qword ptr [r15 + 0x40], 0
00421D0C  je       0x140421d8c
00421D0E  movzx    eax, dil
00421D12  lea      rdx, [rsp + 0x28]
00421D17  imul     eax, dword ptr [rsp + 0x78]
00421D1C  lea      rcx, [rsp + 0x24]
00421D21  mov      dword ptr [rsp + 0x24], 0xff
00421D29  sar      eax, 3
00421D2C  mov      dword ptr [rsp + 0x28], eax
00421D30  call     0x140407bc0
00421D35  movzx    edi, al
00421D38  mov      dword ptr [rsp + 0x24], 0xff
00421D40  movzx    eax, r14b
00421D44  lea      rdx, [rsp + 0x28]
00421D49  imul     eax, dword ptr [rsp + 0x7c]
00421D4E  lea      rcx, [rsp + 0x24]
00421D53  sar      eax, 3
00421D56  mov      dword ptr [rsp + 0x28], eax
00421D5A  call     0x140407bc0
00421D5F  movzx    r14d, al
00421D63  mov      dword ptr [rsp + 0x24], 0xff
00421D6B  movzx    eax, sil
00421D6F  lea      rdx, [rsp + 0x28]
00421D74  imul     eax, dword ptr [rbp - 0x80]
00421D78  lea      rcx, [rsp + 0x24]
00421D7D  sar      eax, 3
00421D80  mov      dword ptr [rsp + 0x28], eax
00421D84  call     0x140407bc0
00421D89  movzx    esi, al
00421D8C  cmp      byte ptr [rsp + 0x2c], 0
00421D91  je       0x140421dbe
00421D93  mov      ecx, dword ptr [rsp + 0x40]
00421D97  movzx    eax, r14b
00421D9B  mov      r14d, dword ptr [r13 + 4]
00421D9F  imul     r14d, eax
00421DA3  movzx    eax, sil
00421DA7  mov      esi, dword ptr [r13 + 8]
00421DAB  movzx    edi, dil
00421DAF  imul     edi, dword ptr [r13]
00421DB4  imul     esi, eax
00421DB7  sar      r14d, cl
00421DBA  sar      edi, cl
00421DBC  sar      esi, cl
00421DBE  cmp      byte ptr [rsp + 0x2d], 0
00421DC3  je       0x140421e00
00421DC5  mov      ecx, dword ptr [rsp + 0x48]
00421DC9  not      dil
00421DCC  not      r14b
00421DCF  movzx    edi, dil
00421DD3  imul     edi, dword ptr [rsp + 0x44]
00421DD8  not      sil
00421DDB  movzx    r14d, r14b
00421DDF  imul     r14d, dword ptr [rsp + 0x4c]
00421DE5  movzx    eax, sil
00421DE9  imul     eax, dword ptr [rsp + 0x50]
00421DEE  sar      edi, cl
00421DF0  not      dil
00421DF3  sar      r14d, cl
00421DF6  not      r14b
00421DF9  sar      eax, cl
00421DFB  not      al
00421DFD  movzx    esi, al
00421E00  cmp      byte ptr [rsp + 0x20], 0
00421E05  je       0x140421e86
00421E07  movzx    eax, dil
00421E0B  lea      rdx, [rsp + 0x28]
00421E10  imul     eax, dword ptr [rsp + 0x60]
00421E15  lea      rcx, [rsp + 0x24]
00421E1A  mov      dword ptr [rsp + 0x24], 0xff
00421E22  shr      eax, 3
00421E25  mov      dword ptr [rsp + 0x28], eax
00421E29  call     0x140407bc0
00421E2E  movzx    edi, al
00421E31  mov      dword ptr [rsp + 0x24], 0xff
00421E39  movzx    eax, r14b
00421E3D  lea      rdx, [rsp + 0x28]
00421E42  imul     eax, dword ptr [rsp + 0x64]
00421E47  lea      rcx, [rsp + 0x24]
00421E4C  shr      eax, 3
00421E4F  mov      dword ptr [rsp + 0x28], eax
00421E53  call     0x140407bc0
00421E58  movzx    r14d, al
00421E5C  mov      dword ptr [rsp + 0x24], 0xff
00421E64  movzx    eax, sil
00421E68  lea      rdx, [rsp + 0x28]
00421E6D  imul     eax, dword ptr [rsp + 0x68]
00421E72  lea      rcx, [rsp + 0x24]
00421E77  shr      eax, 3
00421E7A  mov      dword ptr [rsp + 0x28], eax
00421E7E  call     0x140407bc0
00421E83  movzx    esi, al
00421E86  mov      r8, qword ptr [rbp - 0x58]
00421E8A  mov      byte ptr [r8 + rbx*4 + 2], dil
00421E8F  mov      byte ptr [r8 + rbx*4 + 1], r14b
00421E94  mov      r14, qword ptr [rsp + 0x70]
00421E99  mov      byte ptr [r8 + rbx*4], sil
00421E9D  inc      rbx
00421EA0  mov      qword ptr [rbp - 0x40], rbx
00421EA4  sub      r12, 1
00421EA8  jne      0x140421be0
00421EAE  movzx    eax, word ptr [rsp + 0x2e]
00421EB3  add      r15, 8
00421EB7  mov      rdi, qword ptr [rbp - 0x38]
00421EBB  inc      ax
00421EBE  mov      rsi, qword ptr [rbp - 0x30]
00421EC2  inc      rdi
00421EC5  mov      r13, qword ptr [rbp - 0x28]
00421EC9  mov      r12, qword ptr [rbp - 0x60]
00421ECD  mov      word ptr [rsp + 0x2e], ax
00421ED2  mov      qword ptr [rbp - 0x38], rdi
00421ED6  cmp      ax, 7
00421EDA  jl       0x140421890
00421EE0  test     dword ptr [rbp - 0x7c], 0xfff0000
00421EE7  mov      rsi, r14
00421EEA  jne      0x140421f7b
00421EF0  cmp      dword ptr [r14 + 0x24], 0
00421EF5  je       0x140421f7b
00421EFB  mov      rax, qword ptr [r14 + 0x10]
00421EFF  lea      rcx, [r8 + 0x160]
00421F06  add      rax, 0x160
00421F0C  mov      edx, 5
00421F11  lea      rcx, [rcx + 0x80]
00421F18  movups   xmm0, xmmword ptr [rax]
00421F1B  lea      rax, [rax + 0x80]
00421F22  movups   xmmword ptr [rcx - 0x80], xmm0
00421F26  movups   xmm1, xmmword ptr [rax - 0x70]
00421F2A  movups   xmmword ptr [rcx - 0x70], xmm1
00421F2E  movups   xmm0, xmmword ptr [rax - 0x60]
00421F32  movups   xmmword ptr [rcx - 0x60], xmm0
00421F36  movups   xmm1, xmmword ptr [rax - 0x50]
00421F3A  movups   xmmword ptr [rcx - 0x50], xmm1
00421F3E  movups   xmm0, xmmword ptr [rax - 0x40]
00421F42  movups   xmmword ptr [rcx - 0x40], xmm0
00421F46  movups   xmm1, xmmword ptr [rax - 0x30]
00421F4A  movups   xmmword ptr [rcx - 0x30], xmm1
00421F4E  movups   xmm0, xmmword ptr [rax - 0x20]
00421F52  movups   xmmword ptr [rcx - 0x20], xmm0
00421F56  movups   xmm1, xmmword ptr [rax - 0x10]
00421F5A  movups   xmmword ptr [rcx - 0x10], xmm1
00421F5E  sub      rdx, 1
00421F62  jne      0x140421f11
00421F64  movups   xmm0, xmmword ptr [rax]
00421F67  lea      r12d, [rdx + 1]
00421F6B  movups   xmmword ptr [rcx], xmm0
00421F6E  movups   xmm1, xmmword ptr [rax + 0x10]
00421F72  movups   xmmword ptr [rcx + 0x10], xmm1
00421F76  jmp      0x140422022
00421F7B  mov      r12d, 1
00421F81  lea      rax, [r8 + 0x18]
00421F85  lea      r9, [r8 + 0x160]
00421F8C  mov      ebx, r12d
00421F8F  lea      edi, [r12 + 5]
00421F94  lea      r8, [rax + 0x30]
00421F98  cmp      bx, 7
00421F9C  jae      0x14042200e
00421F9E  mov      ecx, 7
00421FA3  sub      cx, bx
00421FA6  movzx    r11d, cx
00421FAA  nop      word ptr [rax + rax]
00421FB0  mov      r10d, 8
00421FB6  nop      word ptr [rax + rax]
00421FC0  movzx    ecx, byte ptr [rax + 2]
00421FC4  movzx    edx, byte ptr [r8 + 2]
00421FC9  add      edx, ecx
00421FCB  shr      edx, 1
00421FCD  mov      byte ptr [r9 + 2], dl
00421FD1  movzx    ecx, byte ptr [rax + 1]
00421FD5  movzx    edx, byte ptr [r8 + 1]
00421FDA  add      edx, ecx
00421FDC  shr      edx, 1
00421FDE  mov      byte ptr [r9 + 1], dl
00421FE2  movzx    edx, byte ptr [rax]
00421FE5  add      rax, 4
00421FE9  movzx    ecx, byte ptr [r8]
00421FED  add      r8, 4
00421FF1  add      edx, ecx
00421FF3  shr      edx, 1
00421FF5  mov      byte ptr [r9], dl
00421FF8  add      r9, 4
00421FFC  sub      r10, r12
00421FFF  jne      0x140421fc0
00422001  sub      rax, 0x20
00422005  add      r8, 0x10
00422009  sub      r11, r12
0042200C  jne      0x140421fb0
0042200E  add      rax, 0x30
00422012  inc      bx
00422015  sub      rdi, r12
00422018  jne      0x140421f94
0042201E  mov      r8, qword ptr [rbp - 0x58]
00422022  mov      r11, qword ptr [rbp - 0x30]
00422026  mov      ebx, 0xff
0042202B  mov      rdi, qword ptr [rbp - 0x58]
0042202F  mov      r10d, 0xfe
00422035  mov      r9d, 4
0042203B  mov      ecx, dword ptr [r11 + 0x194]
00422042  shl      ebx, cl
00422044  shl      r10d, cl
00422047  cmp      dword ptr [rsi + 0x18], r9d
0042204B  jle      0x1404220a9
0042204D  mov      r15, qword ptr [rbp - 0x48]
00422051  add      r8, 0x12
00422055  mov      r14d, dword ptr [rbp + 0xa0]
0042205C  sub      r15, rdi
0042205F  nop      
00422060  movzx    edx, byte ptr [r8 - 2]
00422065  mov      ecx, dword ptr [r11 + 0x198]
0042206C  movzx    eax, byte ptr [r8 - 1]
00422071  lea      r8, [r8 + 4]
00422075  shl      edx, cl
00422077  mov      ecx, dword ptr [r11 + 0x194]
0042207E  shl      eax, cl
00422080  mov      ecx, dword ptr [r11 + 0x190]
00422087  or       edx, eax
00422089  movzx    eax, byte ptr [r8 - 4]
0042208E  shl      eax, cl
00422090  or       edx, eax
00422092  or       edx, r14d
00422095  cmp      edx, ebx
00422097  cmove    edx, r10d
0042209B  inc      r9d
0042209E  mov      dword ptr [r15 + r8 - 6], edx
004220A3  cmp      r9d, dword ptr [rsi + 0x18]
004220A7  jl       0x140422060
004220A9  cmp      r12w, 1
004220AE  jne      0x1404220b8
004220B0  mov      rcx, rdi
004220B3  call     0x14045e690
004220B8  mov      rcx, qword ptr [rbp + 0x30]
004220BC  xor      rcx, rsp
004220BF  call     0x1404f77a0
004220C4  mov      rbx, qword ptr [rsp + 0x190]
004220CC  add      rsp, 0x140
004220D3  pop      r15
004220D5  pop      r14
004220D7  pop      r13
004220D9  pop      r12
004220DB  pop      rdi
004220DC  pop      rsi
004220DD  pop      rbp
004220DE  ret      
004220DF  int3     
004220E0  push     rbx
004220E2  sub      rsp, 0x20
004220E6  mov      rbx, rcx
004220E9  mov      rcx, qword ptr [rcx + 8]
004220ED  test     rcx, rcx
004220F0  je       0x14042210c
004220F2  mov      rax, qword ptr [rip + 0x245467]
004220F9  movsxd   rdx, dword ptr [rax + 0xfa0]
00422100  add      rdx, rcx
00422103  mov      qword ptr [rbx], rdx
00422106  add      rsp, 0x20
0042210A  pop      rbx
0042210B  ret      
0042210C  call     0x14050933c
00422111  and      eax, 0x7fff
00422116  imul     edx, eax, 0x7fff
0042211C  sar      edx, 0xf
0042211F  mov      qword ptr [rbx + 8], rdx
00422123  mov      rax, qword ptr [rip + 0x245436]
0042212A  movsxd   rcx, dword ptr [rax + 0xfa0]
00422131  add      rcx, rdx
00422134  mov      qword ptr [rbx], rcx
00422137  add      rsp, 0x20
0042213B  pop      rbx
0042213C  ret      
0042213D  int3     
0042213E  int3     
0042213F  int3     
00422140  mov      rax, qword ptr [rdx + 0x10]
00422144  mov      qword ptr [rcx + 0x10], rax
00422148  mov      eax, dword ptr [rdx + 0x18]
0042214B  mov      dword ptr [rcx + 0x18], eax
0042214E  movzx    eax, word ptr [rdx + 0x20]
00422152  mov      word ptr [rcx + 0x20], ax
00422156  mov      byte ptr [rcx + 0x22], 0
0042215A  mov      eax, dword ptr [rdx + 0x28]
0042215D  mov      dword ptr [rcx + 0x28], eax
00422160  movzx    eax, word ptr [rdx + 0x2c]
00422164  mov      word ptr [rcx + 0x2c], ax
00422168  movzx    eax, byte ptr [rdx + 0x2e]
0042216C  mov      byte ptr [rcx + 0x2e], al
0042216F  ret      
00422170  mov      qword ptr [rcx + 0x10], rdx
00422174  mov      dword ptr [rcx + 0x18], r8d
00422178  mov      word ptr [rcx + 0x20], r9w
0042217D  ret      
0042217E  int3     
0042217F  int3     
00422180  movzx    eax, r8w
00422184  mov      r8, qword ptr [rcx + 0x10]
00422188  lea      r10, [rax*4]
00422190  mov      eax, dword ptr [r8 + rax*4]
00422194  mov      byte ptr [r8 + r10 + 2], r9b
00422199  movzx    r8d, r9w
0042219D  mov      dword ptr [rdx], eax
0042219F  mov      rax, qword ptr [rcx + 0x10]
004221A3  shr      r8w, 8
004221A8  shr      r9d, 0x10
004221AC  mov      byte ptr [rax + r10 + 1], r8b
004221B1  mov      rax, qword ptr [rcx + 0x10]
004221B5  mov      byte ptr [r10 + rax], r9b
004221B9  mov      rax, rdx
004221BC  ret      
004221BD  int3     
004221BE  int3     
004221BF  int3     
004221C0  mov      qword ptr [rsp + 8], rbx
004221C5  mov      qword ptr [rsp + 0x10], rbp
004221CA  mov      qword ptr [rsp + 0x18], rsi
004221CF  mov      qword ptr [rsp + 0x20], rdi
004221D4  push     r14
004221D6  sub      rsp, 0x20
004221DA  mov      r10, qword ptr [rcx + 0x10]
004221DE  mov      r14, rcx
004221E1  movzx    eax, dx
004221E4  mov      rbp, r9
004221E7  movzx    edi, r8w
004221EB  mov      byte ptr [rax + rcx + 0x28], dil
004221F0  mov      rcx, qword ptr [r9 + 0x100]
004221F7  movzx    eax, dx
004221FA  lea      edx, [rax + rax*2]
004221FD  lea      edx, [rdx*4 + 4]
00422204  lea      rsi, [r10 + rdx*4]
00422208  call     0x1403f6d50
0042220D  xor      ebx, ebx
0042220F  nop      
00422210  mov      r9d, edi
00422213  mov      r8d, ebx
00422216  mov      rdx, rsi
00422219  mov      rcx, rbp
0042221C  call     0x140411b50
00422221  add      rsi, 4
00422225  inc      ebx
00422227  cmp      ebx, 0xc
0042222A  jl       0x140422210
0042222C  mov      rbx, qword ptr [rsp + 0x30]
00422231  mov      rbp, qword ptr [rsp + 0x38]
00422236  mov      rsi, qword ptr [rsp + 0x40]
0042223B  mov      rdi, qword ptr [rsp + 0x48]
00422240  mov      dword ptr [r14 + 0x24], 0
00422248  add      rsp, 0x20
0042224C  pop      r14
0042224E  ret      
0042224F  int3     
00422250  push     rbx
00422252  sub      rsp, 0x20
00422256  xor      r8d, r8d
00422259  mov      word ptr [rcx + 0x20], dx
0042225D  mov      dword ptr [rcx + 0x24], r8d
00422261  mov      rbx, rcx
00422264  mov      byte ptr [rcx + 0x22], 1
00422268  movzx    ecx, dx
0042226B  test     ecx, ecx
0042226D  je       0x14042232e
00422273  cmp      ecx, 1
00422276  jne      0x14042233c
0042227C  mov      rcx, qword ptr [rbx + 0x10]
00422280  mov      eax, 0x100
00422285  mov      dword ptr [rbx + 0x18], eax
00422288  test     rcx, rcx
0042228B  je       0x140422295
0042228D  call     0x14045e690
00422292  mov      eax, dword ptr [rbx + 0x18]
00422295  movsxd   rcx, eax
00422298  mov      eax, 4
0042229D  mul      rcx
004222A0  mov      rcx, 0xffffffffffffffff
004222A7  cmovo    rax, rcx
004222AB  mov      rcx, rax
004222AE  call     0x1404f77c4
004222B3  movsxd   r8, dword ptr [rbx + 0x18]
004222B7  xor      edx, edx
004222B9  shl      r8, 2
004222BD  mov      rcx, rax
004222C0  mov      qword ptr [rbx + 0x10], rax
004222C4  call     0x1404fab70
004222C9  mov      rax, qword ptr [rbx + 0x10]
004222CD  mov      byte ptr [rax + 2], 0
004222D1  mov      rax, qword ptr [rbx + 0x10]
004222D5  mov      byte ptr [rax + 1], 0xff
004222D9  mov      rax, qword ptr [rbx + 0x10]
004222DD  mov      byte ptr [rax], 0
004222E0  mov      rax, qword ptr [rbx + 0x10]
004222E4  mov      byte ptr [rax + 6], 0
004222E8  mov      rax, qword ptr [rbx + 0x10]
004222EC  mov      byte ptr [rax + 5], 0
004222F0  mov      rax, qword ptr [rbx + 0x10]
004222F4  mov      byte ptr [rax + 4], 0
004222F8  mov      rax, qword ptr [rbx + 0x10]
004222FC  mov      byte ptr [rax + 0xa], 0
00422300  mov      rax, qword ptr [rbx + 0x10]
00422304  mov      byte ptr [rax + 9], 0
00422308  mov      rax, qword ptr [rbx + 0x10]
0042230C  mov      byte ptr [rax + 8], 0
00422310  mov      rax, qword ptr [rbx + 0x10]
00422314  mov      byte ptr [rax + 0xe], 0
00422318  mov      rax, qword ptr [rbx + 0x10]
0042231C  mov      byte ptr [rax + 0xd], 0
00422320  mov      rax, qword ptr [rbx + 0x10]
00422324  mov      byte ptr [rax + 0xc], 0
00422328  add      rsp, 0x20
0042232C  pop      rbx
0042232D  ret      
0042232E  mov      rcx, 0xffffffffffffffff
00422335  mov      qword ptr [rbx + 0x10], r8
00422339  mov      dword ptr [rbx + 0x18], ecx
0042233C  add      rsp, 0x20
00422340  pop      rbx
00422341  ret      
00422342  int3     
00422343  int3     
00422344  int3     
00422345  int3     
00422346  int3     
00422347  int3     
00422348  int3     
00422349  int3     
0042234A  int3     
0042234B  int3     
0042234C  int3     
0042234D  int3     
0042234E  int3     
0042234F  int3     
00422350  lea      rax, [rip + 0x19e7b9]
00422357  mov      qword ptr [rcx + 0x10], 0x11
0042235F  mov      qword ptr [rcx], rax
00422362  xor      eax, eax
00422364  mov      qword ptr [rcx + 8], rax
00422368  mov      qword ptr [rcx + 0x18], rax
0042236C  mov      qword ptr [rcx + 0x20], rax
00422370  mov      rax, rcx
00422373  mov      dword ptr [rcx + 0x28], edx
00422376  ret      
00422377  int3     
00422378  int3     
00422379  int3     
0042237A  int3     
0042237B  int3     
0042237C  int3     
0042237D  int3     
0042237E  int3     
0042237F  int3     
00422380  push     rbx
00422382  sub      rsp, 0x20
00422386  lea      rax, [rip + 0x19e783]
0042238D  mov      rbx, rcx
00422390  mov      qword ptr [rcx], rax
00422393  call     0x1404226e0
00422398  lea      rax, [rip + 0x1dcfd9]
0042239F  mov      qword ptr [rbx], rax
004223A2  add      rsp, 0x20
004223A6  pop      rbx
004223A7  ret      
004223A8  int3     
004223A9  int3     
004223AA  int3     
004223AB  int3     
004223AC  int3     
004223AD  int3     
004223AE  int3     
004223AF  int3     
004223B0  mov      qword ptr [rsp + 0x18], rbp
004223B5  mov      qword ptr [rsp + 0x20], rsi
004223BA  push     r14
004223BC  sub      rsp, 0x20
004223C0  mov      rsi, rcx
004223C3  xor      eax, eax
004223C5  movzx    ecx, byte ptr [rdx]
004223C8  mov      r14, rdx
004223CB  mov      r9, rdx
004223CE  test     cl, cl
004223D0  je       0x1404223f6
004223D2  nop      dword ptr [rax]
004223D6  nop      word ptr [rax + rax]
004223E0  imul     eax, eax, 0x21
004223E3  lea      r9, [r9 + 1]
004223E7  movsx    r8d, cl
004223EB  movzx    ecx, byte ptr [r9]
004223EF  add      eax, r8d
004223F2  test     cl, cl
004223F4  jne      0x1404223e0
004223F6  mov      rcx, qword ptr [rsi + 8]
004223FA  xor      edx, edx
004223FC  div      dword ptr [rsi + 0x10]
004223FF  mov      qword ptr [rsp + 0x30], rbx
00422404  mov      ebp, edx
00422406  test     rcx, rcx
00422409  je       0x140422439
0042240B  mov      rbx, qword ptr [rcx + rdx*8]
0042240F  test     rbx, rbx
00422412  je       0x140422434
00422414  mov      rcx, qword ptr [rbx + 0x10]
00422418  mov      rdx, r14
0042241B  call     0x140503d4c
00422420  test     eax, eax
00422422  je       0x140422511
00422428  mov      rbx, qword ptr [rbx]
0042242B  test     rbx, rbx
0042242E  jne      0x140422414
00422430  mov      rcx, qword ptr [rsi + 8]
00422434  test     rcx, rcx
00422437  jne      0x14042247a
00422439  mov      rcx, 0xffffffffffffffff
00422440  mov      qword ptr [rsp + 0x38], rdi
00422445  mov      edi, dword ptr [rsi + 0x10]
00422448  mov      eax, 8
0042244D  mul      rdi
00422450  cmovo    rax, rcx
00422454  mov      rcx, rax
00422457  call     0x1404f77c4
0042245C  lea      r8, [rdi*8]
00422464  mov      qword ptr [rsi + 8], rax
00422468  xor      edx, edx
0042246A  mov      rcx, rax
0042246D  call     0x1404fab70
00422472  mov      dword ptr [rsi + 0x10], edi
00422475  mov      rdi, qword ptr [rsp + 0x38]
0042247A  cmp      qword ptr [rsi + 0x18], 0
0042247F  jne      0x1404224c4
00422481  mov      edx, dword ptr [rsi + 0x28]
00422484  lea      rcx, [rsi + 0x20]
00422488  mov      r8d, 0x20
0042248E  call     0x140407af0
00422493  mov      edx, dword ptr [rsi + 0x28]
00422496  add      rax, 0x10
0042249A  dec      edx
0042249C  movsxd   rcx, edx
0042249F  shl      rcx, 5
004224A3  add      rax, rcx
004224A6  test     edx, edx
004224A8  js       0x1404224c4
004224AA  nop      word ptr [rax + rax]
004224B0  mov      rcx, qword ptr [rsi + 0x18]
004224B4  mov      qword ptr [rax], rcx
004224B7  mov      qword ptr [rsi + 0x18], rax
004224BB  sub      rax, 0x20
004224BF  sub      edx, 1
004224C2  jns      0x1404224b0
004224C4  mov      rbx, qword ptr [rsi + 0x18]
004224C8  mov      rdx, r14
004224CB  mov      rax, qword ptr [rbx]
004224CE  lea      rcx, [rbx + 0x10]
004224D2  inc      dword ptr [rsi + 0x14]
004224D5  mov      qword ptr [rsi + 0x18], rax
004224D9  mov      rax, qword ptr [rip + 0x23a630]
004224E0  mov      qword ptr [rcx], rax
004224E3  mov      rax, qword ptr [rip + 0x23a626]
004224EA  mov      qword ptr [rbx + 0x18], rax
004224EE  mov      dword ptr [rbx + 8], ebp
004224F1  call     0x1403fd810
004224F6  mov      rax, qword ptr [rsi + 8]
004224FA  lea      rdx, [rbp*8]
00422502  mov      rcx, qword ptr [rdx + rax]
00422506  mov      qword ptr [rbx], rcx
00422509  mov      rax, qword ptr [rsi + 8]
0042250D  mov      qword ptr [rdx + rax], rbx
00422511  mov      rbp, qword ptr [rsp + 0x40]
00422516  lea      rax, [rbx + 0x18]
0042251A  mov      rbx, qword ptr [rsp + 0x30]
0042251F  mov      rsi, qword ptr [rsp + 0x48]
00422524  add      rsp, 0x20
00422528  pop      r14
0042252A  ret      
0042252B  int3     
0042252C  int3     
0042252D  int3     
0042252E  int3     
0042252F  int3     
00422530  mov      qword ptr [rsp + 8], rbx
00422535  push     rdi
00422536  sub      rsp, 0x20
0042253A  lea      rax, [rip + 0x19e5cf]
00422541  mov      ebx, edx
00422543  mov      qword ptr [rcx], rax
00422546  mov      rdi, rcx
00422549  call     0x1404226e0
0042254E  lea      rax, [rip + 0x1dce23]
00422555  mov      qword ptr [rdi], rax
00422558  test     bl, 1
0042255B  je       0x14042256a
0042255D  mov      edx, 0x30
00422562  mov      rcx, rdi
00422565  call     0x14045e690
0042256A  mov      rbx, qword ptr [rsp + 0x30]
0042256F  mov      rax, rdi
00422572  add      rsp, 0x20
00422576  pop      rdi
00422577  ret      
00422578  int3     
00422579  int3     
0042257A  int3     
0042257B  int3     
0042257C  int3     
0042257D  int3     
0042257E  int3     
0042257F  int3     
00422580  mov      qword ptr [rsp + 0x10], rbx
00422585  mov      qword ptr [rsp + 0x18], rbp
0042258A  push     rsi
0042258B  sub      rsp, 0x20
0042258F  mov      rbx, qword ptr [rdx]
00422592  mov      rbp, r9
00422595  mov      r9, r8
00422598  mov      rsi, rdx
0042259B  mov      r8, rcx
0042259E  cmp      rbx, -1
004225A2  jne      0x1404225d6
004225A4  mov      r11d, dword ptr [rcx + 0x10]
004225A8  xor      r10d, r10d
004225AB  test     r11d, r11d
004225AE  je       0x1404225d6
004225B0  mov      qword ptr [rsp + 0x30], rdi
004225B5  mov      rdi, qword ptr [rcx + 8]
004225B9  nop      dword ptr [rax]
004225C0  mov      rbx, qword ptr [rdi + r10*8]
004225C4  test     rbx, rbx
004225C7  jne      0x1404225d1
004225C9  inc      r10d
004225CC  cmp      r10d, r11d
004225CF  jb       0x1404225c0
004225D1  mov      rdi, qword ptr [rsp + 0x30]
004225D6  mov      rax, qword ptr [rbx]
004225D9  test     rax, rax
004225DC  jne      0x1404225ff
004225DE  mov      ecx, dword ptr [rbx + 8]
004225E1  mov      edx, dword ptr [r8 + 0x10]
004225E5  inc      ecx
004225E7  cmp      ecx, edx
004225E9  jae      0x1404225ff
004225EB  mov      r8, qword ptr [r8 + 8]
004225EF  nop      
004225F0  mov      rax, qword ptr [r8 + rcx*8]
004225F4  test     rax, rax
004225F7  jne      0x1404225ff
004225F9  inc      ecx
004225FB  cmp      ecx, edx
004225FD  jb       0x1404225f0
004225FF  lea      rdx, [rbx + 0x10]
00422603  mov      qword ptr [rsi], rax
00422606  mov      rcx, r9
00422609  call     0x1403fd770
0042260E  lea      rdx, [rbx + 0x18]
00422612  mov      rcx, rbp
00422615  mov      rbx, qword ptr [rsp + 0x38]
0042261A  mov      rbp, qword ptr [rsp + 0x40]
0042261F  add      rsp, 0x20
00422623  pop      rsi
00422624  jmp      0x1403fd770
00422629  int3     
0042262A  int3     
0042262B  int3     
0042262C  int3     
0042262D  int3     
0042262E  int3     
0042262F  int3     
00422630  mov      qword ptr [rsp + 0x10], rsi
00422635  push     rdi
00422636  sub      rsp, 0x20
0042263A  movzx    eax, byte ptr [rdx]
0042263D  xor      r9d, r9d
00422640  mov      rsi, r8
00422643  mov      rdi, rdx
00422646  mov      r11, rcx
00422649  mov      r10, rdx
0042264C  test     al, al
0042264E  je       0x140422666
00422650  imul     r9d, r9d, 0x21
00422654  lea      r10, [r10 + 1]
00422658  movsx    eax, al
0042265B  add      r9d, eax
0042265E  movzx    eax, byte ptr [r10]
00422662  test     al, al
00422664  jne      0x140422650
00422666  mov      rcx, qword ptr [rcx + 8]
0042266A  mov      qword ptr [rsp + 0x30], rbx
0042266F  test     rcx, rcx
00422672  je       0x1404226a8
00422674  xor      edx, edx
00422676  mov      eax, r9d
00422679  div      dword ptr [r11 + 0x10]
0042267D  mov      rbx, qword ptr [rcx + rdx*8]
00422681  test     rbx, rbx
00422684  je       0x1404226a8
00422686  nop      word ptr [rax + rax]
00422690  mov      rcx, qword ptr [rbx + 0x10]
00422694  mov      rdx, rdi
00422697  call     0x140503d4c
0042269C  test     eax, eax
0042269E  je       0x1404226ba
004226A0  mov      rbx, qword ptr [rbx]
004226A3  test     rbx, rbx
004226A6  jne      0x140422690
004226A8  xor      eax, eax
004226AA  mov      rbx, qword ptr [rsp + 0x30]
004226AF  mov      rsi, qword ptr [rsp + 0x38]
004226B4  add      rsp, 0x20
004226B8  pop      rdi
004226B9  ret      
004226BA  lea      rdx, [rbx + 0x18]
004226BE  mov      rcx, rsi
004226C1  call     0x1403fd770
004226C6  mov      rbx, qword ptr [rsp + 0x30]
004226CB  mov      eax, 1
004226D0  mov      rsi, qword ptr [rsp + 0x38]
004226D5  add      rsp, 0x20
004226D9  pop      rdi
004226DA  ret      
004226DB  int3     
004226DC  int3     
004226DD  int3     
004226DE  int3     
004226DF  int3     
004226E0  mov      qword ptr [rsp + 0x18], rbp
004226E5  push     rdi
004226E6  sub      rsp, 0x20
004226EA  mov      rdi, rcx
004226ED  xor      ebp, ebp
004226EF  mov      rcx, qword ptr [rcx + 8]
004226F3  test     rcx, rcx
004226F6  je       0x14042275e
004226F8  mov      qword ptr [rsp + 0x38], rsi
004226FD  mov      esi, ebp
004226FF  cmp      dword ptr [rdi + 0x10], ebp
00422702  jbe      0x140422750
00422704  mov      qword ptr [rsp + 0x30], rbx
00422709  nop      dword ptr [rax]
00422710  mov      ebx, esi
00422712  mov      rax, rcx
00422715  mov      rbx, qword ptr [rcx + rbx*8]
00422719  test     rbx, rbx
0042271C  je       0x140422741
0042271E  nop      
00422720  lea      rcx, [rbx + 0x10]
00422724  call     0x1403fd740
00422729  lea      rcx, [rbx + 0x18]
0042272D  call     0x1403fd740
00422732  mov      rbx, qword ptr [rbx]
00422735  test     rbx, rbx
00422738  jne      0x140422720
0042273A  mov      rcx, qword ptr [rdi + 8]
0042273E  mov      rax, rcx
00422741  inc      esi
00422743  cmp      esi, dword ptr [rdi + 0x10]
00422746  jb       0x140422710
00422748  mov      rbx, qword ptr [rsp + 0x30]
0042274D  mov      rcx, rax
00422750  call     0x14045e690
00422755  mov      rsi, qword ptr [rsp + 0x38]
0042275A  mov      qword ptr [rdi + 8], rbp
0042275E  mov      rcx, qword ptr [rdi + 0x20]
00422762  mov      dword ptr [rdi + 0x14], ebp
00422765  mov      qword ptr [rdi + 0x18], rbp
00422769  call     0x140407b40
0042276E  mov      qword ptr [rdi + 0x20], rbp
00422772  mov      rbp, qword ptr [rsp + 0x40]
00422777  add      rsp, 0x20
0042277B  pop      rdi
0042277C  ret      
0042277D  int3     
0042277E  int3     
0042277F  int3     
00422780  mov      qword ptr [rsp + 8], rbx
00422785  mov      qword ptr [rsp + 0x10], rbp
0042278A  mov      qword ptr [rsp + 0x18], rsi
0042278F  push     rdi
00422790  sub      rsp, 0x20
00422794  mov      r10, qword ptr [rcx + 8]
00422798  mov      rsi, rdx
0042279B  mov      rbp, rcx
0042279E  test     r10, r10
004227A1  je       0x1404227fe
004227A3  movzx    r8d, byte ptr [rdx]
004227A7  xor      eax, eax
004227A9  mov      r9, rdx
004227AC  test     r8b, r8b
004227AF  je       0x1404227c7
004227B1  imul     eax, eax, 0x21
004227B4  lea      r9, [r9 + 1]
004227B8  movsx    ecx, r8b
004227BC  movzx    r8d, byte ptr [r9]
004227C0  add      eax, ecx
004227C2  test     r8b, r8b
004227C5  jne      0x1404227b1
004227C7  xor      edx, edx
004227C9  div      dword ptr [rbp + 0x10]
004227CC  mov      rbx, qword ptr [r10 + rdx*8]
004227D0  lea      rdi, [r10 + rdx*8]
004227D4  test     rbx, rbx
004227D7  je       0x1404227fe
004227D9  nop      dword ptr [rax]
004227E0  mov      rcx, qword ptr [rbx + 0x10]
004227E4  mov      rdx, rsi
004227E7  call     0x140503d4c
004227EC  mov      rcx, qword ptr [rbx]
004227EF  test     eax, eax
004227F1  je       0x140422815
004227F3  mov      rdi, rbx
004227F6  mov      rbx, rcx
004227F9  test     rcx, rcx
004227FC  jne      0x1404227e0
004227FE  xor      eax, eax
00422800  mov      rbx, qword ptr [rsp + 0x30]
00422805  mov      rbp, qword ptr [rsp + 0x38]
0042280A  mov      rsi, qword ptr [rsp + 0x40]
0042280F  add      rsp, 0x20
00422813  pop      rdi
00422814  ret      
00422815  mov      qword ptr [rdi], rcx
00422818  lea      rcx, [rbx + 0x10]
0042281C  call     0x1403fd740
00422821  lea      rcx, [rbx + 0x18]
00422825  call     0x1403fd740
0042282A  mov      rax, qword ptr [rbp + 0x18]
0042282E  mov      qword ptr [rbx], rax
00422831  sub      dword ptr [rbp + 0x14], 1
00422835  mov      qword ptr [rbp + 0x18], rbx
00422839  jne      0x140422843
0042283B  mov      rcx, rbp
0042283E  call     0x1404226e0
00422843  mov      eax, 1
00422848  jmp      0x140422800
0042284A  int3     
0042284B  int3     
0042284C  int3     
0042284D  int3     
0042284E  int3     
0042284F  int3     
00422850  xor      eax, eax
00422852  mov      dword ptr [rcx + 8], 0xffffffff
00422859  mov      qword ptr [rcx + 0x18], rax
0042285D  mov      qword ptr [rcx + 0x10], rax
00422861  lea      rax, [rip + 0xb2a8]
00422868  mov      qword ptr [rcx + 0x20], rax
0042286C  mov      rax, rcx
0042286F  ret      
00422870  mov      r11d, dword ptr [rcx]
00422873  mov      r10d, dword ptr [rdx]
00422876  cmp      r11d, r8d
00422879  jne      0x140422893
0042287B  cmp      r10d, r8d
0042287E  jle      0x140422888
00422880  cmp      dword ptr [r9], r8d
00422883  jg       0x1404228c5
00422885  cmp      r10d, r8d
00422888  jge      0x14042288f
0042288A  cmp      dword ptr [r9], r8d
0042288D  jl       0x1404228c5
0042288F  mov      eax, dword ptr [rcx + 4]
00422892  ret      
00422893  cmp      r10d, r8d
00422896  je       0x1404228c5
00422898  cmp      r11d, r8d
0042289B  jge      0x1404228a5
0042289D  cmp      r10d, r8d
004228A0  jl       0x1404228c5
004228A2  cmp      r11d, r8d
004228A5  jle      0x1404228ac
004228A7  cmp      r10d, r8d
004228AA  jg       0x1404228c5
004228AC  mov      eax, dword ptr [rdx + 4]
004228AF  sub      r8d, r11d
004228B2  mov      ecx, dword ptr [rcx + 4]
004228B5  sub      r10d, r11d
004228B8  sub      eax, ecx
004228BA  imul     eax, r8d
004228BE  cdq      
004228BF  idiv     r10d
004228C2  add      eax, ecx
004228C4  ret      
004228C5  mov      eax, 0xffffffff
004228CA  ret      
004228CB  int3     
004228CC  int3     
004228CD  int3     
004228CE  int3     
004228CF  int3     
004228D0  mov      r11, rsp
004228D3  push     rsi
004228D4  push     rdi
004228D5  sub      rsp, 0xf8
004228DC  mov      rax, qword ptr [rip + 0x2420f5]
004228E3  xor      rax, rsp
004228E6  mov      qword ptr [rsp + 0xb0], rax
004228EE  mov      r10d, dword ptr [r9]
004228F1  mov      rsi, rcx
004228F4  mov      rax, qword ptr [rsp + 0x140]
004228FC  mov      edi, dword ptr [r9 + 8]
00422900  dec      edi
00422902  mov      dword ptr [rsp + 0x40], r8d
00422907  mov      qword ptr [rsp + 0x80], rdx
0042290F  mov      rax, qword ptr [rax]
00422912  mov      qword ptr [rsp + 0x70], rax
00422917  mov      eax, dword ptr [r9 + 4]
0042291B  mov      dword ptr [rsp + 0x48], eax
0042291F  mov      dword ptr [r11 - 0x64], eax
00422923  mov      eax, dword ptr [r9 + 0xc]
00422927  dec      eax
00422929  mov      qword ptr [rsp + 0x98], rcx
00422931  cmp      dword ptr [rcx + 8], 3
00422935  mov      dword ptr [rsp + 0x6c], r10d
0042293A  mov      dword ptr [r11 - 0x68], r10d
0042293E  mov      dword ptr [r11 - 0x60], edi
00422942  mov      dword ptr [r11 - 0x5c], eax
00422946  jge      0x14042294f
00422948  xor      eax, eax
0042294A  jmp      0x140422e6d
0042294F  mov      r8d, dword ptr [rsp + 0x138]
00422957  mov      ecx, r8d
0042295A  mov      qword ptr [rsp + 0xf0], rbx
00422962  and      ecx, 4
00422965  mov      qword ptr [rsp + 0xe8], rbp
0042296D  mov      qword ptr [rsp + 0xe0], r12
00422975  mov      qword ptr [rsp + 0xd8], r13
0042297D  mov      qword ptr [rsp + 0xd0], r14
00422985  mov      qword ptr [rsp + 0xc8], r15
0042298D  mov      dword ptr [rsp + 0x54], r8d
00422992  test     r8b, 1
00422996  je       0x1404229ae
00422998  test     ecx, ecx
0042299A  lea      rax, [rip + 0xb34f]
004229A1  lea      rdx, [rip + 0xb168]
004229A8  cmove    rax, rdx
004229AC  jmp      0x1404229de
004229AE  test     r8b, 0x10
004229B2  je       0x1404229ca
004229B4  test     ecx, ecx
004229B6  lea      rax, [rip + 0xb413]
004229BD  lea      rdx, [rip + 0xb36c]
004229C4  cmove    rax, rdx
004229C8  jmp      0x1404229de
004229CA  test     ecx, ecx
004229CC  lea      rax, [rip + 0xb17d]
004229D3  lea      rdx, [rip + 0xb2b6]
004229DA  cmovne   rax, rdx
004229DE  mov      qword ptr [rsi + 0x20], rax
004229E2  xor      ebp, ebp
004229E4  mov      r11, qword ptr [rsi]
004229E7  mov      eax, 1
004229EC  mov      r9d, dword ptr [rsi + 8]
004229F0  movzx    edx, ax
004229F3  movzx    r14d, word ptr [r11 + 2]
004229F8  mov      dword ptr [rsp + 0x68], r14d
004229FD  mov      ebx, r14d
00422A00  cmp      r9d, eax
00422A03  jle      0x140422a42
00422A05  mov      r8d, eax
00422A08  nop      dword ptr [rax + rax]
00422A10  movsx    rax, dx
00422A14  movzx    ecx, word ptr [r11 + rax*4 + 2]
00422A1A  cmp      ecx, ebx
00422A1C  jae      0x140422a25
00422A1E  mov      ebx, ecx
00422A20  mov      ebp, r8d
00422A23  jmp      0x140422a2c
00422A25  cmp      ecx, r14d
00422A28  cmova    r14d, ecx
00422A2C  inc      dx
00422A2F  movsx    r8d, dx
00422A33  cmp      r8d, r9d
00422A36  jl       0x140422a10
00422A38  mov      r8d, dword ptr [rsp + 0x54]
00422A3D  mov      dword ptr [rsp + 0x68], r14d
00422A42  xor      edx, edx
00422A44  mov      eax, ebp
00422A46  mov      esi, 1
00422A4B  movzx    r12d, word ptr [r11 + rax*4]
00422A50  lea      eax, [rbp + 1]
00422A53  div      r9d
00422A56  lea      eax, [r9 - 1]
00422A5A  mov      r13d, r12d
00422A5D  add      eax, ebp
00422A5F  mov      r15d, edx
00422A62  movzx    ecx, word ptr [r11 + r15*4]
00422A67  xor      edx, edx
00422A69  movzx    ebp, word ptr [r11 + r15*4 + 2]
00422A6F  sub      ecx, r12d
00422A72  div      r9d
00422A75  lea      r9, [r15*4]
00422A7D  mov      eax, ecx
00422A7F  mov      r14d, edx
00422A82  cdq      
00422A83  xor      eax, edx
00422A85  mov      qword ptr [rsp + 0x88], r9
00422A8D  sub      eax, edx
00422A8F  mov      edx, 0xffffffff
00422A94  test     ecx, ecx
00422A96  cmovns   dx, si
00422A9A  sub      ebp, ebx
00422A9C  mov      dword ptr [rsp + 0x54], edx
00422AA0  test     ebp, ebp
00422AA2  jle      0x140422abc
00422AA4  cdq      
00422AA5  idiv     ebp
00422AA7  mov      r9d, edx
00422AAA  mov      dword ptr [rsp + 0x64], edx
00422AAE  sub      r9d, ebp
00422AB1  mov      dword ptr [rsp + 0x60], eax
00422AB5  mov      dword ptr [rsp + 0x50], r9d
00422ABA  jmp      0x140422ad4
00422ABC  mov      eax, dword ptr [rsp + 0x40]
00422AC0  mov      dword ptr [rsp + 0x60], eax
00422AC4  mov      eax, dword ptr [rsp + 0x40]
00422AC8  mov      dword ptr [rsp + 0x64], eax
00422ACC  mov      eax, dword ptr [rsp + 0x40]
00422AD0  mov      dword ptr [rsp + 0x50], eax
00422AD4  movzx    ecx, word ptr [r11 + r14*4]
00422AD9  lea      r9, [r14*4]
00422AE1  sub      ecx, r12d
00422AE4  mov      qword ptr [rsp + 0x90], r9
00422AEC  mov      eax, ecx
00422AEE  cdq      
00422AEF  xor      eax, edx
00422AF1  sub      eax, edx
00422AF3  mov      edx, 0xffffffff
00422AF8  test     ecx, ecx
00422AFA  cmovns   dx, si
00422AFE  movzx    esi, word ptr [r11 + r9 + 2]
00422B04  sub      esi, ebx
00422B06  mov      dword ptr [rsp + 0x78], edx
00422B0A  test     esi, esi
00422B0C  jle      0x140422b1f
00422B0E  cdq      
00422B0F  idiv     esi
00422B11  mov      dword ptr [rsp + 0x58], eax
00422B15  mov      eax, edx
00422B17  sub      eax, esi
00422B19  mov      dword ptr [rsp + 0x5c], edx
00422B1D  jmp      0x140422b33
00422B1F  mov      eax, dword ptr [rsp + 0x40]
00422B23  mov      dword ptr [rsp + 0x58], eax
00422B27  mov      eax, dword ptr [rsp + 0x40]
00422B2B  mov      dword ptr [rsp + 0x5c], eax
00422B2F  mov      eax, dword ptr [rsp + 0x40]
00422B33  mov      r11d, dword ptr [rsp + 0x48]
00422B38  mov      dword ptr [rsp + 0x4c], eax
00422B3C  and      r8d, 8
00422B40  je       0x140422b4d
00422B42  mov      ecx, dword ptr [rsp + 0xac]
00422B49  sub      ecx, ebx
00422B4B  jmp      0x140422b52
00422B4D  mov      ecx, ebx
00422B4F  sub      ecx, r11d
00422B52  mov      r9d, dword ptr [rsp + 0x40]
00422B57  mov      eax, ebx
00422B59  mov      edx, r9d
00422B5C  neg      edx
00422B5E  test     r8d, r8d
00422B61  cmove    edx, r9d
00422B65  sub      eax, r11d
00422B68  add      dword ptr [rsp + 0x74], eax
00422B6C  cmp      ebx, dword ptr [rsp + 0x68]
00422B70  ja       0x140422e38
00422B76  imul     r9d, ecx
00422B7A  movsxd   rax, r9d
00422B7D  add      rax, qword ptr [rsp + 0x80]
00422B85  mov      qword ptr [rsp + 0x40], rax
00422B8A  movsxd   rax, edx
00422B8D  mov      qword ptr [rsp + 0x80], rax
00422B95  nop      word ptr [rax + rax]
00422BA0  mov      r11, qword ptr [rsp + 0x98]
00422BA8  mov      rcx, qword ptr [rsp + 0x88]
00422BB0  mov      r9, qword ptr [r11]
00422BB3  movzx    eax, word ptr [r9 + rcx + 2]
00422BB9  cmp      ebx, eax
00422BBB  jne      0x140422c5b
00422BC1  mov      r8d, dword ptr [r11 + 8]
00422BC5  lea      eax, [r15 + 1]
00422BC9  movzx    r12d, word ptr [r9 + rcx]
00422BCE  xor      edx, edx
00422BD0  div      r8d
00422BD3  movzx    ebp, word ptr [r9 + rdx*4 + 2]
00422BD9  lea      rcx, [r9 + rdx*4]
00422BDD  mov      r15d, edx
00422BE0  sub      ebp, ebx
00422BE2  jne      0x140422c0e
00422BE4  nop      dword ptr [rax]
00422BE8  nop      dword ptr [rax + rax]
00422BF0  movzx    r12d, word ptr [rcx]
00422BF4  lea      eax, [r15 + 1]
00422BF8  xor      edx, edx
00422BFA  div      r8d
00422BFD  movzx    ebp, word ptr [r9 + rdx*4 + 2]
00422C03  lea      rcx, [r9 + rdx*4]
00422C07  mov      r15d, edx
00422C0A  sub      ebp, ebx
00422C0C  je       0x140422bf0
00422C0E  movzx    ecx, word ptr [r9 + r15*4]
00422C13  lea      rax, [r15*4]
00422C1B  mov      qword ptr [rsp + 0x88], rax
00422C23  mov      r8d, ecx
00422C26  mov      eax, r12d
00422C29  sub      eax, ecx
00422C2B  mov      ecx, 1
00422C30  sub      r8d, r12d
00422C33  cmovns   eax, r8d
00422C37  cdq      
00422C38  idiv     ebp
00422C3A  mov      dword ptr [rsp + 0x60], eax
00422C3E  mov      eax, edx
00422C40  sub      eax, ebp
00422C42  mov      dword ptr [rsp + 0x64], edx
00422C46  mov      dword ptr [rsp + 0x50], eax
00422C4A  test     r8d, r8d
00422C4D  mov      eax, 0xffffffff
00422C52  cmovns   ax, cx
00422C56  mov      word ptr [rsp + 0x54], ax
00422C5B  mov      rcx, qword ptr [rsp + 0x90]
00422C63  movzx    eax, word ptr [r9 + rcx + 2]
00422C69  cmp      ebx, eax
00422C6B  jb       0x140422d0e
00422C71  mov      r8d, dword ptr [r11 + 8]
00422C75  xor      edx, edx
00422C77  movzx    r13d, word ptr [r9 + rcx]
00422C7C  lea      eax, [r8 - 1]
00422C80  add      eax, r14d
00422C83  div      r8d
00422C86  movzx    esi, word ptr [r9 + rdx*4 + 2]
00422C8C  lea      rcx, [r9 + rdx*4]
00422C90  mov      r14d, edx
00422C93  sub      esi, ebx
00422C95  jne      0x140422cc1
00422C97  nop      word ptr [rax + rax]
00422CA0  movzx    r13d, word ptr [rcx]
00422CA4  lea      eax, [r8 - 1]
00422CA8  add      eax, r14d
00422CAB  xor      edx, edx
00422CAD  div      r8d
00422CB0  movzx    esi, word ptr [r9 + rdx*4 + 2]
00422CB6  lea      rcx, [r9 + rdx*4]
00422CBA  mov      r14d, edx
00422CBD  sub      esi, ebx
00422CBF  je       0x140422ca0
00422CC1  movzx    ecx, word ptr [r9 + r14*4]
00422CC6  lea      rax, [r14*4]
00422CCE  mov      qword ptr [rsp + 0x90], rax
00422CD6  mov      r8d, ecx
00422CD9  mov      eax, r13d
00422CDC  sub      eax, ecx
00422CDE  mov      ecx, 1
00422CE3  sub      r8d, r13d
00422CE6  cmovns   eax, r8d
00422CEA  cdq      
00422CEB  idiv     esi
00422CED  mov      dword ptr [rsp + 0x58], eax
00422CF1  mov      eax, edx
00422CF3  sub      eax, esi
00422CF5  mov      dword ptr [rsp + 0x5c], edx
00422CF9  mov      dword ptr [rsp + 0x4c], eax
00422CFD  test     r8d, r8d
00422D00  mov      eax, 0xffffffff
00422D05  cmovns   ax, cx
00422D09  mov      word ptr [rsp + 0x78], ax
00422D0E  cmp      ebx, dword ptr [rsp + 0x48]
00422D12  jl       0x140422dab
00422D18  cmp      ebx, dword ptr [rsp + 0xac]
00422D1F  jg       0x140422dab
00422D25  cmp      r13d, r12d
00422D28  ja       0x140422d42
00422D2A  cmp      r12d, edi
00422D2D  jge      0x140422d32
00422D2F  mov      edi, r12d
00422D32  sub      edi, r10d
00422D35  cmp      r13d, r10d
00422D38  jle      0x140422d5a
00422D3A  mov      r8d, r13d
00422D3D  sub      r8d, r10d
00422D40  jmp      0x140422d5d
00422D42  cmp      r13d, edi
00422D45  jge      0x140422d4a
00422D47  mov      edi, r13d
00422D4A  sub      edi, r10d
00422D4D  cmp      r12d, r10d
00422D50  jle      0x140422d5a
00422D52  mov      r8d, r12d
00422D55  sub      r8d, r10d
00422D58  jmp      0x140422d5d
00422D5A  xor      r8d, r8d
00422D5D  mov      rdx, qword ptr [rsp + 0x40]
00422D62  lea      rax, [rsp + 0x70]
00422D67  mov      qword ptr [rsp + 0x30], rax
00422D6C  mov      r9d, edi
00422D6F  lea      rax, [rsp + 0xa0]
00422D77  mov      rcx, r11
00422D7A  mov      qword ptr [rsp + 0x28], rax
00422D7F  mov      eax, dword ptr [rsp + 0x130]
00422D86  mov      dword ptr [rsp + 0x20], eax
00422D8A  call     qword ptr [r11 + 0x20]
00422D8E  mov      eax, dword ptr [rsp + 0xa4]
00422D95  mov      edi, dword ptr [rsp + 0xa8]
00422D9C  mov      dword ptr [rsp + 0x48], eax
00422DA0  mov      eax, dword ptr [rsp + 0xa0]
00422DA7  mov      dword ptr [rsp + 0x6c], eax
00422DAB  inc      dword ptr [rsp + 0x74]
00422DAF  inc      ebx
00422DB1  movsx    ecx, word ptr [rsp + 0x78]
00422DB6  movsx    r9d, word ptr [rsp + 0x54]
00422DBC  mov      edx, ecx
00422DBE  imul     edx, dword ptr [rsp + 0x58]
00422DC3  mov      r10d, r9d
00422DC6  imul     r10d, dword ptr [rsp + 0x60]
00422DCC  mov      rax, qword ptr [rsp + 0x80]
00422DD4  add      qword ptr [rsp + 0x40], rax
00422DD9  mov      r8d, dword ptr [rsp + 0x5c]
00422DDE  add      r8d, dword ptr [rsp + 0x4c]
00422DE3  add      edx, r13d
00422DE6  mov      r11d, dword ptr [rsp + 0x64]
00422DEB  add      r10d, r12d
00422DEE  add      r11d, dword ptr [rsp + 0x50]
00422DF3  mov      eax, r8d
00422DF6  test     r8d, r8d
00422DF9  lea      r13d, [rdx + rcx]
00422DFD  mov      ecx, r11d
00422E00  cmovle   r13d, edx
00422E04  lea      r12d, [r10 + r9]
00422E08  sub      eax, esi
00422E0A  test     r8d, r8d
00422E0D  cmovle   eax, r8d
00422E11  test     r11d, r11d
00422E14  mov      dword ptr [rsp + 0x4c], eax
00422E18  cmovle   r12d, r10d
00422E1C  mov      r10d, dword ptr [rsp + 0x6c]
00422E21  sub      ecx, ebp
00422E23  test     r11d, r11d
00422E26  cmovle   ecx, r11d
00422E2A  mov      dword ptr [rsp + 0x50], ecx
00422E2E  cmp      ebx, dword ptr [rsp + 0x68]
00422E32  jbe      0x140422ba0
00422E38  mov      r15, qword ptr [rsp + 0xc8]
00422E40  mov      eax, 1
00422E45  mov      r14, qword ptr [rsp + 0xd0]
00422E4D  mov      r13, qword ptr [rsp + 0xd8]
00422E55  mov      r12, qword ptr [rsp + 0xe0]
00422E5D  mov      rbp, qword ptr [rsp + 0xe8]
00422E65  mov      rbx, qword ptr [rsp + 0xf0]
00422E6D  mov      rcx, qword ptr [rsp + 0xb0]
00422E75  xor      rcx, rsp
00422E78  call     0x1404f77a0
00422E7D  add      rsp, 0xf8
00422E84  pop      rdi
00422E85  pop      rsi
00422E86  ret      
00422E87  int3     
00422E88  int3     
00422E89  int3     
00422E8A  int3     
00422E8B  int3     
00422E8C  int3     
00422E8D  int3     
00422E8E  int3     
00422E8F  int3     
00422E90  push     rbx
00422E92  push     rbp
00422E93  push     rsi
00422E94  push     rdi
00422E95  push     r12
00422E97  push     r13
00422E99  push     r14
00422E9B  push     r15
00422E9D  sub      rsp, 0x78
00422EA1  mov      rax, qword ptr [rip + 0x241b30]
00422EA8  xor      rax, rsp
00422EAB  mov      qword ptr [rsp + 0x68], rax
00422EB0  mov      rax, qword ptr [rsp + 0xf0]
00422EB8  mov      r14, rcx
00422EBB  mov      dword ptr [rsp + 0x48], r8d
00422EC0  mov      qword ptr [rsp + 0x50], rdx
00422EC5  mov      rax, qword ptr [rax]
00422EC8  mov      qword ptr [rsp + 0x40], rax
00422ECD  mov      eax, dword ptr [r9]
00422ED0  mov      dword ptr [rsp + 0x58], eax
00422ED4  mov      eax, dword ptr [r9 + 4]
00422ED8  mov      dword ptr [rsp + 0x5c], eax
00422EDC  mov      eax, dword ptr [r9 + 8]
00422EE0  dec      eax
00422EE2  mov      dword ptr [rsp + 0x60], eax
00422EE6  mov      eax, dword ptr [r9 + 0xc]
00422EEA  dec      eax
00422EEC  cmp      dword ptr [rcx + 8], 3
00422EF0  mov      dword ptr [rsp + 0x64], eax
00422EF4  jl       0x140423292
00422EFA  mov      r12d, dword ptr [rsp + 0xe8]
00422F02  mov      ecx, r12d
00422F05  and      ecx, 4
00422F08  test     r12b, 1
00422F0C  je       0x140422f24
00422F0E  test     ecx, ecx
00422F10  lea      rax, [rip + 0xadd9]
00422F17  lea      rdx, [rip + 0xabf2]
00422F1E  cmove    rax, rdx
00422F22  jmp      0x140422f54
00422F24  test     r12b, 0x10
00422F28  je       0x140422f40
00422F2A  test     ecx, ecx
00422F2C  lea      rax, [rip + 0xae9d]
00422F33  lea      rdx, [rip + 0xadf6]
00422F3A  cmove    rax, rdx
00422F3E  jmp      0x140422f54
00422F40  test     ecx, ecx
00422F42  lea      rax, [rip + 0xac07]
00422F49  lea      rdx, [rip + 0xad40]
00422F50  cmovne   rax, rdx
00422F54  mov      qword ptr [r14 + 0x20], rax
00422F58  lea      r13, [rip + 0x307af1]
00422F5F  mov      ebx, dword ptr [r14 + 8]
00422F63  xor      r15d, r15d
00422F66  mov      qword ptr [r14 + 0x10], 0
00422F6E  test     ebx, ebx
00422F70  jle      0x140423292
00422F76  xor      ebp, ebp
00422F78  nop      dword ptr [rax + rax]
00422F80  mov      rcx, qword ptr [r14]
00422F83  inc      r15d
00422F86  mov      eax, r15d
00422F89  cdq      
00422F8A  idiv     ebx
00422F8C  movzx    r9d, word ptr [rcx + rbp + 2]
00422F92  movsx    rax, dx
00422F96  movzx    r8d, word ptr [rcx + rax*4 + 2]
00422F9C  movzx    edx, word ptr [rcx + rax*4]
00422FA0  cmp      r9w, r8w
00422FA4  movzx    eax, word ptr [rcx + rbp]
00422FA8  movzx    ecx, dx
00422FAB  cmovae   cx, ax
00422FAF  cmovae   ax, dx
00422FB3  movzx    r11d, ax
00422FB7  movzx    eax, r9w
00422FBB  cmovae   ax, r8w
00422FC0  cmovae   r8w, r9w
00422FC5  movzx    esi, r8w
00422FC9  movzx    r10d, ax
00422FCD  sub      esi, r10d
00422FD0  je       0x140423063
00422FD6  mov      r9, r13
00422FD9  movzx    ecx, cx
00422FDC  sub      ecx, r11d
00422FDF  mov      eax, 1
00422FE4  sub      eax, esi
00422FE6  mov      r8d, ecx
00422FE9  sar      r8d, 0x1f
00422FED  add      r13, 0x28
00422FF1  mov      dword ptr [r9 + 0x18], eax
00422FF5  and      r8d, 0xfffffffe
00422FF9  mov      eax, ecx
00422FFB  mov      qword ptr [r9], 0
00423002  cdq      
00423003  mov      dword ptr [r9 + 8], r11d
00423007  xor      eax, edx
00423009  mov      dword ptr [r9 + 0xc], r10d
0042300D  sub      eax, edx
0042300F  mov      dword ptr [r9 + 0x24], esi
00423013  cdq      
00423014  mov      dword ptr [r9 + 0x20], esi
00423018  idiv     esi
0042301A  inc      r8d
0042301D  mov      dword ptr [r9 + 0x10], r8d
00423021  imul     r8d, eax
00423025  mov      dword ptr [r9 + 0x1c], edx
00423029  lea      rdx, [r14 + 0x10]
0042302D  mov      dword ptr [r9 + 0x14], r8d
00423031  mov      rax, qword ptr [r14 + 0x10]
00423035  test     rax, rax
00423038  je       0x140423059
0042303A  nop      word ptr [rax + rax]
00423040  cmp      dword ptr [rax + 0xc], r10d
00423044  jg       0x140423059
00423046  jne      0x14042304e
00423048  cmp      dword ptr [rax + 8], r11d
0042304C  jg       0x140423059
0042304E  mov      rdx, rax
00423051  mov      rax, qword ptr [rax]
00423054  test     rax, rax
00423057  jne      0x140423040
00423059  mov      qword ptr [rdx], r9
0042305C  mov      qword ptr [r9], rax
0042305F  mov      ebx, dword ptr [r14 + 8]
00423063  add      rbp, 4
00423067  cmp      r15d, ebx
0042306A  jl       0x140422f80
00423070  mov      rax, qword ptr [r14 + 0x10]
00423074  test     rax, rax
00423077  je       0x140423292
0042307D  mov      qword ptr [r14 + 0x18], 0
00423085  movsx    ebp, word ptr [rax + 0xc]
00423089  mov      eax, ebp
0042308B  and      r12d, 8
0042308F  je       0x140423099
00423091  mov      ecx, dword ptr [rsp + 0x64]
00423095  sub      ecx, eax
00423097  jmp      0x14042309f
00423099  mov      ecx, eax
0042309B  sub      ecx, dword ptr [rsp + 0x5c]
0042309F  mov      edx, dword ptr [rsp + 0x48]
004230A3  mov      r13d, edx
004230A6  neg      r13d
004230A9  test     r12d, r12d
004230AC  mov      r12d, dword ptr [rsp + 0xe0]
004230B4  cmove    r13d, edx
004230B8  sub      eax, dword ptr [rsp + 0x5c]
004230BC  add      dword ptr [rsp + 0x44], eax
004230C0  xor      eax, eax
004230C2  imul     ecx, edx
004230C5  movsxd   r15, ecx
004230C8  add      r15, qword ptr [rsp + 0x50]
004230CD  nop      dword ptr [rax]
004230D0  mov      rcx, qword ptr [r14 + 0x10]
004230D4  test     rcx, rcx
004230D7  jne      0x1404230e2
004230D9  test     rax, rax
004230DC  je       0x14042328b
004230E2  lea      r8, [r14 + 0x18]
004230E6  test     rcx, rcx
004230E9  je       0x140423134
004230EB  movsx    r9d, bp
004230EF  nop      
004230F0  cmp      dword ptr [rcx + 0xc], r9d
004230F4  jne      0x140423134
004230F6  test     rax, rax
004230F9  je       0x140423110
004230FB  movsx    ecx, word ptr [rcx + 8]
004230FF  nop      
00423100  cmp      dword ptr [rax + 8], ecx
00423103  jge      0x140423110
00423105  mov      r8, rax
00423108  mov      rax, qword ptr [rax]
0042310B  test     rax, rax
0042310E  jne      0x140423100
00423110  mov      rcx, qword ptr [r14 + 0x10]
00423114  mov      qword ptr [r8], rcx
00423117  mov      rcx, qword ptr [r14 + 0x10]
0042311B  mov      rdx, qword ptr [rcx]
0042311E  mov      qword ptr [r14 + 0x10], rdx
00423122  mov      rcx, qword ptr [r8]
00423125  mov      qword ptr [rcx], rax
00423128  mov      rcx, qword ptr [r14 + 0x10]
0042312C  mov      r8, qword ptr [r8]
0042312F  test     rcx, rcx
00423132  jne      0x1404230f0
00423134  movsx    eax, bp
00423137  cmp      eax, dword ptr [rsp + 0x5c]
0042313B  jl       0x1404231ac
0042313D  cmp      eax, dword ptr [rsp + 0x64]
00423141  jg       0x1404231ac
00423143  mov      rdx, qword ptr [r14 + 0x18]
00423147  test     rdx, rdx
0042314A  je       0x1404231ac
0042314C  nop      dword ptr [rax]
00423150  mov      ecx, dword ptr [rdx + 8]
00423153  lea      rax, [rsp + 0x40]
00423158  mov      r10d, dword ptr [rsp + 0x58]
0042315D  xor      r8d, r8d
00423160  mov      rbx, qword ptr [rdx]
00423163  sub      ecx, r10d
00423166  cmp      dword ptr [rdx + 8], r10d
0042316A  mov      r9d, dword ptr [rsp + 0x60]
0042316F  cmovg    r8d, ecx
00423173  mov      qword ptr [rsp + 0x30], rax
00423178  mov      ecx, dword ptr [rbx + 8]
0042317B  lea      rax, [rsp + 0x58]
00423180  mov      edx, ecx
00423182  mov      qword ptr [rsp + 0x28], rax
00423187  sub      edx, r10d
0042318A  mov      dword ptr [rsp + 0x20], r12d
0042318F  sub      r9d, r10d
00423192  cmp      ecx, dword ptr [rsp + 0x60]
00423196  mov      rcx, r14
00423199  cmovl    r9d, edx
0042319D  mov      rdx, r15
004231A0  call     qword ptr [r14 + 0x20]
004231A4  mov      rdx, qword ptr [rbx]
004231A7  test     rdx, rdx
004231AA  jne      0x140423150
004231AC  mov      rdx, qword ptr [r14 + 0x18]
004231B0  xor      ecx, ecx
004231B2  test     rdx, rdx
004231B5  je       0x14042321f
004231B7  mov      rax, qword ptr [r14 + 0x10]
004231BB  test     rax, rax
004231BE  je       0x1404231cf
004231C0  sub      dword ptr [rdx + 0x24], 1
004231C4  je       0x1404231d8
004231C6  mov      rax, qword ptr [r14 + 0x10]
004231CA  test     rax, rax
004231CD  jne      0x1404231eb
004231CF  dec      dword ptr [rdx + 0x24]
004231D2  cmp      dword ptr [rdx + 0x24], -1
004231D6  jne      0x1404231eb
004231D8  mov      rax, qword ptr [rdx]
004231DB  test     rcx, rcx
004231DE  jne      0x1404231e6
004231E0  mov      qword ptr [r14 + 0x18], rax
004231E4  jmp      0x140423217
004231E6  mov      qword ptr [rcx], rax
004231E9  jmp      0x140423217
004231EB  mov      r9d, dword ptr [rdx + 0x14]
004231EF  add      r9d, dword ptr [rdx + 8]
004231F3  mov      eax, dword ptr [rdx + 0x1c]
004231F6  add      dword ptr [rdx + 0x18], eax
004231F9  mov      r8d, dword ptr [rdx + 0x18]
004231FD  mov      dword ptr [rdx + 8], r9d
00423201  js       0x140423214
00423203  mov      ecx, dword ptr [rdx + 0x10]
00423206  add      ecx, r9d
00423209  sub      r8d, dword ptr [rdx + 0x20]
0042320D  mov      dword ptr [rdx + 0x18], r8d
00423211  mov      dword ptr [rdx + 8], ecx
00423214  mov      rcx, rdx
00423217  mov      rdx, qword ptr [rdx]
0042321A  test     rdx, rdx
0042321D  jne      0x1404231b7
0042321F  mov      rax, qword ptr [r14 + 0x18]
00423223  test     rax, rax
00423226  je       0x140423279
00423228  nop      dword ptr [rax + rax]
00423230  mov      rcx, qword ptr [rax]
00423233  lea      r8, [r14 + 0x18]
00423237  xor      r9d, r9d
0042323A  mov      rdx, rax
0042323D  test     rcx, rcx
00423240  je       0x140423274
00423242  mov      eax, dword ptr [rcx + 8]
00423245  cmp      dword ptr [rdx + 8], eax
00423248  jle      0x140423262
0042324A  mov      qword ptr [r8], rcx
0042324D  mov      r9d, 1
00423253  mov      rax, qword ptr [rdx]
00423256  mov      rcx, qword ptr [rax]
00423259  mov      qword ptr [rdx], rcx
0042325C  mov      rax, qword ptr [r8]
0042325F  mov      qword ptr [rax], rdx
00423262  mov      r8, qword ptr [r8]
00423265  mov      rdx, qword ptr [r8]
00423268  mov      rcx, qword ptr [rdx]
0042326B  test     rcx, rcx
0042326E  jne      0x140423242
00423270  mov      rax, qword ptr [r14 + 0x18]
00423274  test     r9d, r9d
00423277  jne      0x140423230
00423279  inc      dword ptr [rsp + 0x44]
0042327D  inc      bp
00423280  movsxd   rcx, r13d
00423283  add      r15, rcx
00423286  jmp      0x1404230d0
0042328B  mov      eax, 1
00423290  jmp      0x140423294
00423292  xor      eax, eax
00423294  mov      rcx, qword ptr [rsp + 0x68]
00423299  xor      rcx, rsp
0042329C  call     0x1404f77a0
004232A1  add      rsp, 0x78
004232A5  pop      r15
004232A7  pop      r14
004232A9  pop      r13
004232AB  pop      r12
004232AD  pop      rdi
004232AE  pop      rsi
004232AF  pop      rbp
004232B0  pop      rbx
004232B1  ret      
004232B2  int3     
004232B3  int3     
004232B4  int3     
004232B5  int3     
004232B6  int3     
004232B7  int3     
004232B8  int3     
004232B9  int3     
004232BA  int3     
004232BB  int3     
004232BC  int3     
004232BD  int3     
004232BE  int3     
004232BF  int3     
004232C0  push     rbx
004232C2  sub      rsp, 0x60
004232C6  mov      eax, dword ptr [r8]
004232C9  movzx    ebx, dx
004232CC  test     eax, eax
004232CE  jne      0x1404232de
004232D0  cmp      dword ptr [r8 + 4], eax
004232D4  jne      0x1404232de
004232D6  mov      al, 1
004232D8  add      rsp, 0x60
004232DC  pop      rbx
004232DD  ret      
004232DE  xorps    xmm0, xmm0
004232E1  movaps   xmmword ptr [rsp + 0x50], xmm6
004232E6  cvtsi2ss xmm0, dword ptr [rcx + 4]
004232EB  movaps   xmmword ptr [rsp + 0x40], xmm7
004232F0  xorps    xmm2, xmm2
004232F3  cvtsi2ss xmm2, dword ptr [rcx]
004232F7  movaps   xmm1, xmm0
004232FA  movaps   xmmword ptr [rsp + 0x30], xmm8
00423300  movaps   xmmword ptr [rsp + 0x20], xmm9
00423306  xorps    xmm8, xmm8
0042330A  cvtsi2ss xmm8, eax
0042330F  mulss    xmm0, xmm0
00423313  xorps    xmm7, xmm7
00423316  cvtsi2ss xmm7, dword ptr [r8 + 4]
0042331C  movaps   xmm9, xmm8
00423320  mulss    xmm9, xmm2
00423325  mulss    xmm2, xmm2
00423329  mulss    xmm1, xmm7
0042332D  addss    xmm0, xmm2
00423331  addss    xmm9, xmm1
00423336  call     0x14050a11c
0042333B  mulss    xmm8, xmm8
00423340  movaps   xmm6, xmm0
00423343  mulss    xmm7, xmm7
00423347  addss    xmm8, xmm7
0042334C  movaps   xmm0, xmm8
00423350  call     0x14050a11c
00423355  movsd    xmm1, qword ptr [rip + 0x1e80eb]
0042335D  mulss    xmm6, xmm0
00423361  divss    xmm9, xmm6
00423366  cvtps2pd xmm0, xmm9
0042336A  call     0x140513b24
0042336F  movsd    xmm1, qword ptr [rip + 0x1e8219]
00423377  call     0x140513abc
0042337C  call     0x140509380
00423381  movaps   xmm9, xmmword ptr [rsp + 0x20]
00423387  xorps    xmm1, xmm1
0042338A  movaps   xmm8, xmmword ptr [rsp + 0x30]
00423390  movaps   xmm7, xmmword ptr [rsp + 0x40]
00423395  movaps   xmm6, xmmword ptr [rsp + 0x50]
0042339A  cvtsd2ss xmm1, xmm0
0042339E  movzx    eax, bx
004233A1  shr      eax, 1
004233A3  mulss    xmm1, dword ptr [rip + 0x17f19d]
004233AB  cvtps2pd xmm2, xmm1
004233AE  divsd    xmm2, qword ptr [rip + 0x169afa]
004233B6  cvttsd2si ecx, xmm2
004233BA  cmp      ecx, eax
004233BC  setle    al
004233BF  add      rsp, 0x60
004233C3  pop      rbx
004233C4  ret      
004233C5  int3     
004233C6  int3     
004233C7  int3     
004233C8  int3     
004233C9  int3     
004233CA  int3     
004233CB  int3     
004233CC  int3     
004233CD  int3     
004233CE  int3     
004233CF  int3     
004233D0  mov      qword ptr [rsp + 8], rbx
004233D5  mov      qword ptr [rsp + 0x10], rbp
004233DA  mov      qword ptr [rsp + 0x18], rsi
004233DF  mov      qword ptr [rsp + 0x20], rdi
004233E4  push     r12
004233E6  push     r14
004233E8  push     r15
004233EA  sub      rsp, 0x20
004233EE  xor      esi, esi
004233F0  mov      rbx, r8
004233F3  movzx    ebp, dx
004233F6  mov      r11, rcx
004233F9  cmp      dx, 1
004233FD  jne      0x140423434
004233FF  mov      rax, qword ptr [r8]
00423402  cmp      dword ptr [rcx], eax
00423404  jne      0x140423413
00423406  shr      rax, 0x20
0042340A  cmp      dword ptr [rcx + 4], eax
0042340D  je       0x14042359a
00423413  xor      al, al
00423415  mov      rbx, qword ptr [rsp + 0x40]
0042341A  mov      rbp, qword ptr [rsp + 0x48]
0042341F  mov      rsi, qword ptr [rsp + 0x50]
00423424  mov      rdi, qword ptr [rsp + 0x58]
00423429  add      rsp, 0x20
0042342D  pop      r15
0042342F  pop      r14
00423431  pop      r12
00423433  ret      
00423434  cmp      bp, 2
00423438  jne      0x140423452
0042343A  mov      r8d, dword ptr [r8]
0042343D  lea      rdx, [rcx + 8]
00423441  mov      r9, rdx
00423444  call     0x140422870
00423449  cmp      eax, dword ptr [rbx + 4]
0042344C  jne      0x140423413
0042344E  mov      al, 1
00423450  jmp      0x140423415
00423452  movzx    edi, si
00423455  cmp      si, bp
00423458  jge      0x140423590
0042345E  mov      r14d, dword ptr [r8 + 4]
00423462  mov      ecx, dword ptr [r8]
00423465  movsx    r15, bp
00423469  lea      r12d, [r15 - 1]
0042346D  nop      dword ptr [rax]
00423470  movsx    rax, di
00423474  mov      r10d, dword ptr [r11 + rax*8]
00423478  lea      r8, [r11 + rax*8]
0042347C  movsx    rdx, di
00423480  mov      rax, rdx
00423483  cmp      edx, r12d
00423486  jne      0x1404234e8
00423488  mov      r9d, dword ptr [r11]
0042348B  cmp      r10d, ecx
0042348E  jne      0x1404234bd
00423490  cmp      r9d, ecx
00423493  jle      0x1404234a3
00423495  cmp      dword ptr [r11 + rdx*8 - 8], ecx
0042349A  jg       0x14042356d
004234A0  cmp      r9d, ecx
004234A3  jge      0x140423530
004234A9  cmp      dword ptr [r11 + rdx*8 - 8], ecx
004234AE  jl       0x14042356d
004234B4  mov      eax, dword ptr [r8 + 4]
004234B8  jmp      0x140423572
004234BD  cmp      r9d, ecx
004234C0  je       0x14042356d
004234C6  cmp      r10d, ecx
004234C9  jge      0x1404234d7
004234CB  cmp      r9d, ecx
004234CE  jl       0x14042356d
004234D4  cmp      r10d, ecx
004234D7  jle      0x1404234e2
004234D9  cmp      r9d, ecx
004234DC  jg       0x14042356d
004234E2  mov      eax, dword ptr [r11 + 4]
004234E6  jmp      0x140423552
004234E8  mov      r9d, dword ptr [r11 + rdx*8 + 8]
004234ED  lea      rdx, [r11 + rdx*8]
004234F1  test     di, di
004234F4  jne      0x140423513
004234F6  cmp      r10d, ecx
004234F9  jne      0x140423536
004234FB  cmp      r9d, ecx
004234FE  jle      0x14042350a
00423500  cmp      dword ptr [r11 + r15*8 - 8], ecx
00423505  jg       0x14042356d
00423507  cmp      r9d, ecx
0042350A  jge      0x140423530
0042350C  cmp      dword ptr [r11 + r15*8 - 8], ecx
00423511  jmp      0x14042352e
00423513  cmp      r10d, ecx
00423516  jne      0x140423536
00423518  cmp      r9d, ecx
0042351B  jle      0x140423527
0042351D  cmp      dword ptr [r11 + rax*8 - 8], ecx
00423522  jg       0x14042356d
00423524  cmp      r9d, ecx
00423527  jge      0x140423530
00423529  cmp      dword ptr [r11 + rax*8 - 8], ecx
0042352E  jl       0x14042356d
00423530  mov      eax, dword ptr [r8 + 4]
00423534  jmp      0x140423572
00423536  cmp      r9d, ecx
00423539  je       0x14042356d
0042353B  cmp      r10d, ecx
0042353E  jge      0x140423548
00423540  cmp      r9d, ecx
00423543  jl       0x14042356d
00423545  cmp      r10d, ecx
00423548  jle      0x14042354f
0042354A  cmp      r9d, ecx
0042354D  jg       0x14042356d
0042354F  mov      eax, dword ptr [rdx + 0xc]
00423552  mov      r8d, dword ptr [r8 + 4]
00423556  sub      r9d, r10d
00423559  sub      eax, r8d
0042355C  mov      edx, ecx
0042355E  sub      edx, r10d
00423561  imul     eax, edx
00423564  cdq      
00423565  idiv     r9d
00423568  add      eax, r8d
0042356B  jmp      0x140423572
0042356D  mov      eax, 0xffffffff
00423572  cmp      eax, r14d
00423575  je       0x14042359a
00423577  cmp      eax, -1
0042357A  je       0x140423584
0042357C  cmp      eax, r14d
0042357F  jge      0x140423584
00423581  inc      si
00423584  inc      di
00423587  cmp      di, bp
0042358A  jl       0x140423470
00423590  test     sil, 1
00423594  je       0x140423413
0042359A  mov      al, 1
0042359C  jmp      0x140423415
004235A1  int3     
004235A2  int3     
004235A3  int3     
004235A4  int3     
004235A5  int3     
004235A6  int3     
004235A7  int3     
004235A8  int3     
004235A9  int3     
004235AA  int3     
004235AB  int3     
004235AC  int3     
004235AD  int3     
004235AE  int3     
004235AF  int3     
004235B0  mov      qword ptr [rsp + 0x18], rbp
004235B5  mov      qword ptr [rsp + 0x20], rsi
004235BA  push     rdi
004235BB  push     r15
004235BD  mov      ebp, 1
004235C2  mov      rdi, r9
004235C5  mov      dword ptr [r9], ebp
004235C8  mov      r15, r8
004235CB  mov      dword ptr [r8], ebp
004235CE  mov      rsi, rcx
004235D1  cmp      dx, 4
004235D5  jb       0x1404236cc
004235DB  movzx    eax, dx
004235DE  mov      r8d, dword ptr [rcx + rax*8 - 4]
004235E3  sub      r8d, dword ptr [rcx + 4]
004235E7  mov      qword ptr [rsp + 0x18], rbx
004235EC  mov      qword ptr [rsp + 0x20], r14
004235F1  lea      r14, [rcx + rax*8]
004235F5  lea      ebx, [rax - 1]
004235F8  lea      rax, [rcx + 4]
004235FC  test     r8d, r8d
004235FF  jle      0x140423608
00423601  movzx    edx, bp
00423604  xor      ecx, ecx
00423606  jmp      0x14042364a
00423608  xor      edx, edx
0042360A  test     r8d, r8d
0042360D  setns    dl
00423610  xor      ecx, ecx
00423612  dec      dx
00423615  test     r8d, r8d
00423618  js       0x14042364a
0042361A  nop      word ptr [rax + rax]
00423620  cmp      ecx, ebx
00423622  jge      0x14042364c
00423624  mov      edx, dword ptr [rax]
00423626  lea      r8, [rax + 8]
0042362A  sub      edx, dword ptr [r8]
0042362D  test     edx, edx
