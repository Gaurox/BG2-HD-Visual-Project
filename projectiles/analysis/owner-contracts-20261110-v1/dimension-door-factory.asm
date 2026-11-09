22c9e4: mov ecx, 0x428
22c9e9: call 0x4f7a88
22c9ee: mov rbx, rax
22c9f1: test rax, rax
22c9f4: je 0x22cb35
22c9fa: lea rdx, [rip + 0x3bedac] ; b''
22ca01: lea rcx, [rsp + 0x78]
22ca06: call 0x3fd6b0
22ca0b: lea rdx, [rip + 0x3bed9b] ; b''
22ca12: lea rcx, [rbp - 0x58]
22ca16: call 0x3fd6b0
22ca1b: lea rdx, [rip + 0x36fe66] ; b'SPDimDr'
22ca22: lea rcx, [rbp - 0x78]
22ca26: call 0x3fd6b0
22ca2b: mov rcx, rbx
22ca2e: call 0x226910
22ca33: lea rax, [rip + 0x36f6e6] ; b'P\x84"@\x01'
22ca3a: lea rcx, [rbx + 0x1b8]
22ca41: mov qword ptr [rbx], rax
22ca44: call 0x410f70
22ca49: lea rcx, [rbx + 0x2f0]
22ca50: call 0x410d80
22ca55: mov rax, qword ptr [rip + 0x4300b4] ; b'$\xcbe@\x01'
22ca5c: lea rcx, [rbx + 0x418]
22ca63: lea rdx, [rbp - 0x78]
22ca67: mov qword ptr [rcx], rax
22ca6a: call 0x3fd770
22ca6f: lea r8, [rip + 0x3de1c6] ; b'2'
22ca76: lea rdx, [rbp - 0x78]
22ca7a: lea rcx, [rbp - 0x18]
22ca7e: call 0x3fd8e0
22ca83: mov rdx, rax
22ca86: lea rcx, [rbp - 0x20]
22ca8a: call 0x3ff710
22ca8f: lea rcx, [rbx + 0x2c0]
22ca96: mov r9d, r14d
22ca99: mov r8d, r14d
22ca9c: lea rdx, [rbp - 0x20]
22caa0: call 0x14d080
22caa5: lea rcx, [rbp - 0x18]
22caa9: call 0x3fd740
22caae: mov rax, qword ptr [rsp + 0x78]
22cab3: cmp dword ptr [rax - 8], edi
22cab6: je 0x22cae2
22cab8: lea rdx, [rsp + 0x78]
22cabd: lea rcx, [rbp - 0x10]
22cac1: call 0x3ff710
22cac6: mov r9d, r14d
22cac9: lea rdx, [rbp - 0x10]
22cacd: mov r8d, r14d
22cad0: lea rcx, [rbx + 0x2f0]
22cad7: call 0x18aa40
22cadc: movzx eax, r14b
22cae0: jmp 0x22cae4
22cae2: xor al, al
22cae4: xor edx, edx
22cae6: mov byte ptr [rbx + 0x414], al
22caec: lea rcx, [rbx + 0x1b8]
22caf3: call 0x412380
22caf8: xor edx, edx
22cafa: lea rcx, [rbx + 0x1b8]
22cb01: call 0x411610
22cb06: lea rcx, [rbx + 0x140]
22cb0d: lea r8, [rbp - 0x58]
22cb11: lea rdx, [rbp + 8]
22cb15: call 0x3ff890
22cb1a: mov dword ptr [rbx + 0x410], edi
22cb20: mov byte ptr [rbx + 0x415], dil
22cb27: mov byte ptr [rbx + 0x420], dil
22cb2e: mov edi, 0x70
22cb33: jmp 0x22cb37
22cb35: xor ebx, ebx
22cb37: test dil, 0x40
22cb3b: je 0x22cb49
22cb3d: and edi, 0xffffffbf
22cb40: lea rcx, [rbp - 0x78]
22cb44: call 0x3fd740
22cb49: test dil, 0x20
22cb4d: je 0x22cb5b
22cb4f: and edi, 0xffffffdf
22cb52: lea rcx, [rbp - 0x58]
22cb56: call 0x3fd740
22cb5b: test dil, 0x10
22cb5f: .byte 0x74
