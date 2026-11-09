228e60: push rbx
228e62: sub rsp, 0x50
228e66: mov rax, qword ptr [rip + 0x43e6db] ; b''
228e6d: mov rbx, rcx
228e70: mov rcx, qword ptr [rax + 0x1090]
228e77: cmp dword ptr [rcx + 0x9690], 0
228e7e: je 0x228e8f
228e80: mov eax, dword ptr [rbx + 0x48]
228e83: cmp dword ptr [rcx + 0x9694], eax
228e89: jne 0x2290ee
228e8f: cmp dword ptr [rbx + 0x3d0], 0
228e96: je 0x2290ee
228e9c: movzx eax, word ptr [rbx + 0x3fc]
228ea3: test ax, ax
228ea6: jle 0x228eb8
228ea8: dec ax
228eab: mov word ptr [rbx + 0x3fc], ax
228eb2: add rsp, 0x50
228eb6: pop rbx
228eb7: ret 
228eb8: cmp word ptr [rbx + 0x3b8], 0
228ec0: jle 0x229090
228ec6: mov rcx, qword ptr [rbx + 0x3c8]
228ecd: lea rdx, [rsp + 0x68]
228ed2: mov eax, dword ptr [rbx + 0x48]
228ed5: mov dword ptr [rcx + 0x70], eax
228ed8: mov ecx, dword ptr [rbx + 0x6c]
228edb: call 0x276700
228ee0: test al, al
228ee2: je 0x228ef6
228ee4: mov rax, qword ptr [rbx]
228ee7: mov rcx, rbx
228eea: call qword ptr [rax + 0xe0]
228ef0: add rsp, 0x50
228ef4: pop rbx
228ef5: ret 
228ef6: mov rcx, qword ptr [rsp + 0x68]
228efb: mov rax, qword ptr [rcx + 0x18]
228eff: cmp qword ptr [rbx + 0x18], rax
228f03: jne 0x228ee4
228f05: mov rax, qword ptr [rcx]
228f08: call qword ptr [rax + 0x40]
228f0b: movzx r9d, byte ptr [rip + 0x375ccf] ; b'\x0e\x10'
228f13: lea r8, [rbx + 0x3d8]
228f1a: mov ecx, dword ptr [rbx + 0x3f8]
228f20: shl r9w, 5
228f25: cmp al, byte ptr [rip + 0x3707fc] ; b''
228f2b: lea rax, [rip + 0x3707fe] ; b'\xff\x05\x05\x05\x05\x05\x05\x05\x05\x05\xff\x05\x05\xff\x05\x05\xff\x05\x05\x05\x05\x05\x05\x05\xff\x05\xff\x05\xff\xff\xff\x05\x08\x01\x03'
228f32: jne 0x228f68
228f34: mov edx, dword ptr [rbx + 0x6c]
228f37: mov dword ptr [rsp + 0x48], 0
228f3f: mov byte ptr [rsp + 0x40], 0
228f44: mov dword ptr [rsp + 0x38], 0
228f4c: mov dword ptr [rsp + 0x30], 1
228f54: mov dword ptr [rsp + 0x28], ecx
228f58: mov rcx, qword ptr [rbx + 0x18]
228f5c: mov qword ptr [rsp + 0x20], rax
228f61: call 0x180de0
228f66: jmp 0x228f90
228f68: mov rdx, qword ptr [rsp + 0x68]
228f6d: mov byte ptr [rsp + 0x38], 0
228f72: mov dword ptr [rsp + 0x30], 1
228f7a: mov dword ptr [rsp + 0x28], ecx
228f7e: mov rdx, qword ptr [rdx + 0xc]
228f82: mov rcx, qword ptr [rbx + 0x18]
228f86: mov qword ptr [rsp + 0x20], rax
228f8b: call 0x181720
228f90: mov ecx, eax
228f92: cmp eax, -1
228f95: je 0x229090
228f9b: cmp dword ptr [rbx + 0x3bc], 0
228fa2: jne 0x228faa
228fa4: mov eax, dword ptr [rbx + 0x6c]
228fa7: mov dword ptr [rbx + 0x68], eax
228faa: lea rdx, [rsp + 0x68]
228faf: mov dword ptr [rbx + 0x6c], ecx
228fb2: call 0x276700
228fb7: test al, al
228fb9: jne 0x2290ee
228fbf: mov rax, qword ptr [rsp + 0x68]
228fc4: mov qword ptr [rsp + 0x60], rdi
228fc9: mov rdi, qword ptr [rbx + 0x80]
228fd0: mov rcx, qword ptr [rax + 0xc]
228fd4: mov qword ptr [rbx + 0xf8], rcx
228fdb: test rdi, rdi
228fde: je 0x22900f
228fe0: mov rcx, qword ptr [rdi + 0x10]
228fe4: mov rdi, qword ptr [rdi]
228fe7: mov rax, qword ptr [rcx]
228fea: call qword ptr [rax + 8]
228fed: mov rdx, qword ptr [rbx + 0x3c8]
228ff4: movzx ecx, word ptr [rdx + 0x60]
228ff8: mov dword ptr [rax + 0xa0], ecx
228ffe: lea rcx, [rdx + 0x78]
229002: mov rdx, rax
229005: call 0x4075c0
22900a: test rdi, rdi
22900d: jne 0x228fe0
22900f: movzx eax, word ptr [rbx + 0x3f4]
229016: mov rcx, qword ptr [rbx + 0x3c8]
22901d: mov r9d, dword ptr [rbx + 0x6c]
229021: mov r8d, dword ptr [rbx + 0x68]
229025: mov rdx, qword ptr [rbx + 0x18]
229029: mov word ptr [rsp + 0x30], ax
22902e: mov eax, dword ptr [rbx + 0x3f0]
229034: mov dword ptr [rsp + 0x28], eax
229038: mov rax, qword ptr [rbx + 0xf8]
22903f: mov dword ptr [rbx + 0x3d0], 0
229049: mov r10, qword ptr [rcx]
22904c: mov qword ptr [rsp + 0x20], rax
229051: call qword ptr [r10 + 0xd0]
229058: movzx ecx, word ptr [rbx + 0x3c0]
22905f: xor edx, edx
229061: inc cx
229064: call 0x22bf00
229069: dec word ptr [rbx + 0x3b8]
229070: mov rdi, qword ptr [rsp + 0x60]
229075: mov qword ptr [rbx + 0x3c8], rax
22907c: movzx eax, word ptr [rbx + 0x3ba]
229083: mov word ptr [rbx + 0x3fc], ax
22908a: add rsp, 0x50
22908e: pop rbx
22908f: ret 
