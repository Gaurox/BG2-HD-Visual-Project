22c8c7: mov ecx, 0x3c0
22c8cc: call 0x4f7a88
22c8d1: mov rbx, rax
22c8d4: test rax, rax
22c8d7: je 0x22c9cf
22c8dd: lea rdx, [rip + 0x370174] ; b'COLRSPRY'
22c8e4: lea rcx, [rbp - 0x20]
22c8e8: call 0x3ff800
22c8ed: mov rcx, rbx
22c8f0: mov rdx, qword ptr [rax]
22c8f3: call 0x227600
22c8f8: mov rcx, qword ptr [rbx + 0x1b8]
22c8ff: lea rax, [rip + 0x36ee5a] ; b'`\x82"@\x01'
22c906: xor edx, edx
22c908: mov qword ptr [rbx], rax
22c90b: call 0x412380
22c910: xor ecx, ecx
22c912: mov dword ptr [rsp + 0x70], 0x14
22c91a: mov qword ptr [rbx + 0x1f8], rcx
22c921: lea r8, [rip + 0x3bee85] ; b''
22c928: mov dword ptr [rbx + 0x200], ecx
22c92e: lea rdx, [rbp - 0x18]
22c932: mov dword ptr [rbx + 0x210], ecx
22c938: lea rcx, [rbx + 0x140]
22c93f: mov dword ptr [rsp + 0x74], 0xf
22c947: mov rax, qword ptr [rsp + 0x70]
22c94c: mov qword ptr [rbx + 0x204], rax
22c953: mov eax, 0x80
22c958: mov word ptr [rbx + 0x20c], ax
22c95f: mov eax, 5
22c964: mov word ptr [rbx + 0x214], ax
22c96b: call 0x3ff960
22c970: mov eax, 0x37
22c975: mov dword ptr [rbx + 0x70], 0xffffffff
22c97c: lea rcx, [rbx + 0x178]
22c983: mov word ptr [rbx + 0x3b8], ax
22c98a: lea rdx, [rip + 0x3bee1c] ; b''
22c991: call 0x3fd810
22c996: mov dword ptr [rsp + 0x70], 0x2d
22c99e: lea r8, [rip + 0x36fed7] ; b'TRA_05'
22c9a5: mov dword ptr [rsp + 0x74], 0x46
22c9ad: mov rax, qword ptr [rsp + 0x70]
22c9b2: mov qword ptr [rbx + 0x164], rax
22c9b9: mov dword ptr [rbx + 0x180], 0xffffffff
22c9c3: mov byte ptr [rbx + 0x158], r14b
22c9ca: jmp 0x22c317
22c9cf: xor ebx, ebx
22c9d1: lea r8, [rip + 0x36fea4] ; b'TRA_05'
22c9d8: mov byte ptr [rbx + 0x158], r14b
22c9df: jmp 0x22c317
