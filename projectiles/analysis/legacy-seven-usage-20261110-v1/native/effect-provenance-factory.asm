14c930: test rdx, rdx
14c933: je 0x14ca6d
14c939: push rdi
14c93a: push r12
14c93c: push r13
14c93e: push r14
14c940: sub rsp, 0x28
14c944: mov qword ptr [rsp + 0x58], rbp
14c949: mov r13d, r8d
14c94c: mov ebp, dword ptr [rsp + 0x80]
14c953: mov r12d, r9d
14c956: mov qword ptr [rsp + 0x60], rsi
14c95b: mov rdi, rdx
14c95e: mov esi, dword ptr [rdx + 0x110]
14c964: mov r14, rcx
14c967: mov qword ptr [rsp + 0x20], r15
14c96c: mov r15, qword ptr [rsp + 0x70]
14c971: mov rax, qword ptr [r15 + 0xc]
14c975: mov qword ptr [rdx + 0x80], rax
14c97c: mov eax, dword ptr [r15 + 0x48]
14c980: mov dword ptr [rdx + 0x110], eax
14c986: mov dword ptr [rdx + 0x150], eax
14c98c: mov r8, qword ptr [rcx + 8]
14c990: test r8, r8
14c993: je 0x14c9c7
14c995: mov r9d, dword ptr [rdx + 0xa0]
14c99c: nop dword ptr [rax]
14c9a0: mov rdx, qword ptr [r8 + 0x10]
14c9a4: mov r8, qword ptr [r8]
14c9a7: mov rcx, qword ptr [rdx + 8]
14c9ab: movsx eax, word ptr [rcx + 0x60]
14c9af: cmp eax, r9d
14c9b2: jne 0x14c9b9
14c9b4: cmp esi, dword ptr [rcx + 0x6c]
14c9b7: je 0x14c9e8
14c9b9: cmp dword ptr [rdx + 0x14], ebp
14c9bc: je 0x14ca53
14c9c2: test r8, r8
14c9c5: jne 0x14c9a0
14c9c7: mov ecx, 0x20
14c9cc: mov qword ptr [rsp + 0x50], rbx
14c9d1: call 0x4f7a88
14c9d6: mov rbx, rax
14c9d9: test rax, rax
14c9dc: je 0x14c9f2
14c9de: mov qword ptr [rax + 8], 0
14c9e6: jmp 0x14c9f4
14c9e8: mov rdx, rdi
14c9eb: call 0x22a270
14c9f0: jmp 0x14ca53
14c9f2: xor ebx, ebx
14c9f4: mov eax, dword ptr [rsp + 0x78]
14c9f8: mov rdx, r15
14c9fb: mov dword ptr [rbx + 0x10], eax
14c9fe: mov eax, dword ptr [rsp + 0x88]
14ca05: mov dword ptr [rbx + 0x18], eax
14ca08: mov eax, dword ptr [rsp + 0x90]
14ca0f: mov dword ptr [rbx + 0x1c], eax
14ca12: mov dword ptr [rbx], r13d
14ca15: mov dword ptr [rbx + 4], r12d
14ca19: mov dword ptr [rbx + 0x14], ebp
14ca1c: movzx ecx, word ptr [rdi + 0xa0]
14ca23: inc cx
14ca26: call 0x22bf00
14ca2b: mov qword ptr [rbx + 8], rax
14ca2f: test rax, rax
14ca32: je 0x14ca43
14ca34: mov dword ptr [rax + 0x6c], esi
14ca37: mov rdx, rdi
14ca3a: mov rcx, qword ptr [rbx + 8]
14ca3e: call 0x22a270
14ca43: mov rdx, rbx
14ca46: mov rcx, r14
14ca49: call 0x4075c0
14ca4e: mov rbx, qword ptr [rsp + 0x50]
14ca53: mov rsi, qword ptr [rsp + 0x60]
14ca58: mov rbp, qword ptr [rsp + 0x58]
14ca5d: mov r15, qword ptr [rsp + 0x20]
14ca62: add rsp, 0x28
14ca66: pop r14
14ca68: pop r13
14ca6a: pop r12
14ca6c: pop rdi
14ca6d: ret 
