3c0d7c: lea rcx, [rbp + 0x28]
3c0d80: call 0x3ff960
3c0d85: mov rdx, qword ptr [rbp + 0x28]
3c0d89: lea rcx, [rbp + 0x48]
3c0d8d: mov r12d, 1
3c0d93: mov edi, r12d
3c0d96: call 0x253990
3c0d9b: lea rcx, [rbp + 0x48]
3c0d9f: call 0x2547c0
3c0da4: test rax, rax
3c0da7: je 0x3c0dbb
3c0da9: mov edi, dword ptr [rax + 0x78]
3c0dac: mov edx, r12d
3c0daf: mov r8, qword ptr [rax]
3c0db2: and edi, r12d
3c0db5: mov rcx, rax
3c0db8: call qword ptr [r8]
3c0dbb: mov edx, 0xd7
3c0dc0: lea rcx, [rbp + 0x58]
3c0dc4: call 0x1ce0d0
3c0dc9: movzx eax, word ptr [rip + 0x1d0958] ; b''
3c0dd0: lea r9, [rbp - 0x30]
3c0dd4: mov word ptr [rbp + 0x64], ax
3c0dd8: lea rdx, [rbp - 0x28]
3c0ddc: xor eax, eax
3c0dde: mov dword ptr [rbp + 0x66], 5
3c0de5: test edi, edi
3c0de7: mov qword ptr [rbp - 0x30], 0xffffffffffffffff
3c0def: mov r8d, 0xffffffff
3c0df5: mov qword ptr [rbp - 0x28], 0xffffffffffffffff
3c0dfd: setne al
3c0e00: mov dword ptr [rsp + 0x20], 0xffffffff
3c0e08: lea rcx, [rbp + 0x58]
3c0e0c: mov dword ptr [rbp + 0x60], eax
3c0e0f: call 0x1de3d0
3c0e14: lea r8, [rbp + 0x28]
3c0e18: mov r15, rax
3c0e1b: lea rdx, [rbp + 0x40]
3c0e1f: lea rcx, [rax + 0x30]
3c0e23: call 0x3ff880
3c0e28: mov rcx, qword ptr [r14 + 0xc]
3c0e2c: mov qword ptr [r15 + 0x80], rcx
