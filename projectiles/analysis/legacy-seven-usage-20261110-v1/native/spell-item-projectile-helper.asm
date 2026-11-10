353e90: push rbx
353e92: push rbp
353e93: push rsi
353e94: push rdi
353e95: push r13
353e97: push r15
353e99: sub rsp, 0x78
353e9d: mov rax, qword ptr [rip + 0x310b34] ; b'2\xa2\xdf-\x99+'
353ea4: xor rax, rsp
353ea7: mov qword ptr [rsp + 0x68], rax
353eac: cmp word ptr [rdx], 1
353eb0: mov r13d, r8d
353eb3: mov r15, rdx
353eb6: mov rbp, rcx
353eb9: jne 0x353f78
353ebf: mov ecx, 0x10
353ec4: call 0x4f7a88
353ec9: xor edi, edi
353ecb: test rax, rax
353ece: je 0x353ee1
353ed0: mov rdx, qword ptr [r15 + 6]
353ed4: mov rcx, rax
353ed7: call 0x164f90
353edc: mov rbx, rax
353edf: jmp 0x353ee4
353ee1: mov rbx, rdi
353ee4: xor edx, edx
353ee6: mov rcx, rbx
353ee9: call 0x24ed80
353eee: mov rcx, rbx
353ef1: mov rbp, rax
353ef4: mov esi, edi
353ef6: call 0x24edd0
353efb: test eax, eax
353efd: jle 0x353f2e
353eff: nop 
353f00: mov edx, esi
353f02: mov rcx, rbx
353f05: call 0x24ed80
353f0a: movzx ecx, word ptr [rax + 0x10]
353f0e: cmp ecx, r13d
353f11: jg 0x353f2e
353f13: mov edx, esi
353f15: mov rcx, rbx
353f18: call 0x24ed80
353f1d: mov rcx, rbx
353f20: mov rbp, rax
353f23: inc esi
353f25: call 0x24edd0
353f2a: cmp esi, eax
353f2c: jl 0x353f00
353f2e: mov esi, edi
353f30: test rbp, rbp
353f33: je 0x353f39
353f35: movzx esi, word ptr [rbp + 0x26]
353f39: test rbx, rbx
353f3c: je 0x3540d0
353f42: cmp qword ptr [rbx], rdi
353f45: je 0x353f63
353f47: lea rcx, [rbx + 8]
353f4b: lea rdx, [rip + 0x29785b] ; b''
353f52: call 0x3ffb60
353f57: test eax, eax
353f59: je 0x353f63
353f5b: mov rcx, qword ptr [rbx]
353f5e: call 0x1e1e0
353f63: mov edx, 0x10
353f68: mov qword ptr [rbx], rdi
353f6b: mov rcx, rbx
353f6e: call 0x45e690
353f73: jmp 0x3540d0
353f78: mov qword ptr [rsp + 0xc8], r12
353f80: mov ecx, 0xa8
353f85: mov qword ptr [rsp + 0x70], r14
353f8a: call 0x4f7a88
353f8f: xor edi, edi
353f91: test rax, rax
353f94: je 0x353fbb
353f96: mov rdx, qword ptr [r15 + 6]
353f9a: xor r9d, r9d
353f9d: mov dword ptr [rsp + 0x30], edi
353fa1: xor r8d, r8d
353fa4: mov word ptr [rsp + 0x28], di
353fa9: mov rcx, rax
353fac: mov word ptr [rsp + 0x20], di
353fb1: call 0x1fa9b0
353fb6: mov r14, rax
353fb9: jmp 0x353fbe
353fbb: mov r14, rdi
353fbe: movsx edx, word ptr [r15 + 4]
353fc3: mov rcx, r14
353fc6: call 0x1fb330
353fcb: mov r12, rax
353fce: mov ecx, 1
353fd3: test rax, rax
353fd6: jne 0x353fdf
353fd8: mov esi, edi
353fda: jmp 0x3540b4
353fdf: movzx esi, word ptr [rax + 0x2a]
353fe3: cmp esi, ecx
353fe5: jne 0x3540b4
353feb: cmp di, word ptr [rax + 0x1e]
353fef: jae 0x3540b4
353ff5: nop word ptr [rax + rax]
354000: movsx edx, word ptr [r15 + 4]
354005: mov r9, rbp
354008: mov r8d, edi
35400b: mov rcx, r14
35400e: call 0x1fb410
354013: mov rbx, rax
354016: cmp dword ptr [rax + 0x10], 0x94
35401d: jne 0x354092
35401f: lea rcx, [rsp + 0x46]
354024: call 0x3ff870
354029: mov eax, 0xffffffff
35402e: mov dword ptr [rsp + 0x40], 0xffffffff
354036: lea r8, [rip + 0x297770] ; b''
35403d: mov word ptr [rsp + 0x44], ax
354042: lea rdx, [rsp + 0x58]
354047: lea rcx, [rsp + 0x46]
35404c: call 0x3ff960
354051: mov eax, 1
354056: mov dword ptr [rsp + 0x50], 0xffffffff
35405e: lea r8, [rbx + 0x30]
354062: mov word ptr [rsp + 0x40], ax
354067: lea rdx, [rsp + 0x60]
35406c: lea rcx, [rsp + 0x46]
354071: call 0x3ff880
354076: cmp dword ptr [rbx + 0x20], 0
35407a: lea rdx, [rsp + 0x40]
35407f: mov rcx, rbp
354082: mov r8d, r13d
354085: jne 0x35408b
354087: mov r8d, dword ptr [rbx + 0x1c]
35408b: call 0x353e90
354090: mov esi, eax
354092: mov rax, qword ptr [rbx]
354095: mov edx, 1
35409a: mov rcx, rbx
35409d: call qword ptr [rax]
35409f: movzx eax, word ptr [r12 + 0x1e]
3540a5: inc edi
3540a7: cmp edi, eax
3540a9: jl 0x354000
3540af: mov ecx, 1
3540b4: mov r12, qword ptr [rsp + 0xc8]
3540bc: test r14, r14
3540bf: je 0x3540cb
3540c1: mov rax, qword ptr [r14]
3540c4: mov edx, ecx
3540c6: mov rcx, r14
3540c9: call qword ptr [rax]
3540cb: mov r14, qword ptr [rsp + 0x70]
3540d0: mov eax, esi
3540d2: mov rcx, qword ptr [rsp + 0x68]
3540d7: xor rcx, rsp
3540da: call 0x4f77a0
3540df: .byte 0x48
