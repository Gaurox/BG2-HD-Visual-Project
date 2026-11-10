1cab18: movzx edi, word ptr [rcx + 0x20]
1cab1c: mov qword ptr [rsp + 0x78], rax
1cab21: shr rax, 0x20
1cab25: inc eax
1cab27: mov dword ptr [rsp + 0x7c], eax
1cab2b: mov eax, 0xfff
1cab30: and di, ax
1cab33: mov eax, 0x1000
1cab38: add di, ax
1cab3b: lea ecx, [rdi + 1]
1cab3e: call 0x22bf00
