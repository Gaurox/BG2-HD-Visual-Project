0042B350  mov      r11, rsp
0042B353  push     rbp
0042B354  push     r14
0042B356  push     r15
0042B358  lea      rbp, [r11 - 0x28]
0042B35C  sub      rsp, 0x110
0042B363  mov      rax, qword ptr [rip + 0x23966e]
0042B36A  xor      rax, rsp
0042B36D  mov      qword ptr [rbp - 0x70], rax
0042B371  xor      r14d, r14d
0042B374  cmp      dword ptr [rip + 0x2b48c55], r14d
0042B37B  mov      r15d, r14d
0042B37E  je       0x14042bbb5
0042B384  mov      qword ptr [r11 + 8], rbx
0042B388  lea      rbx, [rip + 0x2b48cc1]
0042B38F  mov      qword ptr [r11 + 0x10], rsi
0042B393  mov      esi, r14d
0042B396  mov      qword ptr [r11 + 0x18], rdi
0042B39A  mov      qword ptr [r11 - 0x28], r13
0042B39E  nop      
0042B3A0  mov      edi, dword ptr [rbx + 0x14]
0042B3A3  add      edi, dword ptr [rbx + 0x18]
0042B3A6  test     edi, edi
0042B3A8  jle      0x14042b433
0042B3AE  mov      eax, dword ptr [rip + 0x2b48bb8]
0042B3B4  mov      ecx, dword ptr [rbx + 0x28]
0042B3B7  shl      ecx, 0x15
0042B3BA  xor      ecx, eax
0042B3BC  and      ecx, 0x3fe00000
0042B3C2  xor      eax, ecx
0042B3C4  mov      dword ptr [rip + 0x2b48ba2], eax
0042B3CA  cmp      edi, dword ptr [rbx + 4]
0042B3CD  jge      0x14042b3f5
0042B3CF  cmp      esi, 1
0042B3D2  jne      0x14042b3f5
0042B3D4  movsxd   rax, dword ptr [rbx]
0042B3D7  xor      edx, edx
0042B3D9  mov      r8, rax
0042B3DC  imul     eax, edi
0042B3DF  shl      r8, 2
0042B3E3  movsxd   rcx, eax
0042B3E6  mov      rax, qword ptr [rbx + 0x20]
0042B3EA  lea      rcx, [rax + rcx*4]
0042B3EE  call     0x1404fab70
0042B3F3  inc      edi
0042B3F5  mov      rax, qword ptr [rbx + 0x20]
0042B3F9  mov      r9d, edi
0042B3FC  mov      r8d, dword ptr [rbx]
0042B3FF  xor      edx, edx
0042B401  mov      byte ptr [rsp + 0x28], r14b
0042B406  xor      ecx, ecx
0042B408  mov      qword ptr [rsp + 0x20], rax
0042B40D  call     0x140413600
0042B412  imul     edi, dword ptr [rbx]
0042B415  xor      edx, edx
0042B417  mov      rcx, qword ptr [rbx + 0x20]
0042B41B  movsxd   r8, edi
0042B41E  shl      r8, 2
0042B422  call     0x1404fab70
0042B427  mov      qword ptr [rbx + 8], r14
0042B42B  mov      qword ptr [rbx + 0x14], r14
0042B42F  mov      dword ptr [rbx + 0x10], r14d
0042B433  inc      esi
0042B435  add      rbx, 0x30
0042B439  cmp      esi, 2
0042B43C  jb       0x14042b3a0
0042B442  cmp      dword ptr [rip + 0x2b48b87], r14d
0042B449  lea      rdi, [rip - 0x42b450]
0042B450  mov      r13d, r14d
0042B453  jle      0x14042bb43
0042B459  mov      qword ptr [rsp + 0x108], r12
0042B461  lea      rdx, [rip + 0x105e76]
0042B468  movaps   xmmword ptr [rsp + 0xf0], xmm6
0042B470  mov      r12, r14
0042B473  movss    xmm6, dword ptr [rip + 0x1dff8d]
0042B47B  movaps   xmmword ptr [rsp + 0xe0], xmm7
0042B483  movsd    xmm7, qword ptr [rip + 0x1dffbd]
0042B48B  movaps   xmmword ptr [rsp + 0xd0], xmm8
0042B494  movss    xmm8, dword ptr [rip + 0x196163]
0042B49D  movaps   xmmword ptr [rsp + 0xc0], xmm9
0042B4A6  movss    xmm9, dword ptr [rip + 0x19514d]
0042B4AF  movaps   xmmword ptr [rsp + 0xb0], xmm10
0042B4B8  movss    xmm10, dword ptr [rip + 0x16408b]
0042B4C1  movaps   xmmword ptr [rsp + 0xa0], xmm11
0042B4CA  movss    xmm11, dword ptr [rip + 0x196131]
0042B4D3  nop      dword ptr [rax]
0042B4D7  nop      word ptr [rax + rax]
0042B4E0  lea      rsi, [r12 + r12*2]
0042B4E4  mov      ecx, dword ptr [rdi + rsi*4 + 0x2f5bf28]
0042B4EB  test     r12, r12
0042B4EE  jne      0x14042b500
0042B4F0  mov      ebx, ecx
0042B4F2  xor      ebx, dword ptr [rip + 0x2b48aec]
0042B4F8  or       ebx, dword ptr [rip + 0x2b48aea]
0042B4FE  jmp      0x14042b509
0042B500  mov      ebx, dword ptr [rdi + rsi*4 + 0x2f5bf1c]
0042B507  xor      ebx, ecx
0042B509  mov      eax, ecx
0042B50B  and      eax, 0xf
0042B50E  lea      r14, [rax + rax*4]
0042B512  bt       ebx, 0x14
0042B516  jae      0x14042b53c
0042B518  bt       ecx, 0x14
0042B51C  lea      rax, [rip + 0x105dc1]
0042B523  mov      ecx, 0xc11
0042B528  cmovb    rax, rdx
0042B52C  call     rax
0042B52E  mov      ecx, dword ptr [rdi + rsi*4 + 0x2f5bf28]
0042B535  lea      rdx, [rip + 0x105da2]
0042B53C  bt       ebx, 8
0042B540  jae      0x14042b55f
0042B542  bt       ecx, 8
0042B546  lea      rax, [rip + 0x105d97]
0042B54D  mov      ecx, 0xbe2
0042B552  cmovb    rax, rdx
0042B556  call     rax
0042B558  mov      ecx, dword ptr [rdi + rsi*4 + 0x2f5bf28]
0042B55F  test     ebx, 0x1e00
0042B565  jne      0x14042b56f
0042B567  test     ebx, 0x1e000
0042B56D  je       0x14042b593
0042B56F  mov      rax, rcx
0042B572  shr      rcx, 9
0042B576  shr      rax, 0xd
0042B57A  and      ecx, 0xf
0042B57D  and      eax, 0xf
0042B580  mov      ecx, dword ptr [rdi + rcx*4 + 0x5c12b0]
0042B587  mov      edx, dword ptr [rdi + rax*4 + 0x5c12b0]
0042B58E  call     0x1405312cc
0042B593  cmp      byte ptr [rip + 0x2b489ce], 0
0042B59A  je       0x14042b70c
0042B5A0  test     bl, 0xf
0042B5A3  je       0x14042b70c
0042B5A9  mov      ecx, dword ptr [rdi + r14*8 + 0x75c040]
0042B5B1  call     qword ptr [rip + 0x32b9c1]
0042B5B7  mov      ecx, dword ptr [rdi + r14*8 + 0x75c060]
0042B5BF  and      ebx, 0xc033ff7f
0042B5C5  or       ebx, 0x220040
0042B5CB  xor      r15d, r15d
0042B5CE  cmp      ecx, -1
0042B5D1  je       0x14042b5e4
0042B5D3  movd     xmm1, dword ptr [rip + 0x2b48a71]
0042B5DB  cvtdq2ps xmm1, xmm1
0042B5DE  call     qword ptr [rip + 0x32b9fc]
0042B5E4  mov      ecx, dword ptr [rdi + r14*8 + 0x75c058]
0042B5EC  cmp      ecx, -1
0042B5EF  je       0x14042b6a1
0042B5F5  xorps    xmm1, xmm1
0042B5F8  lea      r8, [rsp + 0x38]
0042B5FD  cvtsi2ss xmm1, dword ptr [rip + 0x2b48a0b]
0042B605  mov      edx, 1
0042B60A  xorps    xmm0, xmm0
0042B60D  movaps   xmm2, xmm6
0042B610  cvtsi2ss xmm0, dword ptr [rip + 0x2b489e8]
0042B618  divss    xmm1, xmm0
0042B61C  xorps    xmm0, xmm0
0042B61F  subss    xmm1, xmm6
0042B623  mulss    xmm1, xmm9
0042B628  maxss    xmm0, xmm1
0042B62C  minss    xmm2, xmm0
0042B630  movaps   xmm0, xmm10
0042B634  movaps   xmm1, xmm2
0042B637  addss    xmm1, xmm2
0042B63B  mulss    xmm2, xmm2
0042B63F  subss    xmm0, xmm1
0042B643  xorps    xmm1, xmm1
0042B646  cvtsi2ss xmm1, dword ptr [rip + 0x2b489c6]
0042B64E  mulss    xmm0, xmm2
0042B652  movaps   xmm2, xmm6
0042B655  movss    dword ptr [rsp + 0x38], xmm0
0042B65B  xorps    xmm0, xmm0
0042B65E  cvtsi2ss xmm0, dword ptr [rip + 0x2b4899e]
0042B666  divss    xmm1, xmm0
0042B66A  xorps    xmm0, xmm0
0042B66D  subss    xmm1, xmm6
0042B671  mulss    xmm1, xmm9
0042B676  maxss    xmm0, xmm1
0042B67A  minss    xmm2, xmm0
0042B67E  movaps   xmm0, xmm10
0042B682  movaps   xmm1, xmm2
0042B685  addss    xmm1, xmm2
0042B689  mulss    xmm2, xmm2
0042B68D  subss    xmm0, xmm1
0042B691  mulss    xmm0, xmm2
0042B695  movss    dword ptr [rsp + 0x3c], xmm0
0042B69B  call     qword ptr [rip + 0x32b947]
0042B6A1  mov      ecx, dword ptr [rdi + r14*8 + 0x75c05c]
0042B6A9  cmp      ecx, -1
0042B6AC  je       0x14042b6e8
0042B6AE  mov      eax, dword ptr [rip + 0x2b4894c]
0042B6B4  lea      r8, [rsp + 0x40]
0042B6B9  dec      eax
0042B6BB  mov      edx, 1
0042B6C0  movd     xmm0, eax
0042B6C4  mov      eax, dword ptr [rip + 0x2b4893a]
0042B6CA  cvtdq2ps xmm0, xmm0
0042B6CD  dec      eax
0042B6CF  movss    dword ptr [rsp + 0x40], xmm0
0042B6D5  movd     xmm0, eax
0042B6D9  cvtdq2ps xmm0, xmm0
0042B6DC  movss    dword ptr [rsp + 0x44], xmm0
0042B6E2  call     qword ptr [rip + 0x32b900]
0042B6E8  mov      ecx, dword ptr [rdi + r14*8 + 0x75c064]
0042B6F0  cmp      ecx, -1
0042B6F3  je       0x14042b70c
0042B6F5  cmp      byte ptr [rip + 0x2b4886c], r15b
0042B6FC  je       0x14042b70c
0042B6FE  movss    xmm1, dword ptr [rip + 0x2b4893e]
0042B706  call     qword ptr [rip + 0x32b8d4]
0042B70C  test     ebx, 0xe0000
0042B712  je       0x14042b753
0042B714  mov      ecx, dword ptr [rdi + r14*8 + 0x75c054]
0042B71C  cmp      ecx, -1
0042B71F  je       0x14042b753
0042B721  cmp      byte ptr [rip + 0x2b48840], 0
0042B728  je       0x14042b753
0042B72A  mov      r8d, dword ptr [rdi + rsi*4 + 0x2f5bf28]
0042B732  lea      rax, [rip + 0x195b9f]
0042B739  shr      r8, 0x11
0042B73D  mov      edx, 1
0042B742  and      r8d, 7
0042B746  shl      r8, 4
0042B74A  add      r8, rax
0042B74D  call     qword ptr [rip + 0x32b89d]
0042B753  test     bl, 0xc0
0042B756  je       0x14042b819
0042B75C  mov      edi, dword ptr [rdi + rsi*4 + 0x2f5bf28]
0042B763  lea      rax, [rip + 0x2b487be]
0042B76A  shr      rdi, 6
0042B76E  and      edi, 3
0042B771  shl      rdi, 4
0042B775  add      rdi, rax
0042B778  cmp      byte ptr [rip + 0x2b487e9], 0
0042B77F  je       0x14042b7a0
0042B781  mov      r8, rdi
0042B784  mov      edx, 1
0042B789  lea      rdi, [rip - 0x42b790]
0042B790  mov      ecx, dword ptr [rdi + r14*8 + 0x75c044]
0042B798  call     qword ptr [rip + 0x32b852]
0042B79E  jmp      0x14042b819
0042B7A0  mov      ecx, 0x1701
0042B7A5  call     0x140531314
0042B7AA  movss    xmm0, dword ptr [rdi]
0042B7AE  lea      rcx, [rsp + 0x50]
0042B7B3  movss    xmm1, dword ptr [rdi + 8]
0042B7B8  movss    dword ptr [rsp + 0x50], xmm0
0042B7BE  movss    xmm0, dword ptr [rdi + 4]
0042B7C3  movss    dword ptr [rsp + 0x64], xmm0
0042B7C9  movaps   xmm0, xmmword ptr [rip + 0x195e40]
0042B7D0  movaps   xmmword ptr [rsp + 0x70], xmm0
0042B7D5  movss    xmm0, dword ptr [rdi + 0xc]
0042B7DA  movss    dword ptr [rbp - 0x7c], xmm0
0042B7DF  movss    dword ptr [rbp - 0x80], xmm1
0042B7E4  mov      qword ptr [rsp + 0x54], 0
0042B7ED  mov      qword ptr [rsp + 0x5c], 0
0042B7F6  mov      qword ptr [rsp + 0x68], 0
0042B7FF  mov      dword ptr [rbp - 0x78], 0
0042B806  mov      dword ptr [rbp - 0x74], 0x3f800000
0042B80D  call     0x140531326
0042B812  lea      rdi, [rip - 0x42b819]
0042B819  mov      eax, dword ptr [rdi + rsi*4 + 0x2f5bf28]
0042B820  shr      rax, 0x15
0042B824  and      eax, 0x1ff
0042B829  lea      rax, [rax + rax*4]
0042B82D  lea      rdi, [rdi + rax*8]
0042B831  lea      rdi, [rdi + 0x757040]
0042B838  test     ebx, 0x3fe00000
0042B83E  je       0x14042baa0
0042B844  test     r15, r15
0042B847  je       0x14042b85f
0042B849  mov      eax, dword ptr [rdi + 4]
0042B84C  cmp      dword ptr [r15 + 4], eax
0042B850  jne      0x14042b85f
0042B852  mov      eax, dword ptr [rdi + 8]
0042B855  cmp      dword ptr [r15 + 8], eax
0042B859  je       0x14042b912
0042B85F  cmp      byte ptr [rip + 0x2b48702], 0
0042B866  movaps   xmm1, xmm6
0042B869  movd     xmm0, dword ptr [rdi + 4]
0042B86E  movd     xmm2, dword ptr [rdi + 8]
0042B873  cvtdq2ps xmm0, xmm0
0042B876  cvtdq2ps xmm2, xmm2
0042B879  divss    xmm1, xmm0
0042B87D  movaps   xmm0, xmm6
0042B880  divss    xmm0, xmm2
0042B884  movss    dword ptr [rsp + 0x30], xmm1
0042B88A  movss    dword ptr [rsp + 0x34], xmm0
0042B890  je       0x14042b8b3
0042B892  lea      rax, [rip - 0x42b899]
0042B899  mov      edx, 1
0042B89E  mov      ecx, dword ptr [rax + r14*8 + 0x75c048]
0042B8A6  lea      r8, [rsp + 0x30]
0042B8AB  call     qword ptr [rip + 0x32b737]
0042B8B1  jmp      0x14042b90f
0042B8B3  mov      ecx, 0x84c1
0042B8B8  call     qword ptr [rip + 0x32b68a]
0042B8BE  mov      ecx, 0x1702
0042B8C3  call     0x140531314
0042B8C8  call     0x140531320
0042B8CD  movss    xmm1, dword ptr [rsp + 0x34]
0042B8D3  movaps   xmm2, xmm6
0042B8D6  movss    xmm0, dword ptr [rsp + 0x30]
0042B8DC  call     0x14053132c
0042B8E1  mov      ecx, 0x84c0
0042B8E6  call     qword ptr [rip + 0x32b65c]
0042B8EC  mov      ecx, 0x1702
0042B8F1  call     0x140531314
0042B8F6  call     0x140531320
0042B8FB  movss    xmm1, dword ptr [rsp + 0x34]
0042B901  movaps   xmm2, xmm6
0042B904  movss    xmm0, dword ptr [rsp + 0x30]
0042B90A  call     0x14053132c
0042B90F  mov      r15, rdi
0042B912  cmp      dword ptr [rdi + 0x24], 0
0042B916  je       0x14042ba1d
0042B91C  mov      ecx, 0x84c0
0042B921  call     qword ptr [rip + 0x32b629]
0042B927  mov      ecx, 0x84c0
0042B92C  call     qword ptr [rip + 0x32b616]
0042B932  mov      ecx, 0xde1
0042B937  call     0x1405312de
0042B93C  mov      edx, dword ptr [rdi]
0042B93E  mov      ecx, 0xde1
0042B943  call     0x140531380
0042B948  mov      edx, 0x2200
0042B94D  mov      ecx, 0x2300
0042B952  mov      r8d, 0x1e01
0042B958  call     0x140531362
0042B95D  mov      ecx, 0x84c1
0042B962  call     qword ptr [rip + 0x32b5e8]
0042B968  mov      ecx, 0x84c1
0042B96D  call     qword ptr [rip + 0x32b5d5]
0042B973  mov      ecx, 0xde1
0042B978  call     0x1405312de
0042B97D  mov      edx, dword ptr [rdi + 0x24]
0042B980  mov      ecx, 0xde1
0042B985  call     0x140531380
0042B98A  movaps   xmm2, xmm11
0042B98E  mov      edx, 0x2200
0042B993  mov      ecx, 0x2300
0042B998  call     0x14053135c
0042B99D  mov      edx, 0x8571
0042B9A2  mov      ecx, 0x2300
0042B9A7  mov      r8d, 0x1e01
0042B9AD  call     0x140531362
0042B9B2  mov      edx, 0x8580
0042B9B7  mov      ecx, 0x2300
0042B9BC  mov      r8d, 0x84c0
0042B9C2  call     0x140531362
0042B9C7  mov      edx, 0x8590
0042B9CC  mov      ecx, 0x2300
0042B9D1  mov      r8d, 0x300
0042B9D7  call     0x140531362
0042B9DC  mov      edx, 0x8572
0042B9E1  mov      ecx, 0x2300
0042B9E6  mov      r8d, 0x1e01
0042B9EC  call     0x140531362
0042B9F1  mov      edx, 0x8588
0042B9F6  mov      ecx, 0x2300
0042B9FB  mov      r8d, 0x84c1
0042BA01  call     0x140531362
0042BA06  mov      edx, 0x8598
0042BA0B  mov      ecx, 0x2300
0042BA10  mov      r8d, 0x302
0042BA16  call     0x140531362
0042BA1B  jmp      0x14042ba7c
0042BA1D  mov      ecx, 0x84c1
0042BA22  call     qword ptr [rip + 0x32b528]
0042BA28  mov      ecx, 0x84c1
0042BA2D  call     qword ptr [rip + 0x32b515]
0042BA33  mov      ecx, 0xde1
0042BA38  call     0x1405312e4
0042BA3D  mov      ecx, 0x84c0
0042BA42  call     qword ptr [rip + 0x32b508]
0042BA48  mov      ecx, 0x84c0
0042BA4D  call     qword ptr [rip + 0x32b4f5]
0042BA53  mov      ecx, 0xde1
0042BA58  call     0x1405312de
0042BA5D  mov      edx, dword ptr [rdi]
0042BA5F  mov      ecx, 0xde1
0042BA64  call     0x140531380
0042BA69  movaps   xmm2, xmm8
0042BA6D  mov      edx, 0x2200
0042BA72  mov      ecx, 0x2300
0042BA77  call     0x14053135c
0042BA7C  cmp      byte ptr [rdi + 0xc], 0
0042BA80  lea      rdi, [rip - 0x42ba87]
0042BA87  jne      0x14042baa7
0042BA89  mov      ecx, dword ptr [rdi + rsi*4 + 0x2f5bf28]
0042BA90  shr      ecx, 0x15
0042BA93  and      ecx, 0x1ff
0042BA99  call     0x14042ca10
0042BA9E  jmp      0x14042baa7
0042BAA0  lea      rdi, [rip - 0x42baa7]
0042BAA7  mov      r8d, dword ptr [rdi + rsi*4 + 0x2f5bf30]
0042BAAF  cmp      r8d, -1
0042BAB3  jne      0x14042bac9
0042BAB5  movaps   xmm0, xmm7
0042BAB8  call     0x140531302
0042BABD  mov      ecx, 0x4500
0042BAC2  call     0x1405312c0
0042BAC7  jmp      0x14042baea
0042BAC9  mov      eax, dword ptr [rdi + rsi*4 + 0x2f5bf28]
0042BAD0  mov      edx, dword ptr [rdi + rsi*4 + 0x2f5bf2c]
0042BAD7  shr      rax, 4
0042BADB  and      eax, 3
0042BADE  mov      ecx, dword ptr [rdi + rax*4 + 0x5c12a0]
0042BAE5  call     0x140531344
0042BAEA  inc      r13d
0042BAED  lea      rdx, [rip + 0x1057ea]
0042BAF4  inc      r12
0042BAF7  cmp      r13d, dword ptr [rip + 0x2b484d2]
0042BAFE  jl       0x14042b4e0
0042BB04  movaps   xmm11, xmmword ptr [rsp + 0xa0]
0042BB0D  xor      r14d, r14d
0042BB10  movaps   xmm10, xmmword ptr [rsp + 0xb0]
0042BB19  movaps   xmm9, xmmword ptr [rsp + 0xc0]
0042BB22  movaps   xmm8, xmmword ptr [rsp + 0xd0]
0042BB2B  movaps   xmm7, xmmword ptr [rsp + 0xe0]
0042BB33  movaps   xmm6, xmmword ptr [rsp + 0xf0]
0042BB3B  mov      r12, qword ptr [rsp + 0x108]
0042BB43  mov      rsi, qword ptr [rsp + 0x138]
0042BB4B  mov      rbx, qword ptr [rsp + 0x130]
0042BB53  movsxd   rax, r13d
0042BB56  mov      r13, qword ptr [rsp + 0x100]
0042BB5E  mov      dword ptr [rip + 0x2b48483], r14d
0042BB65  lea      rcx, [rax + rax*2]
0042BB69  mov      eax, dword ptr [rdi + rcx*4 + 0x2f5bf1c]
0042BB70  and      dword ptr [rip + 0x2b483f5], 0xffffffcf
0042BB77  mov      rdi, qword ptr [rsp + 0x140]
0042BB7F  mov      dword ptr [rip + 0x2b4845f], eax
0042BB85  movzx    eax, word ptr [rip + 0x2b484c0]
0042BB8C  sub      ax, 1
0042BB90  mov      qword ptr [rip + 0x2b483d5], 0
0042BB9B  mov      dword ptr [rip + 0x2b4842e], r14d
0042BBA2  cmovns   ax, r14w
0042BBA7  mov      dword ptr [rip + 0x2b4849a], r14d
0042BBAE  mov      word ptr [rip + 0x2b483c7], ax
0042BBB5  mov      rcx, qword ptr [rbp - 0x70]
0042BBB9  xor      rcx, rsp
0042BBBC  call     0x1404f77a0
0042BBC1  add      rsp, 0x110
0042BBC8  pop      r15
0042BBCA  pop      r14
0042BBCC  pop      rbp
0042BBCD  ret      
0042BBCE  int3     
0042BBCF  int3     
0042BBD0  mov      qword ptr [rsp + 8], rbx
0042BBD5  mov      qword ptr [rsp + 0x10], rbp
0042BBDA  mov      qword ptr [rsp + 0x18], rsi
0042BBDF  push     rdi
0042BBE0  push     r14
0042BBE2  push     r15
0042BBE4  sub      rsp, 0x20
0042BBE8  movzx    r14d, r9b
0042BBEC  lea      rbx, [rip + 0x32b475]
0042BBF3  mov      esi, r8d
0042BBF6  movzx    r15d, dl
0042BBFA  mov      ebp, ecx
0042BBFC  mov      edi, 1
0042BC01  cmp      dword ptr [rbx], 0
0042BC04  je       0x14042bc1b
0042BC06  inc      edi
0042BC08  add      rbx, 0x28
0042BC0C  cmp      edi, 0x200
0042BC12  jb       0x14042bc01
0042BC14  xor      eax, eax
0042BC16  jmp      0x14042bc9b
0042BC1B  mov      rdx, rbx
