22c1e6: lea rdx, [rip + 0x37067b] ; b'Spsmkjet'
22c1ed: lea rcx, [rsp + 0x60]
22c1f2: call 0x3fd810
22c1f7: lea rdx, [rip + 0x3bf5af] ; b''
22c1fe: lea rcx, [rsp + 0x50]
22c203: call 0x3fd810
22c208: lea rdx, [rip + 0x3bf59e] ; b''
22c20f: lea rcx, [rsp + 0x58]
22c214: call 0x3fd810
22c219: mov ecx, 0x418
22c21e: call 0x4f7a88
22c223: mov rbx, rax
22c226: test rax, rax
22c229: je 0x22c30e
22c22f: mov rcx, rax
22c232: call 0x226910
22c237: lea rax, [rip + 0x370142] ; b'0\x81"@\x01'
22c23e: lea rcx, [rbx + 0x1b8]
22c245: mov qword ptr [rbx], rax
22c248: call 0x410f70
22c24d: lea rcx, [rbx + 0x2f0]
22c254: call 0x410d80
22c259: lea rdx, [rsp + 0x60]
22c25e: lea rcx, [rbp - 0x20]
22c262: call 0x3ff710
22c267: lea rcx, [rbx + 0x2c0]
22c26e: mov r9d, r14d
22c271: mov r8d, r14d
22c274: lea rdx, [rbp - 0x20]
22c278: call 0x14d080
22c27d: mov rax, qword ptr [rsp + 0x50]
22c282: cmp dword ptr [rax - 8], edi
22c285: je 0x22c2b1
22c287: lea rdx, [rsp + 0x50]
22c28c: lea rcx, [rbp - 0x18]
22c290: call 0x3ff710
22c295: mov r9d, r14d
22c298: lea rdx, [rbp - 0x18]
22c29c: mov r8d, r14d
22c29f: lea rcx, [rbx + 0x2f0]
22c2a6: call 0x18aa40
22c2ab: movzx eax, r14b
22c2af: jmp 0x22c2b3
22c2b1: xor al, al
22c2b3: xor edx, edx
22c2b5: mov byte ptr [rbx + 0x414], al
22c2bb: lea rcx, [rbx + 0x1b8]
22c2c2: call 0x412380
22c2c7: xor edx, edx
22c2c9: lea rcx, [rbx + 0x1b8]
22c2d0: call 0x411610
22c2d5: lea rcx, [rbx + 0x140]
22c2dc: lea r8, [rsp + 0x58]
22c2e1: lea rdx, [rbp - 0x10]
22c2e5: call 0x3ff890
22c2ea: lea rax, [rip + 0x3701bf] ; b'0\x81"@\x01'
22c2f1: mov dword ptr [rbx + 0x410], 8
22c2fb: mov qword ptr [rbx], rax
22c2fe: mov byte ptr [rbx + 0x415], dil
22c305: mov byte ptr [rbx + 0x158], r14b
22c30c: jmp 0x22c310
22c30e: xor ebx, ebx
22c310: lea r8, [rip + 0x3bf496] ; b''
22c317: lea rdx, [rbp - 0x20]
22c31b: lea rcx, [rbx + 0x140]
22c322: call 0x3ff960
22c327: lea rdx, [rbp - 0x20]
22c32b: .byte 0xe9
