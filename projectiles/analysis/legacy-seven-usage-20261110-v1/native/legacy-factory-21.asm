22bffc: mov ecx, 0x3c0
22c001: call 0x4f7a88
22c006: mov rbx, rax
22c009: test rax, rax
22c00c: je 0x22c12d
22c012: lea rdx, [rip + 0x370a4f] ; b'SPBRNHND'
22c019: lea rcx, [rbp - 0x20]
22c01d: call 0x3ff800
22c022: mov rcx, rbx
22c025: mov rdx, qword ptr [rax]
22c028: call 0x227600
22c02d: mov rcx, qword ptr [rbx + 0x1b8]
22c034: lea rax, [rip + 0x36f85d] ; b'`\x82"@\x01'
22c03b: xor edx, edx
22c03d: mov qword ptr [rbx], rax
22c040: call 0x412380
22c045: mov rax, qword ptr [rip + 0x43b4fc] ; b''
22c04c: lea rcx, [rbx + 0x1c8]
22c053: xor edx, edx
22c055: mov r9, qword ptr [rax + 0x1090]
22c05c: add r9, 0x63d8
22c063: lea r8d, [rdx + 0x43]
22c067: call 0x4221c0
22c06c: mov rcx, qword ptr [rbx + 0x1b8]
22c073: lea rdx, [rbx + 0x1c8]
22c07a: call 0x412390
22c07f: xor ecx, ecx
22c081: mov dword ptr [rsp + 0x78], 0x14
22c089: mov qword ptr [rbx + 0x1f8], rcx
22c090: lea r8, [rip + 0x3bf716] ; b''
22c097: mov dword ptr [rbx + 0x200], ecx
22c09d: lea rdx, [rbp - 0x18]
22c0a1: mov dword ptr [rbx + 0x210], ecx
22c0a7: lea rcx, [rbx + 0x140]
22c0ae: mov dword ptr [rsp + 0x7c], 0xf
22c0b6: mov rax, qword ptr [rsp + 0x78]
22c0bb: mov qword ptr [rbx + 0x204], rax
22c0c2: mov eax, 0x80
22c0c7: mov word ptr [rbx + 0x20c], ax
22c0ce: mov eax, 5
22c0d3: mov word ptr [rbx + 0x214], ax
22c0da: call 0x3ff960
22c0df: mov eax, 0x1e
22c0e4: mov dword ptr [rbx + 0x70], 0xffffffff
22c0eb: lea rcx, [rbx + 0x178]
22c0f2: mov word ptr [rbx + 0x3b8], ax
22c0f9: lea rdx, [rip + 0x3bf6ad] ; b''
22c100: call 0x3fd810
22c105: mov dword ptr [rsp + 0x78], 0x17
22c10d: mov dword ptr [rsp + 0x7c], 0x32
22c115: mov rax, qword ptr [rsp + 0x78]
22c11a: mov qword ptr [rbx + 0x164], rax
22c121: mov dword ptr [rbx + 0x180], 0xffffffff
22c12b: jmp 0x22c12f
22c12d: xor ebx, ebx
22c12f: lea rcx, [rbx + 0x140]
22c136: mov byte ptr [rbx + 0x158], r14b
22c13d: lea r8, [rip + 0x37070c] ; b'TRA_30'
22c144: lea rdx, [rbp - 0x20]
22c148: call 0x3ff960
22c14d: lea rdx, [rbp - 0x20]
22c151: jmp 0x22e8d9
