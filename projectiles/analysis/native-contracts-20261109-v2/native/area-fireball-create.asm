22f8e4: cmp byte ptr [rbx + 0x3f0], 0xff
22f8eb: mov qword ptr [rsp + 0xe8], r12
22f8f3: je 0x22fb8d
22f8f9: cmp word ptr [rbx + 0x3c0], r14w
22f901: je 0x22fb8d
22f907: movzx eax, byte ptr [rbx + 0x416]
22f90e: mov ecx, 0x3d0
22f913: mov byte ptr [rbp + 0x1f], al
22f916: mov byte ptr [rbp + 0x20], al
22f919: mov byte ptr [rbp + 0x21], al
22f91c: mov byte ptr [rbp + 0x22], al
22f91f: mov byte ptr [rbp + 0x23], al
22f922: mov byte ptr [rbp + 0x24], al
22f925: mov byte ptr [rbp + 0x25], al
22f928: call 0x4f7a88
22f92d: mov r10, rax
22f930: test rax, rax
22f933: je 0x22fb86
22f939: movsx ecx, word ptr [rbx + 0x3c6]
22f940: lea rdx, [rbx + 0xf8]
22f947: mov eax, dword ptr [rbx + 0x16c]
22f94d: lea r9, [rbp + 0x1f]
22f951: movsx r8d, word ptr [rbx + 0x3cc]
22f959: mov qword ptr [rsp + 0x58], rdx
22f95e: movzx edx, byte ptr [rbx + 0x3f0]
22f965: imul r8d, ecx
22f969: movzx ecx, word ptr [rbx + 0x428]
22f970: mov word ptr [rsp + 0x50], cx
22f975: mov ecx, dword ptr [rbx + 0x424]
22f97b: mov dword ptr [rsp + 0x48], ecx
22f97f: mov rcx, r10
22f982: mov word ptr [rsp + 0x40], r8w
22f988: movzx r8d, word ptr [rbx + 0x60]
22f98d: mov dword ptr [rsp + 0x38], eax
22f991: movzx eax, byte ptr [rip + 0x37d4c9] ; b'\x01\x02\x01\x02'
22f998: mov byte ptr [rsp + 0x30], al
22f99c: movzx eax, byte ptr [rbx + 0x64]
22f9a0: mov byte ptr [rsp + 0x28], al
22f9a4: movzx eax, word ptr [rbx + 0x3c0]
22f9ab: mov word ptr [rsp + 0x20], ax
22f9b0: call 0x1e8a20
22f9b5: mov r13, rax
