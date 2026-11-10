22e7b4: mov ecx, 0x328
22e7b9: call 0x4f7a88
22e7be: mov rbx, rax
22e7c1: test rax, rax
22e7c4: je 0x22e817
22e7c6: lea rdx, [rip + 0x36e243] ; b'EFF_P78'
22e7cd: lea rcx, [rbp - 0x10]
22e7d1: call 0x3fd6b0
22e7d6: lea rdx, [rip + 0x36e23b] ; b'SPHOLYMT'
22e7dd: lea rcx, [rbp + 8]
22e7e1: call 0x3fd6b0
22e7e6: movzx ecx, byte ptr [rip + 0x36ff67] ; b'\x0f<\x05\x18\xe0\xa5\x01'
22e7ed: lea r8, [rbp - 0x10]
22e7f1: add cx, cx
22e7f4: lea rdx, [rbp + 8]
22e7f8: mov word ptr [rsp + 0x28], cx
22e7fd: mov r9b, 0xff
22e800: mov rcx, rbx
22e803: mov dword ptr [rsp + 0x20], r14d
22e808: call 0x227cd0
22e80d: mov rbx, rax
22e810: mov edi, 0x6000
22e815: jmp 0x22e819
22e817: xor ebx, ebx
22e819: bt edi, 0xe
22e81d: jae 0x22e82c
22e81f: btr edi, 0xe
22e823: lea rcx, [rbp + 8]
22e827: call 0x3fd740
22e82c: bt edi, 0xd
22e830: jae 0x22e8be
22e836: lea rcx, [rbp - 0x10]
22e83a: jmp 0x22e8b9
