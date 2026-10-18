0022BF00 mov      qword ptr [rsp + 0x18], rbx
0022BF05 push     rbp
0022BF06 push     rsi
0022BF07 push     rdi
0022BF08 push     r12
0022BF0A push     r13
0022BF0C push     r14
0022BF0E push     r15
0022BF10 lea      rbp, [rsp - 0x60]
0022BF15 sub      rsp, 0x160
0022BF1C mov      rax, qword ptr [rip + 0x438ab5]
0022BF23 xor      rax, rsp
0022BF26 mov      qword ptr [rbp + 0x58], rax
0022BF2A mov      rax, qword ptr [rip + 0x430bdf]
0022BF31 mov      rsi, rdx
0022BF34 mov      qword ptr [rsp + 0x68], rdx
0022BF39 movzx    r13d, cx
0022BF3D mov      word ptr [rbp - 0x80], cx
0022BF41 lea      rdx, [rip + 0x42f3a0]
0022BF48 xor      edi, edi
0022BF4A mov      qword ptr [rsp + 0x60], rax
0022BF4F lea      rcx, [rbp + 0x28]
0022BF53 mov      dword ptr [rbp - 0x7c], edi
0022BF56 mov      qword ptr [rsp + 0x58], rax
0022BF5B xor      ebx, ebx
0022BF5D mov      qword ptr [rsp + 0x50], rax
0022BF62 mov      qword ptr [rbp + 0x28], rax
0022BF66 call     0x14011ea00
0022BF6B movzx    r15d, r13w
0022BF6F mov      dword ptr [rbp - 0x7c], r15d
0022BF73 cmp      r13w, 0xe
0022BF78 jne      0x14022bf84
0022BF7A mov      r15d, 4
0022BF80 mov      dword ptr [rbp - 0x7c], r15d
0022BF84 movzx    r12d, r15w
0022BF88 lea      rdx, [rip - 0x22bf8f]
0022BF8F dec      r12d
0022BF92 mov      r14d, 1
0022BF98 cmp      r12d, 0xfe
0022BF9F ja       0x14022e8f5
0022BFA5 movsxd   rax, r12d
0022BFA8 movzx    eax, byte ptr [rdx + rax + 0x22eebc]
0022BFB0 mov      ecx, dword ptr [rdx + rax*4 + 0x22eddc]
0022BFB7 add      rcx, rdx
0022BFBA jmp      rcx
0022BFBC mov      ecx, 0x1b8
0022BFC1 call     0x1404f7a88
0022BFC6 mov      rbx, rax
0022BFC9 test     rax, rax
0022BFCC je       0x14022bff5
0022BFCE xor      edx, edx
0022BFD0 mov      r8d, 0x1b8
0022BFD6 mov      rcx, rax
0022BFD9 call     0x1404fab70
0022BFDE mov      rcx, rbx
0022BFE1 call     0x140226910
0022BFE6 lea      rax, [rip + 0x370003]
0022BFED mov      qword ptr [rbx], rax
0022BFF0 jmp      0x14022e8ec
0022BFF5 xor      ebx, ebx
0022BFF7 jmp      0x14022e8f5
0022BFFC mov      ecx, 0x3c0
0022C001 call     0x1404f7a88
0022C006 mov      rbx, rax
0022C009 test     rax, rax
0022C00C je       0x14022c12d
0022C012 lea      rdx, [rip + 0x370a4f]
0022C019 lea      rcx, [rbp - 0x20]
0022C01D call     0x1403ff800
0022C022 mov      rcx, rbx
0022C025 mov      rdx, qword ptr [rax]
0022C028 call     0x140227600
0022C02D mov      rcx, qword ptr [rbx + 0x1b8]
0022C034 lea      rax, [rip + 0x36f85d]
0022C03B xor      edx, edx
0022C03D mov      qword ptr [rbx], rax
0022C040 call     0x140412380
0022C045 mov      rax, qword ptr [rip + 0x43b4fc]
0022C04C lea      rcx, [rbx + 0x1c8]
0022C053 xor      edx, edx
0022C055 mov      r9, qword ptr [rax + 0x1090]
0022C05C add      r9, 0x63d8
0022C063 lea      r8d, [rdx + 0x43]
0022C067 call     0x1404221c0
0022C06C mov      rcx, qword ptr [rbx + 0x1b8]
0022C073 lea      rdx, [rbx + 0x1c8]
0022C07A call     0x140412390
0022C07F xor      ecx, ecx
0022C081 mov      dword ptr [rsp + 0x78], 0x14
0022C089 mov      qword ptr [rbx + 0x1f8], rcx
0022C090 lea      r8, [rip + 0x3bf716]
0022C097 mov      dword ptr [rbx + 0x200], ecx
0022C09D lea      rdx, [rbp - 0x18]
0022C0A1 mov      dword ptr [rbx + 0x210], ecx
0022C0A7 lea      rcx, [rbx + 0x140]
0022C0AE mov      dword ptr [rsp + 0x7c], 0xf
0022C0B6 mov      rax, qword ptr [rsp + 0x78]
0022C0BB mov      qword ptr [rbx + 0x204], rax
0022C0C2 mov      eax, 0x80
0022C0C7 mov      word ptr [rbx + 0x20c], ax
0022C0CE mov      eax, 5
0022C0D3 mov      word ptr [rbx + 0x214], ax
0022C0DA call     0x1403ff960
0022C0DF mov      eax, 0x1e
0022C0E4 mov      dword ptr [rbx + 0x70], 0xffffffff
0022C0EB lea      rcx, [rbx + 0x178]
0022C0F2 mov      word ptr [rbx + 0x3b8], ax
0022C0F9 lea      rdx, [rip + 0x3bf6ad]
0022C100 call     0x1403fd810
0022C105 mov      dword ptr [rsp + 0x78], 0x17
0022C10D mov      dword ptr [rsp + 0x7c], 0x32
0022C115 mov      rax, qword ptr [rsp + 0x78]
0022C11A mov      qword ptr [rbx + 0x164], rax
0022C121 mov      dword ptr [rbx + 0x180], 0xffffffff
0022C12B jmp      0x14022c12f
0022C12D xor      ebx, ebx
0022C12F lea      rcx, [rbx + 0x140]
0022C136 mov      byte ptr [rbx + 0x158], r14b
0022C13D lea      r8, [rip + 0x37070c]
0022C144 lea      rdx, [rbp - 0x20]
0022C148 call     0x1403ff960
0022C14D lea      rdx, [rbp - 0x20]
0022C151 jmp      0x14022e8d9
0022C156 mov      ecx, 0x3c0
0022C15B call     0x1404f7a88
0022C160 test     rax, rax
0022C163 je       0x14022c170
0022C165 mov      rcx, rax
0022C168 call     0x140227800
0022C16D mov      rbx, rax
0022C170 lea      rcx, [rbx + 0x140]
0022C177 mov      byte ptr [rbx + 0x158], r14b
0022C17E lea      r8, [rip + 0x3706d3]
0022C185 lea      rdx, [rbp - 0x20]
0022C189 call     0x1403ff960
0022C18E lea      rdx, [rbp - 0x20]
0022C192 jmp      0x14022e8d9
0022C197 mov      ecx, 0x3c0
0022C19C call     0x1404f7a88
0022C1A1 test     rax, rax
0022C1A4 je       0x14022c1b1
0022C1A6 mov      rcx, rax
0022C1A9 call     0x140227800
0022C1AE mov      rbx, rax
0022C1B1 xor      edx, edx
0022C1B3 mov      byte ptr [rbx + 0x158], r14b
0022C1BA mov      rcx, rbx
0022C1BD lea      r8d, [rdx + 0x43]
0022C1C1 call     0x140235d80
0022C1C6 lea      rcx, [rbx + 0x140]
0022C1CD lea      r8, [rip + 0x37068c]
0022C1D4 lea      rdx, [rbp - 0x20]
0022C1D8 call     0x1403ff960
0022C1DD lea      rdx, [rbp - 0x20]
0022C1E1 jmp      0x14022e8d9
0022C1E6 lea      rdx, [rip + 0x37067b]
0022C1ED lea      rcx, [rsp + 0x60]
0022C1F2 call     0x1403fd810
0022C1F7 lea      rdx, [rip + 0x3bf5af]
0022C1FE lea      rcx, [rsp + 0x50]
0022C203 call     0x1403fd810
0022C208 lea      rdx, [rip + 0x3bf59e]
0022C20F lea      rcx, [rsp + 0x58]
0022C214 call     0x1403fd810
0022C219 mov      ecx, 0x418
0022C21E call     0x1404f7a88
0022C223 mov      rbx, rax
0022C226 test     rax, rax
0022C229 je       0x14022c30e
0022C22F mov      rcx, rax
0022C232 call     0x140226910
0022C237 lea      rax, [rip + 0x370142]
0022C23E lea      rcx, [rbx + 0x1b8]
0022C245 mov      qword ptr [rbx], rax
0022C248 call     0x140410f70
0022C24D lea      rcx, [rbx + 0x2f0]
0022C254 call     0x140410d80
0022C259 lea      rdx, [rsp + 0x60]
0022C25E lea      rcx, [rbp - 0x20]
0022C262 call     0x1403ff710
0022C267 lea      rcx, [rbx + 0x2c0]
0022C26E mov      r9d, r14d
0022C271 mov      r8d, r14d
0022C274 lea      rdx, [rbp - 0x20]
0022C278 call     0x14014d080
0022C27D mov      rax, qword ptr [rsp + 0x50]
0022C282 cmp      dword ptr [rax - 8], edi
0022C285 je       0x14022c2b1
0022C287 lea      rdx, [rsp + 0x50]
0022C28C lea      rcx, [rbp - 0x18]
0022C290 call     0x1403ff710
0022C295 mov      r9d, r14d
0022C298 lea      rdx, [rbp - 0x18]
0022C29C mov      r8d, r14d
0022C29F lea      rcx, [rbx + 0x2f0]
0022C2A6 call     0x14018aa40
0022C2AB movzx    eax, r14b
0022C2AF jmp      0x14022c2b3
0022C2B1 xor      al, al
0022C2B3 xor      edx, edx
0022C2B5 mov      byte ptr [rbx + 0x414], al
0022C2BB lea      rcx, [rbx + 0x1b8]
0022C2C2 call     0x140412380
0022C2C7 xor      edx, edx
0022C2C9 lea      rcx, [rbx + 0x1b8]
0022C2D0 call     0x140411610
0022C2D5 lea      rcx, [rbx + 0x140]
0022C2DC lea      r8, [rsp + 0x58]
0022C2E1 lea      rdx, [rbp - 0x10]
0022C2E5 call     0x1403ff890
0022C2EA lea      rax, [rip + 0x3701bf]
0022C2F1 mov      dword ptr [rbx + 0x410], 8
0022C2FB mov      qword ptr [rbx], rax
0022C2FE mov      byte ptr [rbx + 0x415], dil
0022C305 mov      byte ptr [rbx + 0x158], r14b
0022C30C jmp      0x14022c310
0022C30E xor      ebx, ebx
0022C310 lea      r8, [rip + 0x3bf496]
0022C317 lea      rdx, [rbp - 0x20]
0022C31B lea      rcx, [rbx + 0x140]
0022C322 call     0x1403ff960
0022C327 lea      rdx, [rbp - 0x20]
0022C32B jmp      0x14022e8d9
0022C330 mov      ecx, 0x328
0022C335 call     0x1404f7a88
0022C33A mov      rbx, rax
0022C33D test     rax, rax
0022C340 je       0x14022c392
0022C342 lea      rdx, [rip + 0x3bf464]
0022C349 lea      rcx, [rbp - 0x68]
0022C34D call     0x1403fd6b0
0022C352 lea      rdx, [rip + 0x36cedf]
0022C359 lea      rcx, [rbp - 0x70]
0022C35D call     0x1403fd6b0
0022C362 movzx    ecx, byte ptr [rip + 0x3723eb]
0022C369 lea      r8, [rbp - 0x68]
0022C36D add      cx, cx
0022C370 lea      rdx, [rbp - 0x70]
0022C374 mov      word ptr [rsp + 0x28], cx
0022C379 mov      r9b, 0xff
0022C37C mov      rcx, rbx
0022C37F mov      dword ptr [rsp + 0x20], edi
0022C383 call     0x140227cd0
0022C388 mov      rbx, rax
0022C38B mov      edi, 3
0022C390 jmp      0x14022c394
0022C392 xor      ebx, ebx
0022C394 test     dil, 2
0022C398 je       0x14022c3a6
0022C39A and      edi, 0xfffffffd
0022C39D lea      rcx, [rbp - 0x70]
0022C3A1 call     0x1403fd740
0022C3A6 test     r14b, dil
0022C3A9 je       0x14022c310
0022C3AF lea      rcx, [rbp - 0x68]
0022C3B3 call     0x1403fd740
0022C3B8 jmp      0x14022c310
0022C3BD mov      ecx, 0x328
0022C3C2 call     0x1404f7a88
0022C3C7 mov      rbx, rax
0022C3CA test     rax, rax
0022C3CD je       0x14022c422
0022C3CF lea      rdx, [rip + 0x3bf3d7]
0022C3D6 lea      rcx, [rsp + 0x70]
0022C3DB call     0x1403fd6b0
0022C3E0 lea      rdx, [rip + 0x36ce59]
0022C3E7 lea      rcx, [rbp - 0x60]
0022C3EB call     0x1403fd6b0
0022C3F0 movzx    ecx, byte ptr [rip + 0x37235d]
0022C3F7 lea      r8, [rsp + 0x70]
0022C3FC add      cx, cx
0022C3FF lea      rdx, [rbp - 0x60]
0022C403 mov      word ptr [rsp + 0x28], cx
0022C408 mov      r9b, 0xff
0022C40B mov      rcx, rbx
0022C40E mov      dword ptr [rsp + 0x20], r14d
0022C413 call     0x140227cd0
0022C418 mov      rbx, rax
0022C41B mov      edi, 0xc
0022C420 jmp      0x14022c424
0022C422 xor      ebx, ebx
0022C424 test     dil, 8
0022C428 je       0x14022c436
0022C42A and      edi, 0xfffffff7
0022C42D lea      rcx, [rbp - 0x60]
0022C431 call     0x1403fd740
0022C436 test     dil, 4
0022C43A je       0x14022c310
0022C440 lea      rcx, [rsp + 0x70]
0022C445 call     0x1403fd740
0022C44A jmp      0x14022c310
0022C44F mov      ecx, 0x3f0
0022C454 call     0x1404f7a88
0022C459 mov      rbx, rax
0022C45C test     rax, rax
0022C45F je       0x14022c618
0022C465 movzx    edi, word ptr [rip + 0x394210]
0022C46C lea      rdx, [rip + 0x3705c5]
0022C473 lea      rcx, [rbp - 0x18]
0022C477 call     0x1403ff800
0022C47C mov      rcx, rbx
0022C47F mov      rdx, qword ptr [rax]
0022C482 call     0x140227600
0022C487 lea      rax, [rip + 0x36fa2a]
0022C48E mov      edx, 0xa
0022C493 lea      rcx, [rbx + 0x3b8]
0022C49A mov      qword ptr [rbx], rax
0022C49D call     0x1404073a0
0022C4A2 lea      rax, [rip + 0x3608af]
0022C4A9 xor      edx, edx
0022C4AB mov      qword ptr [rbx + 0x3b8], rax
0022C4B2 mov      rcx, qword ptr [rbx + 0x1b8]
0022C4B9 call     0x140412380
0022C4BE or       dword ptr [rbx + 0x118], 8
0022C4C5 cmp      di, r14w
0022C4C9 jne      0x14022c505
0022C4CB mov      rax, qword ptr [rip + 0x43b076]
0022C4D2 lea      rcx, [rbx + 0x1c8]
0022C4D9 xor      edx, edx
0022C4DB mov      r9, qword ptr [rax + 0x1090]
0022C4E2 add      r9, 0x63d8
0022C4E9 lea      r8d, [rdx + 0x21]
0022C4ED call     0x1404221c0
0022C4F2 mov      rcx, qword ptr [rbx + 0x1b8]
0022C4F9 lea      rdx, [rbx + 0x1c8]
0022C500 call     0x140412390
0022C505 lea      eax, [r15 - 0x43]
0022C509 xor      edi, edi
0022C50B movsx    r15d, ax
0022C50F test     r15d, r15d
0022C512 jle      0x14022c566
0022C514 mov      ecx, 0x25
0022C519 xor      edx, edx
0022C51B call     0x14022bf00
0022C520 mov      rsi, rax
0022C523 test     edi, edi
0022C525 je       0x14022c54b
0022C527 lea      rdx, [rip + 0x3bf27f]
0022C52E lea      rcx, [rbp - 0x20]
0022C532 call     0x1403ff7c0
0022C537 lea      rcx, [rsi + 0x140]
0022C53E lea      r8, [rbp - 0x20]
0022C542 lea      rdx, [rbp - 0x10]
0022C546 call     0x1403ff880
0022C54B mov      rdx, rsi
0022C54E lea      rcx, [rbx + 0x3b8]
0022C555 call     0x1404075c0
0022C55A inc      edi
0022C55C cmp      edi, r15d
0022C55F jl       0x14022c514
0022C561 mov      rsi, qword ptr [rsp + 0x68]
0022C566 lea      rdx, [rip + 0x3bf240]
0022C56D mov      dword ptr [rbx + 0x70], 0xffffffff
0022C574 lea      rcx, [rbx + 0x178]
0022C57B call     0x1403fd810
0022C580 xor      edx, edx
0022C582 mov      dword ptr [rsp + 0x70], 0xa
0022C58A mov      ecx, r14d
0022C58D mov      qword ptr [rbx + 0x1f8], rdx
0022C594 lea      rax, [rip + 0x36f91d]
0022C59B mov      dword ptr [rbx + 0x200], ecx
0022C5A1 mov      qword ptr [rbx], rax
0022C5A4 lea      r8, [rip + 0x3bf202]
0022C5AB mov      dword ptr [rbx + 0x210], edx
0022C5B1 lea      rdx, [rbp + 8]
0022C5B5 mov      word ptr [rbx + 0x214], cx
0022C5BC lea      rcx, [rbx + 0x140]
0022C5C3 mov      dword ptr [rsp + 0x74], 7
0022C5CB mov      rax, qword ptr [rsp + 0x70]
0022C5D0 mov      qword ptr [rbx + 0x204], rax
0022C5D7 mov      eax, 0x80
0022C5DC mov      word ptr [rbx + 0x20c], ax
0022C5E3 mov      dword ptr [rbx + 0x180], 0xffffffff
0022C5ED call     0x1403ff960
0022C5F2 lea      rdx, [rip + 0x3bf1b4]
0022C5F9 mov      dword ptr [rbx + 0x70], 0xffffffff
0022C600 lea      rcx, [rbx + 0x178]
0022C607 call     0x1403fd810
0022C60C mov      dword ptr [rbx + 0x180], 0xffffffff
0022C616 jmp      0x14022c61a
0022C618 xor      ebx, ebx
0022C61A lea      rcx, [rbx + 0x140]
0022C621 lea      r8, [rip + 0x37024c]
0022C628 lea      rdx, [rbp - 0x20]
0022C62C call     0x1403ff960
0022C631 lea      rcx, [rbx + 0x14c]
0022C638 lea      r8, [rip + 0x3bf16e]
0022C63F lea      rdx, [rbp - 0x20]
0022C643 call     0x1403ff960
0022C648 mov      byte ptr [rbx + 0x158], r14b
0022C64F jmp      0x14022e8ec
0022C654 mov      ecx, 0x3b8
0022C659 call     0x1404f7a88
0022C65E test     rax, rax
0022C661 je       0x14022e8f5
0022C667 mov      rcx, rax
0022C66A call     0x140227a40
0022C66F mov      rbx, rax
0022C672 jmp      0x14022e8ec
0022C677 mov      ecx, 0x400
0022C67C call     0x1404f7a88
0022C681 mov      rbx, rax
0022C684 test     rax, rax
0022C687 je       0x14022c87d
0022C68D mov      rax, qword ptr [rip + 0x43047c]
0022C694 lea      rdx, [rip + 0x42ec4d]
0022C69B lea      rcx, [rbp + 0x10]
0022C69F mov      qword ptr [rbp + 0x10], rax
0022C6A3 call     0x14011ea00
0022C6A8 lea      rdx, [rip + 0x370389]
0022C6AF lea      rcx, [rbp - 0x20]
0022C6B3 call     0x1403ff800
0022C6B8 mov      rcx, rbx
0022C6BB mov      rdx, qword ptr [rax]
0022C6BE call     0x140227600
0022C6C3 mov      dword ptr [rsp + 0x40], 0xffffffff
0022C6CB lea      rax, [rip + 0x36ff0e]
0022C6D2 mov      byte ptr [rsp + 0x38], dil
0022C6D7 lea      rcx, [rbx + 0x3d8]
0022C6DE mov      byte ptr [rsp + 0x30], dil
0022C6E3 xor      r9d, r9d
0022C6E6 mov      byte ptr [rsp + 0x28], dil
0022C6EB xor      r8d, r8d
0022C6EE xor      edx, edx
0022C6F0 mov      byte ptr [rsp + 0x20], dil
0022C6F5 mov      qword ptr [rbx], rax
0022C6F8 call     0x14011ba20
0022C6FD mov      rcx, qword ptr [rbx + 0x1b8]
0022C704 xor      edx, edx
0022C706 mov      dword ptr [rbx + 0x11c], edi
0022C70C call     0x140412380
0022C711 lea      eax, [r15 - 0x50]
0022C715 mov      dword ptr [rbx + 0x3bc], r14d
0022C71C mov      word ptr [rbx + 0x3b8], ax
0022C723 lea      rdx, [rbp + 0x10]
0022C727 mov      eax, 0x16
0022C72C lea      rcx, [rbx + 0x3d8]
0022C733 mov      word ptr [rbx + 0x3c0], ax
0022C73A xor      r15d, r15d
0022C73D mov      eax, 0x5a
0022C742 mov      dword ptr [rbx + 0x3d0], r15d
0022C749 mov      word ptr [rbx + 0x3ba], ax
0022C750 call     0x14011ea00
0022C755 movzx    ecx, word ptr [rbx + 0x3c0]
0022C75C xor      edx, edx
0022C75E inc      cx
0022C761 call     0x14022bf00
0022C766 lea      rdx, [rip + 0x3bf040]
0022C76D mov      qword ptr [rbx + 0x3c8], rax
0022C774 lea      rcx, [rbx + 0x178]
0022C77B mov      dword ptr [rbx + 0x70], 0xffffffff
0022C782 call     0x1403fd810
0022C787 lea      rcx, [rbp + 0x10]
0022C78B mov      dword ptr [rbx + 0x180], 0xffffffff
0022C795 call     0x1403fd740
0022C79A lea      rax, [rip + 0x36fe3f]
0022C7A1 mov      dword ptr [rsp + 0x70], 0xa
0022C7A9 mov      qword ptr [rbx], rax
0022C7AC lea      rcx, [rbx + 0x140]
0022C7B3 mov      dword ptr [rsp + 0x74], 7
0022C7BB lea      r8, [rip + 0x3befeb]
0022C7C2 mov      rax, qword ptr [rsp + 0x70]
0022C7C7 lea      rdx, [rbp - 0x18]
0022C7CB mov      qword ptr [rbx + 0x204], rax
0022C7D2 mov      eax, 0x80
0022C7D7 mov      word ptr [rbx + 0x20c], ax
0022C7DE mov      qword ptr [rbx + 0x1f8], r15
0022C7E5 mov      dword ptr [rbx + 0x200], r14d
0022C7EC mov      dword ptr [rbx + 0x210], r15d
0022C7F3 mov      word ptr [rbx + 0x214], r14w
0022C7FB call     0x1403ff960
0022C800 lea      rdx, [rip + 0x3befa6]
0022C807 mov      dword ptr [rbx + 0x70], 0xffffffff
0022C80E lea      rcx, [rbx + 0x178]
0022C815 call     0x1403fd810
0022C81A mov      dword ptr [rsp + 0x40], 0xffffffff
0022C822 lea      rcx, [rbp + 0x40]
0022C826 mov      byte ptr [rsp + 0x38], dil
0022C82B xor      r9d, r9d
0022C82E mov      byte ptr [rsp + 0x30], dil
0022C833 xor      r8d, r8d
0022C836 mov      byte ptr [rsp + 0x28], dil
0022C83B xor      edx, edx
0022C83D mov      byte ptr [rsp + 0x20], dil
0022C842 mov      dword ptr [rbx + 0x180], 0xffffffff
0022C84C call     0x14011ba20
0022C851 movzx    eax, byte ptr [rip + 0x360694]
0022C858 lea      rdx, [rbp + 0x40]
0022C85C lea      rcx, [rbx + 0x3d8]
0022C863 mov      byte ptr [rbp + 0x48], al
0022C866 call     0x14011ea00
0022C86B lea      rcx, [rbp + 0x40]
0022C86F mov      dword ptr [rbx + 0x3f8], r14d
0022C876 call     0x1403fd740
0022C87B jmp      0x14022c87f
0022C87D xor      ebx, ebx
0022C87F mov      rax, qword ptr [rsi]
0022C882 mov      rcx, rsi
0022C885 call     qword ptr [rax + 0x20]
0022C888 movzx    ecx, byte ptr [rip + 0x36065e]
0022C88F lea      rdx, [rbp + 0x28]
0022C893 cmp      byte ptr [rax + 8], cl
0022C896 ja       0x14022c8b3
0022C898 movzx    eax, byte ptr [rip + 0x36064b]
0022C89F mov      rcx, rbx
0022C8A2 mov      byte ptr [rbp + 0x30], al
0022C8A5 mov      rax, qword ptr [rbx]
0022C8A8 call     qword ptr [rax + 0x120]
0022C8AE jmp      0x14022e8ec
0022C8B3 mov      byte ptr [rbp + 0x30], cl
0022C8B6 mov      rcx, rbx
0022C8B9 mov      rax, qword ptr [rbx]
0022C8BC call     qword ptr [rax + 0x120]
0022C8C2 jmp      0x14022e8ec
0022C8C7 mov      ecx, 0x3c0
0022C8CC call     0x1404f7a88
0022C8D1 mov      rbx, rax
0022C8D4 test     rax, rax
0022C8D7 je       0x14022c9cf
0022C8DD lea      rdx, [rip + 0x370174]
0022C8E4 lea      rcx, [rbp - 0x20]
0022C8E8 call     0x1403ff800
0022C8ED mov      rcx, rbx
0022C8F0 mov      rdx, qword ptr [rax]
0022C8F3 call     0x140227600
0022C8F8 mov      rcx, qword ptr [rbx + 0x1b8]
0022C8FF lea      rax, [rip + 0x36ee5a]
0022C906 xor      edx, edx
0022C908 mov      qword ptr [rbx], rax
0022C90B call     0x140412380
0022C910 xor      ecx, ecx
0022C912 mov      dword ptr [rsp + 0x70], 0x14
0022C91A mov      qword ptr [rbx + 0x1f8], rcx
0022C921 lea      r8, [rip + 0x3bee85]
0022C928 mov      dword ptr [rbx + 0x200], ecx
0022C92E lea      rdx, [rbp - 0x18]
0022C932 mov      dword ptr [rbx + 0x210], ecx
0022C938 lea      rcx, [rbx + 0x140]
0022C93F mov      dword ptr [rsp + 0x74], 0xf
0022C947 mov      rax, qword ptr [rsp + 0x70]
0022C94C mov      qword ptr [rbx + 0x204], rax
0022C953 mov      eax, 0x80
0022C958 mov      word ptr [rbx + 0x20c], ax
0022C95F mov      eax, 5
0022C964 mov      word ptr [rbx + 0x214], ax
0022C96B call     0x1403ff960
0022C970 mov      eax, 0x37
0022C975 mov      dword ptr [rbx + 0x70], 0xffffffff
0022C97C lea      rcx, [rbx + 0x178]
0022C983 mov      word ptr [rbx + 0x3b8], ax
0022C98A lea      rdx, [rip + 0x3bee1c]
0022C991 call     0x1403fd810
0022C996 mov      dword ptr [rsp + 0x70], 0x2d
0022C99E lea      r8, [rip + 0x36fed7]
0022C9A5 mov      dword ptr [rsp + 0x74], 0x46
0022C9AD mov      rax, qword ptr [rsp + 0x70]
0022C9B2 mov      qword ptr [rbx + 0x164], rax
0022C9B9 mov      dword ptr [rbx + 0x180], 0xffffffff
0022C9C3 mov      byte ptr [rbx + 0x158], r14b
0022C9CA jmp      0x14022c317
0022C9CF xor      ebx, ebx
0022C9D1 lea      r8, [rip + 0x36fea4]
0022C9D8 mov      byte ptr [rbx + 0x158], r14b
0022C9DF jmp      0x14022c317
0022C9E4 mov      ecx, 0x428
0022C9E9 call     0x1404f7a88
0022C9EE mov      rbx, rax
0022C9F1 test     rax, rax
0022C9F4 je       0x14022cb35
0022C9FA lea      rdx, [rip + 0x3bedac]
0022CA01 lea      rcx, [rsp + 0x78]
0022CA06 call     0x1403fd6b0
0022CA0B lea      rdx, [rip + 0x3bed9b]
0022CA12 lea      rcx, [rbp - 0x58]
0022CA16 call     0x1403fd6b0
0022CA1B lea      rdx, [rip + 0x36fe66]
0022CA22 lea      rcx, [rbp - 0x78]
0022CA26 call     0x1403fd6b0
0022CA2B mov      rcx, rbx
0022CA2E call     0x140226910
0022CA33 lea      rax, [rip + 0x36f6e6]
0022CA3A lea      rcx, [rbx + 0x1b8]
0022CA41 mov      qword ptr [rbx], rax
0022CA44 call     0x140410f70
0022CA49 lea      rcx, [rbx + 0x2f0]
0022CA50 call     0x140410d80
0022CA55 mov      rax, qword ptr [rip + 0x4300b4]
0022CA5C lea      rcx, [rbx + 0x418]
0022CA63 lea      rdx, [rbp - 0x78]
0022CA67 mov      qword ptr [rcx], rax
0022CA6A call     0x1403fd770
0022CA6F lea      r8, [rip + 0x3de1c6]
0022CA76 lea      rdx, [rbp - 0x78]
0022CA7A lea      rcx, [rbp - 0x18]
0022CA7E call     0x1403fd8e0
0022CA83 mov      rdx, rax
0022CA86 lea      rcx, [rbp - 0x20]
0022CA8A call     0x1403ff710
0022CA8F lea      rcx, [rbx + 0x2c0]
0022CA96 mov      r9d, r14d
0022CA99 mov      r8d, r14d
0022CA9C lea      rdx, [rbp - 0x20]
0022CAA0 call     0x14014d080
0022CAA5 lea      rcx, [rbp - 0x18]
0022CAA9 call     0x1403fd740
0022CAAE mov      rax, qword ptr [rsp + 0x78]
0022CAB3 cmp      dword ptr [rax - 8], edi
0022CAB6 je       0x14022cae2
0022CAB8 lea      rdx, [rsp + 0x78]
0022CABD lea      rcx, [rbp - 0x10]
0022CAC1 call     0x1403ff710
0022CAC6 mov      r9d, r14d
0022CAC9 lea      rdx, [rbp - 0x10]
0022CACD mov      r8d, r14d
0022CAD0 lea      rcx, [rbx + 0x2f0]
0022CAD7 call     0x14018aa40
0022CADC movzx    eax, r14b
0022CAE0 jmp      0x14022cae4
0022CAE2 xor      al, al
0022CAE4 xor      edx, edx
0022CAE6 mov      byte ptr [rbx + 0x414], al
0022CAEC lea      rcx, [rbx + 0x1b8]
0022CAF3 call     0x140412380
0022CAF8 xor      edx, edx
0022CAFA lea      rcx, [rbx + 0x1b8]
0022CB01 call     0x140411610
0022CB06 lea      rcx, [rbx + 0x140]
0022CB0D lea      r8, [rbp - 0x58]
0022CB11 lea      rdx, [rbp + 8]
0022CB15 call     0x1403ff890
0022CB1A mov      dword ptr [rbx + 0x410], edi
0022CB20 mov      byte ptr [rbx + 0x415], dil
0022CB27 mov      byte ptr [rbx + 0x420], dil
0022CB2E mov      edi, 0x70
0022CB33 jmp      0x14022cb37
0022CB35 xor      ebx, ebx
0022CB37 test     dil, 0x40
0022CB3B je       0x14022cb49
0022CB3D and      edi, 0xffffffbf
0022CB40 lea      rcx, [rbp - 0x78]
0022CB44 call     0x1403fd740
0022CB49 test     dil, 0x20
0022CB4D je       0x14022cb5b
0022CB4F and      edi, 0xffffffdf
0022CB52 lea      rcx, [rbp - 0x58]
0022CB56 call     0x1403fd740
0022CB5B test     dil, 0x10
0022CB5F je       0x14022cb6b
0022CB61 lea      rcx, [rsp + 0x78]
0022CB66 call     0x1403fd740
0022CB6B lea      r8, [rip + 0x36fd1e]
0022CB72 jmp      0x14022c317
0022CB77 lea      rdx, [rip + 0x36c6ca]
0022CB7E lea      rcx, [rsp + 0x60]
0022CB83 call     0x1403fd810
0022CB88 lea      rdx, [rip + 0x3bec1e]
0022CB8F lea      rcx, [rsp + 0x50]
0022CB94 call     0x1403fd810
0022CB99 lea      rdx, [rip + 0x3bec0d]
0022CBA0 lea      rcx, [rsp + 0x58]
0022CBA5 call     0x1403fd810
0022CBAA mov      ecx, 0x418
0022CBAF call     0x1404f7a88
0022CBB4 mov      rbx, rax
0022CBB7 test     rax, rax
0022CBBA je       0x14022c30e
0022CBC0 mov      rcx, rax
0022CBC3 call     0x140226910
0022CBC8 lea      rax, [rip + 0x36f7b1]
0022CBCF lea      rcx, [rbx + 0x1b8]
0022CBD6 mov      qword ptr [rbx], rax
0022CBD9 call     0x140410f70
0022CBDE lea      rcx, [rbx + 0x2f0]
0022CBE5 call     0x140410d80
0022CBEA lea      rdx, [rsp + 0x60]
0022CBEF lea      rcx, [rbp - 0x20]
0022CBF3 call     0x1403ff710
0022CBF8 lea      rcx, [rbx + 0x2c0]
0022CBFF mov      r9d, r14d
0022CC02 mov      r8d, r14d
0022CC05 lea      rdx, [rbp - 0x20]
0022CC09 call     0x14014d080
0022CC0E mov      rax, qword ptr [rsp + 0x50]
0022CC13 cmp      dword ptr [rax - 8], edi
0022CC16 je       0x14022cc42
0022CC18 lea      rdx, [rsp + 0x50]
0022CC1D lea      rcx, [rbp - 0x18]
0022CC21 call     0x1403ff710
0022CC26 mov      r9d, r14d
0022CC29 lea      rdx, [rbp - 0x18]
0022CC2D mov      r8d, r14d
0022CC30 lea      rcx, [rbx + 0x2f0]
0022CC37 call     0x14018aa40
0022CC3C movzx    eax, r14b
0022CC40 jmp      0x14022cc44
0022CC42 xor      al, al
0022CC44 xor      edx, edx
0022CC46 mov      byte ptr [rbx + 0x414], al
0022CC4C lea      rcx, [rbx + 0x1b8]
0022CC53 call     0x140412380
0022CC58 xor      edx, edx
0022CC5A lea      rcx, [rbx + 0x1b8]
0022CC61 call     0x140411610
0022CC66 lea      rcx, [rbx + 0x140]
0022CC6D lea      r8, [rsp + 0x58]
0022CC72 lea      rdx, [rbp - 0x10]
0022CC76 call     0x1403ff890
0022CC7B mov      dword ptr [rbx + 0x410], 8
0022CC85 mov      byte ptr [rbx + 0x415], dil
0022CC8C mov      byte ptr [rbx + 0x158], r14b
0022CC93 jmp      0x14022c310
0022CC98 lea      rdx, [rip + 0x36c5d9]
0022CC9F lea      rcx, [rsp + 0x60]
0022CCA4 call     0x1403fd810
0022CCA9 lea      rdx, [rip + 0x3beafd]
0022CCB0 lea      rcx, [rsp + 0x50]
0022CCB5 call     0x1403fd810
0022CCBA lea      rdx, [rip + 0x3beaec]
0022CCC1 lea      rcx, [rsp + 0x58]
0022CCC6 call     0x1403fd810
0022CCCB mov      ecx, 0x418
0022CCD0 call     0x1404f7a88
0022CCD5 mov      rbx, rax
0022CCD8 test     rax, rax
0022CCDB je       0x14022c30e
0022CCE1 mov      rcx, rax
0022CCE4 call     0x140226910
0022CCE9 lea      rax, [rip + 0x36f690]
0022CCF0 lea      rcx, [rbx + 0x1b8]
0022CCF7 mov      qword ptr [rbx], rax
0022CCFA call     0x140410f70
0022CCFF lea      rcx, [rbx + 0x2f0]
0022CD06 call     0x140410d80
0022CD0B lea      rdx, [rsp + 0x60]
0022CD10 lea      rcx, [rbp - 0x20]
0022CD14 call     0x1403ff710
0022CD19 lea      rcx, [rbx + 0x2c0]
0022CD20 mov      r9d, r14d
0022CD23 mov      r8d, r14d
0022CD26 lea      rdx, [rbp - 0x20]
0022CD2A call     0x14014d080
0022CD2F mov      rax, qword ptr [rsp + 0x50]
0022CD34 cmp      dword ptr [rax - 8], edi
0022CD37 je       0x14022cc42
0022CD3D lea      rdx, [rsp + 0x50]
0022CD42 lea      rcx, [rbp - 0x18]
0022CD46 call     0x1403ff710
0022CD4B mov      r9d, r14d
0022CD4E lea      rdx, [rbp - 0x18]
0022CD52 mov      r8d, r14d
0022CD55 lea      rcx, [rbx + 0x2f0]
0022CD5C call     0x14018aa40
0022CD61 movzx    eax, r14b
0022CD65 jmp      0x14022cc44
0022CD6A lea      rdx, [rip + 0x36c51f]
0022CD71 lea      rcx, [rsp + 0x60]
0022CD76 call     0x1403fd810
0022CD7B lea      rdx, [rip + 0x3bea2b]
0022CD82 lea      rcx, [rsp + 0x50]
0022CD87 call     0x1403fd810
0022CD8C lea      rdx, [rip + 0x3bea1a]
0022CD93 lea      rcx, [rsp + 0x58]
0022CD98 call     0x1403fd810
0022CD9D mov      ecx, 0x418
0022CDA2 call     0x1404f7a88
0022CDA7 mov      rbx, rax
0022CDAA test     rax, rax
0022CDAD je       0x14022c30e
0022CDB3 mov      rcx, rax
0022CDB6 call     0x140226910
0022CDBB lea      rax, [rip + 0x36f5be]
0022CDC2 lea      rcx, [rbx + 0x1b8]
0022CDC9 mov      qword ptr [rbx], rax
0022CDCC call     0x140410f70
0022CDD1 lea      rcx, [rbx + 0x2f0]
0022CDD8 call     0x140410d80
0022CDDD lea      rdx, [rsp + 0x60]
0022CDE2 lea      rcx, [rbp - 0x20]
0022CDE6 call     0x1403ff710
0022CDEB lea      rcx, [rbx + 0x2c0]
0022CDF2 mov      r9d, r14d
0022CDF5 mov      r8d, r14d
0022CDF8 lea      rdx, [rbp - 0x20]
0022CDFC call     0x14014d080
0022CE01 mov      rax, qword ptr [rsp + 0x50]
0022CE06 cmp      dword ptr [rax - 8], edi
0022CE09 je       0x14022cc42
0022CE0F lea      rdx, [rsp + 0x50]
0022CE14 lea      rcx, [rbp - 0x18]
0022CE18 call     0x1403ff710
0022CE1D mov      r9d, r14d
0022CE20 lea      rdx, [rbp - 0x18]
0022CE24 mov      r8d, r14d
0022CE27 lea      rcx, [rbx + 0x2f0]
0022CE2E call     0x14018aa40
0022CE33 movzx    eax, r14b
0022CE37 jmp      0x14022cc44
0022CE3C lea      rdx, [rip + 0x36c405]
0022CE43 lea      rcx, [rsp + 0x60]
0022CE48 call     0x1403fd810
0022CE4D lea      rdx, [rip + 0x36fa44]
0022CE54 lea      rcx, [rsp + 0x50]
0022CE59 call     0x1403fd810
0022CE5E lea      rdx, [rip + 0x3be948]
0022CE65 lea      rcx, [rsp + 0x58]
0022CE6A call     0x1403fd810
0022CE6F mov      ecx, 0x418
0022CE74 call     0x1404f7a88
0022CE79 mov      rbx, rax
0022CE7C test     rax, rax
0022CE7F je       0x14022c30e
0022CE85 mov      rcx, rax
0022CE88 call     0x140226910
0022CE8D lea      rax, [rip + 0x36f4ec]
0022CE94 lea      rcx, [rbx + 0x1b8]
0022CE9B mov      qword ptr [rbx], rax
0022CE9E call     0x140410f70
0022CEA3 lea      rcx, [rbx + 0x2f0]
0022CEAA call     0x140410d80
0022CEAF lea      rdx, [rsp + 0x60]
0022CEB4 lea      rcx, [rbp - 0x20]
0022CEB8 call     0x1403ff710
0022CEBD lea      rcx, [rbx + 0x2c0]
0022CEC4 mov      r9d, r14d
0022CEC7 mov      r8d, r14d
0022CECA lea      rdx, [rbp - 0x20]
0022CECE call     0x14014d080
0022CED3 mov      rax, qword ptr [rsp + 0x50]
0022CED8 cmp      dword ptr [rax - 8], edi
0022CEDB je       0x14022cc42
0022CEE1 lea      rdx, [rsp + 0x50]
0022CEE6 lea      rcx, [rbp - 0x18]
0022CEEA call     0x1403ff710
0022CEEF mov      r9d, r14d
0022CEF2 lea      rdx, [rbp - 0x18]
0022CEF6 mov      r8d, r14d
0022CEF9 lea      rcx, [rbx + 0x2f0]
0022CF00 call     0x14018aa40
0022CF05 movzx    eax, r14b
0022CF09 jmp      0x14022cc44
0022CF0E lea      rdx, [rip + 0x36c363]
0022CF15 lea      rcx, [rsp + 0x60]
0022CF1A call     0x1403fd810
0022CF1F lea      rdx, [rip + 0x36f97a]
0022CF26 lea      rcx, [rsp + 0x50]
0022CF2B call     0x1403fd810
0022CF30 lea      rdx, [rip + 0x3be876]
0022CF37 lea      rcx, [rsp + 0x58]
0022CF3C call     0x1403fd810
0022CF41 mov      ecx, 0x418
0022CF46 call     0x1404f7a88
0022CF4B mov      rbx, rax
0022CF4E test     rax, rax
0022CF51 je       0x14022c30e
0022CF57 mov      rcx, rax
0022CF5A call     0x140226910
0022CF5F lea      rax, [rip + 0x36f41a]
0022CF66 lea      rcx, [rbx + 0x1b8]
0022CF6D mov      qword ptr [rbx], rax
0022CF70 call     0x140410f70
0022CF75 lea      rcx, [rbx + 0x2f0]
0022CF7C call     0x140410d80
0022CF81 lea      rdx, [rsp + 0x60]
0022CF86 lea      rcx, [rbp - 0x20]
0022CF8A call     0x1403ff710
0022CF8F lea      rcx, [rbx + 0x2c0]
0022CF96 mov      r9d, r14d
0022CF99 mov      r8d, r14d
0022CF9C lea      rdx, [rbp - 0x20]
0022CFA0 call     0x14014d080
0022CFA5 mov      rax, qword ptr [rsp + 0x50]
0022CFAA cmp      dword ptr [rax - 8], edi
0022CFAD je       0x14022cc42
0022CFB3 lea      rdx, [rsp + 0x50]
0022CFB8 lea      rcx, [rbp - 0x18]
0022CFBC call     0x1403ff710
0022CFC1 mov      r9d, r14d
0022CFC4 lea      rdx, [rbp - 0x18]
0022CFC8 mov      r8d, r14d
0022CFCB lea      rcx, [rbx + 0x2f0]
0022CFD2 call     0x14018aa40
0022CFD7 movzx    eax, r14b
0022CFDB jmp      0x14022cc44
0022CFE0 lea      rdx, [rip + 0x36c2a9]
0022CFE7 lea      rcx, [rsp + 0x60]
0022CFEC call     0x1403fd810
0022CFF1 lea      rdx, [rip + 0x36f8b8]
0022CFF8 lea      rcx, [rsp + 0x50]
0022CFFD call     0x1403fd810
0022D002 lea      rdx, [rip + 0x3be7a4]
0022D009 lea      rcx, [rsp + 0x58]
0022D00E call     0x1403fd810
0022D013 mov      ecx, 0x418
0022D018 call     0x1404f7a88
0022D01D mov      rbx, rax
0022D020 test     rax, rax
0022D023 je       0x14022c30e
0022D029 mov      rcx, rax
0022D02C call     0x140226910
0022D031 lea      rax, [rip + 0x36f348]
0022D038 lea      rcx, [rbx + 0x1b8]
0022D03F mov      qword ptr [rbx], rax
0022D042 call     0x140410f70
0022D047 lea      rcx, [rbx + 0x2f0]
0022D04E call     0x140410d80
0022D053 lea      rdx, [rsp + 0x60]
0022D058 lea      rcx, [rbp - 0x20]
0022D05C call     0x1403ff710
0022D061 lea      rcx, [rbx + 0x2c0]
0022D068 mov      r9d, r14d
0022D06B mov      r8d, r14d
0022D06E lea      rdx, [rbp - 0x20]
0022D072 call     0x14014d080
0022D077 mov      rax, qword ptr [rsp + 0x50]
0022D07C cmp      dword ptr [rax - 8], edi
0022D07F je       0x14022cc42
0022D085 lea      rdx, [rsp + 0x50]
0022D08A lea      rcx, [rbp - 0x18]
0022D08E call     0x1403ff710
0022D093 mov      r9d, r14d
0022D096 lea      rdx, [rbp - 0x18]
0022D09A mov      r8d, r14d
0022D09D lea      rcx, [rbx + 0x2f0]
0022D0A4 call     0x14018aa40
0022D0A9 movzx    eax, r14b
0022D0AD jmp      0x14022cc44
0022D0B2 lea      rdx, [rip + 0x36c18f]
0022D0B9 lea      rcx, [rsp + 0x60]
0022D0BE call     0x1403fd810
0022D0C3 lea      rdx, [rip + 0x36f7f2]
0022D0CA lea      rcx, [rsp + 0x50]
0022D0CF call     0x1403fd810
0022D0D4 lea      rdx, [rip + 0x3be6d2]
0022D0DB lea      rcx, [rsp + 0x58]
0022D0E0 call     0x1403fd810
0022D0E5 mov      ecx, 0x418
0022D0EA call     0x1404f7a88
0022D0EF mov      rbx, rax
0022D0F2 test     rax, rax
0022D0F5 je       0x14022c30e
0022D0FB mov      rcx, rax
0022D0FE call     0x140226910
0022D103 lea      rax, [rip + 0x36f276]
0022D10A lea      rcx, [rbx + 0x1b8]
0022D111 mov      qword ptr [rbx], rax
0022D114 call     0x140410f70
0022D119 lea      rcx, [rbx + 0x2f0]
0022D120 call     0x140410d80
0022D125 lea      rdx, [rsp + 0x60]
0022D12A lea      rcx, [rbp - 0x20]
0022D12E call     0x1403ff710
0022D133 lea      rcx, [rbx + 0x2c0]
0022D13A mov      r9d, r14d
0022D13D mov      r8d, r14d
0022D140 lea      rdx, [rbp - 0x20]
0022D144 call     0x14014d080
0022D149 mov      rax, qword ptr [rsp + 0x50]
0022D14E cmp      dword ptr [rax - 8], edi
0022D151 je       0x14022cc42
0022D157 lea      rdx, [rsp + 0x50]
0022D15C lea      rcx, [rbp - 0x18]
0022D160 call     0x1403ff710
0022D165 mov      r9d, r14d
0022D168 lea      rdx, [rbp - 0x18]
0022D16C mov      r8d, r14d
0022D16F lea      rcx, [rbx + 0x2f0]
0022D176 call     0x14018aa40
0022D17B movzx    eax, r14b
0022D17F jmp      0x14022cc44
0022D184 lea      rdx, [rip + 0x36c0ed]
0022D18B lea      rcx, [rsp + 0x60]
0022D190 call     0x1403fd810
0022D195 lea      rdx, [rip + 0x36f72c]
0022D19C lea      rcx, [rsp + 0x50]
0022D1A1 call     0x1403fd810
0022D1A6 lea      rdx, [rip + 0x3be600]
0022D1AD lea      rcx, [rsp + 0x58]
0022D1B2 call     0x1403fd810
0022D1B7 mov      ecx, 0x418
0022D1BC call     0x1404f7a88
0022D1C1 mov      rbx, rax
0022D1C4 test     rax, rax
0022D1C7 je       0x14022c30e
0022D1CD mov      rcx, rax
0022D1D0 call     0x140226910
0022D1D5 lea      rax, [rip + 0x36f1a4]
0022D1DC lea      rcx, [rbx + 0x1b8]
0022D1E3 mov      qword ptr [rbx], rax
0022D1E6 call     0x140410f70
0022D1EB lea      rcx, [rbx + 0x2f0]
0022D1F2 call     0x140410d80
0022D1F7 lea      rdx, [rsp + 0x60]
0022D1FC lea      rcx, [rbp - 0x20]
0022D200 call     0x1403ff710
0022D205 lea      rcx, [rbx + 0x2c0]
0022D20C mov      r9d, r14d
0022D20F mov      r8d, r14d
0022D212 lea      rdx, [rbp - 0x20]
0022D216 call     0x14014d080
0022D21B mov      rax, qword ptr [rsp + 0x50]
0022D220 cmp      dword ptr [rax - 8], edi
0022D223 je       0x14022cc42
0022D229 lea      rdx, [rsp + 0x50]
0022D22E lea      rcx, [rbp - 0x18]
0022D232 call     0x1403ff710
0022D237 mov      r9d, r14d
0022D23A lea      rdx, [rbp - 0x18]
0022D23E mov      r8d, r14d
0022D241 lea      rcx, [rbx + 0x2f0]
0022D248 call     0x14018aa40
0022D24D movzx    eax, r14b
0022D251 jmp      0x14022cc44
0022D256 lea      rdx, [rip + 0x36c033]
0022D25D lea      rcx, [rsp + 0x60]
0022D262 call     0x1403fd810
0022D267 lea      rdx, [rip + 0x36f66a]
0022D26E lea      rcx, [rsp + 0x50]
0022D273 call     0x1403fd810
0022D278 lea      rdx, [rip + 0x3be52e]
0022D27F lea      rcx, [rsp + 0x58]
0022D284 call     0x1403fd810
0022D289 mov      ecx, 0x418
0022D28E call     0x1404f7a88
0022D293 mov      rbx, rax
0022D296 test     rax, rax
0022D299 je       0x14022c30e
0022D29F mov      rcx, rax
0022D2A2 call     0x140226910
0022D2A7 lea      rax, [rip + 0x36f0d2]
0022D2AE lea      rcx, [rbx + 0x1b8]
0022D2B5 mov      qword ptr [rbx], rax
0022D2B8 call     0x140410f70
0022D2BD lea      rcx, [rbx + 0x2f0]
0022D2C4 call     0x140410d80
0022D2C9 lea      rdx, [rsp + 0x60]
0022D2CE lea      rcx, [rbp - 0x20]
0022D2D2 call     0x1403ff710
0022D2D7 lea      rcx, [rbx + 0x2c0]
0022D2DE mov      r9d, r14d
0022D2E1 mov      r8d, r14d
0022D2E4 lea      rdx, [rbp - 0x20]
0022D2E8 call     0x14014d080
0022D2ED mov      rax, qword ptr [rsp + 0x50]
0022D2F2 cmp      dword ptr [rax - 8], edi
0022D2F5 je       0x14022cc42
0022D2FB lea      rdx, [rsp + 0x50]
0022D300 lea      rcx, [rbp - 0x18]
0022D304 call     0x1403ff710
0022D309 mov      r9d, r14d
0022D30C lea      rdx, [rbp - 0x18]
0022D310 mov      r8d, r14d
0022D313 lea      rcx, [rbx + 0x2f0]
0022D31A call     0x14018aa40
0022D31F movzx    eax, r14b
0022D323 jmp      0x14022cc44
0022D328 lea      rdx, [rip + 0x36bf19]
0022D32F lea      rcx, [rsp + 0x60]
0022D334 call     0x1403fd810
0022D339 lea      rdx, [rip + 0x36f5a4]
0022D340 lea      rcx, [rsp + 0x50]
0022D345 call     0x1403fd810
0022D34A lea      rdx, [rip + 0x3be45c]
0022D351 lea      rcx, [rsp + 0x58]
0022D356 call     0x1403fd810
0022D35B mov      ecx, 0x418
0022D360 call     0x1404f7a88
0022D365 mov      rbx, rax
0022D368 test     rax, rax
0022D36B je       0x14022c30e
0022D371 mov      rcx, rax
0022D374 call     0x140226910
0022D379 lea      rax, [rip + 0x36f000]
0022D380 lea      rcx, [rbx + 0x1b8]
0022D387 mov      qword ptr [rbx], rax
0022D38A call     0x140410f70
0022D38F lea      rcx, [rbx + 0x2f0]
0022D396 call     0x140410d80
0022D39B lea      rdx, [rsp + 0x60]
0022D3A0 lea      rcx, [rbp - 0x20]
0022D3A4 call     0x1403ff710
0022D3A9 lea      rcx, [rbx + 0x2c0]
0022D3B0 mov      r9d, r14d
0022D3B3 mov      r8d, r14d
0022D3B6 lea      rdx, [rbp - 0x20]
0022D3BA call     0x14014d080
0022D3BF mov      rax, qword ptr [rsp + 0x50]
0022D3C4 cmp      dword ptr [rax - 8], edi
0022D3C7 je       0x14022cc42
0022D3CD lea      rdx, [rsp + 0x50]
0022D3D2 lea      rcx, [rbp - 0x18]
0022D3D6 call     0x1403ff710
0022D3DB mov      r9d, r14d
0022D3DE lea      rdx, [rbp - 0x18]
0022D3E2 mov      r8d, r14d
0022D3E5 lea      rcx, [rbx + 0x2f0]
0022D3EC call     0x14018aa40
0022D3F1 movzx    eax, r14b
0022D3F5 jmp      0x14022cc44
0022D3FA lea      rdx, [rip + 0x36be77]
0022D401 lea      rcx, [rsp + 0x60]
0022D406 call     0x1403fd810
0022D40B lea      rdx, [rip + 0x36f4de]
0022D412 lea      rcx, [rsp + 0x50]
0022D417 call     0x1403fd810
0022D41C lea      rdx, [rip + 0x3be38a]
0022D423 lea      rcx, [rsp + 0x58]
0022D428 call     0x1403fd810
0022D42D mov      ecx, 0x418
0022D432 call     0x1404f7a88
0022D437 mov      rbx, rax
0022D43A test     rax, rax
0022D43D je       0x14022c30e
0022D443 mov      rcx, rax
0022D446 call     0x140226910
0022D44B lea      rax, [rip + 0x36ef2e]
0022D452 lea      rcx, [rbx + 0x1b8]
0022D459 mov      qword ptr [rbx], rax
0022D45C call     0x140410f70
0022D461 lea      rcx, [rbx + 0x2f0]
0022D468 call     0x140410d80
0022D46D lea      rdx, [rsp + 0x60]
0022D472 lea      rcx, [rbp - 0x20]
0022D476 call     0x1403ff710
0022D47B lea      rcx, [rbx + 0x2c0]
0022D482 mov      r9d, r14d
0022D485 mov      r8d, r14d
0022D488 lea      rdx, [rbp - 0x20]
0022D48C call     0x14014d080
0022D491 mov      rax, qword ptr [rsp + 0x50]
0022D496 cmp      dword ptr [rax - 8], edi
0022D499 je       0x14022cc42
0022D49F lea      rdx, [rsp + 0x50]
0022D4A4 lea      rcx, [rbp - 0x18]
0022D4A8 call     0x1403ff710
0022D4AD mov      r9d, r14d
0022D4B0 lea      rdx, [rbp - 0x18]
0022D4B4 mov      r8d, r14d
0022D4B7 lea      rcx, [rbx + 0x2f0]
0022D4BE call     0x14018aa40
0022D4C3 movzx    eax, r14b
0022D4C7 jmp      0x14022cc44
0022D4CC lea      rdx, [rip + 0x36bdbd]
0022D4D3 lea      rcx, [rsp + 0x60]
0022D4D8 call     0x1403fd810
0022D4DD lea      rdx, [rip + 0x36f41c]
0022D4E4 lea      rcx, [rsp + 0x50]
0022D4E9 call     0x1403fd810
0022D4EE lea      rdx, [rip + 0x3be2b8]
0022D4F5 lea      rcx, [rsp + 0x58]
0022D4FA call     0x1403fd810
0022D4FF mov      ecx, 0x418
0022D504 call     0x1404f7a88
0022D509 mov      rbx, rax
0022D50C test     rax, rax
0022D50F je       0x14022c30e
0022D515 mov      rcx, rax
0022D518 call     0x140226910
0022D51D lea      rax, [rip + 0x36ee5c]
0022D524 lea      rcx, [rbx + 0x1b8]
0022D52B mov      qword ptr [rbx], rax
0022D52E call     0x140410f70
0022D533 lea      rcx, [rbx + 0x2f0]
0022D53A call     0x140410d80
0022D53F lea      rdx, [rsp + 0x60]
0022D544 lea      rcx, [rbp - 0x20]
0022D548 call     0x1403ff710
0022D54D lea      rcx, [rbx + 0x2c0]
0022D554 mov      r9d, r14d
0022D557 mov      r8d, r14d
0022D55A lea      rdx, [rbp - 0x20]
0022D55E call     0x14014d080
0022D563 mov      rax, qword ptr [rsp + 0x50]
0022D568 cmp      dword ptr [rax - 8], edi
0022D56B je       0x14022cc42
0022D571 lea      rdx, [rsp + 0x50]
0022D576 lea      rcx, [rbp - 0x18]
0022D57A call     0x1403ff710
0022D57F mov      r9d, r14d
0022D582 lea      rdx, [rbp - 0x18]
0022D586 mov      r8d, r14d
0022D589 lea      rcx, [rbx + 0x2f0]
0022D590 call     0x14018aa40
0022D595 movzx    eax, r14b
0022D599 jmp      0x14022cc44
0022D59E lea      rdx, [rip + 0x36bca3]
0022D5A5 lea      rcx, [rsp + 0x60]
0022D5AA call     0x1403fd810
0022D5AF lea      rdx, [rip + 0x36f356]
0022D5B6 lea      rcx, [rsp + 0x50]
0022D5BB call     0x1403fd810
0022D5C0 lea      rdx, [rip + 0x3be1e6]
0022D5C7 lea      rcx, [rsp + 0x58]
0022D5CC call     0x1403fd810
0022D5D1 mov      ecx, 0x418
0022D5D6 call     0x1404f7a88
0022D5DB mov      rbx, rax
0022D5DE test     rax, rax
0022D5E1 je       0x14022c30e
0022D5E7 mov      rcx, rax
0022D5EA call     0x140226910
0022D5EF lea      rax, [rip + 0x36ed8a]
0022D5F6 lea      rcx, [rbx + 0x1b8]
0022D5FD mov      qword ptr [rbx], rax
0022D600 call     0x140410f70
0022D605 lea      rcx, [rbx + 0x2f0]
0022D60C call     0x140410d80
0022D611 lea      rdx, [rsp + 0x60]
0022D616 lea      rcx, [rbp - 0x20]
0022D61A call     0x1403ff710
0022D61F lea      rcx, [rbx + 0x2c0]
0022D626 mov      r9d, r14d
0022D629 mov      r8d, r14d
0022D62C lea      rdx, [rbp - 0x20]
0022D630 call     0x14014d080
0022D635 mov      rax, qword ptr [rsp + 0x50]
0022D63A cmp      dword ptr [rax - 8], edi
0022D63D je       0x14022cc42
0022D643 lea      rdx, [rsp + 0x50]
0022D648 lea      rcx, [rbp - 0x18]
0022D64C call     0x1403ff710
0022D651 mov      r9d, r14d
0022D654 lea      rdx, [rbp - 0x18]
0022D658 mov      r8d, r14d
0022D65B lea      rcx, [rbx + 0x2f0]
0022D662 call     0x14018aa40
0022D667 movzx    eax, r14b
0022D66B jmp      0x14022cc44
0022D670 lea      rdx, [rip + 0x36bc01]
0022D677 lea      rcx, [rsp + 0x60]
0022D67C call     0x1403fd810
0022D681 lea      rdx, [rip + 0x36f290]
0022D688 lea      rcx, [rsp + 0x50]
0022D68D call     0x1403fd810
0022D692 lea      rdx, [rip + 0x3be114]
0022D699 lea      rcx, [rsp + 0x58]
0022D69E call     0x1403fd810
0022D6A3 mov      ecx, 0x418
0022D6A8 call     0x1404f7a88
0022D6AD mov      rbx, rax
0022D6B0 test     rax, rax
0022D6B3 je       0x14022c30e
0022D6B9 mov      rcx, rax
0022D6BC call     0x140226910
0022D6C1 lea      rax, [rip + 0x36ecb8]
0022D6C8 lea      rcx, [rbx + 0x1b8]
0022D6CF mov      qword ptr [rbx], rax
0022D6D2 call     0x140410f70
0022D6D7 lea      rcx, [rbx + 0x2f0]
0022D6DE call     0x140410d80
0022D6E3 lea      rdx, [rsp + 0x60]
0022D6E8 lea      rcx, [rbp - 0x20]
0022D6EC call     0x1403ff710
0022D6F1 lea      rcx, [rbx + 0x2c0]
0022D6F8 mov      r9d, r14d
0022D6FB mov      r8d, r14d
0022D6FE lea      rdx, [rbp - 0x20]
0022D702 call     0x14014d080
0022D707 mov      rax, qword ptr [rsp + 0x50]
0022D70C cmp      dword ptr [rax - 8], edi
0022D70F je       0x14022cc42
0022D715 lea      rdx, [rsp + 0x50]
0022D71A lea      rcx, [rbp - 0x18]
0022D71E call     0x1403ff710
0022D723 mov      r9d, r14d
0022D726 lea      rdx, [rbp - 0x18]
0022D72A mov      r8d, r14d
0022D72D lea      rcx, [rbx + 0x2f0]
0022D734 call     0x14018aa40
0022D739 movzx    eax, r14b
0022D73D jmp      0x14022cc44
0022D742 lea      rdx, [rip + 0x36bb47]
0022D749 lea      rcx, [rsp + 0x60]
0022D74E call     0x1403fd810
0022D753 lea      rdx, [rip + 0x36f1ce]
0022D75A lea      rcx, [rsp + 0x50]
0022D75F call     0x1403fd810
0022D764 lea      rdx, [rip + 0x3be042]
0022D76B lea      rcx, [rsp + 0x58]
0022D770 call     0x1403fd810
0022D775 mov      ecx, 0x418
0022D77A call     0x1404f7a88
0022D77F mov      rbx, rax
0022D782 test     rax, rax
0022D785 je       0x14022c30e
0022D78B mov      rcx, rax
0022D78E call     0x140226910
0022D793 lea      rax, [rip + 0x36ebe6]
0022D79A lea      rcx, [rbx + 0x1b8]
0022D7A1 mov      qword ptr [rbx], rax
0022D7A4 call     0x140410f70
0022D7A9 lea      rcx, [rbx + 0x2f0]
0022D7B0 call     0x140410d80
0022D7B5 lea      rdx, [rsp + 0x60]
0022D7BA lea      rcx, [rbp - 0x20]
0022D7BE call     0x1403ff710
0022D7C3 lea      rcx, [rbx + 0x2c0]
0022D7CA mov      r9d, r14d
0022D7CD mov      r8d, r14d
0022D7D0 lea      rdx, [rbp - 0x20]
0022D7D4 call     0x14014d080
0022D7D9 mov      rax, qword ptr [rsp + 0x50]
0022D7DE cmp      dword ptr [rax - 8], edi
0022D7E1 je       0x14022cc42
0022D7E7 lea      rdx, [rsp + 0x50]
0022D7EC lea      rcx, [rbp - 0x18]
0022D7F0 call     0x1403ff710
0022D7F5 mov      r9d, r14d
0022D7F8 lea      rdx, [rbp - 0x18]
0022D7FC mov      r8d, r14d
0022D7FF lea      rcx, [rbx + 0x2f0]
0022D806 call     0x14018aa40
0022D80B movzx    eax, r14b
0022D80F jmp      0x14022cc44
0022D814 lea      rdx, [rip + 0x36ba2d]
0022D81B lea      rcx, [rsp + 0x60]
0022D820 call     0x1403fd810
0022D825 lea      rdx, [rip + 0x36f108]
0022D82C lea      rcx, [rsp + 0x50]
0022D831 call     0x1403fd810
0022D836 lea      rdx, [rip + 0x3bdf70]
0022D83D lea      rcx, [rsp + 0x58]
0022D842 call     0x1403fd810
0022D847 mov      ecx, 0x418
0022D84C call     0x1404f7a88
0022D851 mov      rbx, rax
0022D854 test     rax, rax
0022D857 je       0x14022c30e
0022D85D mov      rcx, rax
0022D860 call     0x140226910
0022D865 lea      rax, [rip + 0x36eb14]
0022D86C lea      rcx, [rbx + 0x1b8]
0022D873 mov      qword ptr [rbx], rax
0022D876 call     0x140410f70
0022D87B lea      rcx, [rbx + 0x2f0]
0022D882 call     0x140410d80
0022D887 lea      rdx, [rsp + 0x60]
0022D88C lea      rcx, [rbp - 0x20]
0022D890 call     0x1403ff710
0022D895 lea      rcx, [rbx + 0x2c0]
0022D89C mov      r9d, r14d
0022D89F mov      r8d, r14d
0022D8A2 lea      rdx, [rbp - 0x20]
0022D8A6 call     0x14014d080
0022D8AB mov      rax, qword ptr [rsp + 0x50]
0022D8B0 cmp      dword ptr [rax - 8], edi
0022D8B3 je       0x14022cc42
0022D8B9 lea      rdx, [rsp + 0x50]
0022D8BE lea      rcx, [rbp - 0x18]
0022D8C2 call     0x1403ff710
0022D8C7 mov      r9d, r14d
0022D8CA lea      rdx, [rbp - 0x18]
0022D8CE mov      r8d, r14d
0022D8D1 lea      rcx, [rbx + 0x2f0]
0022D8D8 call     0x14018aa40
0022D8DD movzx    eax, r14b
0022D8E1 jmp      0x14022cc44
0022D8E6 lea      rdx, [rip + 0x36b98b]
0022D8ED lea      rcx, [rsp + 0x60]
0022D8F2 call     0x1403fd810
0022D8F7 lea      rdx, [rip + 0x36f042]
0022D8FE lea      rcx, [rsp + 0x50]
0022D903 call     0x1403fd810
0022D908 lea      rdx, [rip + 0x3bde9e]
0022D90F lea      rcx, [rsp + 0x58]
0022D914 call     0x1403fd810
0022D919 mov      ecx, 0x418
0022D91E call     0x1404f7a88
0022D923 mov      rbx, rax
0022D926 test     rax, rax
0022D929 je       0x14022da04
0022D92F mov      rcx, rax
0022D932 call     0x140226910
0022D937 lea      rax, [rip + 0x36ea42]
0022D93E lea      rcx, [rbx + 0x1b8]
0022D945 mov      qword ptr [rbx], rax
0022D948 call     0x140410f70
0022D94D lea      rcx, [rbx + 0x2f0]
0022D954 call     0x140410d80
0022D959 lea      rdx, [rsp + 0x60]
0022D95E lea      rcx, [rbp - 0x20]
0022D962 call     0x1403ff710
0022D967 lea      rcx, [rbx + 0x2c0]
0022D96E mov      r9d, r14d
0022D971 mov      r8d, r14d
0022D974 lea      rdx, [rbp - 0x20]
0022D978 call     0x14014d080
0022D97D mov      rax, qword ptr [rsp + 0x50]
0022D982 cmp      dword ptr [rax - 8], edi
0022D985 je       0x14022d9b1
0022D987 lea      rdx, [rsp + 0x50]
0022D98C lea      rcx, [rbp - 0x18]
0022D990 call     0x1403ff710
0022D995 mov      r9d, r14d
0022D998 lea      rdx, [rbp - 0x18]
0022D99C mov      r8d, r14d
0022D99F lea      rcx, [rbx + 0x2f0]
0022D9A6 call     0x14018aa40
0022D9AB movzx    eax, r14b
0022D9AF jmp      0x14022d9b3
0022D9B1 xor      al, al
0022D9B3 xor      edx, edx
0022D9B5 mov      byte ptr [rbx + 0x414], al
0022D9BB lea      rcx, [rbx + 0x1b8]
0022D9C2 call     0x140412380
0022D9C7 xor      edx, edx
0022D9C9 lea      rcx, [rbx + 0x1b8]
0022D9D0 call     0x140411610
0022D9D5 lea      rcx, [rbx + 0x140]
0022D9DC lea      r8, [rsp + 0x58]
0022D9E1 lea      rdx, [rbp - 0x10]
0022D9E5 call     0x1403ff890
0022D9EA mov      dword ptr [rbx + 0x410], 8
0022D9F4 mov      byte ptr [rbx + 0x415], dil
0022D9FB mov      byte ptr [rbx + 0x158], r14b
0022DA02 jmp      0x14022da06
0022DA04 xor      ebx, ebx
0022DA06 lea      rcx, [rbx + 0x140]
0022DA0D lea      r8, [rip + 0x3bdd99]
0022DA14 lea      rdx, [rbp - 0x20]
0022DA18 call     0x1403ff960
0022DA1D lea      rdx, [rbp - 0x18]
0022DA21 jmp      0x14022e8d9
0022DA26 lea      rdx, [rip + 0x36b863]
0022DA2D lea      rcx, [rsp + 0x60]
0022DA32 call     0x1403fd810
0022DA37 lea      rdx, [rip + 0x36ef12]
0022DA3E lea      rcx, [rsp + 0x50]
0022DA43 call     0x1403fd810
0022DA48 lea      rdx, [rip + 0x3bdd5e]
0022DA4F lea      rcx, [rsp + 0x58]
0022DA54 call     0x1403fd810
0022DA59 mov      ecx, 0x418
0022DA5E call     0x1404f7a88
0022DA63 mov      rbx, rax
0022DA66 test     rax, rax
0022DA69 je       0x14022da04
0022DA6B mov      rcx, rax
0022DA6E call     0x140226910
0022DA73 lea      rax, [rip + 0x36e906]
0022DA7A lea      rcx, [rbx + 0x1b8]
0022DA81 mov      qword ptr [rbx], rax
0022DA84 call     0x140410f70
0022DA89 lea      rcx, [rbx + 0x2f0]
0022DA90 call     0x140410d80
0022DA95 lea      rdx, [rsp + 0x60]
0022DA9A lea      rcx, [rbp - 0x20]
0022DA9E call     0x1403ff710
0022DAA3 lea      rcx, [rbx + 0x2c0]
0022DAAA mov      r9d, r14d
0022DAAD mov      r8d, r14d
0022DAB0 lea      rdx, [rbp - 0x20]
0022DAB4 call     0x14014d080
0022DAB9 mov      rax, qword ptr [rsp + 0x50]
0022DABE cmp      dword ptr [rax - 8], edi
0022DAC1 je       0x14022d9b1
0022DAC7 lea      rdx, [rsp + 0x50]
0022DACC lea      rcx, [rbp - 0x18]
0022DAD0 call     0x1403ff710
0022DAD5 mov      r9d, r14d
0022DAD8 lea      rdx, [rbp - 0x18]
0022DADC mov      r8d, r14d
0022DADF lea      rcx, [rbx + 0x2f0]
0022DAE6 call     0x14018aa40
0022DAEB movzx    eax, r14b
0022DAEF jmp      0x14022d9b3
0022DAF4 lea      rdx, [rip + 0x36b74d]
0022DAFB lea      rcx, [rsp + 0x60]
0022DB00 call     0x1403fd810
0022DB05 lea      rdx, [rip + 0x36ee50]
0022DB0C lea      rcx, [rsp + 0x50]
0022DB11 call     0x1403fd810
0022DB16 lea      rdx, [rip + 0x3bdc90]
0022DB1D lea      rcx, [rsp + 0x58]
0022DB22 call     0x1403fd810
0022DB27 mov      ecx, 0x418
0022DB2C call     0x1404f7a88
0022DB31 mov      rbx, rax
0022DB34 test     rax, rax
0022DB37 je       0x14022da04
0022DB3D mov      rcx, rax
0022DB40 call     0x140226910
0022DB45 lea      rax, [rip + 0x36e834]
0022DB4C lea      rcx, [rbx + 0x1b8]
0022DB53 mov      qword ptr [rbx], rax
0022DB56 call     0x140410f70
0022DB5B lea      rcx, [rbx + 0x2f0]
0022DB62 call     0x140410d80
0022DB67 lea      rdx, [rsp + 0x60]
0022DB6C lea      rcx, [rbp - 0x20]
0022DB70 call     0x1403ff710
0022DB75 lea      rcx, [rbx + 0x2c0]
0022DB7C mov      r9d, r14d
0022DB7F mov      r8d, r14d
0022DB82 lea      rdx, [rbp - 0x20]
0022DB86 call     0x14014d080
0022DB8B mov      rax, qword ptr [rsp + 0x50]
0022DB90 cmp      dword ptr [rax - 8], edi
0022DB93 je       0x14022d9b1
0022DB99 lea      rdx, [rsp + 0x50]
0022DB9E lea      rcx, [rbp - 0x18]
0022DBA2 call     0x1403ff710
0022DBA7 mov      r9d, r14d
0022DBAA lea      rdx, [rbp - 0x18]
0022DBAE mov      r8d, r14d
0022DBB1 lea      rcx, [rbx + 0x2f0]
0022DBB8 call     0x14018aa40
0022DBBD movzx    eax, r14b
0022DBC1 jmp      0x14022d9b3
0022DBC6 lea      rdx, [rip + 0x36b6ab]
0022DBCD lea      rcx, [rsp + 0x60]
0022DBD2 call     0x1403fd810
0022DBD7 lea      rdx, [rip + 0x36ed8a]
0022DBDE lea      rcx, [rsp + 0x50]
0022DBE3 call     0x1403fd810
0022DBE8 lea      rdx, [rip + 0x3bdbbe]
0022DBEF lea      rcx, [rsp + 0x58]
0022DBF4 call     0x1403fd810
0022DBF9 mov      ecx, 0x418
0022DBFE call     0x1404f7a88
0022DC03 mov      rbx, rax
0022DC06 test     rax, rax
0022DC09 je       0x14022da04
0022DC0F mov      rcx, rax
0022DC12 call     0x140226910
0022DC17 lea      rax, [rip + 0x36e762]
0022DC1E lea      rcx, [rbx + 0x1b8]
0022DC25 mov      qword ptr [rbx], rax
0022DC28 call     0x140410f70
0022DC2D lea      rcx, [rbx + 0x2f0]
0022DC34 call     0x140410d80
0022DC39 lea      rdx, [rsp + 0x60]
0022DC3E lea      rcx, [rbp - 0x20]
0022DC42 call     0x1403ff710
0022DC47 lea      rcx, [rbx + 0x2c0]
0022DC4E mov      r9d, r14d
0022DC51 mov      r8d, r14d
0022DC54 lea      rdx, [rbp - 0x20]
0022DC58 call     0x14014d080
0022DC5D mov      rax, qword ptr [rsp + 0x50]
0022DC62 cmp      dword ptr [rax - 8], edi
0022DC65 je       0x14022d9b1
0022DC6B lea      rdx, [rsp + 0x50]
0022DC70 lea      rcx, [rbp - 0x18]
0022DC74 call     0x1403ff710
0022DC79 mov      r9d, r14d
0022DC7C lea      rdx, [rbp - 0x18]
0022DC80 mov      r8d, r14d
0022DC83 lea      rcx, [rbx + 0x2f0]
0022DC8A call     0x14018aa40
0022DC8F movzx    eax, r14b
0022DC93 jmp      0x14022d9b3
0022DC98 lea      rdx, [rip + 0x36b5f1]
0022DC9F lea      rcx, [rsp + 0x60]
0022DCA4 call     0x1403fd810
0022DCA9 lea      rdx, [rip + 0x36ecc8]
0022DCB0 lea      rcx, [rsp + 0x50]
0022DCB5 call     0x1403fd810
0022DCBA lea      rdx, [rip + 0x3bdaec]
0022DCC1 lea      rcx, [rsp + 0x58]
0022DCC6 call     0x1403fd810
0022DCCB mov      ecx, 0x418
0022DCD0 call     0x1404f7a88
0022DCD5 mov      rbx, rax
0022DCD8 test     rax, rax
0022DCDB je       0x14022da04
0022DCE1 mov      rcx, rax
0022DCE4 call     0x140226910
0022DCE9 lea      rax, [rip + 0x36e690]
0022DCF0 lea      rcx, [rbx + 0x1b8]
0022DCF7 mov      qword ptr [rbx], rax
0022DCFA call     0x140410f70
0022DCFF lea      rcx, [rbx + 0x2f0]
0022DD06 call     0x140410d80
0022DD0B lea      rdx, [rsp + 0x60]
0022DD10 lea      rcx, [rbp - 0x20]
0022DD14 call     0x1403ff710
0022DD19 lea      rcx, [rbx + 0x2c0]
0022DD20 mov      r9d, r14d
0022DD23 mov      r8d, r14d
0022DD26 lea      rdx, [rbp - 0x20]
0022DD2A call     0x14014d080
0022DD2F mov      rax, qword ptr [rsp + 0x50]
0022DD34 cmp      dword ptr [rax - 8], edi
0022DD37 je       0x14022d9b1
0022DD3D lea      rdx, [rsp + 0x50]
0022DD42 lea      rcx, [rbp - 0x18]
0022DD46 call     0x1403ff710
0022DD4B mov      r9d, r14d
0022DD4E lea      rdx, [rbp - 0x18]
0022DD52 mov      r8d, r14d
0022DD55 lea      rcx, [rbx + 0x2f0]
0022DD5C call     0x14018aa40
0022DD61 movzx    eax, r14b
0022DD65 jmp      0x14022d9b3
0022DD6A lea      rdx, [rip + 0x36b4d7]
0022DD71 lea      rcx, [rsp + 0x60]
0022DD76 call     0x1403fd810
0022DD7B lea      rdx, [rip + 0x36b4ce]
0022DD82 lea      rcx, [rsp + 0x50]
0022DD87 call     0x1403fd810
0022DD8C lea      rdx, [rip + 0x3bda1a]
0022DD93 lea      rcx, [rsp + 0x58]
0022DD98 call     0x1403fd810
0022DD9D mov      ecx, 0x418
0022DDA2 call     0x1404f7a88
0022DDA7 mov      rbx, rax
0022DDAA test     rax, rax
0022DDAD je       0x14022da04
0022DDB3 mov      rcx, rax
0022DDB6 call     0x140226910
0022DDBB lea      rax, [rip + 0x36e5be]
0022DDC2 lea      rcx, [rbx + 0x1b8]
0022DDC9 mov      qword ptr [rbx], rax
0022DDCC call     0x140410f70
0022DDD1 lea      rcx, [rbx + 0x2f0]
0022DDD8 call     0x140410d80
0022DDDD lea      rdx, [rsp + 0x60]
0022DDE2 lea      rcx, [rbp - 0x20]
0022DDE6 call     0x1403ff710
0022DDEB lea      rcx, [rbx + 0x2c0]
0022DDF2 mov      r9d, r14d
0022DDF5 mov      r8d, r14d
0022DDF8 lea      rdx, [rbp - 0x20]
0022DDFC call     0x14014d080
0022DE01 mov      rax, qword ptr [rsp + 0x50]
0022DE06 cmp      dword ptr [rax - 8], edi
0022DE09 je       0x14022d9b1
0022DE0F lea      rdx, [rsp + 0x50]
0022DE14 lea      rcx, [rbp - 0x18]
0022DE18 call     0x1403ff710
0022DE1D mov      r9d, r14d
0022DE20 lea      rdx, [rbp - 0x18]
0022DE24 mov      r8d, r14d
0022DE27 lea      rcx, [rbx + 0x2f0]
0022DE2E call     0x14018aa40
0022DE33 movzx    eax, r14b
0022DE37 jmp      0x14022d9b3
0022DE3C lea      rdx, [rip + 0x36b435]
0022DE43 lea      rcx, [rsp + 0x60]
0022DE48 call     0x1403fd810
0022DE4D lea      rdx, [rip + 0x36eb34]
0022DE54 lea      rcx, [rsp + 0x50]
0022DE59 call     0x1403fd810
0022DE5E lea      rdx, [rip + 0x3bd948]
0022DE65 lea      rcx, [rsp + 0x58]
0022DE6A call     0x1403fd810
0022DE6F mov      ecx, 0x418
0022DE74 call     0x1404f7a88
0022DE79 mov      rbx, rax
0022DE7C test     rax, rax
0022DE7F je       0x14022da04
0022DE85 mov      rcx, rax
0022DE88 call     0x140226910
0022DE8D lea      rax, [rip + 0x36e4ec]
0022DE94 lea      rcx, [rbx + 0x1b8]
0022DE9B mov      qword ptr [rbx], rax
0022DE9E call     0x140410f70
0022DEA3 lea      rcx, [rbx + 0x2f0]
0022DEAA call     0x140410d80
0022DEAF lea      rdx, [rsp + 0x60]
0022DEB4 lea      rcx, [rbp - 0x20]
0022DEB8 call     0x1403ff710
0022DEBD lea      rcx, [rbx + 0x2c0]
0022DEC4 mov      r9d, r14d
0022DEC7 mov      r8d, r14d
0022DECA lea      rdx, [rbp - 0x20]
0022DECE call     0x14014d080
0022DED3 mov      rax, qword ptr [rsp + 0x50]
0022DED8 cmp      dword ptr [rax - 8], edi
0022DEDB je       0x14022d9b1
0022DEE1 lea      rdx, [rsp + 0x50]
0022DEE6 lea      rcx, [rbp - 0x18]
0022DEEA call     0x1403ff710
0022DEEF mov      r9d, r14d
0022DEF2 lea      rdx, [rbp - 0x18]
0022DEF6 mov      r8d, r14d
0022DEF9 lea      rcx, [rbx + 0x2f0]
0022DF00 call     0x14018aa40
0022DF05 movzx    eax, r14b
0022DF09 jmp      0x14022d9b3
0022DF0E lea      rdx, [rip + 0x36b37b]
0022DF15 lea      rcx, [rsp + 0x60]
0022DF1A call     0x1403fd810
0022DF1F lea      rdx, [rip + 0x36ea72]
0022DF26 lea      rcx, [rsp + 0x50]
0022DF2B call     0x1403fd810
0022DF30 lea      rdx, [rip + 0x3bd876]
0022DF37 lea      rcx, [rsp + 0x58]
0022DF3C call     0x1403fd810
0022DF41 mov      ecx, 0x418
0022DF46 call     0x1404f7a88
0022DF4B mov      rbx, rax
0022DF4E test     rax, rax
0022DF51 je       0x14022da04
0022DF57 mov      rcx, rax
0022DF5A call     0x140226910
0022DF5F lea      rax, [rip + 0x36e41a]
0022DF66 lea      rcx, [rbx + 0x1b8]
0022DF6D mov      qword ptr [rbx], rax
0022DF70 call     0x140410f70
0022DF75 lea      rcx, [rbx + 0x2f0]
0022DF7C call     0x140410d80
0022DF81 lea      rdx, [rsp + 0x60]
0022DF86 lea      rcx, [rbp - 0x20]
0022DF8A call     0x1403ff710
0022DF8F lea      rcx, [rbx + 0x2c0]
0022DF96 mov      r9d, r14d
0022DF99 mov      r8d, r14d
0022DF9C lea      rdx, [rbp - 0x20]
0022DFA0 call     0x14014d080
0022DFA5 mov      rax, qword ptr [rsp + 0x50]
0022DFAA cmp      dword ptr [rax - 8], edi
0022DFAD je       0x14022d9b1
0022DFB3 lea      rdx, [rsp + 0x50]
0022DFB8 lea      rcx, [rbp - 0x18]
0022DFBC call     0x1403ff710
0022DFC1 mov      r9d, r14d
0022DFC4 lea      rdx, [rbp - 0x18]
0022DFC8 mov      r8d, r14d
0022DFCB lea      rcx, [rbx + 0x2f0]
0022DFD2 call     0x14018aa40
0022DFD7 movzx    eax, r14b
0022DFDB jmp      0x14022d9b3
0022DFE0 mov      ecx, 0x3b8
0022DFE5 call     0x1404f7a88
0022DFEA test     rax, rax
0022DFED je       0x14022dffa
0022DFEF mov      rcx, rax
0022DFF2 call     0x140227b10
0022DFF7 mov      rbx, rax
0022DFFA xor      edx, edx
0022DFFC mov      word ptr [rbx + 0x214], r14w
0022E004 mov      rcx, rbx
0022E007 lea      r8d, [rdx + 0x43]
0022E00B call     0x140235d80
0022E010 jmp      0x14022da06
0022E015 mov      ecx, 0x3b8
0022E01A call     0x1404f7a88
0022E01F test     rax, rax
0022E022 je       0x14022e02f
0022E024 mov      rcx, rax
0022E027 call     0x140227b10
0022E02C mov      rbx, rax
0022E02F xor      edx, edx
0022E031 mov      word ptr [rbx + 0x214], r14w
0022E039 mov      rcx, rbx
0022E03C lea      r8d, [rdx + 0x41]
0022E040 call     0x140235d80
0022E045 jmp      0x14022da06
0022E04A mov      ecx, 0x3b8
0022E04F call     0x1404f7a88
0022E054 test     rax, rax
0022E057 je       0x14022e064
0022E059 mov      rcx, rax
0022E05C call     0x140227b10
0022E061 mov      rbx, rax
0022E064 xor      edx, edx
0022E066 mov      word ptr [rbx + 0x214], r14w
0022E06E mov      rcx, rbx
0022E071 lea      r8d, [rdx + 0x45]
0022E075 call     0x140235d80
0022E07A jmp      0x14022da06
0022E07F mov      ecx, 0x328
0022E084 call     0x1404f7a88
0022E089 mov      rbx, rax
0022E08C test     rax, rax
0022E08F je       0x14022e0e1
0022E091 lea      rdx, [rip + 0x3bd715]
0022E098 lea      rcx, [rbp - 0x48]
0022E09C call     0x1403fd6b0
0022E0A1 lea      rdx, [rip + 0x36b190]
0022E0A8 lea      rcx, [rbp - 0x50]
0022E0AC call     0x1403fd6b0
0022E0B1 movzx    ecx, byte ptr [rip + 0x37069c]
0022E0B8 lea      r8, [rbp - 0x48]
0022E0BC add      cx, cx
0022E0BF lea      rdx, [rbp - 0x50]
0022E0C3 mov      word ptr [rsp + 0x28], cx
0022E0C8 mov      r9b, 0xff
0022E0CB mov      rcx, rbx
0022E0CE mov      dword ptr [rsp + 0x20], edi
0022E0D2 call     0x140227cd0
0022E0D7 mov      rbx, rax
0022E0DA mov      edi, 0x180
0022E0DF jmp      0x14022e0e3
0022E0E1 xor      ebx, ebx
0022E0E3 bt       edi, 8
0022E0E7 jae      0x14022e0f6
0022E0E9 btr      edi, 8
0022E0ED lea      rcx, [rbp - 0x50]
0022E0F1 call     0x1403fd740
0022E0F6 test     dil, dil
0022E0F9 jns      0x14022da06
0022E0FF lea      rcx, [rbp - 0x48]
0022E103 call     0x1403fd740
0022E108 jmp      0x14022da06
0022E10D mov      ecx, 0x328
0022E112 call     0x1404f7a88
0022E117 mov      rbx, rax
0022E11A test     rax, rax
0022E11D je       0x14022e170
0022E11F lea      rdx, [rip + 0x3bd687]
0022E126 lea      rcx, [rbp - 0x38]
0022E12A call     0x1403fd6b0
0022E12F lea      rdx, [rip + 0x36b10a]
0022E136 lea      rcx, [rbp - 0x40]
0022E13A call     0x1403fd6b0
0022E13F movzx    ecx, byte ptr [rip + 0x37060e]
0022E146 lea      r8, [rbp - 0x38]
0022E14A add      cx, cx
0022E14D lea      rdx, [rbp - 0x40]
0022E151 mov      word ptr [rsp + 0x28], cx
0022E156 mov      r9b, 0xff
0022E159 mov      rcx, rbx
0022E15C mov      dword ptr [rsp + 0x20], r14d
0022E161 call     0x140227cd0
0022E166 mov      rbx, rax
0022E169 mov      edi, 0x600
0022E16E jmp      0x14022e172
0022E170 xor      ebx, ebx
0022E172 bt       edi, 0xa
0022E176 jae      0x14022e185
0022E178 btr      edi, 0xa
0022E17C lea      rcx, [rbp - 0x40]
0022E180 call     0x1403fd740
0022E185 bt       edi, 9
0022E189 jae      0x14022da06
0022E18F lea      rcx, [rbp - 0x38]
0022E193 call     0x1403fd740
0022E198 jmp      0x14022da06
0022E19D lea      rdx, [rip + 0x36b0a4]
0022E1A4 lea      rcx, [rsp + 0x60]
0022E1A9 call     0x1403fd810
0022E1AE lea      rdx, [rip + 0x36b09b]
0022E1B5 lea      rcx, [rsp + 0x50]
0022E1BA call     0x1403fd810
0022E1BF lea      rdx, [rip + 0x3bd5e7]
0022E1C6 lea      rcx, [rsp + 0x58]
0022E1CB call     0x1403fd810
0022E1D0 mov      ecx, 0x418
0022E1D5 call     0x1404f7a88
0022E1DA test     rax, rax
0022E1DD je       0x14022da06
0022E1E3 mov      byte ptr [rsp + 0x28], bl
0022E1E7 lea      r9, [rsp + 0x50]
0022E1EC lea      r8, [rsp + 0x58]
0022E1F1 mov      dword ptr [rsp + 0x20], 8
0022E1F9 lea      rdx, [rsp + 0x60]
0022E1FE mov      rcx, rax
0022E201 call     0x140227df0
0022E206 mov      rbx, rax
0022E209 jmp      0x14022da06
0022E20E mov      ecx, 0x3e0
0022E213 call     0x1404f7a88
0022E218 mov      rbx, rax
0022E21B test     rax, rax
0022E21E je       0x14022e277
0022E220 lea      rdx, [rip + 0x36e77d]
0022E227 lea      rcx, [rbp - 8]
0022E22B call     0x1403ff7c0
0022E230 mov      rcx, rbx
0022E233 mov      rdx, qword ptr [rax]
0022E236 call     0x140227600
0022E23B mov      dword ptr [rsp + 0x40], 0xffffffff
0022E243 lea      rax, [rip + 0x36d9fe]
0022E24A mov      byte ptr [rsp + 0x38], dil
0022E24F lea      rcx, [rbx + 0x3c8]
0022E256 mov      byte ptr [rsp + 0x30], dil
0022E25B xor      r9d, r9d
0022E25E mov      byte ptr [rsp + 0x28], dil
0022E263 xor      r8d, r8d
0022E266 xor      edx, edx
0022E268 mov      byte ptr [rsp + 0x20], dil
0022E26D mov      qword ptr [rbx], rax
0022E270 call     0x14011ba20
0022E275 jmp      0x14022e279
0022E277 xor      ebx, ebx
0022E279 lea      rcx, [rbx + 0x140]
0022E280 mov      word ptr [rbx + 0x214], r14w
0022E288 lea      r8, [rip + 0x36e721]
0022E28F lea      rdx, [rbp - 0x20]
0022E293 call     0x1403ff960
0022E298 lea      rcx, [rbx + 0x14c]
0022E29F lea      r8, [rip + 0x36e70a]
0022E2A6 lea      rdx, [rbp - 0x18]
0022E2AA call     0x1403ff960
0022E2AF movzx    eax, word ptr [rbx + 0x64]
0022E2B3 add      ax, ax
0022E2B6 mov      byte ptr [rbx + 0x158], r14b
0022E2BD mov      word ptr [rbx + 0x64], ax
0022E2C1 mov      dword ptr [rbx + 0x3b8], edi
0022E2C7 mov      dword ptr [rbx + 0x3bc], 0xa
0022E2D1 jmp      0x14022e8ec
0022E2D6 mov      ecx, 0x3c8
0022E2DB call     0x1404f7a88
0022E2E0 mov      rbx, rax
0022E2E3 test     rax, rax
0022E2E6 je       0x14022e3b2
0022E2EC lea      rdx, [rip + 0x36e6cd]
0022E2F3 lea      rcx, [rbp]
0022E2F7 call     0x1403ff7c0
0022E2FC mov      rcx, rbx
0022E2FF mov      rdx, qword ptr [rax]
0022E302 call     0x140227600
0022E307 mov      rcx, qword ptr [rbx + 0x1b8]
0022E30E lea      rax, [rip + 0x36d08b]
0022E315 xor      edx, edx
0022E317 mov      qword ptr [rbx], rax
0022E31A call     0x140411610
0022E31F mov      eax, 5
0022E324 mov      qword ptr [rbx + 0x1f8], rdi
0022E32B lea      rcx, [rbx + 0x140]
0022E332 mov      word ptr [rbx + 0x214], ax
0022E339 lea      r8, [rip + 0x3bd46d]
0022E340 mov      dword ptr [rbx + 0x210], edi
0022E346 lea      rdx, [rbp - 8]
0022E34A call     0x1403ff960
0022E34F mov      rcx, qword ptr [rbx + 0x1b8]
0022E356 lea      r9, [rbp - 0x20]
0022E35A xor      r8d, r8d
0022E35D xor      edx, edx
0022E35F call     0x1404119e0
0022E364 movsx    ecx, word ptr [rbp - 0x1c]
0022E368 mov      eax, 0x55555556
0022E36D add      ecx, ecx
0022E36F mov      dword ptr [rbx + 0x70], 0xffffffff
0022E376 imul     ecx
0022E378 lea      rcx, [rbx + 0x178]
0022E37F mov      eax, edx
0022E381 shr      eax, 0x1f
0022E384 add      edx, eax
0022E386 mov      word ptr [rbx + 0x64], dx
0022E38A lea      rdx, [rip + 0x3bd41c]
0022E391 call     0x1403fd810
0022E396 mov      dword ptr [rbx + 0x180], 0xffffffff
0022E3A0 mov      word ptr [rbx + 0x3b8], 0x1e
0022E3A9 mov      byte ptr [rbx + 0x3c0], r14b
0022E3B0 jmp      0x14022e3b4
0022E3B2 xor      ebx, ebx
0022E3B4 mov      byte ptr [rbx + 0x158], r14b
0022E3BB lea      r8, [rip + 0x36e496]
0022E3C2 lea      rdx, [rbp - 8]
0022E3C6 jmp      0x14022c31b
0022E3CB mov      ecx, 0x328
0022E3D0 call     0x1404f7a88
0022E3D5 mov      rbx, rax
0022E3D8 test     rax, rax
0022E3DB je       0x14022e42e
0022E3DD lea      rdx, [rip + 0x3bd3c9]
0022E3E4 lea      rcx, [rbp - 0x28]
0022E3E8 call     0x1403fd6b0
0022E3ED lea      rdx, [rip + 0x36ae4c]
0022E3F4 lea      rcx, [rbp - 0x30]
0022E3F8 call     0x1403fd6b0
0022E3FD movzx    ecx, byte ptr [rip + 0x370350]
0022E404 lea      r8, [rbp - 0x28]
0022E408 add      cx, cx
0022E40B lea      rdx, [rbp - 0x30]
0022E40F mov      word ptr [rsp + 0x28], cx
0022E414 mov      r9b, 0xff
0022E417 mov      rcx, rbx
0022E41A mov      dword ptr [rsp + 0x20], r14d
0022E41F call     0x140227cd0
0022E424 mov      rbx, rax
0022E427 mov      edi, 0x1800
0022E42C jmp      0x14022e430
0022E42E xor      ebx, ebx
0022E430 bt       edi, 0xc
0022E434 jae      0x14022e443
0022E436 btr      edi, 0xc
0022E43A lea      rcx, [rbp - 0x30]
0022E43E call     0x1403fd740
0022E443 bt       edi, 0xb
0022E447 jae      0x14022e452
0022E449 lea      rcx, [rbp - 0x28]
0022E44D call     0x1403fd740
0022E452 lea      rcx, [rbx + 0x1c0]
0022E459 mov      edx, 0xff
0022E45E call     0x140412690
0022E463 lea      r8, [rip + 0x36e566]
0022E46A jmp      0x14022e8c5
0022E46F lea      rdx, [rip + 0x36e562]
0022E476 lea      rcx, [rsp + 0x60]
0022E47B call     0x1403fd810
0022E480 lea      rdx, [rip + 0x3bd326]
0022E487 lea      rcx, [rsp + 0x50]
0022E48C call     0x1403fd810
0022E491 lea      rdx, [rip + 0x3bd315]
0022E498 lea      rcx, [rsp + 0x58]
0022E49D call     0x1403fd810
0022E4A2 mov      ecx, 0x418
0022E4A7 call     0x1404f7a88
0022E4AC test     rax, rax
0022E4AF je       0x14022e8be
0022E4B5 mov      byte ptr [rsp + 0x28], bl
0022E4B9 lea      r9, [rsp + 0x50]
0022E4BE lea      r8, [rsp + 0x58]
0022E4C3 mov      dword ptr [rsp + 0x20], 8
0022E4CB lea      rdx, [rsp + 0x60]
0022E4D0 mov      rcx, rax
0022E4D3 call     0x140227df0
0022E4D8 mov      rbx, rax
0022E4DB jmp      0x14022e8be
0022E4E0 lea      rdx, [rip + 0x36e4f1]
0022E4E7 lea      rcx, [rsp + 0x60]
0022E4EC call     0x1403fd810
0022E4F1 lea      rdx, [rip + 0x36e4e8]
0022E4F8 lea      rcx, [rsp + 0x50]
0022E4FD call     0x1403fd810
0022E502 lea      rdx, [rip + 0x3bd2a4]
0022E509 lea      rcx, [rsp + 0x58]
0022E50E call     0x1403fd810
0022E513 mov      ecx, 0x418
0022E518 call     0x1404f7a88
0022E51D test     rax, rax
0022E520 je       0x14022e8be
0022E526 mov      byte ptr [rsp + 0x28], bl
0022E52A lea      r9, [rsp + 0x50]
0022E52F lea      r8, [rsp + 0x58]
0022E534 mov      dword ptr [rsp + 0x20], 8
0022E53C lea      rdx, [rsp + 0x60]
0022E541 mov      rcx, rax
0022E544 call     0x140227df0
0022E549 mov      rbx, rax
0022E54C jmp      0x14022e8be
0022E551 lea      rdx, [rip + 0x36e480]
0022E558 lea      rcx, [rsp + 0x60]
0022E55D call     0x1403fd810
0022E562 lea      rdx, [rip + 0x36e47f]
0022E569 lea      rcx, [rsp + 0x50]
0022E56E call     0x1403fd810
0022E573 lea      rdx, [rip + 0x3bd233]
0022E57A lea      rcx, [rsp + 0x58]
0022E57F call     0x1403fd810
0022E584 mov      ecx, 0x418
0022E589 call     0x1404f7a88
0022E58E test     rax, rax
0022E591 je       0x14022e8be
0022E597 mov      byte ptr [rsp + 0x28], bl
0022E59B lea      r9, [rsp + 0x50]
0022E5A0 lea      r8, [rsp + 0x58]
0022E5A5 mov      dword ptr [rsp + 0x20], 8
0022E5AD lea      rdx, [rsp + 0x60]
0022E5B2 mov      rcx, rax
0022E5B5 call     0x140227df0
0022E5BA mov      rbx, rax
0022E5BD jmp      0x14022e8be
0022E5C2 lea      rdx, [rip + 0x36e40f]
0022E5C9 lea      rcx, [rsp + 0x60]
0022E5CE call     0x1403fd810
0022E5D3 lea      rdx, [rip + 0x36e416]
0022E5DA lea      rcx, [rsp + 0x50]
0022E5DF call     0x1403fd810
0022E5E4 lea      rdx, [rip + 0x3bd1c2]
0022E5EB lea      rcx, [rsp + 0x58]
0022E5F0 call     0x1403fd810
0022E5F5 mov      ecx, 0x418
0022E5FA call     0x1404f7a88
0022E5FF test     rax, rax
0022E602 je       0x14022e8be
0022E608 mov      byte ptr [rsp + 0x28], bl
0022E60C lea      r9, [rsp + 0x50]
0022E611 lea      r8, [rsp + 0x58]
0022E616 mov      dword ptr [rsp + 0x20], 8
0022E61E lea      rdx, [rsp + 0x60]
0022E623 mov      rcx, rax
0022E626 call     0x140227df0
0022E62B mov      rbx, rax
0022E62E jmp      0x14022e8be
0022E633 lea      rdx, [rip + 0x36e39e]
0022E63A lea      rcx, [rsp + 0x60]
0022E63F call     0x1403fd810
0022E644 lea      rdx, [rip + 0x36e3ad]
0022E64B lea      rcx, [rsp + 0x50]
0022E650 call     0x1403fd810
0022E655 lea      rdx, [rip + 0x3bd151]
0022E65C lea      rcx, [rsp + 0x58]
0022E661 call     0x1403fd810
0022E666 mov      ecx, 0x418
0022E66B call     0x1404f7a88
0022E670 test     rax, rax
0022E673 je       0x14022e8be
0022E679 mov      byte ptr [rsp + 0x28], bl
0022E67D lea      r9, [rsp + 0x50]
0022E682 lea      r8, [rsp + 0x58]
0022E687 mov      dword ptr [rsp + 0x20], 8
0022E68F lea      rdx, [rsp + 0x60]
0022E694 mov      rcx, rax
0022E697 call     0x140227df0
0022E69C mov      rbx, rax
0022E69F jmp      0x14022e8be
0022E6A4 lea      rdx, [rip + 0x36e32d]
0022E6AB lea      rcx, [rsp + 0x60]
0022E6B0 call     0x1403fd810
0022E6B5 lea      rdx, [rip + 0x36e344]
0022E6BC lea      rcx, [rsp + 0x50]
0022E6C1 call     0x1403fd810
0022E6C6 lea      rdx, [rip + 0x3bd0e0]
0022E6CD lea      rcx, [rsp + 0x58]
0022E6D2 call     0x1403fd810
0022E6D7 mov      ecx, 0x418
0022E6DC call     0x1404f7a88
0022E6E1 test     rax, rax
0022E6E4 je       0x14022e8be
0022E6EA mov      byte ptr [rsp + 0x28], bl
0022E6EE lea      r9, [rsp + 0x50]
0022E6F3 lea      r8, [rsp + 0x58]
0022E6F8 mov      dword ptr [rsp + 0x20], 8
0022E700 lea      rdx, [rsp + 0x60]
0022E705 mov      rcx, rax
0022E708 call     0x140227df0
0022E70D mov      rbx, rax
0022E710 jmp      0x14022e8be
0022E715 lea      rdx, [rip + 0x36e2bc]
0022E71C lea      rcx, [rsp + 0x60]
0022E721 call     0x1403fd810
0022E726 lea      rdx, [rip + 0x36e2db]
0022E72D lea      rcx, [rsp + 0x50]
0022E732 call     0x1403fd810
0022E737 lea      rdx, [rip + 0x3bd06f]
0022E73E lea      rcx, [rsp + 0x58]
0022E743 call     0x1403fd810
0022E748 mov      ecx, 0x418
0022E74D call     0x1404f7a88
0022E752 test     rax, rax
0022E755 je       0x14022e8be
0022E75B mov      byte ptr [rsp + 0x28], bl
0022E75F lea      r9, [rsp + 0x50]
0022E764 lea      r8, [rsp + 0x58]
0022E769 mov      dword ptr [rsp + 0x20], 8
0022E771 lea      rdx, [rsp + 0x60]
0022E776 mov      rcx, rax
0022E779 call     0x140227df0
0022E77E mov      rbx, rax
0022E781 jmp      0x14022e8be
0022E786 lea      rdx, [rip + 0x36aacb]
0022E78D lea      rcx, [rsp + 0x60]
0022E792 call     0x1403fd810
0022E797 lea      rdx, [rip + 0x3bd00f]
0022E79E lea      rcx, [rsp + 0x50]
0022E7A3 call     0x1403fd810
0022E7A8 lea      rdx, [rip + 0x36aab9]
0022E7AF jmp      0x14022e498
0022E7B4 mov      ecx, 0x328
0022E7B9 call     0x1404f7a88
0022E7BE mov      rbx, rax
0022E7C1 test     rax, rax
0022E7C4 je       0x14022e817
0022E7C6 lea      rdx, [rip + 0x36e243]
0022E7CD lea      rcx, [rbp - 0x10]
0022E7D1 call     0x1403fd6b0
0022E7D6 lea      rdx, [rip + 0x36e23b]
0022E7DD lea      rcx, [rbp + 8]
0022E7E1 call     0x1403fd6b0
0022E7E6 movzx    ecx, byte ptr [rip + 0x36ff67]
0022E7ED lea      r8, [rbp - 0x10]
0022E7F1 add      cx, cx
0022E7F4 lea      rdx, [rbp + 8]
0022E7F8 mov      word ptr [rsp + 0x28], cx
0022E7FD mov      r9b, 0xff
0022E800 mov      rcx, rbx
0022E803 mov      dword ptr [rsp + 0x20], r14d
0022E808 call     0x140227cd0
0022E80D mov      rbx, rax
0022E810 mov      edi, 0x6000
0022E815 jmp      0x14022e819
0022E817 xor      ebx, ebx
0022E819 bt       edi, 0xe
0022E81D jae      0x14022e82c
0022E81F btr      edi, 0xe
0022E823 lea      rcx, [rbp + 8]
0022E827 call     0x1403fd740
0022E82C bt       edi, 0xd
0022E830 jae      0x14022e8be
0022E836 lea      rcx, [rbp - 0x10]
0022E83A jmp      0x14022e8b9
0022E83C mov      ecx, 0x328
0022E841 call     0x1404f7a88
0022E846 mov      rbx, rax
0022E849 test     rax, rax
0022E84C je       0x14022e89a
0022E84E lea      rdx, [rip + 0x3bcf58]
0022E855 lea      rcx, [rbp - 0x20]
0022E859 call     0x1403fd6b0
0022E85E lea      rdx, [rip + 0x36e1c3]
0022E865 lea      rcx, [rbp - 0x18]
0022E869 call     0x1403fd6b0
0022E86E mov      eax, 0x1d
0022E873 lea      r8, [rbp - 0x20]
0022E877 mov      word ptr [rsp + 0x28], ax
0022E87C lea      rdx, [rbp - 0x18]
0022E880 mov      r9b, 0xff
0022E883 mov      dword ptr [rsp + 0x20], r14d
0022E888 mov      rcx, rbx
0022E88B call     0x140227cd0
0022E890 mov      rbx, rax
0022E893 mov      edi, 0x18000
0022E898 jmp      0x14022e89c
0022E89A xor      ebx, ebx
0022E89C bt       edi, 0x10
0022E8A0 jae      0x14022e8af
0022E8A2 btr      edi, 0x10
0022E8A6 lea      rcx, [rbp - 0x18]
0022E8AA call     0x1403fd740
0022E8AF bt       edi, 0xf
0022E8B3 jae      0x14022e8be
0022E8B5 lea      rcx, [rbp - 0x20]
0022E8B9 call     0x1403fd740
0022E8BE lea      r8, [rip + 0x3bcee8]
0022E8C5 lea      rdx, [rbp]
0022E8C9 lea      rcx, [rbx + 0x140]
0022E8D0 call     0x1403ff960
0022E8D5 lea      rdx, [rbp - 8]
0022E8D9 lea      r8, [rip + 0x3bcecd]
0022E8E0 lea      rcx, [rbx + 0x14c]
0022E8E7 call     0x1403ff960
0022E8EC test     rbx, rbx
0022E8EF jne      0x14022ed7f
0022E8F5 mov      rax, qword ptr [rip + 0x438c4c]
0022E8FC mov      edx, r12d
0022E8FF mov      rcx, qword ptr [rax + 0x1090]
0022E906 add      rcx, 0x1810
0022E90D call     0x14011b480
0022E912 mov      rdi, rax
0022E915 test     rax, rax
0022E918 je       0x14022e94d
0022E91A mov      ecx, 0x3b8
0022E91F call     0x1404f7a88
0022E924 test     rax, rax
0022E927 je       0x14022e936
0022E929 mov      rcx, rax
0022E92C call     0x140227a40
0022E931 mov      rbx, rax
0022E934 jmp      0x14022e938
0022E936 xor      ebx, ebx
0022E938 lea      rdx, [rdi + 8]
0022E93C lea      rcx, [rbx + 0x178]
0022E943 call     0x1403fd770
0022E948 jmp      0x14022ed7f
0022E94D mov      rax, qword ptr [rip + 0x438bf4]
0022E954 mov      edx, r12d
0022E957 mov      rcx, qword ptr [rax + 0x1090]
0022E95E add      rcx, 0x1880
0022E965 call     0x14011b480
0022E96A test     rax, rax
0022E96D je       0x14022ed47
0022E973 lea      r12, [rax + 8]
0022E977 mov      rdx, r12
0022E97A lea      rcx, [rbp]
0022E97E call     0x1403ff710
0022E983 lea      rcx, [rbp + 0x10]
0022E987 mov      rdx, qword ptr [rax]
0022E98A call     0x140227930
0022E98F mov      rcx, qword ptr [rbp + 0x10]
0022E993 test     rcx, rcx
0022E996 je       0x14022ed47
0022E99C call     0x1403f6d50
0022E9A1 test     rax, rax
0022E9A4 je       0x14022ed1e
0022E9AA mov      rcx, qword ptr [rbp + 0x10]
0022E9AE mov      eax, dword ptr [rcx + 0x48]
0022E9B1 cmp      eax, 8
0022E9B4 jbe      0x14022ed1e
0022E9BA add      eax, -8
0022E9BD je       0x14022ed1e
0022E9C3 call     0x1403f6d50
0022E9C8 mov      r15, rax
0022E9CB add      r15, 8
0022E9CF je       0x14022ed1e
0022E9D5 test     dword ptr [r15 + 0x24], 0x100000
0022E9DD je       0x14022ea9b
0022E9E3 mov      rax, qword ptr [rsi]
0022E9E6 mov      rcx, rsi
0022E9E9 call     qword ptr [rax + 8]
0022E9EC cmp      al, byte ptr [rip + 0x36ad2d]
0022E9F2 jne      0x14022ea9b
0022E9F8 movzx    eax, byte ptr [rsi + 0x586]
0022E9FF lea      rcx, [rip - 0x22ea06]
0022EA06 mov      r13d, dword ptr [rcx + rax*4 + 0x5c0710]
0022EA0E mov      ecx, 0x30
0022EA13 call     0x1404f7a88
0022EA18 mov      r14, rax
0022EA1B test     rax, rax
0022EA1E je       0x14022ea7a
0022EA20 mov      edi, dword ptr [rsi + 0x48]
0022EA23 mov      rcx, qword ptr [rsp + 0x68]
0022EA28 mov      esi, dword ptr [r15 + 0x28]
0022EA2C call     0x1403579b0
0022EA31 lea      rcx, [rip + 0x360740]
0022EA38 mov      dword ptr [r14 + 0x14], esi
0022EA3C mov      rsi, qword ptr [rsp + 0x68]
0022EA41 mov      qword ptr [r14], rcx
0022EA44 mov      dword ptr [r14 + 0xc], edi
0022EA48 mov      dword ptr [r14 + 8], edi
0022EA4C mov      dword ptr [r14 + 0x10], eax
0022EA50 mov      dword ptr [r14 + 0x18], r13d
0022EA54 mov      dword ptr [r14 + 0x1c], 0xbed7d7
0022EA5C mov      dword ptr [r14 + 0x20], 0xffffffff
0022EA64 mov      byte ptr [r14 + 0x24], 0
0022EA69 mov      dword ptr [r14 + 0x28], 0
0022EA71 mov      word ptr [r14 + 0x2c], 0x100
0022EA78 jmp      0x14022ea7d
0022EA7A xor      r14d, r14d
0022EA7D mov      rcx, qword ptr [rip + 0x438ac4]
0022EA84 xor      r8d, r8d
0022EA87 add      rcx, 0x1768
0022EA8E mov      rdx, r14
0022EA91 call     0x140204ec0
0022EA96 movzx    r13d, word ptr [rbp - 0x80]
0022EA9B movzx    ecx, word ptr [r15]
0022EA9F sub      ecx, 1
0022EAA2 je       0x14022ecf1
0022EAA8 sub      ecx, 1
0022EAAB je       0x14022eafd
0022EAAD cmp      ecx, 1
0022EAB0 jne      0x14022ed1e
0022EAB6 mov      ecx, 0x4a8
0022EABB call     0x1404f7a88
0022EAC0 mov      rbx, rax
0022EAC3 test     rax, rax
0022EAC6 je       0x14022eaf3
0022EAC8 mov      rdx, r12
0022EACB lea      rcx, [rsp + 0x68]
0022EAD0 call     0x1403ff710
0022EAD5 mov      r8, rsi
0022EAD8 mov      rdx, r15
0022EADB mov      rcx, rbx
0022EADE mov      r9, qword ptr [rax]
0022EAE1 call     0x140226b80
0022EAE6 mov      rbx, rax
0022EAE9 mov      eax, 3
0022EAEE jmp      0x14022ed17
0022EAF3 xor      ebx, ebx
0022EAF5 lea      eax, [rbx + 3]
0022EAF8 jmp      0x14022ed17
0022EAFD mov      eax, dword ptr [r15 + 0x24]
0022EB01 test     al, al
0022EB03 jns      0x14022eb8b
0022EB09 mov      ecx, 0x3b8
0022EB0E call     0x1404f7a88
0022EB13 mov      rbx, rax
0022EB16 test     rax, rax
0022EB19 je       0x14022ece8
0022EB1F mov      rdx, r15
0022EB22 mov      rcx, rax
0022EB25 call     0x1402270e0
0022EB2A test     dword ptr [rbx + 0x188], 0x20000
0022EB34 lea      rax, [rip + 0x36dbdd]
0022EB3B mov      qword ptr [rbx], rax
0022EB3E je       0x14022eb61
0022EB40 movzx    ecx, byte ptr [rip + 0x36fc0d]
0022EB47 movzx    eax, cx
0022EB4A add      ax, ax
0022EB4D add      cx, ax
0022EB50 mov      eax, 2
0022EB55 mov      word ptr [rbx + 0x184], cx
0022EB5C jmp      0x14022ed17
0022EB61 mov      rcx, qword ptr [rbx + 0x1b8]
0022EB68 movzx    edx, word ptr [rcx + 0x11a]
0022EB6F call     0x140411cc0
0022EB74 movzx    ecx, al
0022EB77 mov      eax, 2
0022EB7C dec      cx
0022EB7F mov      word ptr [rbx + 0x184], cx
0022EB86 jmp      0x14022ed17
0022EB8B bt       eax, 0xa
0022EB8F jae      0x14022ec4c
0022EB95 mov      ecx, 0x3f0
0022EB9A call     0x1404f7a88
0022EB9F mov      rbx, rax
0022EBA2 test     rax, rax
0022EBA5 je       0x14022ece8
0022EBAB mov      rdx, r15
0022EBAE mov      rcx, rax
0022EBB1 call     0x1402270e0
0022EBB6 lea      rax, [rip + 0x36d2fb]
0022EBBD mov      edx, 0xa
0022EBC2 lea      rcx, [rbx + 0x3b8]
0022EBC9 mov      qword ptr [rbx], rax
0022EBCC call     0x1404073a0
0022EBD1 cmp      qword ptr [rsp + 0x68], 0
0022EBD7 lea      rax, [rip + 0x35e17a]
0022EBDE mov      qword ptr [rbx + 0x3b8], rax
0022EBE5 jne      0x14022ebfa
0022EBE7 mov      eax, 1
0022EBEC mov      word ptr [rbx + 0x4c], ax
0022EBF0 mov      eax, 2
0022EBF5 jmp      0x14022ed17
0022EBFA test     r13w, r13w
0022EBFE je       0x14022ecea
0022EC04 mov      r14d, 0xffff
0022EC0A nop      word ptr [rax + rax]
0022EC10 xor      edx, edx
0022EC12 movzx    ecx, r13w
0022EC16 call     0x14022bf00
0022EC1B mov      rdx, rax
0022EC1E lea      rcx, [rbx + 0x3b8]
0022EC25 mov      rdi, rax
0022EC28 add      r13w, r14w
0022EC2C call     0x1404075c0
0022EC31 cmp      word ptr [rdi + 0x4c], 0
0022EC36 je       0x14022ecea
0022EC3C test     r13w, r13w
0022EC40 jne      0x14022ec10
0022EC42 mov      eax, 2
0022EC47 jmp      0x14022ed17
0022EC4C bt       eax, 0xe
0022EC50 jae      0x14022ecc4
0022EC52 mov      ecx, 0x4d8
0022EC57 call     0x1404f7a88
0022EC5C mov      rbx, rax
0022EC5F test     rax, rax
0022EC62 je       0x14022ece8
0022EC68 mov      rdx, r15
0022EC6B mov      rcx, rax
0022EC6E call     0x1402270e0
0022EC73 lea      rax, [rip + 0x36c85e]
0022EC7A mov      dword ptr [rbx + 0x4cc], 0x3c
0022EC84 mov      qword ptr [rbx], rax
0022EC87 xor      edi, edi
0022EC89 mov      eax, 3
0022EC8E mov      dword ptr [rbx + 0x4c4], edi
0022EC94 mov      dword ptr [rbx + 0x4c8], eax
0022EC9A call     0x140232aa0
0022EC9F mov      eax, 0x6e
0022ECA4 mov      dword ptr [rbx + 0x70], 0xffffffff
0022ECAB mov      word ptr [rbx + 0x184], ax
0022ECB2 lea      eax, [rdi + 2]
0022ECB5 mov      byte ptr [rbx + 0x3b8], dil
0022ECBC mov      dword ptr [rbx + 0x4c0], edi
0022ECC2 jmp      0x14022ed17
0022ECC4 mov      ecx, 0x3b8
0022ECC9 call     0x1404f7a88
0022ECCE test     rax, rax
0022ECD1 je       0x14022ece8
0022ECD3 mov      rdx, r15
0022ECD6 mov      rcx, rax
0022ECD9 call     0x1402270e0
0022ECDE mov      rbx, rax
0022ECE1 mov      eax, 2
0022ECE6 jmp      0x14022ed17
0022ECE8 xor      ebx, ebx
0022ECEA mov      eax, 2
0022ECEF jmp      0x14022ed17
0022ECF1 mov      ecx, 0x1b8
0022ECF6 call     0x1404f7a88
0022ECFB test     rax, rax
0022ECFE je       0x14022ed10
0022ED00 mov      rdx, r15
0022ED03 mov      rcx, rax
0022ED06 call     0x140226630
0022ED0B mov      rbx, rax
0022ED0E jmp      0x14022ed12
0022ED10 xor      ebx, ebx
0022ED12 mov      eax, 1
0022ED17 mov      word ptr [rbx + 0xca], ax
0022ED1E cmp      qword ptr [rbp + 0x10], 0
0022ED23 je       0x14022ed42
0022ED25 lea      rdx, [rip + 0x3bca81]
0022ED2C lea      rcx, [rbp + 0x18]
0022ED30 call     0x1403ffb60
0022ED35 test     eax, eax
0022ED37 je       0x14022ed42
0022ED39 mov      rcx, qword ptr [rbp + 0x10]
0022ED3D call     0x14001e1e0
0022ED42 test     rbx, rbx
0022ED45 jne      0x14022ed7f
0022ED47 mov      ecx, 0x1b8
0022ED4C call     0x1404f7a88
0022ED51 mov      rbx, rax
0022ED54 test     rax, rax
0022ED57 je       0x14022ed7d
0022ED59 xor      edx, edx
0022ED5B mov      r8d, 0x1b8
0022ED61 mov      rcx, rax
0022ED64 call     0x1404fab70
0022ED69 mov      rcx, rbx
0022ED6C call     0x140226910
0022ED71 lea      rax, [rip + 0x36d278]
0022ED78 mov      qword ptr [rbx], rax
0022ED7B jmp      0x14022ed7f
0022ED7D xor      ebx, ebx
0022ED7F mov      eax, dword ptr [rbp - 0x7c]
0022ED82 lea      rcx, [rbp + 0x28]
0022ED86 dec      ax
0022ED89 mov      word ptr [rbx + 0x60], ax
0022ED8D call     0x1403fd740
0022ED92 lea      rcx, [rsp + 0x50]
0022ED97 call     0x1403fd740
0022ED9C lea      rcx, [rsp + 0x58]
0022EDA1 call     0x1403fd740
0022EDA6 lea      rcx, [rsp + 0x60]
0022EDAB call     0x1403fd740
0022EDB0 mov      rax, rbx
0022EDB3 mov      rcx, qword ptr [rbp + 0x58]
0022EDB7 xor      rcx, rsp
0022EDBA call     0x1404f77a0
0022EDBF mov      rbx, qword ptr [rsp + 0x1b0]
0022EDC7 add      rsp, 0x160
0022EDCE pop      r15
0022EDD0 pop      r14
0022EDD2 pop      r13
0022EDD4 pop      r12
0022EDD6 pop      rdi
0022EDD7 pop      rsi
0022EDD8 pop      rbp
0022EDD9 ret      
0022EDDA nop      
0022EDDC mov      esp, 0xfc0022bf
0022EDE1 mov      edi, 0xc1560022
0022EDE6 and      al, byte ptr [rax]
0022EDE8 xchg     edi, eax
0022EDE9 shl      dword ptr [rdx], 0
0022EDEC out      0xc1, al
0022EDEE and      al, byte ptr [rax]
0022EDF0 mov      ebp, 0x300022c3
0022EDF5 ret      
0022EDF6 and      al, byte ptr [rax]
