235a10: mov r11, rsp
235a13: push rbp
235a14: push r14
235a16: lea rbp, [r11 - 0x5f]
235a1a: sub rsp, 0xa8
235a21: mov rax, qword ptr [rip + 0x42efb0] ; b'2\xa2\xdf-\x99+'
235a28: xor rax, rsp
235a2b: mov qword ptr [rbp + 0x27], rax
235a2f: mov r9, qword ptr [rcx + 0x18]
235a33: mov r14, rcx
235a36: test r9, r9
235a39: je 0x235d31
235a3f: mov eax, dword ptr [r14 + 0x10]
235a43: cdq 
235a44: mov qword ptr [r11 + 0x18], rsi
235a48: mov esi, dword ptr [rcx + 0x410]
235a4e: mov qword ptr [r11 - 0x28], r15
235a52: lea r15, [r9 + 0x5c8]
235a59: mov r11d, dword ptr [rcx + 0xc]
235a5d: movzx ecx, byte ptr [rip + 0x369187] ; b' \x0f'
235a64: idiv ecx
235a66: movsx ecx, word ptr [r9 + 0xbbc]
235a6e: movsx r8d, ax
235a72: mov eax, r11d
235a75: imul r8d, ecx
235a79: cdq 
235a7a: movzx ecx, byte ptr [rip + 0x369169] ; b'  \x0f'
235a81: idiv ecx
235a83: add ax, r8w
235a87: movsx rax, ax
235a8b: test eax, eax
235a8d: js 0x235d21
235a93: cmp eax, dword ptr [r9 + 0xbb8]
235a9a: jge 0x235d21
235aa0: mov rcx, rax
235aa3: mov rax, qword ptr [r9 + 0xbb0]
235aaa: movzx ecx, word ptr [rax + rcx*2]
235aae: test word ptr [rip + 0x369133], cx ; b'\xff\x7f  \x0f'
235ab5: je 0x235d21
235abb: mov eax, dword ptr [r15 + 0xc0]
235ac2: lea rdx, [r14 + 0xc]
235ac6: movzx r8d, byte ptr [r14 + 0x28]
235acb: mov rcx, r9
235ace: mov qword ptr [rsp + 0xc8], rbx
235ad6: mov ebx, dword ptr [r15 + 0x78]
235ada: mov qword ptr [rsp + 0xd8], rdi
235ae2: mov edi, dword ptr [r15 + 0x80]
235ae9: mov qword ptr [rsp + 0xa0], r12
235af1: mov r12d, dword ptr [r15 + 0xc4]
235af8: mov qword ptr [rsp + 0x98], r13
235b00: mov r13d, dword ptr [r15 + 0x84]
235b07: sub r13d, dword ptr [r15 + 0x7c]
235b0b: add r13d, r12d
235b0e: mov dword ptr [rbp - 9], eax
235b11: mov dword ptr [rbp - 0x11], r11d
235b15: call 0x180c10
235b1a: mov ecx, dword ptr [r14 + 0x10]
235b1e: lea rdx, [rbp - 0x19]
235b22: sub ecx, dword ptr [r14 + 0x14]
235b26: add eax, ecx
235b28: lea rcx, [r14 + 0x1b8]
235b2f: mov dword ptr [rbp - 0xd], eax
235b32: call 0x411660
235b37: lea rdx, [rbp - 1]
235b3b: lea rcx, [r14 + 0x1b8]
235b42: call 0x411780
235b47: mov ecx, dword ptr [rbp + 3]
235b4a: xor eax, eax
235b4c: mov r8d, dword ptr [rbp - 0xd]
235b50: sub r8d, dword ptr [rbp - 0x15]
235b54: mov r11d, dword ptr [rbp - 0x11]
235b58: sub r11d, dword ptr [rbp - 0x19]
235b5c: mov dword ptr [rbp + 0x13], ecx
235b5f: lea r9d, [r8 + rcx]
235b63: mov qword ptr [rbp + 7], rax
235b67: mov rax, qword ptr [rbp - 1]
235b6b: mov ecx, dword ptr [rbp - 9]
235b6e: mov edx, ecx
235b70: sub edx, ebx
235b72: mov dword ptr [rbp + 0xf], eax
235b75: add edx, edi
235b77: mov dword ptr [rbp + 0x17], r11d
235b7b: mov dword ptr [rbp + 0x1b], r8d
235b7f: lea r10d, [r11 + rax]
235b83: mov dword ptr [rbp + 0x1f], r10d
235b87: mov dword ptr [rbp + 0x23], r9d
235b8b: cmp r11d, edx
235b8e: jge 0x235d01
235b94: cmp r10d, ecx
235b97: jl 0x235d01
235b9d: cmp r8d, r13d
235ba0: jge 0x235d01
235ba6: cmp r9d, r12d
235ba9: jl 0x235d01
235baf: cmp r11d, ecx
235bb2: cmovge ecx, r11d
235bb6: cmp edx, r10d
235bb9: cmovge edx, r10d
235bbd: cmp r8d, r12d
235bc0: cmovge r12d, r8d
235bc4: cmp r13d, r9d
235bc7: cmovge r13d, r9d
235bcb: cmp edx, ecx
235bcd: jle 0x235d01
235bd3: cmp r13d, r12d
235bd6: jle 0x235d01
235bdc: test esi, esi
235bde: je 0x235be8
235be0: or esi, dword ptr [rip + 0x36c75e] ; b'\x80'
235be6: jmp 0x235bf4
235be8: mov esi, dword ptr [rip + 0x36c75a] ; b''
235bee: and esi, 0xfffffff7
235bf1: or esi, 1
235bf4: lea rax, [rbp - 0x19]
235bf8: mov r8d, esi
235bfb: lea r9, [rbp - 0x11]
235bff: mov qword ptr [rsp + 0x20], rax
235c04: lea rdx, [rbp + 7]
235c08: mov rcx, r15
235c0b: call 0x29e1b0
235c10: mov r8d, esi
235c13: lea rdx, [rbp + 7]
235c17: mov rcx, r15
235c1a: call 0x29e190
235c1f: test eax, eax
235c21: je 0x235d01
235c27: cmp byte ptr [r14 + 0x414], 0
235c2f: je 0x235c70
235c31: mov rcx, qword ptr [r14 + 0x3f0]
235c38: call 0x3f6d50
235c3d: mov rbx, qword ptr [r14 + 0x3f0]
235c44: mov rcx, rbx
235c47: call 0x3f7890
235c4c: mov rcx, rbx
235c4f: mov edi, eax
235c51: call 0x3f78b0
235c56: movzx r9d, word ptr [rip + 0x38aa1a] ; b''
235c5e: lea rcx, [r14 + 0x1b8]
235c65: mov rdx, rax
235c68: mov r8d, edi
235c6b: call 0x4123c0
235c70: movzx eax, byte ptr [r14 + 0x415]
235c78: lea rdx, [r14 + 0x1b8]
235c7f: mov r9d, dword ptr [rbp - 0x15]
235c83: mov rcx, r15
235c86: mov r8d, dword ptr [rbp - 0x19]
235c8a: mov dword ptr [rsp + 0x28], eax
235c8e: mov dword ptr [rsp + 0x20], esi
235c92: call 0x29e260
235c97: mov r8d, dword ptr [rbp - 0xd]
235c9b: lea rax, [rbp + 0x17]
235c9f: mov edx, dword ptr [rbp - 0x11]
235ca2: xor r9d, r9d
235ca5: mov dword ptr [rsp + 0x38], esi
235ca9: mov rcx, r15
235cac: mov byte ptr [rsp + 0x30], 0
235cb1: mov qword ptr [rsp + 0x28], rax
235cb6: lea rax, [rbp - 0x19]
235cba: mov qword ptr [rsp + 0x20], rax
235cbf: call 0x29e4c0
235cc4: xor eax, eax
235cc6: lea r9, [rbp - 9]
235cca: xor r8d, r8d
235ccd: mov qword ptr [rbp - 9], rax
235cd1: mov edx, esi
235cd3: mov rcx, r15
235cd6: call 0x29ea40
235cdb: mov eax, dword ptr [rbp - 0x15]
235cde: lea rdx, [rbp + 7]
235ce2: mov r9d, dword ptr [rbp - 0xd]
235ce6: mov rcx, r15
235ce9: mov r8d, dword ptr [rbp - 0x11]
235ced: mov dword ptr [rsp + 0x30], esi
235cf1: mov dword ptr [rsp + 0x28], eax
235cf5: mov eax, dword ptr [rbp - 0x19]
235cf8: mov dword ptr [rsp + 0x20], eax
235cfc: call 0x29df60
235d01: mov r13, qword ptr [rsp + 0x98]
235d09: mov r12, qword ptr [rsp + 0xa0]
235d11: mov rdi, qword ptr [rsp + 0xd8]
235d19: mov rbx, qword ptr [rsp + 0xc8]
235d21: mov rsi, qword ptr [rsp + 0xd0]
235d29: mov r15, qword ptr [rsp + 0x90]
235d31: mov rcx, qword ptr [rbp + 0x27]
235d35: xor rcx, rsp
235d38: call 0x4f77a0
235d3d: add rsp, 0xa8
235d44: pop r14
235d46: pop rbp
235d47: ret 
